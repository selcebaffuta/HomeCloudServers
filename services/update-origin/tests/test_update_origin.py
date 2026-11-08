from __future__ import annotations

import datetime as dt
import errno
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from homecloud_update_origin.model import UpdateOriginError, build_plan, validate_plan
from homecloud_update_origin.publisher import Publisher
from homecloud_update_origin import publisher as publisher_module
from homecloud_update_origin.cli import main


ORIGIN = "https://updates.homecloud.test"
COMMIT = "a" * 40


def timestamp(value):
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


class SignedOriginFixture:
    """Ephemeral test keys and signed fixtures; never real release material."""
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

    def keypair(self, name):
        private = self.root / f"{name}-private.pem"
        public = self.root / f"{name}-public.pem"
        subprocess.run(
            [
                "/usr/bin/openssl", "genpkey", "-algorithm", "RSA",
                "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(private),
            ],
            check=True, capture_output=True,
        )
        subprocess.run(
            [
                "/usr/bin/openssl", "pkey", "-in", str(private),
                "-pubout", "-out", str(public),
            ],
            check=True, capture_output=True,
        )
        private.chmod(0o600)
        public.chmod(0o644)
        return private, public

    @staticmethod
    def key_entry(public, status="active"):
        pem = public.read_text(encoding="ascii")
        return {
            "key_id": hashlib.sha256(pem.encode()).hexdigest(),
            "algorithm": "rsa-sha256", "public_key_pem": pem, "status": status,
        }

    def trust_release(self, sequence, keys, *, private_key=None, root_public=None):
        private_key = private_key or self.private_key
        root_public = root_public or self.public_key
        now = dt.datetime.now(dt.timezone.utc)
        metadata = {
            "schema": 1, "product": "homecloud-trust", "sequence": sequence,
            "published_at": timestamp(now - dt.timedelta(minutes=1)),
            "expires_at": timestamp(now + dt.timedelta(days=90)),
            "root_key_id": hashlib.sha256(root_public.read_bytes()).hexdigest(),
            "release_keys": sorted(keys, key=lambda item: item["key_id"]),
        }
        path = self.root / f"trust-{sequence}-{hashlib.sha256(json.dumps(metadata, sort_keys=True).encode()).hexdigest()[:8]}.json"
        signature = path.with_name(path.name + ".sig")
        path.write_text(json.dumps(metadata, sort_keys=True) + "\n", encoding="utf-8")
        subprocess.run(
            [
                "/usr/bin/openssl", "dgst", "-sha256", "-sign", str(private_key),
                "-out", str(signature), str(path),
            ],
            check=True, capture_output=True,
        )
        return metadata, path, signature

    def release(
        self, sequence=1, *, payload=b"bundle-one", packages=None,
        published_at=None, expires_at=None, os_version="13", release_sequence=None, commit=None,
    ):
        bundle = self.root / f"bundle-{sequence}-{hashlib.sha256(payload).hexdigest()[:8]}.tar.gz"
        bundle.write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        now = dt.datetime.now(dt.timezone.utc)
        release_sequence = sequence if release_sequence is None else release_sequence
        commit = commit if commit is not None else f"{release_sequence:040x}"
        plan = build_plan(
            origin=ORIGIN, sequence=sequence,
            published_at=published_at or timestamp(now - dt.timedelta(minutes=1)),
            expires_at=expires_at or timestamp(now + dt.timedelta(days=7)),
            os_id="debian", os_version=os_version, architecture="arm64",
            commit=commit, release_sequence=release_sequence,
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


class UpdateOriginTest(SignedOriginFixture, unittest.TestCase):
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

    def test_staging_promotion_reuses_exact_signed_plan_and_is_idempotent(self):
        release = self.release(sequence=7)
        publisher = Publisher(self.root / "publication", self.public_key, ORIGIN)
        publisher.publish(
            channel="staging", plan_path=release[1],
            signature_path=release[2], bundle_path=release[3],
        )
        result = publisher.promote(platform="debian-13-arm64")
        publication = self.root / "publication"
        staging = publication / "v1/staging/debian-13-arm64.json"
        stable = publication / "v1/stable/debian-13-arm64.json"

        self.assertEqual(stable.read_bytes(), staging.read_bytes())
        self.assertEqual(
            stable.with_name(stable.name + ".sig").read_bytes(),
            staging.with_name(staging.name + ".sig").read_bytes(),
        )
        self.assertEqual(result, publisher.promote(platform="debian-13-arm64"))
        audit = (publication / ".audit/promotion.jsonl").read_text().splitlines()
        self.assertEqual(len(audit), 2)
        self.assertTrue(all(json.loads(line)["result"] == "verified" for line in audit))

    def test_promotion_rejects_missing_tampered_expired_or_older_staging(self):
        publisher = Publisher(self.root / "publication", self.public_key, ORIGIN)
        with self.assertRaisesRegex(UpdateOriginError, "non esiste"):
            publisher.promote(platform="debian-13-arm64")

        release = self.release(sequence=4, payload=b"stable")
        publisher.publish(
            channel="stable", plan_path=release[1],
            signature_path=release[2], bundle_path=release[3],
        )
        older = self.release(sequence=3, payload=b"older")
        publisher.publish(
            channel="staging", plan_path=older[1],
            signature_path=older[2], bundle_path=older[3],
        )
        with self.assertRaisesRegex(UpdateOriginError, "sequenza"):
            publisher.promote(platform="debian-13-arm64")

        separate = self.root / "tampered-publication"
        tampered_publisher = Publisher(separate, self.public_key, ORIGIN)
        candidate = self.release(sequence=8, payload=b"candidate")
        published = tampered_publisher.publish(
            channel="staging", plan_path=candidate[1],
            signature_path=candidate[2], bundle_path=candidate[3],
        )
        bundle = separate / "releases" / f"{published['bundle_sha256']}.tar.gz"
        bundle.write_bytes(b"tampered!")
        with self.assertRaisesRegex(UpdateOriginError, "bundle staging"):
            tampered_publisher.promote(platform="debian-13-arm64")
        self.assertFalse((separate / "v1/stable/debian-13-arm64.json").exists())

        missing_root = self.root / "missing-bundle-publication"
        missing_publisher = Publisher(missing_root, self.public_key, ORIGIN)
        missing = self.release(sequence=9, payload=b"missing")
        published = missing_publisher.publish(
            channel="staging", plan_path=missing[1],
            signature_path=missing[2], bundle_path=missing[3],
        )
        (missing_root / "releases" / f"{published['bundle_sha256']}.tar.gz").unlink()
        with self.assertRaisesRegex(UpdateOriginError, "non apribile"):
            missing_publisher.promote(platform="debian-13-arm64")
        self.assertFalse((missing_root / "v1/stable/debian-13-arm64.json").exists())

        now = dt.datetime.now(dt.timezone.utc)
        expired = self.release(sequence=10, payload=b"expired")
        expired_root = self.root / "expired-publication"
        # Publishing also rejects expired plans, so emulate a staging endpoint
        # that expired after a previously successful publication.
        expired_publisher = Publisher(expired_root, self.public_key, ORIGIN)
        expired_publisher.publish(
            channel="staging", plan_path=expired[1],
            signature_path=expired[2], bundle_path=expired[3],
        )
        plan = dict(expired[0])
        plan["published_at"] = timestamp(now - dt.timedelta(days=2))
        plan["expires_at"] = timestamp(now - dt.timedelta(days=1))
        endpoint = expired_root / "v1/staging/debian-13-arm64.json"
        expired[1].write_text(json.dumps(plan, sort_keys=True) + "\n")
        subprocess.run(
            [
                "/usr/bin/openssl", "dgst", "-sha256", "-sign", str(self.private_key),
                "-out", str(expired[2]), str(expired[1]),
            ],
            check=True, capture_output=True,
        )
        endpoint.write_bytes(expired[1].read_bytes())
        endpoint.with_name(endpoint.name + ".sig").write_bytes(expired[2].read_bytes())
        with self.assertRaisesRegex(UpdateOriginError, "scaduto"):
            expired_publisher.promote(platform="debian-13-arm64")
        self.assertFalse((expired_root / "v1/stable/debian-13-arm64.json").exists())

    def test_invalid_signature_and_bundle_mismatch_are_rejected(self):
        release = self.release()
        release[2].write_bytes(b"not-a-signature")
        with self.assertRaisesRegex(UpdateOriginError, "Firma"):
            self.publish(release)

        release = self.release(sequence=2)
        release[3].write_bytes(b"changed-after-signing")
        with self.assertRaisesRegex(UpdateOriginError, "Bundle"):
            self.publish(release)

        release = self.release(sequence=3, payload=b"same-length")
        release[3].write_bytes(b"other-bytes")
        self.assertEqual(len(b"same-length"), len(b"other-bytes"))
        with self.assertRaisesRegex(UpdateOriginError, "Bundle"):
            self.publish(release)

        release = self.release(sequence=4, payload=b"truncate-this")
        release[3].write_bytes(b"truncated")
        with self.assertRaisesRegex(UpdateOriginError, "Bundle"):
            self.publish(release)

        release = self.release(sequence=5, payload=b"wrong-declared-size")
        plan = dict(release[0])
        plan["homecloud"] = dict(plan["homecloud"])
        plan["homecloud"]["bundle_size"] += 1
        release[1].write_text(json.dumps(plan, sort_keys=True) + "\n")
        subprocess.run(
            [
                "/usr/bin/openssl", "dgst", "-sha256", "-sign", str(self.private_key),
                "-out", str(release[2]), str(release[1]),
            ],
            check=True, capture_output=True,
        )
        with self.assertRaisesRegex(UpdateOriginError, "Bundle"):
            self.publish(release)

        release = self.release(sequence=6, payload=b"symlink")
        target = self.root / "real-bundle.tar.gz"
        target.write_bytes(release[3].read_bytes())
        release[3].unlink()
        release[3].symlink_to(target)
        with self.assertRaisesRegex(UpdateOriginError, "non apribile"):
            self.publish(release)

    def test_channel_sequence_is_strictly_monotonic(self):
        publication = self.root / "publication"
        self.publish(self.release(sequence=4), publication)
        with self.assertRaisesRegex(UpdateOriginError, "sequenza"):
            self.publish(self.release(sequence=3, payload=b"older"), publication)
        with self.assertRaisesRegex(UpdateOriginError, "sequenza"):
            self.publish(self.release(sequence=4, payload=b"changed"), publication)

    def test_channel_platform_digest_and_sequence_inputs_are_bounded(self):
        release = self.release()
        publisher = Publisher(self.root / "publication", self.public_key, ORIGIN)
        for channel in ("../stable", "/stable", "stable/x", ".hidden"):
            with self.subTest(channel=channel):
                with self.assertRaisesRegex(UpdateOriginError, "Canale"):
                    publisher.publish(
                        channel=channel, plan_path=release[1],
                        signature_path=release[2], bundle_path=release[3],
                    )
        with self.assertRaisesRegex(UpdateOriginError, "Piattaforma"):
            publisher.promote(platform="../../etc/passwd")

        plan = dict(release[0])
        plan["homecloud"] = dict(plan["homecloud"])
        for digest in ("f" * 63, "g" * 64):
            plan["homecloud"]["bundle_sha256"] = digest
            with self.subTest(digest=digest):
                with self.assertRaisesRegex(UpdateOriginError, "Release HomeCloud"):
                    validate_plan(plan, ORIGIN)
        plan = dict(release[0])
        plan["sequence"] = 2**63
        with self.assertRaisesRegex(UpdateOriginError, "Piano aggiornamenti"):
            validate_plan(plan, ORIGIN)

    def test_concurrent_publication_is_serialized_and_keeps_highest_sequence(self):
        publication = self.root / "concurrent-publication"
        older = self.release(sequence=20, payload=b"older-concurrent")
        newer = self.release(sequence=21, payload=b"newer-concurrent")

        def publish(release):
            try:
                return self.publish(release, publication)
            except UpdateOriginError as error:
                return str(error)

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(publish, (older, newer)))
        endpoint = publication / "v1/stable/debian-13-arm64.json"
        self.assertEqual(json.loads(endpoint.read_text())["sequence"], 21)
        self.assertTrue(any(isinstance(result, dict) for result in results))

    def test_crash_between_plan_and_signature_fails_closed_and_retry_repairs(self):
        publication = self.root / "crash-publication"
        publisher = Publisher(publication, self.public_key, ORIGIN)
        stable = self.release(sequence=30, payload=b"stable-before-crash")
        staging = self.release(sequence=31, payload=b"staging-after-crash")
        publisher.publish(
            channel="stable", plan_path=stable[1],
            signature_path=stable[2], bundle_path=stable[3],
        )
        publisher.publish(
            channel="staging", plan_path=staging[1],
            signature_path=staging[2], bundle_path=staging[3],
        )
        signature_target = publication / "v1/stable/debian-13-arm64.json.sig"
        original_replace = publisher_module.os.replace

        def fail_signature(source, target):
            if Path(target) == signature_target:
                raise OSError("simulated power loss")
            return original_replace(source, target)

        with mock.patch.object(publisher_module.os, "replace", side_effect=fail_signature):
            with self.assertRaises(OSError):
                publisher.promote(platform="debian-13-arm64")
        endpoint = publication / "v1/stable/debian-13-arm64.json"
        self.assertEqual(json.loads(endpoint.read_text())["sequence"], 31)
        verification = subprocess.run(
            [
                "/usr/bin/openssl", "dgst", "-sha256", "-verify", str(self.public_key),
                "-signature", str(signature_target), str(endpoint),
            ],
            check=False, capture_output=True,
        )
        self.assertNotEqual(verification.returncode, 0)
        publisher.promote(platform="debian-13-arm64")
        subprocess.run(
            [
                "/usr/bin/openssl", "dgst", "-sha256", "-verify", str(self.public_key),
                "-signature", str(signature_target), str(endpoint),
            ],
            check=True, capture_output=True,
        )

    def test_first_publish_recovers_missing_signature_only_for_exact_plan(self):
        publication = self.root / "publication"
        approved = self.release(sequence=41)
        endpoint = publication / "v1/stable/debian-13-arm64.json"
        signature_path = endpoint.with_suffix(".json.sig")
        replace = publisher_module.os.replace

        def fail_first_signature(source, target):
            if Path(target) == signature_path:
                raise OSError("simulated interruption before signature rename")
            return replace(source, target)

        with mock.patch.object(publisher_module.os, "replace", side_effect=fail_first_signature):
            with self.assertRaises(OSError):
                self.publish(approved, publication)
        self.assertEqual(endpoint.read_bytes(), approved[1].read_bytes())
        self.assertFalse(signature_path.exists())

        for sequence in (40, 41, 42):
            with self.subTest(sequence=sequence):
                other = self.release(sequence=sequence, payload=b"not-the-approved-plan")
                with self.assertRaisesRegex(UpdateOriginError, "incompleto"):
                    self.publish(other, publication)
                self.assertFalse(signature_path.exists())

        self.publish(approved, publication)
        self.assertEqual(signature_path.read_bytes(), approved[2].read_bytes())
        endpoint.unlink()  # Signature-only is not a trusted sequence floor.
        with self.assertRaisesRegex(UpdateOriginError, "incompleto"):
            self.publish(approved, publication)

    def test_trust_retry_requires_exact_metadata_when_signature_is_missing(self):
        publication = self.root / "publication"
        publisher = Publisher(publication, self.public_key, ORIGIN)
        first = self.trust_release(1, [self.key_entry(self.public_key)])
        second = self.trust_release(2, [self.key_entry(self.public_key)])

        def publish(data):
            return publisher.publish_trust(
                channel="stable", metadata_path=data[1], signature_path=data[2],
                root_public_key=self.public_key,
            )

        endpoint = publication / publish(first)["metadata_path"]
        signature_path = endpoint.with_suffix(".json.sig")
        signature_path.unlink()
        with self.assertRaisesRegex(UpdateOriginError, "incompleto"):
            publish(second)
        self.assertFalse(signature_path.exists())
        publish(first)
        self.assertEqual(signature_path.read_bytes(), first[2].read_bytes())
        publish(second)
        with self.assertRaisesRegex(UpdateOriginError, "monotono"):
            publish(first)

    def test_promotion_does_not_switch_when_audit_directory_cannot_be_synced(self):
        publication = self.root / "publication"
        publisher = Publisher(publication, self.public_key, ORIGIN)
        stable = self.release(sequence=8)
        self.publish(stable, publication)
        staged = self.release(sequence=9)
        publisher.publish(channel="staging", plan_path=staged[1],
                          signature_path=staged[2], bundle_path=staged[3])
        original = publisher_module._fsync_directory

        def fail_audit(path):
            if path == publication / ".audit":
                raise OSError(errno.EIO, "simulated audit directory sync failure")
            return original(path)

        with mock.patch.object(publisher_module, "_fsync_directory", side_effect=fail_audit):
            with self.assertRaises(OSError):
                publisher.promote(platform="debian-13-arm64")
        endpoint = publication / "v1/stable/debian-13-arm64.json"
        self.assertEqual(endpoint.read_bytes(), stable[1].read_bytes())
        self.assertEqual(endpoint.with_suffix(".json.sig").read_bytes(), stable[2].read_bytes())

    def test_promotion_cli_pins_the_staging_plan_that_was_reviewed(self):
        publication = self.root / "publication"
        publisher = Publisher(publication, self.public_key, ORIGIN)

        def stage(release):
            return publisher.publish(channel="staging", plan_path=release[1],
                                     signature_path=release[2], bundle_path=release[3])

        self.publish(self.release(sequence=41), publication)
        stable = publication / "v1/stable/debian-13-arm64.json"
        before = stable.read_bytes()
        first = stage(self.release(sequence=42))
        second = stage(self.release(sequence=43))
        command = ["promote", "--origin", ORIGIN, "--platform", "debian-13-arm64",
                   "--root", str(publication), "--public-key", str(self.public_key),
                   "--key-directory", str(self.root / "absent-keyring"), "--expected-plan-sha256"]
        with self.assertRaisesRegex(SystemExit, "piano approvato"):
            main([*command, first["plan_sha256"]])
        self.assertEqual(stable.read_bytes(), before)
        self.assertFalse((publication / ".audit").exists())

        with redirect_stdout(io.StringIO()) as receipt:
            main([*command, second["plan_sha256"]])
        self.assertEqual(json.loads(receipt.getvalue())["plan_sha256"], second["plan_sha256"])
        self.assertEqual(hashlib.sha256(stable.read_bytes()).hexdigest(), second["plan_sha256"])

    def test_new_plan_cannot_downgrade_runtime_or_change_sequence_of_same_commit(self):
        publication = self.root / "publication"
        approved = self.release(sequence=10, release_sequence=4)
        self.publish(approved, publication)
        for runtime_sequence, commit in ((3, None), (4, COMMIT), (5, approved[0]["homecloud"]["commit"])):
            with self.subTest(runtime_sequence=runtime_sequence, commit=commit):
                with self.assertRaisesRegex(UpdateOriginError, "release_sequence"):
                    self.publish(self.release(sequence=11, release_sequence=runtime_sequence,
                                              commit=commit), publication)

        # Renewal and package-only plans for the same installed runtime remain valid.
        renewed = self.release(sequence=12, release_sequence=4,
                               packages=[{"name": "openssl", "version": "1:3.5.1-1+deb13u1", "reason": "security"}])
        self.assertEqual(self.publish(renewed, publication)["sequence"], 12)

    def test_valid_ecdsa_signature_does_not_satisfy_rsa_release_contract(self):
        private, public = self.root / "ec-test-key.pem", self.root / "ec-test-public.pem"
        subprocess.run(["/usr/bin/openssl", "genpkey", "-algorithm", "EC", "-pkeyopt",
                        "ec_paramgen_curve:P-256", "-out", str(private)], check=True, capture_output=True, timeout=30)
        subprocess.run(["/usr/bin/openssl", "pkey", "-in", str(private), "-pubout", "-out", str(public)],
                       check=True, capture_output=True, timeout=30)
        release = self.release()
        subprocess.run(["/usr/bin/openssl", "dgst", "-sha256", "-sign", str(private),
                        "-out", str(release[2]), str(release[1])], check=True, capture_output=True, timeout=30)
        subprocess.run(["/usr/bin/openssl", "dgst", "-sha256", "-verify", str(public),
                        "-signature", str(release[2]), str(release[1])], check=True, capture_output=True, timeout=30)

        publication = self.root / "publication"
        publisher = Publisher(publication, public, ORIGIN)
        with self.assertRaisesRegex(UpdateOriginError, "Firma"):
            publisher.publish(channel="stable", plan_path=release[1], signature_path=release[2], bundle_path=release[3])
        self.assertFalse((publication / "v1/stable/debian-13-arm64.json").exists())

        trust = self.trust_release(1, [self.key_entry(public)])
        with self.assertRaisesRegex(UpdateOriginError, "Chiave release"):
            publisher.publish_trust(channel="stable", metadata_path=trust[1], signature_path=trust[2],
                                    root_public_key=self.public_key)

    def test_publish_retry_repairs_partial_immutable_record(self):
        publication = self.root / "immutable-crash-publication"
        publisher = Publisher(publication, self.public_key, ORIGIN)
        release = self.release(sequence=40, payload=b"immutable-crash")
        original_replace = publisher_module.os.replace

        def fail_immutable_signature(source, target):
            target = Path(target)
            if "plans" in target.parts and target.name.endswith(".json.sig"):
                raise OSError("simulated immutable signature loss")
            return original_replace(source, target)

        with mock.patch.object(
            publisher_module.os, "replace", side_effect=fail_immutable_signature,
        ):
            with self.assertRaises(OSError):
                publisher.publish(
                    channel="staging", plan_path=release[1],
                    signature_path=release[2], bundle_path=release[3],
                )
        self.assertFalse(
            (publication / "v1/staging/debian-13-arm64.json").exists(),
        )
        result = publisher.publish(
            channel="staging", plan_path=release[1],
            signature_path=release[2], bundle_path=release[3],
        )
        self.assertEqual(result["sequence"], 40)

    def test_storage_exhaustion_before_switch_preserves_stable(self):
        publication = self.root / "full-publication"
        publisher = Publisher(publication, self.public_key, ORIGIN)
        stable = self.release(sequence=50, payload=b"stable-on-full-disk")
        candidate = self.release(sequence=51, payload=b"candidate-on-full-disk")
        publisher.publish(
            channel="stable", plan_path=stable[1],
            signature_path=stable[2], bundle_path=stable[3],
        )
        endpoint = publication / "v1/stable/debian-13-arm64.json"
        old_plan = endpoint.read_bytes()
        old_signature = endpoint.with_name(endpoint.name + ".sig").read_bytes()
        with mock.patch.object(
            publisher_module, "_install_content_addressed",
            side_effect=OSError(errno.ENOSPC, "simulated full filesystem"),
        ):
            with self.assertRaises(OSError):
                publisher.publish(
                    channel="stable", plan_path=candidate[1],
                    signature_path=candidate[2], bundle_path=candidate[3],
                )
        self.assertEqual(endpoint.read_bytes(), old_plan)
        self.assertEqual(
            endpoint.with_name(endpoint.name + ".sig").read_bytes(), old_signature,
        )

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

    def test_root_signed_trust_metadata_is_monotonic_and_revocation_is_final(self):
        publisher = Publisher(self.root / "publication", self.public_key, ORIGIN)
        _new_private, new_public = self.keypair("new-release")
        first = self.trust_release(
            1, [self.key_entry(self.public_key), self.key_entry(new_public)],
        )
        result = publisher.publish_trust(
            channel="stable", metadata_path=first[1], signature_path=first[2],
            root_public_key=self.public_key,
        )
        endpoint = self.root / "publication" / result["metadata_path"]
        self.assertEqual(json.loads(endpoint.read_text()), first[0])
        self.assertEqual(
            publisher.publish_trust(
                channel="stable", metadata_path=first[1], signature_path=first[2],
                root_public_key=self.public_key,
            ),
            result,
        )

        second = self.trust_release(
            2, [
                self.key_entry(self.public_key, "revoked"),
                self.key_entry(new_public),
            ],
        )
        publisher.publish_trust(
            channel="stable", metadata_path=second[1], signature_path=second[2],
            root_public_key=self.public_key,
        )
        replay = self.trust_release(
            3, [self.key_entry(self.public_key), self.key_entry(new_public)],
        )
        with self.assertRaisesRegex(UpdateOriginError, "riattivata"):
            publisher.publish_trust(
                channel="stable", metadata_path=replay[1], signature_path=replay[2],
                root_public_key=self.public_key,
            )

    def test_prepare_trust_cli_and_release_key_overlap(self):
        new_private, new_public = self.keypair("overlap")
        output = self.root / "prepared-trust.json"
        with redirect_stdout(io.StringIO()):
            main([
                "prepare-trust", "--sequence", "4",
                "--root-public-key", str(self.public_key),
                "--active-key", str(self.public_key),
                "--active-key", str(new_public), "--output", str(output),
            ])
        trust = json.loads(output.read_text())
        self.assertEqual(trust["sequence"], 4)
        self.assertEqual(len(trust["release_keys"]), 2)

        release = self.release(sequence=12, payload=b"new-key-release")
        subprocess.run(
            [
                "/usr/bin/openssl", "dgst", "-sha256", "-sign", str(new_private),
                "-out", str(release[2]), str(release[1]),
            ],
            check=True, capture_output=True,
        )
        publisher = Publisher(
            self.root / "overlap-publication",
            [self.public_key, new_public], ORIGIN,
        )
        result = publisher.publish(
            channel="staging", plan_path=release[1], signature_path=release[2],
            bundle_path=release[3],
        )
        self.assertEqual(result["sequence"], 12)

    def test_deployment_is_read_only_and_keeps_signing_key_offline(self):
        installer = (ROOT / "deploy/install-debian.sh").read_text(encoding="utf-8")
        nginx = (ROOT / "deploy/nginx-site.conf.in").read_text(encoding="utf-8")

        self.assertNotIn("signing-private", installer)
        self.assertNotIn("private.pem", installer)
        self.assertIn("limit_except GET HEAD", nginx)
        self.assertIn('^/releases/[0-9a-f]{64}\\.tar\\.gz$', nginx)
        self.assertIn("Strict-Transport-Security", nginx)
        self.assertIn("if ! nginx -t", installer)
        self.assertLess(
            installer.index("if ! nginx -t"),
            installer.index("if ! systemctl enable --now"),
        )
        self.assertIn("rollback_nginx", installer)
        self.assertIn("disable_symlinks on", nginx)
        self.assertIn("max_ranges 0", nginx)
        self.assertIn("max_ranges 1", nginx)


if __name__ == "__main__":
    unittest.main()
