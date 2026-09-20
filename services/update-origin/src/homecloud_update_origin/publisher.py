"""Fail-closed publication of pre-signed HomeCloud release artifacts."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
import datetime as dt
from contextlib import contextmanager
from pathlib import Path

from .model import (
    CHANNEL_PATTERN, UpdateOriginError, platform_key, validate_plan,
    validate_trust_metadata,
)


MAX_PLAN_SIZE = 256 * 1024
MAX_SIGNATURE_SIZE = 64 * 1024
MAX_BUNDLE_SIZE = 1024 * 1024 * 1024
PLATFORM_KEYS = {"debian-12-arm64", "debian-13-arm64"}


def _open_regular(path: Path, maximum: int, *, trusted=False):
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise UpdateOriginError(f"File release non apribile: {path}") from error
    metadata = os.fstat(descriptor)
    if (
        not stat.S_ISREG(metadata.st_mode) or not 1 <= metadata.st_size <= maximum
        or trusted and metadata.st_mode & 0o022
        or trusted and os.geteuid() == 0 and metadata.st_uid != 0
    ):
        os.close(descriptor)
        detail = "File di fiducia non protetto" if trusted else "File release non valido"
        raise UpdateOriginError(f"{detail}: {path}")
    return descriptor, metadata.st_size


def _snapshot(path: Path, destination: Path, maximum: int, *, trusted=False) -> tuple[str, int]:
    source_descriptor, expected_size = _open_regular(path, maximum, trusted=trusted)
    digest = hashlib.sha256()
    total = 0
    try:
        with os.fdopen(os.dup(source_descriptor), "rb") as source, destination.open("xb") as target:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                total += len(block)
                if total > maximum:
                    raise UpdateOriginError(f"File release troppo grande: {path}")
                digest.update(block)
                target.write(block)
            target.flush()
            os.fsync(target.fileno())
    finally:
        os.close(source_descriptor)
    if total != expected_size:
        raise UpdateOriginError(f"File release modificato durante la lettura: {path}")
    destination.chmod(0o600)
    return digest.hexdigest(), total


def _secure_bytes(path: Path, maximum: int, *, trusted=False) -> bytes:
    descriptor, expected_size = _open_regular(path, maximum, trusted=trusted)
    payload = bytearray()
    try:
        while len(payload) < expected_size:
            block = os.read(descriptor, min(1024 * 1024, expected_size - len(payload)))
            if not block:
                break
            payload.extend(block)
    finally:
        os.close(descriptor)
    if len(payload) != expected_size:
        raise UpdateOriginError(f"File modificato durante la lettura: {path}")
    return bytes(payload)


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise UpdateOriginError("Piano release JSON non leggibile.") from error


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _public_directory(path: Path) -> None:
    if path.exists() or path.is_symlink():
        metadata = path.stat(follow_symlinks=False)
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_mode & 0o022
            or os.geteuid() == 0 and metadata.st_uid != 0
        ):
            raise UpdateOriginError(f"Directory pubblica non sicura: {path}")
    else:
        path.mkdir(mode=0o755)
    path.chmod(0o755)


def _private_directory(path: Path) -> None:
    if path.exists() or path.is_symlink():
        metadata = path.stat(follow_symlinks=False)
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_mode & 0o077
            or os.geteuid() == 0 and metadata.st_uid != 0
        ):
            raise UpdateOriginError(f"Directory privata non sicura: {path}")
    else:
        path.mkdir(mode=0o700)
    path.chmod(0o700)


def _atomic_bytes(path: Path, payload: bytes) -> None:
    _public_directory(path.parent)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o644)
        with os.fdopen(descriptor, "wb") as target:
            target.write(payload)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _install_content_addressed(source: Path, target: Path, digest: str, size: int) -> None:
    _public_directory(target.parent)
    if target.exists() or target.is_symlink():
        descriptor, existing_size = _open_regular(target, MAX_BUNDLE_SIZE, trusted=True)
        existing_digest = hashlib.sha256()
        try:
            with os.fdopen(os.dup(descriptor), "rb") as source_stream:
                for block in iter(lambda: source_stream.read(1024 * 1024), b""):
                    existing_digest.update(block)
        finally:
            os.close(descriptor)
        if existing_size != size or existing_digest.hexdigest() != digest:
            raise UpdateOriginError("Un bundle content-addressed esistente non corrisponde all'hash.")
        return
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}-", dir=target.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        shutil.copyfile(source, temporary)
        temporary.chmod(0o644)
        with temporary.open("rb") as stream:
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        _fsync_directory(target.parent)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _install_immutable_pair(
    payload_path: Path, signature_path: Path, payload: bytes, signature: bytes,
) -> None:
    payload_present = payload_path.exists() or payload_path.is_symlink()
    signature_present = signature_path.exists() or signature_path.is_symlink()
    if (
        payload_present
        and _secure_bytes(payload_path, MAX_PLAN_SIZE, trusted=True) != payload
    ):
        raise UpdateOriginError("Il record immutabile è già occupato.")
    if (
        signature_present
        and _secure_bytes(
            signature_path, MAX_SIGNATURE_SIZE, trusted=True,
        ) != signature
    ):
        raise UpdateOriginError("La firma del record immutabile è già occupata.")
    if not payload_present:
        _atomic_bytes(payload_path, payload)
    if not signature_present:
        _atomic_bytes(signature_path, signature)


class Publisher:
    def __init__(self, root: Path, public_key: Path | list[Path], origin: str):
        self.root = Path(root)
        if isinstance(public_key, (str, os.PathLike)):
            public_key = [Path(public_key)]
        self.public_keys = [Path(path) for path in public_key]
        if not self.public_keys or len(self.public_keys) > 8:
            raise UpdateOriginError("Keyring di pubblicazione non valida.")
        self.origin = origin

    def publish(
        self, *, channel: str, plan_path: Path, signature_path: Path, bundle_path: Path,
    ) -> dict:
        self._validate_channel(channel)
        with self._publication_lock():
            return self._publish_locked(
                channel=channel, plan_path=Path(plan_path),
                signature_path=Path(signature_path), bundle_path=Path(bundle_path),
            )

    def promote(
        self, *, platform: str, source_channel: str = "staging",
        target_channel: str = "stable",
    ) -> dict:
        """Promote one already-published, signed release without rebuilding it."""
        self._validate_channel(source_channel)
        self._validate_channel(target_channel)
        if source_channel == target_channel:
            raise UpdateOriginError("I canali sorgente e destinazione devono essere diversi.")
        if platform not in PLATFORM_KEYS:
            raise UpdateOriginError("Piattaforma di promozione non valida.")
        with self._publication_lock():
            return self._promote_locked(
                platform=platform, source_channel=source_channel,
                target_channel=target_channel,
            )

    def publish_trust(
        self, *, channel: str, metadata_path: Path, signature_path: Path,
        root_public_key: Path,
    ) -> dict:
        self._validate_channel(channel)
        with self._publication_lock():
            return self._publish_trust_locked(
                channel=channel, metadata_path=Path(metadata_path),
                signature_path=Path(signature_path),
                root_public_key=Path(root_public_key),
            )

    @staticmethod
    def _validate_channel(channel: str) -> None:
        if not isinstance(channel, str) or not CHANNEL_PATTERN.fullmatch(channel):
            raise UpdateOriginError("Canale release non valido.")

    @contextmanager
    def _publication_lock(self):
        self._prepare_root()
        lock_flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            lock_descriptor = os.open(self.root / ".publish.lock", lock_flags, 0o600)
        except OSError as error:
            raise UpdateOriginError("Lock di pubblicazione non disponibile.") from error
        lock_metadata = os.fstat(lock_descriptor)
        if (
            not stat.S_ISREG(lock_metadata.st_mode)
            or os.geteuid() == 0 and lock_metadata.st_uid != 0
        ):
            os.close(lock_descriptor)
            raise UpdateOriginError("Lock di pubblicazione non sicuro.")
        os.fchmod(lock_descriptor, 0o600)
        with os.fdopen(lock_descriptor, "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def _prepare_root(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True, mode=0o755)
        metadata = self.root.stat(follow_symlinks=False)
        if (
            not stat.S_ISDIR(metadata.st_mode) or metadata.st_mode & 0o022
            or os.geteuid() == 0 and metadata.st_uid != 0
        ):
            raise UpdateOriginError("Directory di pubblicazione non sicura.")
        self.root.chmod(0o755)

    def _publish_locked(self, *, channel, plan_path, signature_path, bundle_path):
        with tempfile.TemporaryDirectory(prefix=".publish-", dir=self.root) as staging_name:
            staging = Path(staging_name)
            staging.chmod(0o700)
            plan_copy = staging / "release.json"
            signature_copy = staging / "release.json.sig"
            bundle_copy = staging / "bundle.tar.gz"
            key_copies = []
            plan_digest, _ = _snapshot(plan_path, plan_copy, MAX_PLAN_SIZE)
            _snapshot(signature_path, signature_copy, MAX_SIGNATURE_SIZE)
            for index, public_key in enumerate(self.public_keys):
                key_copy = staging / f"release-public-{index}.pem"
                _snapshot(public_key, key_copy, MAX_SIGNATURE_SIZE, trusted=True)
                key_copies.append(key_copy)
            self._verify_signature_any(plan_copy, signature_copy, key_copies)
            plan = validate_plan(_read_json(plan_copy), self.origin)
            # Validate the small authenticated control files before copying a
            # potentially large bundle into the private staging directory.
            bundle_digest, bundle_size = _snapshot(
                bundle_path, bundle_copy, MAX_BUNDLE_SIZE,
            )
            target = plan["homecloud"]
            if bundle_digest != target["bundle_sha256"] or bundle_size != target["bundle_size"]:
                raise UpdateOriginError("Bundle, dimensione e hash del piano non corrispondono.")

            key = platform_key(plan["platform"])
            for directory in (
                self.root / "releases", self.root / "plans", self.root / "plans" / key,
                self.root / "v1", self.root / "v1" / channel,
            ):
                _public_directory(directory)
            endpoint = self.root / "v1" / channel / f"{key}.json"
            endpoint_signature = endpoint.with_name(endpoint.name + ".sig")
            plan_bytes = plan_copy.read_bytes()
            signature_bytes = signature_copy.read_bytes()
            self._check_sequence(
                endpoint, endpoint_signature, plan, plan_bytes, signature_bytes,
                key_copies,
            )

            bundle_target = self.root / "releases" / f"{bundle_digest}.tar.gz"
            _install_content_addressed(bundle_copy, bundle_target, bundle_digest, bundle_size)
            immutable = self.root / "plans" / key / f"{plan['sequence']}-{plan_digest}.json"
            immutable_signature = immutable.with_name(immutable.name + ".sig")
            _install_immutable_pair(
                immutable, immutable_signature, plan_bytes, signature_bytes,
            )

            # The v1 protocol uses two files, so a cryptographically consistent
            # pair cannot be switched in one rename. Publish the verified plan
            # first and its signature second: readers fail closed on a transient
            # mismatch, and a retry can repair a crash after the first rename.
            _atomic_bytes(endpoint, plan_bytes)
            _atomic_bytes(endpoint_signature, signature_bytes)
            return {
                "channel": channel,
                "platform": key,
                "sequence": plan["sequence"],
                "plan_sha256": plan_digest,
                "bundle_sha256": bundle_digest,
                "metadata_path": str(endpoint.relative_to(self.root)),
            }

    def _promote_locked(self, *, platform, source_channel, target_channel):
        source = self.root / "v1" / source_channel / f"{platform}.json"
        source_signature = source.with_name(source.name + ".sig")
        if not source.exists() or not source_signature.exists():
            raise UpdateOriginError("La release staging richiesta non esiste.")

        with tempfile.TemporaryDirectory(prefix=".promote-", dir=self.root) as staging_name:
            staging = Path(staging_name)
            staging.chmod(0o700)
            plan_copy = staging / "release.json"
            signature_copy = staging / "release.json.sig"
            key_copies = []
            plan_digest, _ = _snapshot(source, plan_copy, MAX_PLAN_SIZE, trusted=True)
            _snapshot(
                source_signature, signature_copy, MAX_SIGNATURE_SIZE, trusted=True,
            )
            for index, public_key in enumerate(self.public_keys):
                key_copy = staging / f"release-public-{index}.pem"
                _snapshot(public_key, key_copy, MAX_SIGNATURE_SIZE, trusted=True)
                key_copies.append(key_copy)
            self._verify_signature_any(plan_copy, signature_copy, key_copies)
            plan = validate_plan(_read_json(plan_copy), self.origin)
            if platform_key(plan["platform"]) != platform:
                raise UpdateOriginError("La release staging appartiene a un'altra piattaforma.")

            bundle = self.root / "releases" / f"{plan['homecloud']['bundle_sha256']}.tar.gz"
            bundle_digest, bundle_size = self._digest_public_bundle(bundle)
            if (
                bundle_digest != plan["homecloud"]["bundle_sha256"]
                or bundle_size != plan["homecloud"]["bundle_size"]
            ):
                raise UpdateOriginError("Il bundle staging non corrisponde al piano firmato.")

            target_directory = self.root / "v1" / target_channel
            _public_directory(self.root / "v1")
            _public_directory(target_directory)
            target = target_directory / f"{platform}.json"
            target_signature = target.with_name(target.name + ".sig")
            plan_bytes = plan_copy.read_bytes()
            signature_bytes = signature_copy.read_bytes()
            self._check_sequence(
                target, target_signature, plan, plan_bytes, signature_bytes,
                key_copies,
            )

            # The audit record is durable before the channel pointer changes.
            # After a power loss it proves what was authorized; re-running the
            # idempotent promotion reconciles any fail-closed signature mismatch.
            self._audit_promotion({
                "operation": "promote",
                "source_channel": source_channel,
                "target_channel": target_channel,
                "platform": platform,
                "sequence": plan["sequence"],
                "plan_sha256": plan_digest,
                "bundle_sha256": bundle_digest,
                "result": "verified",
            })
            _atomic_bytes(target, plan_bytes)
            _atomic_bytes(target_signature, signature_bytes)
            return {
                "source_channel": source_channel,
                "target_channel": target_channel,
                "platform": platform,
                "sequence": plan["sequence"],
                "plan_sha256": plan_digest,
                "bundle_sha256": bundle_digest,
                "metadata_path": str(target.relative_to(self.root)),
            }

    def _publish_trust_locked(
        self, *, channel, metadata_path, signature_path, root_public_key,
    ):
        with tempfile.TemporaryDirectory(prefix=".trust-", dir=self.root) as staging_name:
            staging = Path(staging_name)
            staging.chmod(0o700)
            metadata_copy = staging / "trust.json"
            signature_copy = staging / "trust.json.sig"
            root_copy = staging / "trust-root.pem"
            metadata_digest, _ = _snapshot(
                metadata_path, metadata_copy, MAX_PLAN_SIZE,
            )
            _snapshot(signature_path, signature_copy, MAX_SIGNATURE_SIZE)
            root_digest, _ = _snapshot(
                root_public_key, root_copy, MAX_SIGNATURE_SIZE, trusted=True,
            )
            self._verify_signature(metadata_copy, signature_copy, root_copy)
            metadata = validate_trust_metadata(
                _read_json(metadata_copy), root_digest,
            )
            self._validate_embedded_release_keys(metadata, staging / "keys")

            for directory in (
                self.root / "trust", self.root / "v1", self.root / "v1" / channel,
            ):
                _public_directory(directory)
            endpoint = self.root / "v1" / channel / "trust.json"
            endpoint_signature = endpoint.with_name("trust.json.sig")
            metadata_bytes = metadata_copy.read_bytes()
            signature_bytes = signature_copy.read_bytes()
            self._check_trust_sequence(
                endpoint, endpoint_signature, metadata, metadata_bytes,
                signature_bytes, root_copy, root_digest,
            )

            immutable = self.root / "trust" / f"{metadata['sequence']}-{metadata_digest}.json"
            immutable_signature = immutable.with_name(immutable.name + ".sig")
            _install_immutable_pair(
                immutable, immutable_signature, metadata_bytes, signature_bytes,
            )
            _atomic_bytes(endpoint, metadata_bytes)
            _atomic_bytes(endpoint_signature, signature_bytes)
            return {
                "channel": channel,
                "sequence": metadata["sequence"],
                "metadata_sha256": metadata_digest,
                "root_key_id": root_digest,
                "metadata_path": str(endpoint.relative_to(self.root)),
            }

    def _digest_public_bundle(self, path: Path) -> tuple[str, int]:
        descriptor, expected_size = _open_regular(
            path, MAX_BUNDLE_SIZE, trusted=True,
        )
        digest = hashlib.sha256()
        total = 0
        try:
            with os.fdopen(os.dup(descriptor), "rb") as source:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    total += len(block)
                    digest.update(block)
        finally:
            os.close(descriptor)
        if total != expected_size:
            raise UpdateOriginError("Bundle pubblico modificato durante la verifica.")
        return digest.hexdigest(), total

    def _audit_promotion(self, entry: dict) -> None:
        directory = self.root / ".audit"
        _private_directory(directory)
        path = directory / "promotion.jsonl"
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
        flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path, flags, 0o600)
        except OSError as error:
            raise UpdateOriginError("Audit log promozioni non disponibile.") from error
        try:
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o077
                or os.geteuid() == 0 and metadata.st_uid != 0
            ):
                raise UpdateOriginError("Audit log promozioni non sicuro.")
            os.fchmod(descriptor, 0o600)
            payload = {
                "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
                **entry,
            }
            encoded = (
                json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n"
            ).encode()
            written = 0
            while written < len(encoded):
                count = os.write(descriptor, encoded[written:])
                if count <= 0:
                    raise UpdateOriginError("Scrittura audit promozioni incompleta.")
                written += count
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    @staticmethod
    def _validate_embedded_release_keys(metadata: dict, directory: Path) -> None:
        directory.mkdir(mode=0o700)
        for key in metadata["release_keys"]:
            path = directory / f"{key['key_id']}.pem"
            path.write_text(key["public_key_pem"], encoding="ascii")
            path.chmod(0o600)
            try:
                result = subprocess.run(
                    [
                        "/usr/bin/openssl", "pkey", "-pubin", "-in", str(path),
                        "-noout",
                    ],
                    check=False, capture_output=True, timeout=30,
                )
            except (OSError, subprocess.TimeoutExpired) as error:
                raise UpdateOriginError(
                    "Validazione della chiave release non disponibile.",
                ) from error
            if result.returncode != 0:
                raise UpdateOriginError("Chiave release crittograficamente non valida.")

    def _check_trust_sequence(
        self, endpoint, endpoint_signature, metadata, metadata_bytes,
        signature_bytes, root_key, root_key_id,
    ) -> None:
        endpoint_present = endpoint.exists() or endpoint.is_symlink()
        signature_present = endpoint_signature.exists() or endpoint_signature.is_symlink()
        if not endpoint_present and not signature_present:
            return
        if not endpoint_present or not signature_present:
            raise UpdateOriginError("Stato trust del canale incompleto.")
        current_bytes = _secure_bytes(endpoint, MAX_PLAN_SIZE, trusted=True)
        current_signature = _secure_bytes(
            endpoint_signature, MAX_SIGNATURE_SIZE, trusted=True,
        )
        if current_bytes == metadata_bytes:
            return
        with tempfile.TemporaryDirectory(prefix="current-trust-", dir=self.root) as temporary_name:
            temporary = Path(temporary_name)
            current_path = temporary / "trust.json"
            current_signature_path = temporary / "trust.json.sig"
            current_path.write_bytes(current_bytes)
            current_signature_path.write_bytes(current_signature)
            self._verify_signature(current_path, current_signature_path, root_key)
            current = validate_trust_metadata(
                _read_json(current_path), root_key_id, check_time=False,
            )
        if metadata["sequence"] <= current["sequence"]:
            raise UpdateOriginError("La sequenza trust deve crescere in modo monotono.")
        current_status = {
            key["key_id"]: key["status"] for key in current["release_keys"]
        }
        candidate_status = {
            key["key_id"]: key["status"] for key in metadata["release_keys"]
        }
        if not set(current_status) <= set(candidate_status):
            raise UpdateOriginError("Le chiavi trust precedenti non possono essere omesse.")
        if any(
            status == "revoked" and candidate_status[key_id] != "revoked"
            for key_id, status in current_status.items()
        ):
            raise UpdateOriginError("Una chiave trust revocata non può essere riattivata.")

    def _check_sequence(
        self, endpoint, endpoint_signature, plan, plan_bytes, signature_bytes, keys,
    ):
        endpoint_present = endpoint.exists() or endpoint.is_symlink()
        signature_present = endpoint_signature.exists() or endpoint_signature.is_symlink()
        if not endpoint_present and not signature_present:
            return
        if not endpoint_present or not signature_present:
            raise UpdateOriginError("Stato del canale incompleto.")
        current_plan = _secure_bytes(endpoint, MAX_PLAN_SIZE, trusted=True)
        current_signature = _secure_bytes(
            endpoint_signature, MAX_SIGNATURE_SIZE, trusted=True,
        )
        if current_plan == plan_bytes:
            return
        with tempfile.TemporaryDirectory(prefix="current-", dir=self.root) as temporary_name:
            temporary = Path(temporary_name)
            current_plan_path = temporary / "current.json"
            current_signature_path = temporary / "current.sig"
            current_plan_path.write_bytes(current_plan)
            current_signature_path.write_bytes(current_signature)
            self._verify_signature_any(current_plan_path, current_signature_path, keys)
            current = validate_plan(
                _read_json(current_plan_path), self.origin, check_time=False,
            )
        if platform_key(current["platform"]) != platform_key(plan["platform"]):
            raise UpdateOriginError("Il canale esistente appartiene a una piattaforma diversa.")
        if plan["sequence"] <= current["sequence"]:
            raise UpdateOriginError("La sequenza deve crescere in modo strettamente monotono.")

    @staticmethod
    def _verify_signature(plan: Path, signature: Path, public_key: Path) -> None:
        try:
            result = subprocess.run(
                [
                    "/usr/bin/openssl", "dgst", "-sha256", "-verify", str(public_key),
                    "-signature", str(signature), str(plan),
                ],
                check=False, capture_output=True, timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise UpdateOriginError("Verifica firma non disponibile.") from error
        if result.returncode != 0:
            raise UpdateOriginError("Firma del piano release non valida.")

    @classmethod
    def _verify_signature_any(
        cls, plan: Path, signature: Path, public_keys: list[Path],
    ) -> Path:
        for public_key in public_keys:
            try:
                cls._verify_signature(plan, signature, public_key)
                return public_key
            except UpdateOriginError as error:
                if str(error) != "Firma del piano release non valida.":
                    raise
        raise UpdateOriginError("Firma del piano release non valida.")
