"""Strict release-plan model shared by preparation and publication."""

from __future__ import annotations

import datetime as dt
import re
import urllib.parse


COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
PACKAGE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9+.-]{0,79}$")
VERSION_PATTERN = re.compile(r"^[0-9][0-9A-Za-z.+:~_-]{0,119}$")
PLATFORM_PATTERN = re.compile(r"^[a-z0-9._-]{1,32}$")
CHANNEL_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")
HOST_LABEL_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


class UpdateOriginError(RuntimeError):
    """A release cannot be prepared or published safely."""


def normalize_origin(value: str) -> str:
    if not isinstance(value, str):
        raise UpdateOriginError("L'origine pubblica deve essere una stringa HTTPS.")
    try:
        parsed = urllib.parse.urlsplit(value)
        port = parsed.port
    except ValueError as error:
        raise UpdateOriginError("Origine pubblica non valida.") from error
    hostname = parsed.hostname or ""
    if (
        parsed.scheme != "https" or not parsed.hostname or port not in (None, 443)
        or parsed.username or parsed.password or parsed.query or parsed.fragment
        or parsed.path not in ("", "/")
        or len(hostname) > 253 or hostname.endswith(".") or "." not in hostname
        or any(not HOST_LABEL_PATTERN.fullmatch(label) for label in hostname.split("."))
    ):
        raise UpdateOriginError("L'origine pubblica deve essere un host HTTPS sulla porta 443.")
    return f"https://{hostname}"


def platform_key(platform: dict) -> str:
    return f"{platform['os_id']}-{platform['os_version']}-{platform['architecture']}"


def _timestamp(value: str) -> dt.datetime:
    if not isinstance(value, str) or len(value) > 40 or not value.endswith("Z"):
        raise UpdateOriginError("Timestamp del piano non valido.")
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise UpdateOriginError("Timestamp del piano non valido.") from error
    if parsed.utcoffset() != dt.timedelta(0):
        raise UpdateOriginError("Il timestamp del piano deve essere UTC.")
    return parsed


def validate_plan(plan: dict, origin: str, *, now=None, check_time=True) -> dict:
    origin = normalize_origin(origin)
    expected = {
        "schema", "product", "sequence", "published_at", "expires_at",
        "platform", "homecloud", "linux",
    }
    if (
        not isinstance(plan, dict) or set(plan) != expected
        or type(plan.get("schema")) is not int or plan["schema"] != 1
        or plan.get("product") != "homecloud"
        or type(plan.get("sequence")) is not int
        or not 1 <= plan["sequence"] <= 2**63 - 1
    ):
        raise UpdateOriginError("Piano aggiornamenti non valido.")
    published = _timestamp(plan.get("published_at"))
    expires = _timestamp(plan.get("expires_at"))
    current = now or dt.datetime.now(dt.timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise UpdateOriginError("L'orario di validazione deve includere il fuso orario.")
    if expires <= published:
        raise UpdateOriginError("Intervallo temporale del piano non valido.")
    if expires - published > dt.timedelta(days=31):
        raise UpdateOriginError("Il piano non può restare valido per più di 31 giorni.")
    if check_time and (published > current + dt.timedelta(minutes=10) or expires <= current):
        raise UpdateOriginError("Piano scaduto o non ancora valido.")

    platform = plan.get("platform")
    if (
        not isinstance(platform, dict)
        or set(platform) != {"os_id", "os_version", "architecture"}
        or any(
            not isinstance(platform.get(key), str)
            or not PLATFORM_PATTERN.fullmatch(platform[key])
            for key in platform
        )
    ):
        raise UpdateOriginError("Piattaforma del piano non valida.")
    if platform not in (
        {"os_id": "debian", "os_version": "12", "architecture": "arm64"},
        {"os_id": "debian", "os_version": "13", "architecture": "arm64"},
    ):
        raise UpdateOriginError("Piattaforma non supportata dall'origine HomeCloud.")

    target = plan.get("homecloud")
    if (
        not isinstance(target, dict)
        or set(target) != {
            "commit", "release_sequence", "bundle_url", "bundle_sha256", "bundle_size",
        }
        or not isinstance(target.get("commit"), str)
        or not COMMIT_PATTERN.fullmatch(target["commit"])
        or type(target.get("release_sequence")) is not int
        or target["release_sequence"] < 1
        or not isinstance(target.get("bundle_sha256"), str)
        or not HASH_PATTERN.fullmatch(target["bundle_sha256"])
        or type(target.get("bundle_size")) is not int
        or not 1 <= target["bundle_size"] <= 1024 * 1024 * 1024
    ):
        raise UpdateOriginError("Release HomeCloud nel piano non valida.")
    expected_bundle_url = f"{origin}/releases/{target['bundle_sha256']}.tar.gz"
    if target.get("bundle_url") != expected_bundle_url:
        raise UpdateOriginError("Il bundle non usa il percorso content-addressed dell'origine.")

    linux = plan.get("linux")
    packages = linux.get("packages") if isinstance(linux, dict) else None
    if (
        not isinstance(linux, dict)
        or set(linux) != {"requires_homecloud_commit", "packages", "reboot_required"}
        or linux.get("requires_homecloud_commit") != target["commit"]
        or type(linux.get("reboot_required")) is not bool
        or not isinstance(packages, list) or len(packages) > 64
    ):
        raise UpdateOriginError("Piano pacchetti Linux non valido.")
    names = []
    for package in packages:
        if (
            not isinstance(package, dict)
            or set(package) != {"name", "version", "reason"}
            or not isinstance(package.get("name"), str)
            or not PACKAGE_PATTERN.fullmatch(package["name"])
            or not isinstance(package.get("version"), str)
            or not VERSION_PATTERN.fullmatch(package["version"])
            or package.get("reason") not in {"runtime", "security"}
        ):
            raise UpdateOriginError("Pacchetto Linux nel piano non valido.")
        names.append(package["name"])
    if names != sorted(set(names)):
        raise UpdateOriginError("I pacchetti Linux devono essere univoci e ordinati.")
    return plan


def build_plan(
    *, origin: str, sequence: int, published_at: str, expires_at: str,
    os_id: str, os_version: str, architecture: str, commit: str,
    release_sequence: int, bundle_sha256: str, bundle_size: int,
    packages: list[dict], reboot_required: bool,
) -> dict:
    origin = normalize_origin(origin)
    plan = {
        "schema": 1,
        "product": "homecloud",
        "sequence": sequence,
        "published_at": published_at,
        "expires_at": expires_at,
        "platform": {
            "os_id": os_id,
            "os_version": os_version,
            "architecture": architecture,
        },
        "homecloud": {
            "commit": commit,
            "release_sequence": release_sequence,
            "bundle_url": f"{origin}/releases/{bundle_sha256}.tar.gz",
            "bundle_sha256": bundle_sha256,
            "bundle_size": bundle_size,
        },
        "linux": {
            "requires_homecloud_commit": commit,
            "packages": packages,
            "reboot_required": reboot_required,
        },
    }
    return validate_plan(plan, origin)
