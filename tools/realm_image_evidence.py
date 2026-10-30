#!/usr/bin/env python3
"""Capture bounded local image evidence; never authenticate or publish a release."""
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import copy
import ctypes
import datetime as dt
import errno
import hashlib
import json
import math
import os
import platform
import re
import signal
import stat
import subprocess
import tempfile
import uuid
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PINS = ROOT / "config/image-evidence-tools.v1.json"
SCHEMA = ROOT / "schemas/image-evidence.v1.schema.json"
MAX_BYTES = 128 * 1024 * 1024
DIGEST = re.compile(r"sha256:[a-f0-9]{64}\Z")
SHA = re.compile(r"[a-f0-9]{64}\Z")
REVISION = re.compile(r"[a-f0-9]{40}\Z")
SEVERITIES = ("Unknown", "Negligible", "Low", "Medium", "High", "Critical")
INPUTS = (
    "images/base/Dockerfile",
    "images/base/scripts/install-apt-packages",
    "images/base/scripts/verify-apt-packages",
    "images/base/scripts/realm-packages",
    "images/base/tests/smoke.sh",
    "catalog/capabilities.json",
    "config/debian-trixie.json",
    "profiles/base.profile.json",
)
ARTIFACTS = {
    "identity": ("identity.json", "realm-local-image-identity/v1"),
    "syft": ("syft.json", "syft-json/redacted-runtime-config"),
    "sbom": ("sbom.spdx.json", "SPDX-2.3/installed-image"),
    "vulnerabilities": (
        "vulnerabilities.grype.json",
        "grype-json/redacted-runtime-config",
    ),
    "apt_lock": ("apt-lock.json", "realm-apt-lock/v1"),
    "installed_packages": ("apt-installed.tsv", "realm-installed-packages/tsv"),
    "build_metadata": ("build-metadata.json", "realm-build-metadata/v1"),
    "verification": ("verification.json", "realm-image-verification/v1"),
}
LIMITATIONS = [
    "other-native-architectures",
    "registry-publication",
    "image-signatures",
    "provenance-authentication",
    "reproducible-multiarch-build",
]
SELECTORS = {
    "DOCKER_HOST",
    "DOCKER_CONTEXT",
    "DOCKER_TLS",
    "DOCKER_TLS_VERIFY",
    "DOCKER_CERT_PATH",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_bytes(path: Path, limit: int = MAX_BYTES) -> bytes:
    try:
        info = path.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or not 0 < info.st_size <= limit
        ):
            raise ValueError("input must be a bounded, ordinary, unlinked file")
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_nlink != 1
                or opened.st_ino != info.st_ino
                or opened.st_dev != info.st_dev
                or opened.st_size != info.st_size
            ):
                raise ValueError("input changed before it could be opened")
            data = stream.read(limit + 1)
        if len(data) > limit or len(data) != info.st_size:
            raise ValueError("input changed or exceeded its bound")
        return data
    except OSError as exc:
        raise ValueError("required evidence file is unavailable") from exc


def unique_object(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object member")
        result[key] = value
    return result


def reject_constant(_value: str) -> None:
    raise ValueError("nonfinite JSON number")


def finite_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("nonfinite JSON number")
    return result


def decode(data: bytes) -> Any:
    # Bound nesting before the decoder allocates nested containers. Quotes and
    # escaped quotes are skipped; this is a guard, not a second JSON parser.
    depth = 0
    quoted = False
    escaped = False
    for byte in data:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
        elif byte in (123, 91):
            depth += 1
            if depth > 64:
                raise ValueError("JSON nesting exceeds the evidence bound")
        elif byte in (125, 93):
            depth -= 1
    try:
        return json.loads(
            data,
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
            parse_float=finite_float,
        )
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("malformed or excessive JSON") from exc


def read_json(path: Path, limit: int = MAX_BYTES) -> Any:
    return decode(read_bytes(path, limit))


def encode(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode()


def timestamp(value: Any) -> dt.datetime:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})",
        value,
    ):
        raise ValueError("timestamp must use RFC3339 with timezone")
    try:
        return dt.datetime.fromisoformat(value.upper().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp is not a valid calendar instant") from exc


def shape(value: Any, fields: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == fields


def schema_errors(value: Any, schema: dict, root: dict, path: str = "$") -> list[str]:
    """Evaluate only the explicit vocabulary in this repository-owned contract."""
    if "$ref" in schema:
        reference = schema["$ref"]
        if not reference.startswith("#/$defs/"):
            raise ValueError("unsupported contract reference")
        return schema_errors(
            value, root["$defs"][reference.removeprefix("#/$defs/")], root, path
        )
    errors = []
    if "const" in schema and (
        type(value) is not type(schema["const"]) or value != schema["const"]
    ):
        errors.append(f"{path}: unexpected constant")
    if "enum" in schema and not any(
        type(value) is type(item) and value == item for item in schema["enum"]
    ):
        errors.append(f"{path}: unsupported value")
    expected = schema.get("type")
    types = expected if isinstance(expected, list) else [expected] if expected else []
    supported = {
        "object": dict,
        "array": list,
        "string": str,
        "integer": int,
        "boolean": bool,
        "null": type(None),
    }
    if types and not any(type(value) is supported.get(kind) for kind in types):
        return errors + [f"{path}: wrong type"]
    if isinstance(value, dict):
        props = schema.get("properties", {})
        if any(key not in value for key in schema.get("required", [])):
            errors.append(f"{path}: missing required field")
        if schema.get("additionalProperties") is False and set(value) - set(props):
            errors.append(f"{path}: unexpected field")
        if (
            not schema.get("minProperties", 0)
            <= len(value)
            <= schema.get("maxProperties", 100)
        ):
            errors.append(f"{path}: wrong object size")
        for key in value.keys() & props.keys():
            errors.extend(schema_errors(value[key], props[key], root, path + "." + key))
    elif isinstance(value, list):
        if not schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", 100):
            errors.append(f"{path}: wrong array size")
        if schema.get("uniqueItems") and len(
            {json.dumps(item, sort_keys=True) for item in value}
        ) != len(value):
            errors.append(f"{path}: duplicate item")
        for item in value:
            errors.extend(
                schema_errors(item, schema.get("items", {}), root, path + "[]")
            )
    elif isinstance(value, str):
        if len(value) > schema.get("maxLength", 4096) or len(value) < schema.get(
            "minLength", 0
        ):
            errors.append(f"{path}: wrong string length")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            errors.append(f"{path}: invalid string grammar")
        if schema.get("format") == "date-time":
            try:
                timestamp(value)
            except ValueError:
                errors.append(f"{path}: invalid timestamp")
    elif type(value) is int and not schema.get("minimum", -1) <= value <= schema.get(
        "maximum", 10000000
    ):
        errors.append(f"{path}: integer outside bounds")
    return errors[:32]


def validate_receipt(value: Any) -> list[str]:
    schema = read_json(SCHEMA, 65536)
    errors = schema_errors(value, schema, schema)
    if errors:
        return errors
    architecture = value["subject"]["platform"].split("/")[1]
    if architecture != "amd64":
        errors.append("this executable pin is not qualified for the subject platform")
    expected = set(INPUTS) | {
        f"images/base/packages/locks/debian-trixie-{architecture}.lock.json"
    }
    if set(value["source"]["inputs"]) != expected:
        errors.append("source inputs do not match the exact platform")
    if (
        sum(value["vulnerabilities"]["severity_counts"].values())
        != value["vulnerabilities"]["matches"]
    ):
        errors.append("vulnerability severity totals contradict matches")
    if set(value["limitations"]) != set(LIMITATIONS):
        errors.append("required limitations are incomplete")
    try:
        age = int(
            (
                timestamp(value["observed_at"]) - timestamp(value["database"]["built"])
            ).total_seconds()
        )
        if age != value["database"]["age_seconds"] or not 0 <= age <= 432000:
            errors.append("database age is stale, future or contradictory")
    except ValueError:
        errors.append("invalid evidence time")
    return errors


def tool_pins() -> dict:
    pins = read_json(PINS, 16384)
    if (
        not shape(pins, {"schema_version", "contract", "tools", "qualification"})
        or pins["schema_version"] != "1.0.0"
        or pins["contract"] != "realm.image-evidence-tools/v1"
        or not isinstance(pins["tools"], dict)
        or set(pins["tools"]) != {"syft", "grype"}
    ):
        raise ValueError("tool pin contract is invalid")
    for name, value in pins["tools"].items():
        if not shape(
            value,
            {
                "version",
                "source_revision",
                "license",
                "signature_verification",
                "linux/amd64",
            },
        ):
            raise ValueError("tool pin fields are invalid")
        asset = value["linux/amd64"]
        if (
            not shape(asset, {"archive_url", "archive_sha256", "executable_sha256"})
            or not SHA.fullmatch(asset["archive_sha256"])
            or not SHA.fullmatch(asset["executable_sha256"])
            or not REVISION.fullmatch(value["source_revision"])
        ):
            raise ValueError("tool digest pin is invalid")
        expected = f"https://github.com/anchore/{name}/releases/download/v{value['version']}/{name}_{value['version']}_linux_amd64.tar.gz"
        if (
            asset["archive_url"] != expected
            or value["license"] != "Apache-2.0"
            or value["signature_verification"] != "not-performed"
        ):
            raise ValueError("tool source or authentication pin is invalid")
    return pins


def build_plan(image: str, revision: str) -> dict:
    if not isinstance(image, str) or not DIGEST.fullmatch(image):
        raise ValueError("image must be an exact lowercase local configuration digest")
    if not isinstance(revision, str) or not REVISION.fullmatch(revision):
        raise ValueError("source revision must be a full lowercase Git SHA")
    return {
        "status": "planned",
        "release_ready": False,
        "image": {"identity_kind": "local-config", "digest": image},
        "source_revision": revision,
        "steps": [
            "verify source inputs and pinned executable bytes",
            "inspect exact local image and native platform",
            "verify installed lock and non-root smoke offline",
            "scan installed image with Syft",
            "scan that same SBOM with Grype using an existing fresh database",
            "publish a new limited evidence directory without replacement",
        ],
        "unperformed": [
            "build",
            "registry-publication",
            "signing",
            "provenance-authentication",
        ],
    }


def spdx_summary(value: Any, image: str, manifest: str | None = None) -> int:
    if (
        not isinstance(value, dict)
        or value.get("spdxVersion") != "SPDX-2.3"
        or not isinstance(value.get("packages"), list)
    ):
        raise ValueError("installed-image SPDX 2.3 evidence is required")
    info = value.get("creationInfo")
    if not isinstance(info, dict) or "Tool: syft-1.55.0" not in info.get(
        "creators", []
    ):
        raise ValueError("installed-image SPDX must come from the pinned Syft producer")
    roots = [
        p
        for p in value["packages"]
        if isinstance(p, dict) and p.get("primaryPackagePurpose") == "CONTAINER"
    ]
    if len(roots) != 1 or roots[0].get("versionInfo") != image.removeprefix("sha256:"):
        raise ValueError("installed-image SPDX subject does not match the local image")
    if not all(
        isinstance(p, dict)
        and isinstance(p.get("name"), str)
        and isinstance(p.get("SPDXID"), str)
        for p in value["packages"]
    ):
        raise ValueError("installed-image SPDX package record is malformed")
    if len({p["SPDXID"] for p in value["packages"]}) != len(value["packages"]):
        raise ValueError("installed-image SPDX package identities must be unique")
    if manifest is not None:
        checksums = roots[0].get("checksums")
        if (
            not isinstance(checksums, list)
            or {
                "algorithm": "SHA256",
                "checksumValue": manifest.removeprefix("sha256:"),
            }
            not in checksums
        ):
            raise ValueError("installed-image SPDX manifest binding is contradictory")
    return len(value["packages"])


def database_summary(grype: dict, observed: str, database_hash: str) -> dict:
    try:
        status = grype["descriptor"]["db"]["status"]
        built = status["built"]
        age = int((timestamp(observed) - timestamp(built)).total_seconds())
        url = urlsplit(status["from"])
        checksum = parse_qs(url.query, strict_parsing=True)["checksum"]
        if (
            status["valid"] is not True
            or not 0 <= age <= 432000
            or url.scheme != "https"
            or url.netloc != "grype.anchore.io"
            or not url.path.startswith("/databases/v6/")
            or len(checksum) != 1
            or not DIGEST.fullmatch(checksum[0])
        ):
            raise ValueError("database is stale, invalid or not immutably identified")
        return {
            "schema_version": status["schemaVersion"],
            "built": built,
            "source_url": status["from"],
            "archive_sha256": checksum[0].removeprefix("sha256:"),
            "database_sha256": database_hash,
            "reported_valid": True,
            "maximum_age_hours": 120,
            "age_seconds": age,
        }
    except (KeyError, TypeError) as exc:
        raise ValueError("database metadata is incomplete") from exc


def sanitized_tool_document(value: dict, name: str) -> dict:
    """Remove host runtime configuration; preserve all findings and image facts."""
    result = copy.deepcopy(value)
    descriptor = result.get("descriptor")
    if not isinstance(descriptor, dict):
        raise TypeError("scanner descriptor is missing")
    if name == "syft":
        result["descriptor"] = {key: descriptor[key] for key in ("name", "version")}
        metadata = result["source"]["metadata"]
    else:
        status = descriptor["db"]["status"]
        result["descriptor"] = {
            "name": descriptor["name"],
            "version": descriptor["version"],
            "timestamp": descriptor["timestamp"],
            "db": {
                "status": {
                    key: status[key]
                    for key in ("schemaVersion", "from", "built", "valid")
                }
            },
        }
        metadata = result["source"]["target"]
    for key in ("config", "manifest", "labels", "repoDigests", "tags"):
        metadata.pop(key, None)
    metadata["userInput"] = metadata["imageID"]
    return result


def summaries(
    directory: Path,
    revision: str,
    observed: str,
    db_hash: str,
    blobs: dict[str, bytes] | None = None,
) -> dict:
    def data(name: str, limit: int = MAX_BYTES) -> bytes:
        value = (
            blobs[name] if blobs is not None else read_bytes(directory / name, limit)
        )
        if len(value) > limit:
            raise ValueError("artifact exceeds its specific size bound")
        return value

    identity = decode(data("identity.json", 16384))
    syft = decode(data("syft.json"))
    spdx = decode(data("sbom.spdx.json"))
    grype = decode(data("vulnerabilities.grype.json"))
    lock = decode(data("apt-lock.json", 1048576))
    metadata = decode(data("build-metadata.json", 16384))
    verification = decode(data("verification.json", 16384))
    if (
        not shape(
            identity,
            {"local_config_digest", "platform", "source_revision", "execution"},
        )
        or identity["source_revision"] != revision
        or identity["execution"] != "native"
        or not DIGEST.fullmatch(identity["local_config_digest"])
    ):
        raise ValueError("image identity does not match source and execution")
    image = identity["local_config_digest"]
    image_platform = identity["platform"]
    for name, doc, field in (("syft", syft, "metadata"), ("grype", grype, "target")):
        try:
            source = doc["source"]
            target = source[field]
            if (
                source["type"] != "image"
                or target["imageID"] != image
                or f"{target['os']}/{target['architecture']}" != image_platform
                or doc["descriptor"]["name"] != name
            ):
                raise ValueError(
                    "scanner image identity contradicts the captured image"
                )
            if doc["descriptor"]["version"] != tool_pins()["tools"][name]["version"]:
                raise ValueError("scanner version is not pinned")
            if not DIGEST.fullmatch(target["manifestDigest"]):
                raise ValueError("scanner manifest identity is missing")
        except (KeyError, TypeError) as exc:
            raise ValueError("scanner image metadata is malformed") from exc
    if (
        syft["source"]["metadata"]["manifestDigest"]
        != grype["source"]["target"]["manifestDigest"]
    ):
        raise ValueError("scanner manifest identities disagree")
    package_count = spdx_summary(
        spdx, image, syft["source"]["metadata"]["manifestDigest"]
    )
    if not isinstance(syft.get("artifacts"), list) or not all(
        isinstance(p, dict)
        and isinstance(p.get("id"), str)
        and isinstance(p.get("name"), str)
        and isinstance(p.get("version"), str)
        for p in syft["artifacts"]
    ):
        raise ValueError("Syft package records are malformed")
    if package_count != len(syft["artifacts"]) + 1:
        raise ValueError("SPDX and Syft installed-package inventories disagree")
    if len({p["id"] for p in syft["artifacts"]}) != len(syft["artifacts"]):
        raise ValueError("Syft package identities must be unique")
    spdx_packages = [
        p for p in spdx["packages"] if p.get("primaryPackagePurpose") != "CONTAINER"
    ]
    if Counter((p["name"], p.get("versionInfo", "")) for p in spdx_packages) != Counter(
        (p["name"], p["version"]) for p in syft["artifacts"]
    ):
        raise ValueError("SPDX and Syft package names or versions disagree")
    counts = dict.fromkeys(SEVERITIES, 0)
    if not isinstance(grype.get("matches"), list) or not isinstance(
        grype.get("ignoredMatches"), list
    ):
        raise TypeError("Grype match collections are malformed")
    packages = {p["id"]: p for p in syft["artifacts"]}
    for collection in ("matches", "ignoredMatches"):
        for match in grype[collection]:
            try:
                vulnerability = match["vulnerability"]
                severity = vulnerability["severity"]
                if (
                    severity not in counts
                    or not isinstance(vulnerability["id"], str)
                    or match["artifact"]["id"] not in packages
                    or any(
                        match["artifact"].get(key)
                        != packages[match["artifact"]["id"]][key]
                        for key in ("name", "version")
                    )
                ):
                    raise ValueError(
                        "Grype match has invalid severity or package identity"
                    )
                if collection == "matches":
                    counts[severity] += 1
            except (KeyError, TypeError) as exc:
                raise ValueError("Grype nested match is malformed") from exc
    architecture = image_platform.split("/")[-1]
    if (
        not isinstance(lock, dict)
        or lock.get("architecture") != architecture
        or not shape(
            metadata,
            {
                "schema_version",
                "build_revision",
                "lock_checksum",
                "snapshot",
                "security_snapshot",
                "base_image_digest",
                "base_platform_digest",
            },
        )
        or metadata["schema_version"] != "1.0.0"
        or metadata.get("build_revision") != revision
        or metadata.get("lock_checksum") != lock.get("lock_checksum")
    ):
        raise ValueError("installed lock metadata contradicts source or platform")
    checksum_value = copy.deepcopy(lock)
    checksum_value.pop("lock_checksum", None)
    canonical = (
        json.dumps(checksum_value, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    if lock.get("lock_checksum") != "sha256:" + digest(canonical):
        raise ValueError("installed lock checksum is invalid")
    if (
        metadata["snapshot"] != lock.get("snapshot")
        or metadata["security_snapshot"] != lock.get("security_snapshot")
        or metadata["base_image_digest"] != lock.get("base_image", {}).get("digest")
        or metadata["base_platform_digest"]
        != lock.get("base_image", {}).get("platform_digest")
    ):
        raise ValueError("installed metadata snapshots or base digests disagree")
    if not shape(verification, {"installed_lock", "nonroot_smoke"}) or any(
        not shape(v, {"status", "exit_code"})
        or v["status"] != "passed"
        or type(v["exit_code"]) is not int
        or v["exit_code"] != 0
        for v in verification.values()
    ):
        raise ValueError("image runtime verification is incomplete or failed")
    inventory = data("apt-installed.tsv", 1048576).decode("utf-8")
    rows = inventory.splitlines()
    if (
        not rows
        or rows[0]
        != "name\tlocked_version\tinstalled_version\tarchitecture\tcapability\tsnapshot\tsecurity_snapshot\tbase_image_digest\tbase_platform_digest\tbuild_revision\tlock_checksum"
        or len(rows) != len(lock["packages"]) + 1
        or any(len(row.split("\t")) != 11 for row in rows)
    ):
        raise ValueError("installed package inventory is incomplete")
    expected_rows = {
        (p["name"], p["version"], p["architecture"], p["capability"])
        for p in lock["packages"]
    }
    actual_rows = set()
    for row in rows[1:]:
        values = row.split("\t")
        if (
            values[1] != values[2]
            or values[5:9]
            != [
                lock["snapshot"],
                lock["security_snapshot"],
                lock["base_image"]["digest"],
                lock["base_image"]["platform_digest"],
            ]
            or values[9] != revision
            or values[10] != lock["lock_checksum"]
        ):
            raise ValueError("installed package version/source/lock mismatch")
        actual_rows.add((values[0], values[1], values[3], values[4]))
    if actual_rows != expected_rows:
        raise ValueError("installed package set differs from the lock")
    return {
        "subject": {
            "identity_kind": "local-config",
            "local_config_digest": image,
            "scanner_manifest_digest": syft["source"]["metadata"]["manifestDigest"],
            "platform": image_platform,
            "execution": "native",
            "registry_reference": None,
            "registry_manifest_digest": None,
            "index_digest": None,
        },
        "database": database_summary(grype, observed, db_hash),
        "inventory": {
            "syft_packages": len(syft["artifacts"]),
            "spdx_packages": package_count,
            "locked_packages": len(lock["packages"]),
        },
        "vulnerabilities": {
            "status": "reported",
            "matches": len(grype["matches"]),
            "ignored_matches": len(grype["ignoredMatches"]),
            "severity_counts": counts,
        },
        "verification": verification,
    }


def _verify_evidence(directory: Path) -> dict:
    """Verify portable internal consistency, not origin or cryptographic trust."""
    receipt = read_json(directory / "image-evidence.json", 65536)
    errors = validate_receipt(receipt)
    if errors:
        raise ValueError("; ".join(errors[:8]))
    if {p.name for p in directory.iterdir()} != {"image-evidence.json"} | {
        v[0] for v in ARTIFACTS.values()
    }:
        raise ValueError("evidence directory has missing or unexpected members")
    blobs = {}
    for key, (name, _fmt) in ARTIFACTS.items():
        data = read_bytes(directory / name)
        blobs[name] = data
        artifact = receipt["artifacts"][key]
        if len(data) != artifact["bytes"] or digest(data) != artifact["sha256"]:
            raise ValueError("artifact checksum or byte count is inconsistent")
    architecture = receipt["subject"]["platform"].split("/")[1]
    source_lock = f"images/base/packages/locks/debian-trixie-{architecture}.lock.json"
    if receipt["source"]["inputs"][source_lock] != digest(blobs["apt-lock.json"]):
        raise ValueError("included apt lock contradicts the source-input checksum")
    derived = summaries(
        directory,
        receipt["source"]["revision"],
        receipt["observed_at"],
        receipt["database"]["database_sha256"],
        blobs,
    )
    if any(receipt[key] != value for key, value in derived.items()):
        raise ValueError("receipt claims contradict artifact contents")
    pins = tool_pins()["tools"]
    for name in pins:
        pin = pins[name]
        record = receipt["tools"][name]
        if (
            record["executable_sha256"] != pin["linux/amd64"]["executable_sha256"]
            or record["archive_sha256"] != pin["linux/amd64"]["archive_sha256"]
        ):
            raise ValueError("receipt tool bytes do not match reviewed pins")
    return receipt


def verify_evidence(directory: Path) -> dict:
    """Verify bounded internal consistency; malformed external input raises ValueError."""
    try:
        return _verify_evidence(Path(directory))
    except ValueError:
        raise
    except (
        OSError,
        KeyError,
        TypeError,
        UnicodeError,
        RecursionError,
        IndexError,
        AttributeError,
    ) as exc:
        raise ValueError("malformed or unavailable image evidence") from exc


def run(argv: list[str], env: dict[str, str], timeout: int = 300) -> bytes:
    """Bound execution and terminate only the new process group on timeout."""
    process = subprocess.Popen(
        argv,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, _stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise ValueError("evidence tool deadline exceeded") from exc
    if process.returncode != 0:
        raise ValueError(f"evidence tool failed with exit {process.returncode}")
    if len(stdout) > MAX_BYTES:
        raise ValueError("evidence tool output exceeded the bound")
    return stdout


def publish_directory(source: Path, target: Path) -> None:
    """Linux renameat2 gives atomic no-replace publication, including races."""
    library = ctypes.CDLL(None, use_errno=True)
    try:
        rename = library.renameat2
    except AttributeError as exc:
        raise ValueError(
            "atomic no-replace directory publication is unavailable"
        ) from exc
    rename.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    rename.restype = ctypes.c_int
    if rename(-100, os.fsencode(source), -100, os.fsencode(target), 1) != 0:
        code = ctypes.get_errno()
        if code in (errno.EEXIST, errno.ENOTEMPTY):
            raise ValueError("output already exists; no evidence was replaced")
        raise ValueError("atomic evidence publication failed")


def file_hash(path: Path, limit: int = 4 * 1024 * 1024 * 1024) -> str:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
        raise ValueError("tool/database must be an ordinary bounded file")
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            result.update(block)
    return result.hexdigest()


def run_container(
    docker: list[str],
    options: list[str],
    image: str,
    command: list[str],
    env: dict[str, str],
    timeout: int = 120,
) -> bytes:
    """Clean up only this invocation's container if a Docker client times out."""
    token = uuid.uuid4().hex
    name = "realm-evidence-" + token
    label = "io.egohygiene.realm.evidence-invocation"
    argv = (
        docker
        + ["run", "--rm", "--name", name, "--label", label + "=" + token]
        + options
        + [image]
        + command
    )

    def present() -> bool:
        result = run(
            docker
            + [
                "container",
                "ls",
                "--all",
                "--filter",
                "name=^/" + name + "$",
                "--format",
                "{{.ID}}",
            ],
            env,
            30,
        )
        return bool(result.strip())

    try:
        return run(argv, env, timeout)
    finally:
        try:
            details = decode(
                run(
                    docker + ["container", "inspect", name, "--format", "{{json .}}"],
                    env,
                    30,
                )
            )
        except ValueError:
            # --rm commonly removed a completed container already. A successful
            # filtered read must establish absence before accepting that case.
            if present():
                raise ValueError(
                    "owned container cleanup identity is unavailable"
                ) from None
        else:
            identifier = details.get("Id") if isinstance(details, dict) else None
            config = details.get("Config") if isinstance(details, dict) else None
            labels = config.get("Labels") if isinstance(config, dict) else None
            if (
                not isinstance(identifier, str)
                or not re.fullmatch(r"[a-f0-9]{64}", identifier)
                or details.get("Name") != "/" + name
                or not isinstance(labels, dict)
                or labels.get(label) != token
            ):
                raise ValueError("container ownership did not match; cleanup refused")
            try:
                run(docker + ["container", "rm", "--force", identifier], env, 30)
            except ValueError:
                if present():
                    raise ValueError(
                        "owned container cleanup did not complete"
                    ) from None


def collect(args: argparse.Namespace) -> dict:
    producer_bytes = read_bytes(Path(__file__), 1048576)
    build_plan(args.image, args.source_revision)
    if args.output.exists() or args.output.is_symlink():
        raise ValueError("output already exists")
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise ValueError("this tool pin is qualified only on native Linux AMD64")
    if not args.docker_host.startswith("unix:///"):
        raise ValueError("only an explicitly selected local Docker socket is supported")
    pins = tool_pins()["tools"]
    source = args.source_root.resolve()
    input_paths = INPUTS + ("images/base/packages/locks/debian-trixie-amd64.lock.json",)
    inputs = {}
    base_env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("SYFT_", "GRYPE_")) and key not in SELECTORS
    }
    for name in input_paths:
        expected = run(
            ["git", "-C", str(source), "show", f"{args.source_revision}:{name}"],
            base_env,
            30,
        )
        data = read_bytes(source / name, 1048576)
        if data != expected:
            raise ValueError(
                "canonical build inputs differ from the selected source revision"
            )
        inputs[name] = digest(data)
    tool_records = {}
    executables = {}
    for name in ("syft", "grype"):
        executable = getattr(args, name).resolve()
        checksum_value = file_hash(executable, 256 * 1024 * 1024)
        pin = pins[name]
        if checksum_value != pin["linux/amd64"]["executable_sha256"]:
            raise ValueError(
                "scanner executable checksum differs from the reviewed pin"
            )
        executables[name] = executable
        tool_records[name] = {
            "version": pin["version"],
            "source_revision": pin["source_revision"],
            "archive_sha256": pin["linux/amd64"]["archive_sha256"],
            "executable_sha256": checksum_value,
            "signature_verification": "not-performed",
        }
    docker = ["docker", "--host=" + args.docker_host]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with (
        tempfile.TemporaryDirectory(
            prefix=".realm-evidence-", dir=args.output.parent
        ) as temp,
        tempfile.TemporaryDirectory(prefix="realm-image-tools-") as cache,
    ):
        directory = Path(temp) / "bundle"
        directory.mkdir()
        config = Path(cache) / "empty.yaml"
        config.write_text("{}\n")
        env = base_env | {
            "DOCKER_HOST": args.docker_host,
            "XDG_CACHE_HOME": cache,
            "SYFT_CHECK_FOR_APP_UPDATE": "false",
            "GRYPE_CHECK_FOR_APP_UPDATE": "false",
            "GRYPE_DB_CACHE_DIR": str(args.database_directory.resolve()),
            "GRYPE_DB_AUTO_UPDATE": "false",
            "GRYPE_DB_VALIDATE_AGE": "true",
        }
        for name, executable in executables.items():
            version = decode(run([str(executable), "version", "-o", "json"], env, 30))
            if (
                version.get("version") != pins[name]["version"]
                or version.get("gitCommit") != pins[name]["source_revision"]
                or version.get("platform") != "linux/amd64"
            ):
                raise ValueError(
                    "scanner runtime version/source/platform is inconsistent"
                )
        info = decode(
            run(
                docker + ["image", "inspect", args.image, "--format", "{{json .}}"],
                env,
                30,
            )
        )
        daemon = decode(run(docker + ["info", "--format", "{{json .}}"], env, 30))
        if (
            info.get("Id") != args.image
            or info.get("Os") != "linux"
            or info.get("Architecture") != "amd64"
            or daemon.get("OSType") != "linux"
            or daemon.get("Architecture") not in ("x86_64", "amd64")
        ):
            raise ValueError(
                "image and local execution platform must match native Linux AMD64"
            )
        if (
            info.get("Config", {})
            .get("Labels", {})
            .get("org.opencontainers.image.revision")
            != args.source_revision
        ):
            raise ValueError("image source label does not match the selected revision")
        identity = {
            "local_config_digest": args.image,
            "platform": "linux/amd64",
            "source_revision": args.source_revision,
            "execution": "native",
        }
        (directory / "identity.json").write_bytes(encode(identity))
        root_options = [
            "--network",
            "none",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--user",
            "root",
        ]
        run_container(
            docker,
            root_options
            + [
                "--entrypoint",
                "/usr/local/libexec/realm/verify-apt-packages",
            ],
            args.image,
            [],
            env,
        )
        # The image's non-root smoke deliberately tests its documented sudo boundary.
        run_container(
            docker,
            [
                "--network",
                "none",
                "--entrypoint",
                "/usr/local/libexec/realm/smoke",
            ],
            args.image,
            [],
            env,
        )
        verification = {
            name: {"status": "passed", "exit_code": 0}
            for name in ("installed_lock", "nonroot_smoke")
        }
        (directory / "verification.json").write_bytes(encode(verification))
        for name in ("apt-lock.json", "apt-installed.tsv", "build-metadata.json"):
            data = run_container(
                docker,
                root_options
                + [
                    "--entrypoint",
                    "/bin/cat",
                ],
                args.image,
                ["/usr/local/share/realm/packages/" + name],
                env,
                30,
            )
            (directory / name).write_bytes(data)
        if decode(read_bytes(directory / "apt-lock.json")) != decode(
            read_bytes(source / input_paths[-1])
        ):
            raise ValueError("installed lock differs from the selected source input")
        db_status = decode(
            run(
                [
                    str(executables["grype"]),
                    "--config",
                    str(config),
                    "db",
                    "status",
                    "-o",
                    "json",
                ],
                env,
                60,
            )
        )
        db_path = Path(db_status["path"])
        if not db_path.resolve().is_relative_to(args.database_directory.resolve()):
            raise ValueError("database file is outside the selected cache")
        database_hash = file_hash(db_path)
        raw_syft = Path(cache) / "syft.json"
        spdx = directory / "sbom.spdx.json"
        run(
            [
                str(executables["syft"]),
                "--config",
                str(config),
                "--quiet",
                "scan",
                "docker:" + args.image,
                "--parallelism",
                "2",
                "--output",
                "syft-json=" + str(raw_syft),
                "--output",
                "spdx-json=" + str(spdx),
            ],
            env,
        )
        syft_bytes = read_bytes(raw_syft)
        syft = sanitized_tool_document(decode(syft_bytes), "syft")
        (directory / "syft.json").write_bytes(encode(syft))
        raw_grype = Path(cache) / "grype.json"
        run(
            [
                str(executables["grype"]),
                "--config",
                str(config),
                "--quiet",
                "sbom:" + str(directory / "syft.json"),
                "--output",
                "json",
                "--file",
                str(raw_grype),
            ],
            env,
        )
        grype_bytes = read_bytes(raw_grype)
        grype = sanitized_tool_document(decode(grype_bytes), "grype")
        (directory / "vulnerabilities.grype.json").write_bytes(encode(grype))
        if file_hash(db_path) != database_hash:
            raise ValueError("vulnerability database changed during capture")
        observed = (
            dt.datetime.now(dt.timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )
        derived = summaries(directory, args.source_revision, observed, database_hash)
        artifacts = {}
        for key, (name, fmt) in ARTIFACTS.items():
            data = read_bytes(directory / name)
            raw = (
                digest(syft_bytes)
                if key == "syft"
                else digest(grype_bytes)
                if key == "vulnerabilities"
                else None
            )
            artifacts[key] = {
                "path": name,
                "sha256": digest(data),
                "bytes": len(data),
                "format": fmt,
                "raw_sha256": raw,
            }
        receipt = {
            "schema_version": "1.0.0",
            "contract": "realm.image-evidence/v1",
            "state": "limited",
            "release_ready": False,
            "observed_at": observed,
            "source": {
                "repository": "egohygiene/realm",
                "revision": args.source_revision,
                "inputs": inputs,
            },
            "producer": {
                "name": "realm-image-evidence",
                "version": "1.0.0",
                "sha256": digest(producer_bytes),
            },
            "tools": tool_records,
            **derived,
            "artifacts": artifacts,
            "authentication": {
                name: "not-performed"
                for name in ("image_signatures", "provenance", "registry_publication")
            },
            "limitations": LIMITATIONS,
        }
        (directory / "image-evidence.json").write_bytes(encode(receipt))
        verify_evidence(directory)
        if read_bytes(Path(__file__), 1048576) != producer_bytes:
            raise ValueError(
                "producer source changed during capture; no evidence was published"
            )
        publish_directory(directory, args.output)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser(
        "check-inputs",
        help="Check pinned contract inputs offline without image execution.",
    )
    plan = sub.add_parser("plan", help="Print a read-only local evidence plan.")
    plan.add_argument("--image", required=True)
    plan.add_argument("--source-revision", required=True)
    verify = sub.add_parser(
        "verify",
        aliases=["check"],
        help="Verify a local evidence directory without Docker/network execution.",
    )
    verify.add_argument("--directory", type=Path, required=True)
    capture = sub.add_parser(
        "collect", help="Explicitly execute pinned scanners and installed-image checks."
    )
    capture.add_argument("--image", required=True)
    capture.add_argument("--source-revision", required=True)
    capture.add_argument("--source-root", type=Path, default=ROOT)
    capture.add_argument("--output", type=Path, required=True)
    capture.add_argument("--syft", type=Path, required=True)
    capture.add_argument("--grype", type=Path, required=True)
    capture.add_argument("--database-directory", type=Path, required=True)
    capture.add_argument("--docker-host", default="unix:///var/run/docker.sock")
    args = parser.parse_args()
    try:
        if args.command == "check-inputs":
            tool_pins()
            read_json(SCHEMA, 65536)
            result = {"status": "inputs-valid", "release_ready": False}
        elif args.command == "plan":
            result = build_plan(args.image, args.source_revision)
        elif args.command in ("verify", "check"):
            receipt = verify_evidence(args.directory)
            result = {
                "status": "valid-local-evidence",
                "release_ready": False,
                "receipt": receipt,
            }
        else:
            receipt = collect(args)
            result = {"status": "captured", "release_ready": False, "receipt": receipt}
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        UnicodeError,
        RecursionError,
        IndexError,
    ) as exc:
        print(
            json.dumps(
                {
                    "status": "invalid-or-unavailable",
                    "release_ready": False,
                    "diagnostic": str(exc)[:1024],
                }
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
