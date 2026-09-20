"""Command-line interface for offline plan preparation and server publication."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

from .model import UpdateOriginError, build_plan
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
    result = Publisher(args.root, args.public_key, args.origin).publish(
        channel=args.channel, plan_path=args.plan,
        signature_path=args.signature, bundle_path=args.bundle,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


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
    publish.add_argument("--plan", required=True, type=Path)
    publish.add_argument("--signature", required=True, type=Path)
    publish.add_argument("--bundle", required=True, type=Path)
    publish.set_defaults(handler=_publish)
    return root


def main(argv=None) -> None:
    args = parser().parse_args(argv)
    try:
        args.handler(args)
    except (OSError, UpdateOriginError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
