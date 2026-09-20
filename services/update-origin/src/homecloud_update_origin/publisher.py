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
from pathlib import Path

from .model import CHANNEL_PATTERN, UpdateOriginError, platform_key, validate_plan


MAX_PLAN_SIZE = 256 * 1024
MAX_SIGNATURE_SIZE = 64 * 1024
MAX_BUNDLE_SIZE = 1024 * 1024 * 1024


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


class Publisher:
    def __init__(self, root: Path, public_key: Path, origin: str):
        self.root = Path(root)
        self.public_key = Path(public_key)
        self.origin = origin

    def publish(
        self, *, channel: str, plan_path: Path, signature_path: Path, bundle_path: Path,
    ) -> dict:
        if not isinstance(channel, str) or not CHANNEL_PATTERN.fullmatch(channel):
            raise UpdateOriginError("Canale release non valido.")
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
            return self._publish_locked(
                channel=channel, plan_path=Path(plan_path),
                signature_path=Path(signature_path), bundle_path=Path(bundle_path),
            )

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
            key_copy = staging / "release-public.pem"
            plan_digest, _ = _snapshot(plan_path, plan_copy, MAX_PLAN_SIZE)
            _snapshot(signature_path, signature_copy, MAX_SIGNATURE_SIZE)
            _snapshot(self.public_key, key_copy, MAX_SIGNATURE_SIZE, trusted=True)
            self._verify_signature(plan_copy, signature_copy, key_copy)
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
            self._check_sequence(endpoint, endpoint_signature, plan, plan_bytes, signature_bytes, key_copy)

            bundle_target = self.root / "releases" / f"{bundle_digest}.tar.gz"
            _install_content_addressed(bundle_copy, bundle_target, bundle_digest, bundle_size)
            immutable = self.root / "plans" / key / f"{plan['sequence']}-{plan_digest}.json"
            immutable_signature = immutable.with_name(immutable.name + ".sig")
            if (
                immutable.exists() or immutable.is_symlink()
                or immutable_signature.exists() or immutable_signature.is_symlink()
            ):
                if (
                    _secure_bytes(immutable, MAX_PLAN_SIZE, trusted=True) != plan_bytes
                    or _secure_bytes(
                        immutable_signature, MAX_SIGNATURE_SIZE, trusted=True,
                    ) != signature_bytes
                ):
                    raise UpdateOriginError("Il record immutabile della sequenza è già occupato.")
            else:
                _atomic_bytes(immutable_signature, signature_bytes)
                _atomic_bytes(immutable, plan_bytes)

            # Publish the signature first: a concurrent client can only see a
            # temporary signature mismatch, never an unsigned accepted plan.
            _atomic_bytes(endpoint_signature, signature_bytes)
            _atomic_bytes(endpoint, plan_bytes)
            return {
                "channel": channel,
                "platform": key,
                "sequence": plan["sequence"],
                "plan_sha256": plan_digest,
                "bundle_sha256": bundle_digest,
                "metadata_path": str(endpoint.relative_to(self.root)),
            }

    def _check_sequence(self, endpoint, endpoint_signature, plan, plan_bytes, signature_bytes, key):
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
        if current_plan == plan_bytes and current_signature == signature_bytes:
            return
        with tempfile.TemporaryDirectory(prefix="current-", dir=self.root) as temporary_name:
            temporary = Path(temporary_name)
            current_plan_path = temporary / "current.json"
            current_signature_path = temporary / "current.sig"
            current_plan_path.write_bytes(current_plan)
            current_signature_path.write_bytes(current_signature)
            self._verify_signature(current_plan_path, current_signature_path, key)
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
