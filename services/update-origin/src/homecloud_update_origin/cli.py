"""Command-line interface for offline plan preparation and server publication."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import stat
import subprocess
import tempfile
from pathlib import Path

from .model import UpdateOriginError, build_plan, validate_trust_metadata
from .publisher import Publisher


def _sha256(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            size += len(block)
            digest.update(block)
    return digest.hexdigest(), size


def _package(value: str) -> dict:
    fields = value.split("=", 2)
    if len(fields) != 3:
        raise argparse.ArgumentTypeError("usa NOME=VERSIONE=runtime|security")
    return {"name": fields[0], "version": fields[1], "reason": fields[2]}


def _public_key(path: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise UpdateOriginError(f"Chiave pubblica non apribile: {path}") from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or not 1 <= metadata.st_size <= 16 * 1024:
            raise UpdateOriginError(f"Chiave pubblica non valida: {path}")
        payload = bytearray()
        while len(payload) < metadata.st_size:
            block = os.read(descriptor, metadata.st_size - len(payload))
            if not block:
                break
            payload.extend(block)
    finally:
        os.close(descriptor)
    if len(payload) != metadata.st_size:
        raise UpdateOriginError(f"Chiave pubblica modificata durante la lettura: {path}")
    with tempfile.TemporaryDirectory(prefix="homecloud-key-check-") as temporary:
        snapshot = Path(temporary) / "key.pem"
        snapshot.write_bytes(payload)
        try:
            result = subprocess.run(
                ["/usr/bin/openssl", "pkey", "-pubin", "-in", str(snapshot), "-noout"],
                check=False, capture_output=True, timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise UpdateOriginError("Validazione chiave pubblica non disponibile.") from error
    if result.returncode != 0:
        raise UpdateOriginError(f"Chiave pubblica non valida: {path}")
    return bytes(payload)


def _utc_timestamp(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _prepare(args) -> None:
    digest, size = _sha256(args.bundle)
    now = dt.datetime.now(dt.timezone.utc)
    packages = sorted(args.package, key=lambda item: item["name"])
    plan = build_plan(
        origin=args.origin, sequence=args.sequence,
        published_at=_utc_timestamp(now),
        expires_at=_utc_timestamp(now + dt.timedelta(days=args.valid_days)),
        os_id=args.os_id, os_version=args.os_version, architecture=args.architecture,
        commit=args.commit, release_sequence=args.release_sequence,
        bundle_sha256=digest, bundle_size=size, packages=packages,
        reboot_required=args.reboot_required,
    )
    if args.output.exists() or args.output.is_symlink():
        raise UpdateOriginError("Il piano di destinazione esiste già.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(plan, indent=2, sort_keys=True, separators=(",", ": ")) + "\n",
        encoding="utf-8",
    )
    args.output.chmod(0o644)
    print(f"[OK] piano non firmato: {args.output}")
    print(f"[BUNDLE] size={size} sha256={digest}")
    print("Firma il piano offline; non copiare la chiave privata sul server.")


def _publish(args) -> None:
    result = _publisher(args).publish(
        channel=args.channel, plan_path=args.plan,
        signature_path=args.signature, bundle_path=args.bundle,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


def _promote(args) -> None:
    result = _publisher(args).promote(
        platform=args.platform, source_channel=args.source_channel,
        target_channel=args.target_channel,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


def _publish_trust(args) -> None:
    result = _publisher(args).publish_trust(
        channel=args.channel, metadata_path=args.metadata,
        signature_path=args.signature, root_public_key=args.root_public_key,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


def _publisher(args) -> Publisher:
    key_directory = args.key_directory
    if key_directory.exists() or key_directory.is_symlink():
        if key_directory.is_symlink() or not key_directory.is_dir():
            raise UpdateOriginError("Directory keyring release non sicura.")
        keys = sorted(key_directory.glob("*.pem"))
    else:
        keys = [args.public_key]
    keys.extend(args.additional_public_key)
    return Publisher(args.root, keys, args.origin)


def _prepare_trust(args) -> None:
    root_key = _public_key(args.root_public_key)
    entries = []
    for status, paths in (("active", args.active_key), ("revoked", args.revoked_key)):
        for path in paths:
            payload = _public_key(path)
            try:
                pem = payload.decode("ascii")
            except UnicodeDecodeError as error:
                raise UpdateOriginError(f"Chiave pubblica non ASCII: {path}") from error
            entries.append({
                "key_id": hashlib.sha256(payload).hexdigest(),
                "algorithm": "rsa-sha256",
                "public_key_pem": pem,
                "status": status,
            })
    now = dt.datetime.now(dt.timezone.utc)
    metadata = {
        "schema": 1,
        "product": "homecloud-trust",
        "sequence": args.sequence,
        "published_at": _utc_timestamp(now),
        "expires_at": _utc_timestamp(now + dt.timedelta(days=args.valid_days)),
        "root_key_id": hashlib.sha256(root_key).hexdigest(),
        "release_keys": sorted(entries, key=lambda item: item["key_id"]),
    }
    validate_trust_metadata(metadata, metadata["root_key_id"])
    if args.output.exists() or args.output.is_symlink():
        raise UpdateOriginError("I metadata trust di destinazione esistono già.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(metadata, indent=2, sort_keys=True, separators=(",", ": ")) + "\n",
        encoding="utf-8",
    )
    args.output.chmod(0o644)
    print(f"[OK] metadata trust non firmati: {args.output}")
    print("Firma offline con la trust root; non copiarne la chiave privata sul server.")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Origine aggiornamenti HomeCloud")
    subparsers = root.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="crea un piano da firmare offline")
    prepare.add_argument("--origin", required=True)
    prepare.add_argument("--sequence", required=True, type=int)
    prepare.add_argument("--valid-days", type=int, choices=range(1, 31), default=7)
    prepare.add_argument("--os-id", choices=("debian",), default="debian")
    prepare.add_argument("--os-version", choices=("12", "13"), required=True)
    prepare.add_argument("--architecture", choices=("arm64",), default="arm64")
    prepare.add_argument("--commit", required=True)
    prepare.add_argument("--release-sequence", required=True, type=int)
    prepare.add_argument("--package", action="append", type=_package, default=[])
    prepare.add_argument("--reboot-required", action="store_true")
    prepare.add_argument("--bundle", required=True, type=Path)
    prepare.add_argument("--output", required=True, type=Path)
    prepare.set_defaults(handler=_prepare)

    publish = subparsers.add_parser("publish", help="verifica e pubblica una release firmata")
    publish.add_argument("--origin", required=True)
    publish.add_argument("--channel", default="stable")
    publish.add_argument("--root", type=Path, default=Path("/srv/homecloud-updates"))
    publish.add_argument(
        "--public-key", type=Path,
        default=Path("/etc/homecloud-update-origin/release-signing-public.pem"),
    )
    publish.add_argument(
        "--additional-public-key", action="append", type=Path, default=[],
        help="chiave release pubblica aggiuntiva durante l'overlap",
    )
    publish.add_argument(
        "--key-directory", type=Path,
        default=Path("/etc/homecloud-update-origin/release-keys.d"),
    )
    publish.add_argument("--plan", required=True, type=Path)
    publish.add_argument("--signature", required=True, type=Path)
    publish.add_argument("--bundle", required=True, type=Path)
    publish.set_defaults(handler=_publish)

    promote = subparsers.add_parser(
        "promote", help="promuove una release verificata senza ricostruirla",
    )
    promote.add_argument("--origin", required=True)
    promote.add_argument("--platform", choices=("debian-12-arm64", "debian-13-arm64"), required=True)
    promote.add_argument("--source-channel", default="staging")
    promote.add_argument("--target-channel", default="stable")
    promote.add_argument("--root", type=Path, default=Path("/srv/homecloud-updates"))
    promote.add_argument(
        "--public-key", type=Path,
        default=Path("/etc/homecloud-update-origin/release-signing-public.pem"),
    )
    promote.add_argument(
        "--additional-public-key", action="append", type=Path, default=[],
        help="chiave release pubblica aggiuntiva durante l'overlap",
    )
    promote.add_argument(
        "--key-directory", type=Path,
        default=Path("/etc/homecloud-update-origin/release-keys.d"),
    )
    promote.set_defaults(handler=_promote)

    trust = subparsers.add_parser(
        "publish-trust", help="pubblica metadata keyring firmati dalla root offline",
    )
    trust.add_argument("--origin", required=True)
    trust.add_argument("--channel", default="stable")
    trust.add_argument("--root", type=Path, default=Path("/srv/homecloud-updates"))
    trust.add_argument(
        "--public-key", type=Path,
        default=Path("/etc/homecloud-update-origin/release-signing-public.pem"),
    )
    trust.add_argument(
        "--additional-public-key", action="append", type=Path, default=[],
    )
    trust.add_argument(
        "--key-directory", type=Path,
        default=Path("/etc/homecloud-update-origin/release-keys.d"),
    )
    trust.add_argument("--root-public-key", required=True, type=Path)
    trust.add_argument("--metadata", required=True, type=Path)
    trust.add_argument("--signature", required=True, type=Path)
    trust.set_defaults(handler=_publish_trust)

    prepare_trust = subparsers.add_parser(
        "prepare-trust", help="crea metadata keyring da firmare con la root offline",
    )
    prepare_trust.add_argument("--sequence", required=True, type=int)
    prepare_trust.add_argument("--valid-days", type=int, choices=range(1, 366), default=90)
    prepare_trust.add_argument("--root-public-key", required=True, type=Path)
    prepare_trust.add_argument("--active-key", action="append", type=Path, default=[])
    prepare_trust.add_argument("--revoked-key", action="append", type=Path, default=[])
    prepare_trust.add_argument("--output", required=True, type=Path)
    prepare_trust.set_defaults(handler=_prepare_trust)
    return root


def main(argv=None) -> None:
    args = parser().parse_args(argv)
    try:
        args.handler(args)
    except (OSError, UpdateOriginError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
