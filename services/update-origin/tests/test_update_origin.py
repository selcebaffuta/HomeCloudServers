from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from homecloud_update_origin.model import UpdateOriginError, build_plan, validate_plan
from homecloud_update_origin.publisher import Publisher
from homecloud_update_origin.cli import main


ORIGIN = "https://updates.homecloud.test"
COMMIT = "a" * 40


def timestamp(value):
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


class UpdateOriginTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.private_key = self.root / "private.pem"
        self.public_key = self.root / "public.pem"
        subprocess.run(
            [
                "/usr/bin/openssl", "genpkey", "-algorithm", "RSA",
                "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(self.private_key),
            ],
            check=True, capture_output=True,
        )
        subprocess.run(
            [
                "/usr/bin/openssl", "pkey", "-in", str(self.private_key),
                "-pubout", "-out", str(self.public_key),
            ],
            check=True, capture_output=True,
        )
        self.private_key.chmod(0o600)
        self.public_key.chmod(0o644)

    def tearDown(self):
        self.temporary.cleanup()

    def release(self, sequence=1, *, payload=b"bundle-one", packages=None):
        bundle = self.root / f"bundle-{sequence}-{hashlib.sha256(payload).hexdigest()[:8]}.tar.gz"
        bundle.write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        now = dt.datetime.now(dt.timezone.utc)
        plan = build_plan(
            origin=ORIGIN, sequence=sequence,
            published_at=timestamp(now - dt.timedelta(minutes=1)),
            expires_at=timestamp(now + dt.timedelta(days=7)),
            os_id="debian", os_version="13", architecture="arm64",
            commit=COMMIT, release_sequence=sequence,
            bundle_sha256=digest, bundle_size=len(payload),
            packages=packages or [], reboot_required=False,
        )
        plan_path = self.root / f"release-{sequence}-{digest[:8]}.json"
        signature = plan_path.with_name(plan_path.name + ".sig")
        plan_path.write_text(json.dumps(plan, sort_keys=True) + "\n", encoding="utf-8")
        subprocess.run(
            [
                "/usr/bin/openssl", "dgst", "-sha256", "-sign", str(self.private_key),
                "-out", str(signature), str(plan_path),
            ],
            check=True, capture_output=True,
        )
        return plan, plan_path, signature, bundle

    def publish(self, release, publication=None):
        _plan, plan_path, signature, bundle = release
        publisher = Publisher(
            publication or self.root / "publication", self.public_key, ORIGIN,
        )
        return publisher.publish(
            channel="stable", plan_path=plan_path,
            signature_path=signature, bundle_path=bundle,
        )

    def test_signed_release_is_published_content_addressed_and_idempotently(self):
        release = self.release()
        result = self.publish(release)
        publication = self.root / "publication"
        plan = release[0]
        endpoint = publication / result["metadata_path"]

        self.assertEqual(json.loads(endpoint.read_text()), plan)
        self.assertEqual(
            (publication / "releases" / f"{result['bundle_sha256']}.tar.gz").read_bytes(),
            b"bundle-one",
        )
        self.assertTrue(endpoint.with_name(endpoint.name + ".sig").is_file())
        self.assertEqual(self.publish(release), result)

    def test_invalid_signature_and_bundle_mismatch_are_rejected(self):
        release = self.release()
        release[2].write_bytes(b"not-a-signature")
        with self.assertRaisesRegex(UpdateOriginError, "Firma"):
            self.publish(release)

        release = self.release(sequence=2)
        release[3].write_bytes(b"changed-after-signing")
        with self.assertRaisesRegex(UpdateOriginError, "Bundle"):
            self.publish(release)

    def test_channel_sequence_is_strictly_monotonic(self):
        publication = self.root / "publication"
        self.publish(self.release(sequence=4), publication)
        with self.assertRaisesRegex(UpdateOriginError, "sequenza"):
            self.publish(self.release(sequence=3, payload=b"older"), publication)
        with self.assertRaisesRegex(UpdateOriginError, "sequenza"):
            self.publish(self.release(sequence=4, payload=b"changed"), publication)

    def test_endpoint_symlink_and_unprotected_key_fail_closed(self):
        publication = self.root / "publication"
        release = self.release()
        self.publish(release, publication)
        endpoint = publication / "v1/stable/debian-13-arm64.json"
        endpoint.unlink()
        endpoint.symlink_to("/etc/passwd")
        with self.assertRaises(UpdateOriginError):
            self.publish(self.release(sequence=2), publication)

        endpoint.unlink()
        self.public_key.chmod(0o666)
        with self.assertRaisesRegex(UpdateOriginError, "fiducia"):
            self.publish(self.release(sequence=2), self.root / "second-publication")

        unsafe_publication = self.root / "unsafe-publication"
        self.public_key.chmod(0o644)
        (unsafe_publication / "releases").mkdir(parents=True)
        unsafe_publication.chmod(0o755)
        (unsafe_publication / "releases").chmod(0o777)
        with self.assertRaisesRegex(UpdateOriginError, "Directory pubblica"):
            self.publish(self.release(sequence=3), unsafe_publication)

    def test_plan_contract_rejects_wrong_origin_and_unsorted_packages(self):
        plan, *_ = self.release(packages=[
            {"name": "openssl", "version": "3.5.1-1", "reason": "security"},
        ])
        plan["homecloud"]["bundle_url"] = "https://evil.invalid/release.tar.gz"
        with self.assertRaisesRegex(UpdateOriginError, "content-addressed"):
            validate_plan(plan, ORIGIN)

        plan, *_ = self.release(sequence=2)
        plan["linux"]["packages"] = [
            {"name": "systemd", "version": "257.1-1", "reason": "runtime"},
            {"name": "openssl", "version": "3.5.1-1", "reason": "security"},
        ]
        with self.assertRaisesRegex(UpdateOriginError, "ordinati"):
            validate_plan(plan, ORIGIN)

    def test_origin_requires_public_style_fqdn_and_time_is_aware(self):
        with self.assertRaisesRegex(UpdateOriginError, "host HTTPS"):
            build_plan(
                origin="https://localhost", sequence=1,
                published_at="2026-09-20T10:00:00Z",
                expires_at="2026-09-21T10:00:00Z",
                os_id="debian", os_version="13", architecture="arm64",
                commit=COMMIT, release_sequence=1,
                bundle_sha256="b" * 64, bundle_size=1,
                packages=[], reboot_required=False,
            )

        plan, *_ = self.release()
        with self.assertRaisesRegex(UpdateOriginError, "fuso orario"):
            validate_plan(plan, ORIGIN, now=dt.datetime(2026, 9, 20))

        plan["schema"] = True
        with self.assertRaisesRegex(UpdateOriginError, "Piano aggiornamenti"):
            validate_plan(plan, ORIGIN)

    def test_prepare_cli_creates_a_client_compatible_unsigned_plan(self):
        bundle = self.root / "cli-bundle.tar.gz"
        output = self.root / "cli-release.json"
        bundle.write_bytes(b"cli-bundle")
        with redirect_stdout(io.StringIO()):
            main([
                "prepare", "--origin", ORIGIN, "--sequence", "9",
                "--os-version", "13", "--commit", COMMIT,
                "--release-sequence", "3", "--bundle", str(bundle),
                "--package", "openssl=3.5.1-1=security", "--output", str(output),
            ])
        plan = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(validate_plan(plan, ORIGIN)["sequence"], 9)
        self.assertEqual(plan["linux"]["packages"][0]["name"], "openssl")

    def test_deployment_is_read_only_and_keeps_signing_key_offline(self):
        installer = (ROOT / "deploy/install-debian.sh").read_text(encoding="utf-8")
        nginx = (ROOT / "deploy/nginx-site.conf.in").read_text(encoding="utf-8")

        self.assertNotIn("signing-private", installer)
        self.assertNotIn("private.pem", installer)
        self.assertIn("limit_except GET HEAD", nginx)
        self.assertIn('^/releases/[0-9a-f]{64}\\.tar\\.gz$', nginx)
        self.assertIn("Strict-Transport-Security", nginx)
        self.assertIn("if ! nginx -t", installer)
        self.assertLess(installer.index("if ! nginx -t"), installer.index("systemctl reload"))
        self.assertIn("rollback_nginx", installer)


if __name__ == "__main__":
    unittest.main()
