"""Opt-in unprivileged loopback HTTPS tests; never production/deploy/real keys."""
from __future__ import annotations

import hashlib
import http.client
import io
import json
import os
import shutil
import socket
import ssl
import subprocess
import tarfile
import time
import unittest

from test_update_origin import ORIGIN, ROOT, SignedOriginFixture
from homecloud_update_origin.publisher import Publisher
from homecloud_update_origin.model import validate_plan


HOST = "updates.homecloud.test"


class LoopbackHTTPS(http.client.HTTPSConnection):
    """Fixed local transport, actual TLS hostname verification and SNI intact."""
    def connect(self):
        transport = socket.create_connection(("127.0.0.1", self.port), timeout=self.timeout)
        try:
            self.sock = self._context.wrap_socket(transport, server_hostname=self.host)
        except BaseException:
            transport.close()
            raise


def free_port():
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        return candidate.getsockname()[1]


@unittest.skipUnless(os.environ.get("CI") == "true" and os.environ.get("HOMECLOUD_ORIGIN_NGINX_INTEGRATION") == "1",
                     "HTTPS fixtures run only on the isolated CI runner")
class NginxOriginTest(SignedOriginFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.addCleanup(self.temporary.cleanup)
        self.nginx = None
        self.output = None
        self.assertNotEqual(os.geteuid(), 0, "Regression must run unprivileged, not hide the access-log bug")
        self.assertIsNotNone(shutil.which("nginx"))
        certificate, tls_key = self.root / "tls.pem", self.root / "tls-key.pem"
        subprocess.run(["/usr/bin/openssl", "req", "-x509", "-nodes", "-newkey", "rsa:2048", "-days", "1",
                        "-subj", "/CN=" + HOST, "-addext", "subjectAltName=DNS:" + HOST,
                        "-keyout", str(tls_key), "-out", str(certificate)], check=True, capture_output=True, timeout=30)
        tls_key.chmod(0o600)
        self.context = ssl.create_default_context(cafile=str(certificate))
        # A valid synthetic gzip/tar, not an installable appliance release.
        archive = io.BytesIO()
        with tarfile.open(fileobj=archive, mode="w:gz") as target:
            body = b"DISPOSABLE CI FIXTURE: NOT AN APPLIANCE RELEASE\n"
            member = tarfile.TarInfo("fixture.txt")
            member.size = len(body)
            target.addfile(member, io.BytesIO(body))
        self.release_data = self.release(payload=archive.getvalue())
        self.publication = self.root / "publication"
        self.publish(self.release_data, self.publication)
        self.debian12_data = self.release(sequence=2, payload=archive.getvalue(), os_version="12")
        self.publish(self.debian12_data, self.publication)
        (self.publication / "healthz").write_bytes(b"ok\n")
        self.bundle_path = "/releases/" + self.release_data[0]["homecloud"]["bundle_sha256"] + ".tar.gz"
        self.metadata_path = "/v1/stable/debian-13-arm64.json"
        # Trust root is a separate ephemeral fixture key, never a real root.
        trust_private, self.trust_public = self.keypair("trust")
        self.trust_data = self.trust_release(1, [self.key_entry(self.public_key)],
                                             private_key=trust_private, root_public=self.trust_public)
        Publisher(self.publication, self.public_key, ORIGIN).publish_trust(
            channel="stable", metadata_path=self.trust_data[1], signature_path=self.trust_data[2],
            root_public_key=self.trust_public)
        self.http_port, self.https_port = free_port(), free_port()
        while self.https_port == self.http_port:
            self.https_port = free_port()
        rendered = (ROOT / "deploy/nginx-site.conf.in").read_text()
        rendered = rendered.replace("__HOSTNAME__", HOST).replace("__CERTIFICATE__", str(certificate))
        rendered = rendered.replace("__CERTIFICATE_KEY__", str(tls_key))
        rendered = rendered.replace("/srv/homecloud-updates", str(self.publication))
        # Only test transport addresses/paths differ. Preserve production TLS,
        # methods, regexes, symlink policy, response and cache directives.
        rendered = rendered.replace("listen 80;", f"listen 127.0.0.1:{self.http_port};")
        rendered = rendered.replace("    listen [::]:80;", "")
        rendered = rendered.replace("listen 443 ssl http2;", f"listen 127.0.0.1:{self.https_port} ssl http2;")
        rendered = rendered.replace("    listen [::]:443 ssl http2;", "")
        self.config = self.root / "nginx.conf"
        temporary_paths = "".join(f"{name}_temp_path {self.root}/{name};\n"
                                  for name in ("client_body", "proxy", "fastcgi", "uwsgi", "scgi"))
        self.config.write_text(f"pid {self.root}/nginx.pid;\nerror_log stderr notice;\nevents {{}}\nhttp {{\n"
                               f"access_log {self.root}/access.log;\n{temporary_paths}{rendered}\n}}\n")
        command = ["nginx", "-e", "stderr", "-p", str(self.root) + "/", "-c", str(self.config)]
        subprocess.run(command + ["-t"], check=True, capture_output=True, timeout=10)
        self.output = (self.root / "process.log").open("wb")
        self.addCleanup(self.output.close)
        self.nginx = subprocess.Popen(command + ["-g", "daemon off;"], stdout=self.output, stderr=subprocess.STDOUT)
        self.addCleanup(self.stop_nginx)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if self.nginx.poll() is not None:
                self.fail("Temporary Nginx exited; no system service was touched")
            try:
                if self.request("/healthz")[0] == 200:
                    return
            except (OSError, http.client.HTTPException):
                pass
            time.sleep(.05)
        self.fail("Temporary HTTPS origin did not become ready")

    def stop_nginx(self):
        if self.nginx is not None and self.nginx.poll() is None:
            self.nginx.terminate()
            try:
                self.nginx.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.nginx.kill()
                self.nginx.wait(timeout=5)

    def tearDown(self):
        self.stop_nginx()
        super().tearDown()

    def request(self, path, method="GET", headers=None, context=None, host=HOST):
        client = LoopbackHTTPS(host, self.https_port, context=context or self.context, timeout=3)
        try:
            client.request(method, path, headers=headers or {})
            response = client.getresponse()
            result = {}
            for key, value in response.getheaders():
                key = key.lower()
                result[key] = result[key] + ", " + value if key in result else value
            return response.status, result, response.read()
        finally:
            client.close()

    def security_headers(self, headers):
        self.assertEqual(headers["x-content-type-options"], "nosniff")
        self.assertEqual(headers["referrer-policy"], "no-referrer")
        self.assertIn("default-src 'none'", headers["content-security-policy"])
        self.assertEqual(headers["strict-transport-security"], "max-age=31536000")
        self.assertNotRegex(headers["server"], r"nginx/\d")

    def no_store(self, headers):
        # Error filtering may repeat the same header, but never permit mixed
        # no-store/immutable directives hidden by dict(last-header-wins).
        self.assertEqual({value.strip() for value in headers["cache-control"].split(",")}, {"no-store"})

    def verify_signed_response(self, path, payload, signature, public):
        downloaded = self.root / "downloaded.json"
        detached = self.root / "downloaded.sig"
        status, headers, body = self.request(path)
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(headers["content-type"], "application/octet-stream")
        self.assertEqual(body, payload.read_bytes())
        self.security_headers(headers)
        downloaded.write_bytes(body)
        status, headers, body = self.request(path + ".sig")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(body, signature.read_bytes())
        detached.write_bytes(body)
        subprocess.run(["/usr/bin/openssl", "dgst", "-sha256", "-verify", str(public), "-signature",
                        str(detached), str(downloaded)], check=True, capture_output=True, timeout=10)

    def test_health_get_head_and_missing_health(self):
        status, headers, body = self.request("/healthz")
        self.assertEqual((status, body), (200, b"ok\n"))
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(headers["content-type"], "text/plain")
        self.security_headers(headers)
        self.assertEqual(self.request("/healthz", "HEAD")[2], b"")
        (self.publication / "healthz").unlink()
        status, headers, _ = self.request("/healthz")
        self.assertEqual(status, 503)
        self.assertEqual(headers["cache-control"], "no-store")
        self.security_headers(headers)

    def test_signed_plan_and_trust_bytes_are_not_transformed_or_cached(self):
        self.verify_signed_response(self.metadata_path, self.release_data[1], self.release_data[2], self.public_key)
        self.verify_signed_response("/v1/stable/debian-12-arm64.json", self.debian12_data[1], self.debian12_data[2], self.public_key)
        self.verify_signed_response("/v1/stable/trust.json", self.trust_data[1], self.trust_data[2], self.trust_public)
        status, _, body = self.request(self.metadata_path)
        self.assertEqual(validate_plan(json.loads(body), ORIGIN), self.release_data[0])
        self.assertEqual(self.request(self.metadata_path, "HEAD")[2], b"")
        Publisher(self.publication, self.public_key, ORIGIN).publish(
            channel="a" * 32, plan_path=self.release_data[1], signature_path=self.release_data[2], bundle_path=self.release_data[3])
        self.assertEqual(self.request("/v1/" + "a" * 32 + "/debian-13-arm64.json")[0], 200)

    def test_immutable_artifact_hash_size_head_etag_and_single_range(self):
        status, headers, body = self.request(self.bundle_path)
        self.assertEqual(status, 200)
        target = self.release_data[0]["homecloud"]
        self.assertEqual(hashlib.sha256(body).hexdigest(), target["bundle_sha256"])
        self.assertEqual(len(body), target["bundle_size"])
        self.assertEqual(headers["content-type"], "application/gzip")
        self.assertEqual(headers["cache-control"], "public, max-age=31536000, immutable")
        self.security_headers(headers)
        self.assertEqual(self.request(self.bundle_path, "HEAD")[2], b"")
        status, headers, subset = self.request(self.bundle_path, headers={"Range": "bytes=0-3"})
        self.assertEqual((status, subset), (206, body[:4]))
        self.no_store(headers)
        status, headers, empty = self.request(self.bundle_path, headers={"If-None-Match": self.request(self.bundle_path)[1]["etag"]})
        self.assertEqual((status, empty), (304, b""))
        self.assertIn("immutable", headers["cache-control"])
        self.assertEqual(self.request(self.metadata_path, headers={"Range": "bytes=0-3"})[0], 200)

    def test_missing_objects_and_denied_methods_are_never_immutable(self):
        for path in ("/releases/" + "f" * 64 + ".tar.gz", "/v1/absent/debian-12-arm64.json", "/not-public"):
            with self.subTest(path=path):
                status, headers, _ = self.request(path)
                self.assertEqual(status, 404)
                self.assertEqual(headers["cache-control"], "no-store")
                self.security_headers(headers)
        for path in ("/healthz", self.metadata_path, self.bundle_path):
            for method in ("POST", "PUT", "DELETE", "OPTIONS"):
                with self.subTest(path=path, method=method):
                    status, headers, _ = self.request(path, method)
                    self.assertEqual(status, 403)
                    self.assertEqual(headers["cache-control"], "no-store")
                    self.security_headers(headers)
        status, headers, _ = self.request(self.bundle_path, headers={"Range": "bytes=999999999-"})
        self.assertEqual(status, 416)
        self.no_store(headers)
        status, headers, _ = self.request(self.bundle_path, headers={"If-Match": '"not-the-etag"'})
        self.assertEqual(status, 412)
        self.no_store(headers)

    def test_incomplete_pair_is_not_cacheable_and_exact_retry_recovers_over_https(self):
        path = self.publication / (self.metadata_path.lstrip("/") + ".sig")
        path.unlink()  # Only disposable fixture state is modified.
        status, headers, _ = self.request(self.metadata_path + ".sig")
        self.assertEqual(status, 404)
        self.no_store(headers)
        self.assertEqual(self.request(self.metadata_path)[0], 200)

        self.publish(self.release_data, self.publication)
        self.verify_signed_response(self.metadata_path, self.release_data[1],
                                    self.release_data[2], self.public_key)

    def test_allowlist_traversal_symlinks_and_private_paths(self):
        marker = b"PRIVATE TEST MARKER: MUST NOT BE SERVED"
        outside = self.root / "outside"
        outside.write_bytes(marker)
        symlink = self.publication / "releases" / ("b" * 64 + ".tar.gz")
        symlink.symlink_to(outside)
        long_channel = self.publication / "v1" / ("a" * 33)
        long_channel.mkdir()
        (long_channel / "debian-13-arm64.json").write_bytes(marker)
        for path in ("/.publish.lock", "/plans/", "/.audit/promotion.jsonl", "/../outside", "/%2e%2e/outside",
                     "/v1/stable/../../outside", "/releases/not-a-digest.tar.gz", "/v1/stable/debian-14-arm64.json",
                     "/v1/" + "a" * 33 + "/debian-13-arm64.json", "/releases/" + symlink.name):
            with self.subTest(path=path):
                status, headers, body = self.request(path)
                self.assertIn(status, (400, 403, 404))
                self.assertNotIn(marker, body)
                self.assertNotIn("immutable", headers.get("cache-control", ""))

    def test_http_redirect_and_tls_verification_remain_enforced(self):
        client = http.client.HTTPConnection("127.0.0.1", self.http_port, timeout=3)
        try:
            client.request("GET", self.metadata_path, headers={"Host": HOST})
            response = client.getresponse()
            self.assertEqual(response.status, 308)
            self.assertEqual(response.getheader("Location"), ORIGIN + self.metadata_path)
            response.read()
        finally:
            client.close()
        with self.assertRaises(ssl.SSLCertVerificationError):
            self.request("/healthz", host="wrong.homecloud.test")
        with self.assertRaises(ssl.SSLCertVerificationError):
            self.request("/healthz", context=ssl.create_default_context())
        for version in (ssl.TLSVersion.TLSv1_2, ssl.TLSVersion.TLSv1_3):
            with self.subTest(version=version):
                context = ssl.create_default_context(cafile=str(self.root / "tls.pem"))
                context.minimum_version = context.maximum_version = version
                self.assertEqual(self.request("/healthz", context=context)[0], 200)


if __name__ == "__main__":
    unittest.main()
