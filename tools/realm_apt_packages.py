#!/usr/bin/env python3
"""Resolve, validate, and refresh Realm's snapshot-pinned apt package locks."""

from __future__ import annotations

import argparse
import copy
import difflib
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any
import urllib.request

from realm_profiles import load_json, load_profiles, resolve_profile, validate_catalog


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "1.0.0"
RESOLVER_VERSION = "1.0.0"
SNAPSHOT_PATTERN = re.compile(r"^[0-9]{8}T[0-9]{6}Z$")
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
ARCHITECTURES = {
    "amd64": "linux/amd64",
    "arm64": "linux/arm64",
}
DEFAULT_CATALOG = ROOT / "catalog" / "capabilities.json"
DEFAULT_PROFILES = ROOT / "profiles"
DEFAULT_CONFIG = ROOT / "config" / "debian-trixie.json"
DEFAULT_LOCK_DIRECTORY = ROOT / "images" / "base" / "packages" / "locks"
DEFAULT_DOCKERFILE = ROOT / "images" / "base" / "Dockerfile"


class ContractError(RuntimeError):
    """Raised when a Realm package contract cannot be trusted or resolved."""


def canonical_json(value: Any) -> str:
    """Return the stable JSON representation used for checksums and comparisons."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def object_checksum(value: Any) -> str:
    """Return a sha256 checksum for a parsed JSON value."""

    digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def lock_checksum(lock: dict[str, Any]) -> str:
    """Return the checksum for a lock while excluding its checksum field."""

    content = {key: value for key, value in lock.items() if key != "lock_checksum"}
    return object_checksum(content)


def snapshot_to_iso8601(snapshot: str) -> str:
    """Convert a Debian snapshot identifier to a deterministic ISO-8601 value."""

    if not SNAPSHOT_PATTERN.fullmatch(snapshot):
        raise ContractError(f"invalid snapshot identifier: {snapshot}")
    return (
        f"{snapshot[0:4]}-{snapshot[4:6]}-{snapshot[6:8]}T"
        f"{snapshot[9:11]}:{snapshot[11:13]}:{snapshot[13:15]}Z"
    )


def _unique_strings(value: Any, path: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    if not isinstance(value, list) or not value:
        return [], [f"{path} must be a non-empty array"]
    if any(not isinstance(item, str) or not item for item in value):
        errors.append(f"{path} must contain non-empty strings")
    if isinstance(value, list) and len(value) != len(set(value)):
        errors.append(f"{path} must not contain duplicates")
    return value if isinstance(value, list) else [], errors


def validate_configuration(
    config: dict[str, Any], catalog: dict[str, Any]
) -> list[str]:
    """Validate snapshot, repository, architecture, and base-image invariants."""

    errors = validate_catalog(catalog)
    expected_fields = {
        "schema_version",
        "distribution",
        "release",
        "snapshot",
        "security_snapshot",
        "source_pins",
        "repositories",
        "base_image",
        "architectures",
        "resolver_keyring",
    }
    if set(config) != expected_fields:
        errors.append(
            "apt config fields differ from the v1 contract: "
            + ", ".join(sorted(set(config) ^ expected_fields))
        )
    if config.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"apt config schema_version must be {SCHEMA_VERSION}")
    if config.get("distribution") != "debian":
        errors.append("apt config distribution must be debian")
    release = config.get("release")
    if not isinstance(release, str) or not release:
        errors.append("apt config release must be a non-empty string")
    for field in ("snapshot", "security_snapshot"):
        value = config.get(field)
        if not isinstance(value, str) or not SNAPSHOT_PATTERN.fullmatch(value):
            errors.append(f"apt config {field} must use YYYYMMDDTHHMMSSZ")
    if (
        SNAPSHOT_PATTERN.fullmatch(str(config.get("snapshot", "")))
        and SNAPSHOT_PATTERN.fullmatch(str(config.get("security_snapshot", "")))
        and config["snapshot"] != config["security_snapshot"]
    ):
        errors.append("archive and security snapshots must use one coordinated timestamp")

    source_pins = config.get("source_pins")
    catalog_pins = catalog.get("source_pins", {})
    expected_pin_fields = {"archive", "security", "base_image"}
    if not isinstance(source_pins, dict) or set(source_pins) != expected_pin_fields:
        errors.append("apt config source_pins must name archive, security, and base_image")
        source_pins = {}
    for role, key in source_pins.items():
        if key not in catalog_pins:
            errors.append(f"apt config {role} source pin does not exist: {key}")

    snapshot = config.get("snapshot", "")
    security_snapshot = config.get("security_snapshot", "")
    if source_pins.get("archive") in catalog_pins:
        expected = f"https://snapshot.debian.org/archive/debian/{snapshot}/"
        if catalog_pins[source_pins["archive"]] != expected:
            errors.append("Debian archive source pin and configured snapshot disagree")
    if source_pins.get("security") in catalog_pins:
        expected = (
            "https://snapshot.debian.org/archive/debian-security/"
            f"{security_snapshot}/"
        )
        if catalog_pins[source_pins["security"]] != expected:
            errors.append("Debian security source pin and configured snapshot disagree")

    repositories = config.get("repositories")
    if not isinstance(repositories, dict) or set(repositories) != {"archive", "security"}:
        errors.append("apt config repositories must define archive and security")
        repositories = {}
    for name, repository in repositories.items():
        if not isinstance(repository, dict) or set(repository) != {
            "suites",
            "components",
            "inrelease_sha256",
        }:
            errors.append(
                f"repository {name} must define suites, components, and InRelease hashes"
            )
            continue
        suites, suite_errors = _unique_strings(
            repository.get("suites"), f"{name}.suites"
        )
        _, component_errors = _unique_strings(
            repository.get("components"), f"{name}.components"
        )
        errors.extend(suite_errors + component_errors)
        hashes = repository.get("inrelease_sha256")
        if not isinstance(hashes, dict) or set(hashes) != set(suites):
            errors.append(f"repository {name} must pin every suite InRelease hash")
        elif any(
            not re.fullmatch(r"[0-9a-f]{64}", str(value))
            for value in hashes.values()
        ):
            errors.append(f"repository {name} has an invalid InRelease hash")

    base_image = config.get("base_image")
    if not isinstance(base_image, dict):
        errors.append("apt config base_image must be an object")
        base_image = {}
    expected_base_fields = {"repository", "tag", "digest", "verified_at"}
    if set(base_image) != expected_base_fields:
        errors.append("apt config base_image fields differ from the v1 contract")
    if not DIGEST_PATTERN.fullmatch(str(base_image.get("digest", ""))):
        errors.append("apt config base_image digest must be sha256-pinned")
    if str(base_image.get("tag", "")).lower() in {"", "latest", "edge", "dev"}:
        errors.append("apt config base_image tag must be immutable and readable")
    if not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z",
        str(base_image.get("verified_at", "")),
    ):
        errors.append("apt config base_image verified_at must be UTC ISO-8601")
    if source_pins.get("base_image") in catalog_pins:
        expected = (
            f"{base_image.get('repository')}:{base_image.get('tag')}"
            f"@{base_image.get('digest')}"
        )
        if catalog_pins[source_pins["base_image"]] != expected:
            errors.append("base-image source pin and apt configuration disagree")

    architectures = config.get("architectures")
    if not isinstance(architectures, dict) or set(architectures) != set(ARCHITECTURES):
        errors.append("apt config architectures must be exactly amd64 and arm64")
        architectures = {}
    for architecture, platform in ARCHITECTURES.items():
        record = architectures.get(architecture)
        if not isinstance(record, dict) or set(record) != {
            "platform",
            "base_image_digest",
        }:
            errors.append(f"architecture {architecture} has an invalid record")
            continue
        if record.get("platform") != platform:
            errors.append(f"architecture {architecture} platform must be {platform}")
        if not DIGEST_PATTERN.fullmatch(str(record.get("base_image_digest", ""))):
            errors.append(f"architecture {architecture} image digest is not pinned")

    keyring = config.get("resolver_keyring")
    if not isinstance(keyring, dict) or set(keyring) != {
        "url",
        "sha256",
        "member",
        "member_sha256",
        "target",
    }:
        errors.append("apt config resolver_keyring fields differ from the v1 contract")
        keyring = {}
    if not re.fullmatch(r"[0-9a-f]{64}", str(keyring.get("sha256", ""))):
        errors.append("resolver keyring package must have a sha256 checksum")
    if not re.fullmatch(
        r"[0-9a-f]{64}", str(keyring.get("member_sha256", ""))
    ):
        errors.append("resolver keyring member must have a sha256 checksum")
    if not str(keyring.get("url", "")).startswith(
        "https://snapshot.debian.org/archive/debian/"
    ):
        errors.append("resolver keyring must come from an immutable Debian snapshot")
    if not str(keyring.get("target", "")).startswith("/"):
        errors.append("resolver keyring target must be an absolute image path")
    member = Path(str(keyring.get("member", "")))
    if member.is_absolute() or ".." in member.parts:
        errors.append("resolver keyring member must be a safe relative path")
    return sorted(set(errors))


def validate_dockerfile(config: dict[str, Any], catalog: dict[str, Any]) -> list[str]:
    """Verify the image recipe consumes the configured immutable base exactly."""

    try:
        dockerfile = DEFAULT_DOCKERFILE.read_text(encoding="utf-8")
    except OSError as error:
        return [f"failed to read {DEFAULT_DOCKERFILE}: {error}"]
    errors: list[str] = []
    pin_name = config.get("source_pins", {}).get("base_image")
    expected = catalog.get("source_pins", {}).get(pin_name)
    from_lines = re.findall(
        r"^FROM\s+(\S+)\s+AS\s+realm-base\s*$", dockerfile, re.MULTILINE
    )
    if from_lines != [expected]:
        errors.append("Dockerfile FROM does not equal the configured base-image pin")
    expected_frontend = catalog.get("source_pins", {}).get("dockerfile-frontend")
    if not dockerfile.startswith(f"# syntax={expected_frontend}\n"):
        errors.append("Dockerfile frontend does not equal the immutable catalog pin")
    if f'org.opencontainers.image.base.name="{expected}"' not in dockerfile:
        errors.append("Dockerfile base label does not equal the configured image pin")
    if "apt-get install" in dockerfile:
        errors.append("Dockerfile must not define an independent apt package list")
    if "debian-trixie-${TARGETARCH}.lock.json" not in dockerfile:
        errors.append("Dockerfile must select the architecture-bound package lock")
    for input_path in (
        "catalog/capabilities.json",
        "config/debian-trixie.json",
        "images/base/Dockerfile",
        "profiles/base.profile.json",
    ):
        if f"COPY {input_path} " not in dockerfile:
            errors.append(f"Dockerfile does not bind canonical input: {input_path}")
    return errors


def validate_oci_index(index: dict[str, Any], config: dict[str, Any]) -> list[str]:
    """Verify configured platform manifests are children of one OCI index."""

    errors: list[str] = []
    if index.get("schemaVersion") != 2:
        errors.append("base-image index must use OCI schema version 2")
    manifests = index.get("manifests")
    if not isinstance(manifests, list):
        return errors + ["base-image index has no manifest descriptors"]
    for architecture, record in config["architectures"].items():
        matches = [
            descriptor
            for descriptor in manifests
            if isinstance(descriptor, dict)
            and descriptor.get("platform", {}).get("os") == "linux"
            and descriptor.get("platform", {}).get("architecture") == architecture
        ]
        if len(matches) != 1:
            errors.append(
                f"base-image index must contain one linux/{architecture} manifest"
            )
            continue
        if matches[0].get("digest") != record["base_image_digest"]:
            errors.append(
                f"base-image index linux/{architecture} digest differs from config"
            )
    return errors


def fetch_and_verify_oci_index(config: dict[str, Any]) -> None:
    """Fetch the digest-addressed MCR index and verify its bytes and children."""

    repository = config["base_image"]["repository"]
    registry, separator, image_name = repository.partition("/")
    if not separator or not registry or not image_name:
        raise ContractError(f"invalid base-image repository: {repository}")
    expected_digest = config["base_image"]["digest"]
    url = f"https://{registry}/v2/{image_name}/manifests/{expected_digest}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": ", ".join(
                (
                    "application/vnd.oci.image.index.v1+json",
                    "application/vnd.docker.distribution.manifest.list.v2+json",
                )
            ),
            "User-Agent": "egohygiene-realm-apt-resolver/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            content = response.read()
            response_digest = response.headers.get("Docker-Content-Digest")
    except OSError as error:
        raise ContractError(f"failed to fetch pinned base-image index: {error}") from error
    actual_digest = f"sha256:{hashlib.sha256(content).hexdigest()}"
    if actual_digest != expected_digest or response_digest != expected_digest:
        raise ContractError(
            f"base-image index digest mismatch: expected {expected_digest}, "
            f"got {actual_digest}"
        )
    try:
        index = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ContractError(f"base-image index is not valid JSON: {error}") from error
    errors = validate_oci_index(index, config)
    if errors:
        raise ContractError("; ".join(errors))


def base_package_intent(
    catalog: dict[str, Any],
    profiles: dict[str, dict[str, Any]],
    platform: str,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Resolve base through Realm's canonical profile engine and retain ownership."""

    resolved, errors = resolve_profile(catalog, profiles, "base", platform, "docker")
    if errors or resolved is None:
        raise ContractError("base profile does not resolve: " + "; ".join(errors))
    if resolved["constraints"] != {
        "privileged": False,
        "services": False,
        "secrets": "forbidden",
    }:
        raise ContractError("base profile must forbid privilege, services, and secrets")

    ownership: dict[str, str] = {}
    for capability_name in resolved["capabilities"]:
        capability = catalog["capabilities"][capability_name]
        for package_name in capability["packages"]["apt"]:
            if package_name in ownership:
                raise ContractError(
                    f"apt package {package_name} is selected by both "
                    f"{ownership[package_name]} and {capability_name}"
                )
            ownership[package_name] = capability_name

    resolved_names = {
        package.removeprefix("apt:")
        for package in resolved["packages"]
        if package.startswith("apt:")
    }
    if resolved_names != set(ownership):
        raise ContractError("profile package output and capability ownership disagree")
    return (
        [
            {"name": name, "capability": ownership[name]}
            for name in sorted(ownership)
        ],
        resolved,
    )


def repository_records(
    config: dict[str, Any], catalog: dict[str, Any]
) -> list[dict[str, Any]]:
    """Resolve named catalog pins into installer-ready repository records."""

    records: list[dict[str, Any]] = []
    target_keyring = config["resolver_keyring"]["target"]
    for name in ("archive", "security"):
        pin_name = config["source_pins"][name]
        repository = config["repositories"][name]
        records.append(
            {
                "name": name,
                "uri": catalog["source_pins"][pin_name],
                "suites": repository["suites"],
                "components": repository["components"],
                "signed_by": target_keyring,
                "inrelease_sha256": repository["inrelease_sha256"],
            }
        )
    return records


def build_lock(
    config: dict[str, Any],
    catalog: dict[str, Any],
    profiles: dict[str, dict[str, Any]],
    architecture: str,
    candidates: dict[str, tuple[str, str]],
) -> dict[str, Any]:
    """Build a stable lock from already verified apt candidate data."""

    if architecture not in ARCHITECTURES:
        raise ContractError(f"unsupported architecture: {architecture}")
    intent, resolved = base_package_intent(
        catalog, profiles, ARCHITECTURES[architecture]
    )
    missing = sorted({entry["name"] for entry in intent} - set(candidates))
    unexpected = sorted(set(candidates) - {entry["name"] for entry in intent})
    if missing:
        raise ContractError("required packages did not resolve: " + ", ".join(missing))
    if unexpected:
        raise ContractError("resolver returned unexpected packages: " + ", ".join(unexpected))

    packages = []
    for entry in intent:
        version, package_architecture = candidates[entry["name"]]
        if not version:
            raise ContractError(f"package {entry['name']} has no candidate version")
        if package_architecture not in {"all", architecture}:
            raise ContractError(
                f"package {entry['name']} resolved for {package_architecture}, "
                f"not {architecture}"
            )
        packages.append(
            {
                "name": entry["name"],
                "version": version,
                "architecture": package_architecture,
                "capability": entry["capability"],
                "required": True,
            }
        )

    base = config["base_image"]
    lock: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "resolver_version": RESOLVER_VERSION,
        "catalog_version": catalog["catalog_version"],
        "catalog_checksum": object_checksum(catalog),
        "configuration_checksum": object_checksum(config),
        "profile_checksum": object_checksum(profiles["base"]),
        "resolved_profile_checksum": object_checksum(resolved),
        "profile": "base",
        "projection": "docker",
        "distribution": config["distribution"],
        "release": config["release"],
        "snapshot": config["snapshot"],
        "security_snapshot": config["security_snapshot"],
        "architecture": architecture,
        "platform": ARCHITECTURES[architecture],
        "generated_at": snapshot_to_iso8601(
            max(config["snapshot"], config["security_snapshot"])
        ),
        "base_image": {
            "repository": base["repository"],
            "tag": base["tag"],
            "digest": base["digest"],
            "platform_digest": config["architectures"][architecture][
                "base_image_digest"
            ],
        },
        "keyring": {
            "path": config["resolver_keyring"]["target"],
            "sha256": config["resolver_keyring"]["member_sha256"],
        },
        "repositories": repository_records(config, catalog),
        "packages": packages,
        "aliases": [],
        "transitional_packages": [],
        "unavailable_packages": [],
    }
    lock["lock_checksum"] = lock_checksum(lock)
    return lock


def validate_lock(
    lock: dict[str, Any],
    config: dict[str, Any],
    catalog: dict[str, Any],
    profiles: dict[str, dict[str, Any]],
    architecture: str,
) -> list[str]:
    """Validate a committed lock against current canonical inputs."""

    errors: list[str] = []
    expected_fields = {
        "schema_version",
        "resolver_version",
        "catalog_version",
        "catalog_checksum",
        "configuration_checksum",
        "profile_checksum",
        "resolved_profile_checksum",
        "profile",
        "projection",
        "distribution",
        "release",
        "snapshot",
        "security_snapshot",
        "architecture",
        "platform",
        "generated_at",
        "base_image",
        "keyring",
        "repositories",
        "packages",
        "aliases",
        "transitional_packages",
        "unavailable_packages",
        "lock_checksum",
    }
    if set(lock) != expected_fields:
        errors.append(
            "lock fields differ from the v1 contract: "
            + ", ".join(sorted(set(lock) ^ expected_fields))
        )
    expected_scalars = {
        "schema_version": SCHEMA_VERSION,
        "resolver_version": RESOLVER_VERSION,
        "catalog_version": catalog.get("catalog_version"),
        "catalog_checksum": object_checksum(catalog),
        "configuration_checksum": object_checksum(config),
        "profile_checksum": object_checksum(profiles["base"]),
        "profile": "base",
        "projection": "docker",
        "distribution": config.get("distribution"),
        "release": config.get("release"),
        "snapshot": config.get("snapshot"),
        "security_snapshot": config.get("security_snapshot"),
        "architecture": architecture,
        "platform": ARCHITECTURES.get(architecture),
        "generated_at": snapshot_to_iso8601(
            max(config.get("snapshot", ""), config.get("security_snapshot", ""))
        ),
    }
    try:
        _, resolved = base_package_intent(
            catalog, profiles, ARCHITECTURES[architecture]
        )
        expected_scalars["resolved_profile_checksum"] = object_checksum(resolved)
    except ContractError as error:
        errors.append(str(error))
    for field, expected in expected_scalars.items():
        if lock.get(field) != expected:
            errors.append(f"lock {field} does not match canonical input")

    expected_base = {
        "repository": config["base_image"]["repository"],
        "tag": config["base_image"]["tag"],
        "digest": config["base_image"]["digest"],
        "platform_digest": config["architectures"][architecture][
            "base_image_digest"
        ],
    }
    if lock.get("base_image") != expected_base:
        errors.append("lock base_image does not match the pinned image")
    expected_keyring = {
        "path": config["resolver_keyring"]["target"],
        "sha256": config["resolver_keyring"]["member_sha256"],
    }
    if lock.get("keyring") != expected_keyring:
        errors.append("lock keyring does not match the pinned resolver trust root")
    if lock.get("repositories") != repository_records(config, catalog):
        errors.append("lock repositories do not match configured snapshot pins")

    try:
        intent, _ = base_package_intent(
            catalog, profiles, ARCHITECTURES[architecture]
        )
    except ContractError as error:
        errors.append(str(error))
        intent = []
    expected_owners = {entry["name"]: entry["capability"] for entry in intent}
    packages = lock.get("packages")
    if not isinstance(packages, list):
        errors.append("lock packages must be an array")
        packages = []
    names = [entry.get("name") for entry in packages if isinstance(entry, dict)]
    if names != sorted(names):
        errors.append("lock packages must use stable name ordering")
    if len(names) != len(set(names)):
        errors.append("lock packages must not contain duplicates")
    if set(names) != set(expected_owners):
        errors.append("lock package names do not equal the resolved base profile")
    for entry in packages:
        if not isinstance(entry, dict) or set(entry) != {
            "name",
            "version",
            "architecture",
            "capability",
            "required",
        }:
            errors.append("lock package entry differs from the v1 contract")
            continue
        name = entry["name"]
        if not isinstance(entry["version"], str) or not entry["version"]:
            errors.append(f"lock package {name} has no exact version")
        if entry["architecture"] not in {"all", architecture}:
            errors.append(f"lock package {name} has an incompatible architecture")
        if entry["capability"] != expected_owners.get(name):
            errors.append(f"lock package {name} has incorrect capability ownership")
        if entry["required"] is not True:
            errors.append(f"lock package {name} must be required")
    for field in ("aliases", "transitional_packages", "unavailable_packages"):
        if lock.get(field) != []:
            errors.append(f"base lock {field} must be an explicit empty array")
    if lock.get("lock_checksum") != lock_checksum(lock):
        errors.append("lock checksum does not match lock content")
    return sorted(set(errors))


def _run(
    arguments: list[str],
    *,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        arguments,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    if result.returncode != 0:
        command = " ".join(arguments)
        diagnostics = (result.stdout + "\n" + result.stderr).strip()
        raise ContractError(f"command failed ({command}):\n{diagnostics}")
    return result


def _apt_options(
    root: Path,
    sources: Path,
    architecture: str,
) -> list[str]:
    current_user = pwd.getpwuid(os.geteuid()).pw_name
    return [
        "--config-file",
        str(root / "resolver.conf"),
        "--option",
        f"APT::Sandbox::User={current_user}",
        "--option",
        f"APT::Architecture={architecture}",
        "--option",
        f"APT::Architectures={architecture}",
        "--option",
        "Acquire::AllowInsecureRepositories=false",
        "--option",
        "Acquire::AllowDowngradeToInsecureRepositories=false",
        "--option",
        "Acquire::By-Hash=force",
        "--option",
        "Acquire::https::Verify-Host=true",
        "--option",
        "Acquire::https::Verify-Peer=true",
        "--option",
        "Acquire::Retries=3",
        "--option",
        "APT::Get::AllowUnauthenticated=false",
        "--option",
        f"Dir::Etc::main={root / 'apt.conf'}",
        "--option",
        f"Dir::Etc::parts={root / 'apt.conf.d'}",
        "--option",
        f"Dir::Etc::preferences={root / 'preferences'}",
        "--option",
        f"Dir::Etc::preferencesparts={root / 'preferences.d'}",
        "--option",
        f"Dir::Etc::sourcelist={sources}",
        "--option",
        f"Dir::Etc::sourceparts={root / 'sourceparts'}",
        "--option",
        f"Dir::State::status={root / 'status'}",
        "--option",
        f"Dir::State::Lists={root / 'lists'}",
        "--option",
        f"Dir::Cache::Archives={root / 'archives'}",
        "--option",
        f"Dir::Cache::pkgcache={root / 'pkgcache.bin'}",
        "--option",
        f"Dir::Cache::srcpkgcache={root / 'srcpkgcache.bin'}",
    ]


def _initialize_resolver_root(root: Path) -> None:
    """Create isolated, empty apt configuration and state directories."""

    for directory in (
        root / "apt.conf.d",
        root / "preferences.d",
        root / "sourceparts",
        root / "lists" / "partial",
        root / "archives" / "partial",
        root / "home",
    ):
        directory.mkdir(parents=True, exist_ok=True)
    for path in (root / "apt.conf", root / "preferences", root / "status"):
        path.write_text("", encoding="utf-8")
    isolated_paths = (
        f'Dir::Etc::main "{root / "apt.conf"}";\n'
        f'Dir::Etc::parts "{root / "apt.conf.d"}";\n'
        f'Dir::Etc::preferences "{root / "preferences"}";\n'
        f'Dir::Etc::preferencesparts "{root / "preferences.d"}";\n'
    )
    (root / "bootstrap.conf").write_text(isolated_paths, encoding="utf-8")
    (root / "resolver.conf").write_text(
        "#clear APT::Default-Release;\n"
        "#clear APT::Get::Post-Invoke;\n"
        "#clear APT::Get::Pre-Invoke;\n"
        "#clear APT::Update::Post-Invoke;\n"
        "#clear APT::Update::Post-Invoke-Success;\n"
        "#clear APT::Update::Pre-Invoke;\n"
        "#clear DPkg::Post-Invoke;\n"
        "#clear DPkg::Pre-Install-Pkgs;\n"
        "#clear DPkg::Pre-Invoke;\n"
        "#clear Acquire::Languages;\n"
        'Acquire::Languages "none";\n'
        + isolated_paths,
        encoding="utf-8",
    )


def _resolver_environment(root: Path) -> dict[str, str]:
    """Return an allowlisted resolver environment without host APT overrides."""

    environment = {
        "APT_CONFIG": str(root / "bootstrap.conf"),
        "HOME": str(root / "home"),
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": os.environ.get("PATH", "/usr/sbin:/usr/bin:/sbin:/bin"),
    }
    for name in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "no_proxy",
        "SSL_CERT_DIR",
        "SSL_CERT_FILE",
    ):
        if name in os.environ:
            environment[name] = os.environ[name]
    return environment


def verify_resolver_keyring(config: dict[str, Any], keyring: Path) -> None:
    """Verify the extracted resolver trust root before every network operation."""

    if not keyring.is_file():
        raise ContractError(f"Debian archive keyring does not exist: {keyring}")
    actual = hashlib.sha256(keyring.read_bytes()).hexdigest()
    expected = config["resolver_keyring"]["member_sha256"]
    if actual != expected:
        raise ContractError(
            f"Debian archive keyring checksum mismatch: expected {expected}, "
            f"got {actual}"
        )


def _write_resolver_sources(
    path: Path,
    repositories: list[dict[str, Any]],
    architecture: str,
    keyring: Path,
) -> None:
    lines: list[str] = []
    for repository in repositories:
        for suite in repository["suites"]:
            components = " ".join(repository["components"])
            lines.append(
                "deb "
                f"[arch={architecture} by-hash=force check-valid-until=no "
                f"signed-by={keyring}] "
                f"{repository['uri']} {suite} {components}"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_control_records(value: str) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for paragraph in re.split(r"\n\s*\n", value.strip()):
        record: dict[str, str] = {}
        current_key: str | None = None
        for line in paragraph.splitlines():
            if line[:1].isspace() and current_key:
                record[current_key] += "\n" + line.strip()
                continue
            if ":" not in line:
                continue
            current_key, child = line.split(":", 1)
            record[current_key] = child.strip()
        if record:
            records.append(record)
    return records


def _read_inrelease_hashes(
    lists_directory: Path, repositories: list[dict[str, Any]]
) -> dict[str, dict[str, str]]:
    """Read the signed snapshot metadata hashes apt accepted."""

    discovered: dict[str, dict[str, str]] = {}
    for repository in repositories:
        suite_hashes: dict[str, str] = {}
        for suite in repository["suites"]:
            matches = list(lists_directory.glob(f"*_dists_{suite}_InRelease"))
            if len(matches) != 1:
                raise ContractError(
                    f"expected exactly one InRelease file for {suite}, got {len(matches)}"
                )
            suite_hashes[suite] = hashlib.sha256(matches[0].read_bytes()).hexdigest()
        discovered[repository["name"]] = suite_hashes
    return discovered


def _verify_inrelease_hashes(
    lists_directory: Path, repositories: list[dict[str, Any]]
) -> None:
    """Verify apt consumed the exact signed snapshot metadata recorded in config."""

    discovered = _read_inrelease_hashes(lists_directory, repositories)
    for repository in repositories:
        for suite, expected in repository["inrelease_sha256"].items():
            actual = discovered[repository["name"]][suite]
            if actual != expected:
                raise ContractError(
                    f"InRelease checksum mismatch for {suite}: "
                    f"expected {expected}, got {actual}"
                )


def discover_inrelease_hashes(
    config: dict[str, Any],
    catalog: dict[str, Any],
    architecture: str,
    keyring: Path,
) -> dict[str, dict[str, str]]:
    """Fetch signed candidate metadata and return hashes for a refresh preview."""

    if architecture not in ARCHITECTURES:
        raise ContractError(f"unsupported architecture: {architecture}")
    verify_resolver_keyring(config, keyring)
    repositories = repository_records(config, catalog)
    with tempfile.TemporaryDirectory(prefix="realm-apt-metadata-") as temporary:
        root = Path(temporary)
        _initialize_resolver_root(root)
        sources = root / "realm-snapshot.list"
        _write_resolver_sources(sources, repositories, architecture, keyring.resolve())
        options = _apt_options(root, sources, architecture)
        _run(
            ["apt-get", *options, "--error-on=any", "--quiet=2", "update"],
            environment=_resolver_environment(root),
        )
        return _read_inrelease_hashes(root / "lists", repositories)


def resolve_candidates(
    config: dict[str, Any],
    catalog: dict[str, Any],
    profiles: dict[str, dict[str, Any]],
    architecture: str,
    keyring: Path,
) -> dict[str, tuple[str, str]]:
    """Resolve exact candidates from signed Debian snapshot metadata."""

    verify_resolver_keyring(config, keyring)
    intent, _ = base_package_intent(catalog, profiles, ARCHITECTURES[architecture])
    with tempfile.TemporaryDirectory(prefix="realm-apt-") as temporary:
        root = Path(temporary)
        _initialize_resolver_root(root)
        environment = _resolver_environment(root)
        sources = root / "realm-snapshot.list"
        _write_resolver_sources(
            sources,
            repository_records(config, catalog),
            architecture,
            keyring.resolve(),
        )
        options = _apt_options(root, sources, architecture)
        repositories = repository_records(config, catalog)
        _run(
            ["apt-get", *options, "--error-on=any", "--quiet=2", "update"],
            environment=environment,
        )
        _verify_inrelease_hashes(root / "lists", repositories)

        candidates: dict[str, tuple[str, str]] = {}
        apt_cache = ["apt-cache", *options]
        for entry in intent:
            package_name = entry["name"]
            policy = _run(
                [*apt_cache, "policy", package_name], environment=environment
            ).stdout
            match = re.search(r"^\s*Candidate:\s*(\S+)\s*$", policy, re.MULTILINE)
            if not match or match.group(1) == "(none)":
                raise ContractError(
                    f"required package has no {architecture} candidate: {package_name}"
                )
            version = match.group(1)
            details = _run(
                [*apt_cache, "show", f"{package_name}={version}"],
                environment=environment,
            ).stdout
            records = [
                record
                for record in _parse_control_records(details)
                if record.get("Package") == package_name
                and record.get("Version") == version
                and record.get("Architecture") in {"all", architecture}
            ]
            if not records:
                raise ContractError(
                    f"candidate metadata is incomplete for {package_name}={version}"
                )
            candidates[package_name] = (version, records[0]["Architecture"])

        specifications = [
            f"{name}={version}" for name, (version, _) in sorted(candidates.items())
        ]
        _run(
            [
                "apt-get",
                *options,
                "--simulate",
                "--no-install-recommends",
                "--no-remove",
                "install",
                *specifications,
            ],
            environment=environment,
        )
    return candidates


def resolve_lock(
    config: dict[str, Any],
    catalog: dict[str, Any],
    profiles: dict[str, dict[str, Any]],
    architecture: str,
    keyring: Path,
) -> dict[str, Any]:
    """Resolve candidates and return a complete checksummed lock."""

    configuration_errors = validate_configuration(config, catalog)
    if configuration_errors:
        raise ContractError("; ".join(configuration_errors))
    candidates = resolve_candidates(
        config, catalog, profiles, architecture, keyring
    )
    return build_lock(config, catalog, profiles, architecture, candidates)


def _safe_keyring_cache_directory(output_directory: Path) -> Path:
    """Resolve a cache target and reject broad or unrelated filesystem paths."""

    candidate = output_directory.resolve(strict=False)
    allowed_roots = ((ROOT / ".cache").resolve(), Path(tempfile.gettempdir()).resolve())
    if not any(
        candidate != root and candidate.is_relative_to(root) for root in allowed_roots
    ):
        raise ContractError(
            "keyring output must be below Realm's .cache directory or a temporary directory"
        )
    return candidate


def _atomic_copy(source: Path, target: Path, mode: int) -> None:
    """Replace one known cache file atomically without following target symlinks."""

    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", dir=target.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output, source.open("rb") as input_stream:
            shutil.copyfileobj(input_stream, output)
        temporary.chmod(mode)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def prepare_keyring(config: dict[str, Any], output_directory: Path) -> Path:
    """Download and checksum the pinned Debian archive keyring package."""

    output_directory = _safe_keyring_cache_directory(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    package_path = output_directory / "debian-archive-keyring.deb"
    keyring_path = output_directory / "debian-archive-keyring.pgp"
    with tempfile.TemporaryDirectory(
        prefix=".prepare-keyring-", dir=output_directory
    ) as temporary:
        staging = Path(temporary)
        staged_package = staging / "debian-archive-keyring.deb"
        extraction_root = staging / "root"
        request = urllib.request.Request(
            config["resolver_keyring"]["url"],
            headers={"User-Agent": "egohygiene-realm-apt-resolver/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                with staged_package.open("wb") as stream:
                    shutil.copyfileobj(response, stream)
        except OSError as error:
            raise ContractError(
                f"failed to download Debian archive keyring: {error}"
            ) from error
        actual = hashlib.sha256(staged_package.read_bytes()).hexdigest()
        expected = config["resolver_keyring"]["sha256"]
        if actual != expected:
            raise ContractError(
                f"Debian archive keyring package checksum mismatch: "
                f"expected {expected}, got {actual}"
            )
        _run(["dpkg-deb", "--extract", str(staged_package), str(extraction_root)])
        staged_keyring = extraction_root / config["resolver_keyring"]["member"]
        if not staged_keyring.is_file():
            raise ContractError(
                f"pinned package did not contain the keyring: {staged_keyring}"
            )
        actual_member = hashlib.sha256(staged_keyring.read_bytes()).hexdigest()
        expected_member = config["resolver_keyring"]["member_sha256"]
        if actual_member != expected_member:
            raise ContractError(
                f"Debian archive keyring member checksum mismatch: "
                f"expected {expected_member}, got {actual_member}"
            )
        _atomic_copy(staged_package, package_path, 0o644)
        _atomic_copy(staged_keyring, keyring_path, 0o644)
    verify_resolver_keyring(config, keyring_path)
    return keyring_path


def default_lock_path(directory: Path, config: dict[str, Any], architecture: str) -> Path:
    """Return the canonical lock path for an architecture."""

    return directory / f"{config['distribution']}-{config['release']}-{architecture}.lock.json"


def write_json(path: Path, value: Any) -> None:
    """Write reviewable JSON using stable formatting and a trailing newline."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def load_inputs(
    arguments: argparse.Namespace,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    """Load the apt configuration, capability catalog, and profiles."""

    config = load_json(arguments.config)
    catalog = load_json(arguments.catalog)
    profiles = load_profiles(arguments.profiles)
    return config, catalog, profiles


def check_contracts(arguments: argparse.Namespace) -> int:
    """Run offline configuration and lock validation."""

    config, catalog, profiles = load_inputs(arguments)
    errors = validate_configuration(config, catalog)
    errors.extend(validate_dockerfile(config, catalog))
    if errors:
        for error in sorted(set(errors)):
            print(f"apt contract validation failed: {error}", file=sys.stderr)
        return 1
    for architecture in ARCHITECTURES:
        path = default_lock_path(arguments.lock_directory, config, architecture)
        try:
            lock = load_json(path)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"failed to load {path}: {error}")
            continue
        errors.extend(
            f"{architecture}: {error}"
            for error in validate_lock(lock, config, catalog, profiles, architecture)
        )
    if errors:
        for error in sorted(set(errors)):
            print(f"apt contract validation failed: {error}", file=sys.stderr)
        return 1
    package_count = len(
        base_package_intent(catalog, profiles, ARCHITECTURES["amd64"])[0]
    )
    print(
        f"apt contracts valid: {package_count} base packages, "
        f"{len(ARCHITECTURES)} architectures"
    )
    return 0


def resolve_command(arguments: argparse.Namespace) -> int:
    """Resolve and write one architecture lock."""

    config, catalog, profiles = load_inputs(arguments)
    lock = resolve_lock(
        config, catalog, profiles, arguments.architecture, arguments.keyring
    )
    output = arguments.output or default_lock_path(
        arguments.lock_directory, config, arguments.architecture
    )
    write_json(output, lock)
    print(f"wrote {output}")
    return 0


def verify_lock_command(arguments: argparse.Namespace) -> int:
    """Replay snapshot resolution and compare it with a committed lock."""

    config, catalog, profiles = load_inputs(arguments)
    path = arguments.lock or default_lock_path(
        arguments.lock_directory, config, arguments.architecture
    )
    committed = load_json(path)
    resolved = resolve_lock(
        config, catalog, profiles, arguments.architecture, arguments.keyring
    )
    if committed != resolved:
        difference = difflib.unified_diff(
            json.dumps(committed, indent=2).splitlines(),
            json.dumps(resolved, indent=2).splitlines(),
            fromfile=str(path),
            tofile="fresh-resolution",
            lineterm="",
        )
        print("\n".join(difference), file=sys.stderr)
        return 1
    print(f"lock replay matches {path}")
    return 0


def verify_base_image_command(arguments: argparse.Namespace) -> int:
    """Verify the configured platform manifests against the pinned OCI index."""

    config = load_json(arguments.config)
    catalog = load_json(arguments.catalog)
    errors = validate_configuration(config, catalog)
    errors.extend(validate_dockerfile(config, catalog))
    if errors:
        raise ContractError("; ".join(errors))
    fetch_and_verify_oci_index(config)
    print("base-image OCI index and platform manifests match configuration")
    return 0


def report_image_size_command(arguments: argparse.Namespace) -> int:
    """Report expanded base, result, and delta sizes for one native image."""

    config = load_json(arguments.config)
    if arguments.architecture not in ARCHITECTURES:
        raise ContractError(f"unsupported architecture: {arguments.architecture}")
    base = config["base_image"]
    base_reference = f"{base['repository']}:{base['tag']}@{base['digest']}"
    platform = ARCHITECTURES[arguments.architecture]
    _run(["docker", "pull", "--platform", platform, base_reference])

    def expanded_size(reference: str) -> int:
        result = _run(["docker", "image", "inspect", reference])
        records = json.loads(result.stdout)
        if not isinstance(records, list) or len(records) != 1:
            raise ContractError(f"docker returned invalid size metadata for {reference}")
        size = records[0].get("Size")
        if not isinstance(size, int) or size <= 0:
            raise ContractError(f"docker returned an invalid image size for {reference}")
        return size

    base_size = expanded_size(base_reference)
    result_size = expanded_size(arguments.image)
    print(
        f"| {arguments.architecture} | {base_size} | {result_size} | "
        f"{result_size - base_size:+d} |"
    )
    return 0


def _debian_version_satisfies(left: str, operator: str, right: str) -> bool:
    """Compare two Debian versions using dpkg's canonical ordering rules."""

    result = subprocess.run(
        ["dpkg", "--compare-versions", left, operator, right],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode not in {0, 1}:
        raise ContractError(
            f"dpkg could not compare versions {left!r} and {right!r}: "
            f"{result.stderr.strip()}"
        )
    return result.returncode == 0


def classify_package_changes(
    current: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    """Classify package additions, removals, upgrades, and downgrades."""

    current_versions = {
        entry["name"]: entry["version"] for entry in current["packages"]
    }
    candidate_versions = {
        entry["name"]: entry["version"] for entry in candidate["packages"]
    }
    upgrades: list[dict[str, str]] = []
    downgrades: list[dict[str, str]] = []
    for name in sorted(set(current_versions) & set(candidate_versions)):
        before = current_versions[name]
        after = candidate_versions[name]
        if before == after:
            continue
        change = {"name": name, "from": before, "to": after}
        if _debian_version_satisfies(after, "gt", before):
            upgrades.append(change)
        elif _debian_version_satisfies(after, "lt", before):
            downgrades.append(change)
        else:
            raise ContractError(
                f"Debian versions are different but unordered for {name}: "
                f"{before} and {after}"
            )
    return {
        "added": sorted(set(candidate_versions) - set(current_versions)),
        "removed": sorted(set(current_versions) - set(candidate_versions)),
        "upgrades": upgrades,
        "downgrades": downgrades,
        "aliases": candidate["aliases"],
        "transitional_packages": candidate["transitional_packages"],
        "unavailable_packages": candidate["unavailable_packages"],
    }


def cross_architecture_version_differences(
    locks: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Report candidate versions that are not identical across architectures."""

    versions = {
        architecture: {
            entry["name"]: entry["version"] for entry in lock["packages"]
        }
        for architecture, lock in locks.items()
    }
    names = sorted(set().union(*(set(entries) for entries in versions.values())))
    differences: list[dict[str, Any]] = []
    for name in names:
        by_architecture = {
            architecture: entries.get(name)
            for architecture, entries in sorted(versions.items())
        }
        if len(set(by_architecture.values())) > 1:
            differences.append({"name": name, "versions": by_architecture})
    return differences


def refresh_command(arguments: argparse.Namespace) -> int:
    """Preview an intentional snapshot advance without editing canonical inputs."""

    config, catalog, profiles = load_inputs(arguments)
    candidate_config = copy.deepcopy(config)
    candidate_catalog = copy.deepcopy(catalog)
    candidate_config["snapshot"] = arguments.snapshot
    candidate_config["security_snapshot"] = arguments.security_snapshot
    candidate_catalog["source_pins"][candidate_config["source_pins"]["archive"]] = (
        "https://snapshot.debian.org/archive/debian/"
        f"{arguments.snapshot}/"
    )
    candidate_catalog["source_pins"][candidate_config["source_pins"]["security"]] = (
        "https://snapshot.debian.org/archive/debian-security/"
        f"{arguments.security_snapshot}/"
    )
    discovered_hashes = discover_inrelease_hashes(
        candidate_config,
        candidate_catalog,
        "amd64",
        arguments.keyring,
    )
    for repository_name, suite_hashes in discovered_hashes.items():
        candidate_config["repositories"][repository_name][
            "inrelease_sha256"
        ] = suite_hashes

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "current_snapshot": config["snapshot"],
        "candidate_snapshot": arguments.snapshot,
        "current_security_snapshot": config["security_snapshot"],
        "candidate_security_snapshot": arguments.security_snapshot,
        "candidate_source_pins": {
            name: candidate_catalog["source_pins"][pin_name]
            for name, pin_name in candidate_config["source_pins"].items()
            if name in {"archive", "security"}
        },
        "candidate_inrelease_sha256": discovered_hashes,
        "architectures": {},
    }
    candidate_locks: dict[str, dict[str, Any]] = {}
    for architecture in ARCHITECTURES:
        candidate = resolve_lock(
            candidate_config,
            candidate_catalog,
            profiles,
            architecture,
            arguments.keyring,
        )
        candidate_path = arguments.output_directory / default_lock_path(
            Path("."), candidate_config, architecture
        ).name
        write_json(candidate_path, candidate)
        current_path = default_lock_path(
            arguments.lock_directory, config, architecture
        )
        current = load_json(current_path)
        candidate_locks[architecture] = candidate
        report["architectures"][architecture] = {
            **classify_package_changes(current, candidate),
            "candidate_lock": str(candidate_path),
        }
    report["cross_architecture_version_differences"] = (
        cross_architecture_version_differences(candidate_locks)
    )
    report_path = arguments.output_directory / "change-report.json"
    write_json(report_path, report)
    print(f"refresh preview written to {arguments.output_directory}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--lock-directory", type=Path, default=DEFAULT_LOCK_DIRECTORY
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check", help="validate configuration and locks offline")

    prepare = subparsers.add_parser(
        "prepare-keyring", help="download and verify the resolver keyring"
    )
    prepare.add_argument("--output-directory", type=Path, required=True)

    resolve = subparsers.add_parser(
        "resolve", help="resolve and write one architecture lock"
    )
    resolve.add_argument("--architecture", choices=sorted(ARCHITECTURES), required=True)
    resolve.add_argument("--keyring", type=Path, required=True)
    resolve.add_argument("--output", type=Path)

    verify = subparsers.add_parser(
        "verify-lock", help="replay resolution and compare a committed lock"
    )
    verify.add_argument("--architecture", choices=sorted(ARCHITECTURES), required=True)
    verify.add_argument("--keyring", type=Path, required=True)
    verify.add_argument("--lock", type=Path)

    subparsers.add_parser(
        "verify-base-image",
        help="verify platform manifests in the pinned OCI base-image index",
    )

    image_size = subparsers.add_parser(
        "report-image-size",
        help="report expanded base, result, and delta image sizes",
    )
    image_size.add_argument(
        "--architecture", choices=sorted(ARCHITECTURES), required=True
    )
    image_size.add_argument("--image", required=True)

    refresh = subparsers.add_parser(
        "refresh", help="preview a coordinated archive snapshot advance"
    )
    refresh.add_argument("--snapshot", required=True)
    refresh.add_argument("--security-snapshot", required=True)
    refresh.add_argument("--keyring", type=Path, required=True)
    refresh.add_argument("--output-directory", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the Realm apt package command."""

    arguments = build_parser().parse_args(argv)
    try:
        if arguments.command == "check":
            return check_contracts(arguments)
        if arguments.command == "prepare-keyring":
            config = load_json(arguments.config)
            catalog = load_json(arguments.catalog)
            errors = validate_configuration(config, catalog)
            if errors:
                raise ContractError("; ".join(errors))
            keyring = prepare_keyring(config, arguments.output_directory)
            print(keyring)
            return 0
        if arguments.command == "resolve":
            return resolve_command(arguments)
        if arguments.command == "verify-lock":
            return verify_lock_command(arguments)
        if arguments.command == "verify-base-image":
            return verify_base_image_command(arguments)
        if arguments.command == "report-image-size":
            return report_image_size_command(arguments)
        return refresh_command(arguments)
    except (
        ContractError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as error:
        print(f"apt package operation failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
