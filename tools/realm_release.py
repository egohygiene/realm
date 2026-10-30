#!/usr/bin/env python3
"""Realm-owned, offline container-release preparation; never publish or authenticate.

Aether owns declaration grammar, Hygiene owns rollout, Relay owns immutable
publication mechanics, and image-evidence v1 owns local image observations.
This adapter checks the narrow selected Realm profile and portable bundle
mechanics. Recorded local bytes cannot establish signatures or registry state.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
REVISION = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")
RELATIVE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*")
MAX_JSON = 1024 * 1024
MAX_FILE = 64 * 1024 * 1024
MAX_TOTAL = 256 * 1024 * 1024
MAX_FILES = 512
PINS = {
    "aether-release-schema": (
        "egohygiene/aether",
        "8a2a3d08f3aa9da3847bd5277843506ab855192e",
        "catalog/schemas/aether.repository-release.v1.schema.json",
        "vendor/aether/aether.repository-release.v1.schema.json",
        "8431ea7651336aa7695aee5b9aedce536b1e7c76c3cb15927f64a6206f9cc1f5",
        "draft-source",
    ),
    "hygiene-release-policy": (
        "egohygiene/hygiene",
        "28f9d6c7519d820644572634ba4476614f418d83",
        "catalog/repository-release-policy.json",
        "vendor/hygiene/repository-release-policy.v1.json",
        "20030513c311416c5130a15af897590892025b55cfd79d210be362d47748063f",
        "proposed-source",
    ),
    "relay-release-profiles": (
        "egohygiene/relay",
        "1eada5142f7fc7da7862f335589e3b8f5884ffaf",
        "release-profiles.json",
        "vendor/relay/release-profiles.v1.json",
        "43bc25a8c17329921702311c5601b28affb4e16f398b35d448e14df9cbd6f552",
        "published-v1.5.0",
    ),
}
PLAN_INPUTS = (
    ".egohygiene/release.json",
    "CHANGELOG.md",
    "Taskfile.yml",
    ".github/workflows/release.yml",
    "AGENTS.md",
    "docs/releasing.md",
    "config/release-inputs.v1.json",
    "tools/realm_release.py",
    "schemas/container-release.v1.schema.json",
    "schemas/release-result.v1.schema.json",
) + tuple(value[3] for value in PINS.values())


class UnavailableError(ValueError):
    """Local mechanics cannot establish a requested external acceptance layer."""


def fail(message: str) -> None:
    raise ValueError(message)


def closed(value: Any, keys: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        fail(f"{label} has an unsupported object shape")
    return value


def same(value: Any, expected: Any, label: str) -> None:
    """Compare narrow selected-profile facts without boolean/numeric coercion."""
    if type(value) is not type(expected):
        fail(f"{label} has an unsupported type")
    if isinstance(expected, dict):
        closed(value, set(expected), label)
        for key in expected:
            same(value[key], expected[key], f"{label}.{key}")
    elif isinstance(expected, list):
        if len(value) != len(expected):
            fail(f"{label} has an unsupported item count")
        for item, target in zip(value, expected):
            same(item, target, label)
    elif value != expected:
        fail(f"{label} disagrees with the selected Realm release boundary")


def text(value: Any, label: str, maximum: int = 1000) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        fail(f"{label} must be bounded nonempty text")
    return value


def namespace_uri(value: Any) -> str:
    """Accept the bounded HTTP(S)/URN namespace subset used by this index."""
    value = text(value, "installed SBOM namespace", 4096)
    if (
        not re.fullmatch(r"[A-Za-z0-9._~:/?\[\]@!$&'()*+,;=%-]+", value)
        or re.search(r"%(?![0-9A-Fa-f]{2})", value)
        or "#" in value
    ):
        fail("installed SBOM namespace must be a supported absolute URI")
    try:
        parsed = urlsplit(value)
        if parsed.scheme in {"http", "https"}:
            # Syntax inspection only; no DNS or network request occurs.
            _ = parsed.port
    except ValueError:
        fail("installed SBOM namespace has unsupported URI syntax")
    if any(character in parsed.path + parsed.query for character in "[]"):
        fail("installed SBOM namespace has unsupported path syntax")
    if parsed.scheme in {"http", "https"}:
        if not parsed.netloc or not parsed.hostname:
            fail("installed SBOM namespace requires an HTTP(S) authority")
        if (
            "@" in parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
        ):
            fail("installed SBOM namespace requires a credential-free authority")
        host = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
        authority = host + (f":{parsed.port}" if parsed.port is not None else "")
        if parsed.netloc.lower() != authority.lower():
            fail("installed SBOM namespace requires a supported canonical authority")
    elif parsed.scheme == "urn":
        if parsed.netloc or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9-]{0,31}:.+", parsed.path
        ):
            fail("installed SBOM namespace requires a supported URN identifier")
    else:
        fail("installed SBOM namespace supports HTTP(S) or URN only")
    return value


def relative(value: Any) -> str:
    if not isinstance(value, str) or not RELATIVE.fullmatch(value):
        fail("artifact path must be strict relative POSIX text")
    parsed = PurePosixPath(value)
    if parsed.as_posix() != value or any(part in {".", ".."} for part in parsed.parts):
        fail("artifact path must be normalized without traversal")
    return value


def regular_bytes(path: Path, maximum: int = MAX_FILE) -> bytes:
    for parent in (path, *path.parents):
        if parent.is_symlink():
            fail("symbolic links are unsupported inputs")
    descriptor = os.open(
        path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    )
    with os.fdopen(descriptor, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
            fail("input must be a bounded regular file")
        result = handle.read(maximum + 1)
    if len(result) > maximum:
        fail("input exceeds the byte limit")
    return result


def object_pairs(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            fail("duplicate JSON keys are unsupported")
        result[key] = value
    return result


def decode_object(data: bytes) -> dict:
    value = json.loads(
        data.decode("utf-8"),
        object_pairs_hook=object_pairs,
        parse_constant=lambda _: fail("nonfinite JSON numbers are unsupported"),
    )
    if not isinstance(value, dict):
        fail("JSON input must be an object")
    return value


def read_object(path: Path, maximum: int = MAX_JSON) -> dict:
    return decode_object(regular_bytes(path, maximum))


def canonical(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode()


def checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    if result.returncode:
        fail("local Git source identity is unavailable")
    return result.stdout.strip()


def check(repository: Path) -> dict:
    """Check only Realm's closed current-v1 selection, not arbitrary Aether declarations."""
    pins = read_object(repository / "config/release-inputs.v1.json")
    closed(pins, {"schema_version", "sources"}, "release input lock")
    same(pins["schema_version"], "realm.release-inputs/v1", "release input schema")
    if not isinstance(pins["sources"], list) or len(pins["sources"]) != len(PINS):
        fail("release input lock must contain the three selected owners")
    found = set()
    fields = {
        "id",
        "repository",
        "revision",
        "source_path",
        "local_path",
        "sha256",
        "status",
    }
    for item in pins["sources"]:
        closed(item, fields, "release source")
        key = item["id"]
        if not isinstance(key, str) or key not in PINS or key in found:
            fail("release source identity is unknown or duplicated")
        found.add(key)
        expected = dict(
            zip(
                (
                    "repository",
                    "revision",
                    "source_path",
                    "local_path",
                    "sha256",
                    "status",
                ),
                PINS[key],
            )
        )
        same({key: item[key] for key in expected}, expected, "release source pin")
        if (
            checksum(regular_bytes(repository / relative(item["local_path"])))
            != item["sha256"]
        ):
            fail("release owner contract bytes differ from the selected pin")
    declaration = read_object(repository / ".egohygiene/release.json")
    closed(
        declaration,
        {
            "$schema",
            "schema_version",
            "repository",
            "release",
            "changelog",
            "components",
            "delivery",
            "evidence",
            "automation",
        },
        "declaration",
    )
    same(
        declaration["$schema"],
        "https://egohygiene.io/schemas/aether/repository-release/v1.json",
        "schema URL",
    )
    same(
        declaration["schema_version"],
        "egohygiene.repository-release/v1",
        "schema identity",
    )
    same(
        declaration["repository"],
        {
            "id": "egohygiene/realm",
            "lifecycle": "incubating",
            "release_profile": "container-image",
        },
        "repository",
    )
    same(
        declaration["release"],
        {
            "state": "unreleased",
            "tag_prefix": "v",
            "immutable_tags": True,
            "major_alias": "disabled",
        },
        "release",
    )
    same(
        declaration["changelog"],
        {
            "path": "CHANGELOG.md",
            "format": "keep-a-changelog/1.1",
            "unreleased_heading": "Unreleased",
        },
        "changelog",
    )
    same(
        declaration["components"],
        [
            {
                "id": "realm-base",
                "kind": "container-image",
                "version_authority": {"kind": "git-tag"},
            }
        ],
        "components",
    )
    delivery = closed(declaration["delivery"], {"channels"}, "delivery")
    if not isinstance(delivery["channels"], list) or len(delivery["channels"]) != 2:
        fail("delivery requires separate planned GitHub and registry channels")
    for channel, kind in zip(
        delivery["channels"], ("github-release", "container-registry")
    ):
        fields = {"kind", "state", "notes"} | (
            {"relay_profile"} if kind == "github-release" else set()
        )
        closed(channel, fields, "channel")
        same(channel["kind"], kind, "channel kind")
        same(channel["state"], "planned", "channel state")
        text(channel["notes"], "channel notes", 500)
        if kind == "github-release":
            same(channel["relay_profile"], "container-image", "Relay profile")
    evidence = closed(
        declaration["evidence"],
        {"source", "change", "provenance", "sbom", "signature", "rollback"},
        "evidence",
    )
    for field in ("source", "change", "provenance", "sbom", "signature"):
        same(evidence[field], "required", "future release evidence requirement")
    rollback = closed(evidence["rollback"], {"strategy", "instructions"}, "rollback")
    same(rollback["strategy"], "revoke-channel", "rollback strategy")
    text(rollback["instructions"], "rollback instructions")
    same(
        declaration["automation"],
        {
            "taskfile_path": "Taskfile.yml",
            "tasks": {
                "plan": "release:plan",
                "prepare": "release:prepare",
                "verify": "release:verify",
                "publish": "release:publish",
            },
            "github": {
                "manual_dispatch_required": True,
                "workflow_path": ".github/workflows/release.yml",
                "state": "configured",
            },
        },
        "automation",
    )
    changelog(repository)
    for path in (
        "AGENTS.md",
        "docs/releasing.md",
        "Taskfile.yml",
        ".github/workflows/release.yml",
    ):
        regular_bytes(repository / path)
    return {"status": "valid-local-selection", "rollout": "incubating-advisory"}


def changelog(repository: Path, version: str | None = None) -> str:
    value = regular_bytes(repository / "CHANGELOG.md", MAX_JSON).decode()
    if (
        not value.startswith("# Changelog\n")
        or len(re.findall(r"^## \[Unreleased\]$", value, re.MULTILINE)) != 1
    ):
        fail("changelog requires one exact Unreleased heading")
    if version:
        if re.search(r"^## \[" + re.escape(version[1:]) + r"\]", value, re.MULTILINE):
            fail("target version already has a promoted changelog entry")
        section = value.split("## [Unreleased]\n", 1)[1]
        section = re.split(r"^## \[", section, maxsplit=1, flags=re.MULTILINE)[0]
        if not re.search(r"^[-*] \S", section, re.MULTILINE):
            fail("Unreleased has no reviewable change entry")
    return value


def version_tag(value: str) -> str:
    if not SEMVER.fullmatch(value):
        fail("version must be exact stable vMAJOR.MINOR.PATCH")
    return value


def source_revision(value: str) -> str:
    if not REVISION.fullmatch(value):
        fail("source revision must be a full lowercase Git SHA")
    return value


def plan(repository: Path, version: str) -> dict:
    version_tag(version)
    revision = source_revision(git(repository, "rev-parse", "HEAD"))
    input_sha256 = {
        name: checksum(regular_bytes(repository / name)) for name in PLAN_INPUTS
    }
    check(repository)
    changelog(repository, version)
    tags = git(repository, "tag", "--list", version)
    if tags:
        fail("target immutable tag already exists locally")
    if (
        input_sha256
        != {name: checksum(regular_bytes(repository / name)) for name in PLAN_INPUTS}
        or git(repository, "rev-parse", "HEAD") != revision
    ):
        fail("release inputs changed during local planning")
    return {
        "status": "planned-local",
        "repository": "egohygiene/realm",
        "tag": version,
        "source_revision": revision,
        "source_binding": "head-plus-working-input-checksums",
        "input_sha256": input_sha256,
        "working_tree": "dirty"
        if git(repository, "status", "--porcelain=v1")
        else "clean",
        "profile": "container-image",
        "version_authority": "git-tag",
        "default_branch": "not-authenticated-locally",
        "remote_tags": "not-inspected",
        "rollout": "incubating-advisory",
        "signature": "unavailable",
        "provenance": "unavailable",
    }


def inventory(directory: Path) -> dict[str, bytes]:
    if directory.is_symlink() or not directory.is_dir():
        fail("bundle must be a regular directory")
    files = {}
    total = 0
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            fail("bundle must not contain links")
        if path.is_dir():
            continue
        name = relative(path.relative_to(directory).as_posix())
        data = regular_bytes(path)
        files[name] = data
        total += len(data)
        if len(files) > MAX_FILES or total > MAX_TOTAL:
            fail("bundle exceeds its bounded inventory")
    if not files:
        fail("bundle inventory is empty")
    return files


def write_exclusive(output: Path, repository: Path, files: dict[str, bytes]) -> None:
    """Create an owned complete inventory without replacing an existing directory."""
    output = Path(os.path.abspath(output))
    for parent in (output, *output.parents):
        if parent.is_symlink():
            fail("output must not traverse links")
    if output == repository or (
        output.is_relative_to(repository)
        and output.relative_to(repository).parts[:2] != (".cache", "realm")
    ):
        fail("output must not overlap repository sources")
    for name, data in files.items():
        relative(name)
        if name == "SHA256SUMS" or not isinstance(data, bytes) or len(data) > MAX_FILE:
            fail("unsupported output inventory member")
    if len(files) > MAX_FILES - 1 or sum(map(len, files.values())) > MAX_TOTAL:
        fail("output inventory is too large")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        output.mkdir(exist_ok=False)
    except FileExistsError:
        fail("output already exists; choose a fresh review directory")
    owned = output.stat()
    try:
        for name, data in sorted(files.items()):
            target = output / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as handle:
                handle.write(data)
        sums = "".join(
            f"{checksum(data)}  {name}\n" for name, data in sorted(files.items())
        )
        with (output / "SHA256SUMS").open("x", encoding="utf-8") as handle:
            handle.write(sums)
    except BaseException:
        if not output.is_symlink() and output.exists():
            current = output.stat()
            if (current.st_dev, current.st_ino) == (owned.st_dev, owned.st_ino):
                shutil.rmtree(output)
        raise


def prepare(repository: Path, arguments: argparse.Namespace) -> dict:
    report = plan(repository, arguments.version)
    try:
        promoted_date = date.fromisoformat(arguments.date)
    except ValueError:
        fail("release date must be a real YYYY-MM-DD date")
    if promoted_date.isoformat() != arguments.date:
        fail("release date must be padded YYYY-MM-DD")
    original = changelog(repository, arguments.version)
    if checksum(original.encode()) != report["input_sha256"]["CHANGELOG.md"]:
        fail("changelog changed after the recorded plan")
    replacement = original.replace(
        "## [Unreleased]\n",
        f"## [Unreleased]\n\n## [{arguments.version[1:]}] - {arguments.date}\n",
        1,
    )
    patch = "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            replacement.splitlines(keepends=True),
            fromfile="a/CHANGELOG.md",
            tofile="b/CHANGELOG.md",
        )
    )
    report["status"] = "prepared-local-review"
    write_exclusive(
        arguments.output,
        repository,
        {"plan.json": canonical(envelope(report)), "CHANGELOG.patch": patch.encode()},
    )
    return report


def verify_checksums(files: dict[str, bytes]) -> None:
    if "SHA256SUMS" not in files:
        fail("complete SHA256SUMS inventory is required")
    checksums = {}
    lines = files["SHA256SUMS"].decode().splitlines()
    paths = []
    for line in lines:
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9][A-Za-z0-9._/-]*)", line)
        if not match:
            fail("SHA256SUMS contains an unsupported line")
        digest, name = match.groups()
        relative(name)
        if name in checksums or name == "SHA256SUMS":
            fail("SHA256SUMS contains duplicate or self entries")
        checksums[name] = digest
        paths.append(name)
    if paths != sorted(paths) or set(checksums) != set(files) - {"SHA256SUMS"}:
        fail("SHA256SUMS must cover all payloads exactly once in sorted order")
    if any(checksum(files[name]) != digest for name, digest in checksums.items()):
        fail("bundle file checksum mismatch")


def verified_image(directory: Path) -> tuple[dict, dict[str, bytes], str]:
    """Use the actual #7 verifier, then copy only its exact closed inventory."""
    try:
        from realm_image_evidence import verify_evidence
    except ImportError:
        fail("the image-evidence implementation dependency is unavailable")

    try:
        receipt = verify_evidence(directory)
    except (ValueError, OSError, UnicodeError, RecursionError):
        fail("image evidence failed its owner verification")
    if not isinstance(receipt, dict):
        fail("image evidence verifier returned an unsupported receipt")
    same(receipt.get("contract"), "realm.image-evidence/v1", "image evidence contract")
    same(receipt.get("schema_version"), "1.0.0", "image evidence version")
    same(receipt.get("state"), "limited", "image evidence state")
    same(receipt.get("release_ready"), False, "image evidence readiness")
    files = inventory(directory)
    receipt_name = "image-evidence.json"
    if receipt_name not in files or len(files[receipt_name]) > MAX_JSON:
        fail("image evidence requires its fixed bounded receipt")
    same(decode_object(files[receipt_name]), receipt, "verified image receipt")
    expected = {
        relative(artifact["path"]) for artifact in receipt["artifacts"].values()
    } | {receipt_name}
    if set(files) != expected:
        fail("image evidence contains undeclared files")
    for artifact in receipt["artifacts"].values():
        data = files[artifact["path"]]
        if len(data) != artifact["bytes"] or checksum(data) != artifact["sha256"]:
            fail("captured image artifact changed after owner verification")
    return receipt, files, receipt_name


def bundle_files(
    version: str, revision: str, images: list[tuple[dict, dict[str, bytes], str]]
) -> dict[str, bytes]:
    """Render deterministic root metadata from verified immutable local payloads."""
    version_tag(version)
    source_revision(revision)
    if not 1 <= len(images) <= 2:
        fail("bundle supports one or two observed platform receipts")
    files = {}
    subjects = []
    external_documents = []
    observed_times = []
    platforms = set()
    local_ids = set()
    source_inputs = {}
    namespaces = set()
    for receipt, payloads, receipt_name in sorted(
        images, key=lambda item: item[0]["subject"]["platform"]
    ):
        same(
            receipt["source"]["repository"],
            "egohygiene/realm",
            "image source repository",
        )
        same(receipt["source"]["revision"], revision, "image source revision")
        for name, digest in receipt["source"]["inputs"].items():
            if name in source_inputs and source_inputs[name] != digest:
                fail("platform receipts contradict shared source-input checksums")
            source_inputs[name] = digest
        subject = receipt["subject"]
        platform = subject["platform"]
        if (
            not isinstance(platform, str)
            or platform not in {"linux/amd64", "linux/arm64"}
            or platform in platforms
        ):
            fail("platform receipts are unsupported or duplicated")
        platforms.add(platform)
        same(subject["identity_kind"], "local-config", "image identity kind")
        same(subject["execution"], "native", "image execution")
        for field in ("registry_reference", "registry_manifest_digest", "index_digest"):
            same(subject[field], None, "local-only image registry identity")
        if subject["local_config_digest"] in local_ids:
            fail("different platforms cannot share one local config identity")
        local_ids.add(subject["local_config_digest"])
        prefix = "image-evidence/" + platform.replace("/", "-")
        for name, data in payloads.items():
            files[f"{prefix}/{name}"] = data
        receipt_path = f"{prefix}/{receipt_name}"
        subjects.append(
            {
                "receipt": receipt_path,
                "receipt_sha256": checksum(payloads[receipt_name]),
                **subject,
            }
        )
        sbom_artifact = receipt["artifacts"]["sbom"]
        sbom = json.loads(payloads[sbom_artifact["path"]])
        namespace = namespace_uri(sbom.get("documentNamespace"))
        if namespace in namespaces:
            fail("platform SBOM namespaces must be distinct")
        namespaces.add(namespace)
        external_documents.append(
            {
                "externalDocumentId": "DocumentRef-" + platform.replace("/", "-"),
                "spdxDocument": namespace,
                "checksum": {
                    "algorithm": "SHA256",
                    "checksumValue": sbom_artifact["sha256"],
                },
            }
        )
        observed = datetime.fromisoformat(
            receipt["observed_at"].upper().replace("Z", "+00:00")
        )
        if observed.tzinfo is None:
            fail("image observation must include a timezone")
        observed_times.append(observed)
    manifest = {
        "schema_version": "realm.container-release/v1",
        "repository": "egohygiene/realm",
        "tag": version,
        "source_revision": revision,
        "profile": "container-image",
        "component": "realm-base",
        "images": subjects,
        "registry_index": None,
        "signature_authentication": "not-performed",
        "provenance_authentication": "not-performed",
        "release_ready": False,
        "publication": "not-performed",
    }
    files["image-digest.json"] = canonical(manifest)
    files["provenance.json"] = canonical(
        {
            "schema_version": "realm.container-release-provenance/v1",
            "source_revision": revision,
            "tag": version,
            "image_digest_record_sha256": checksum(files["image-digest.json"]),
            "image_receipts": [
                {"path": item["receipt"], "sha256": item["receipt_sha256"]}
                for item in subjects
            ],
            "state": "local-input-mapping",
            "authentication": "not-performed",
            "publication": "not-performed",
        }
    )
    files["signature.json"] = canonical(
        {
            "schema_version": "realm.container-release-signature/v1",
            "source_revision": revision,
            "tag": version,
            "image_digest_record_sha256": checksum(files["image-digest.json"]),
            "state": "unavailable",
            "verification": "not-performed",
            "bundle": None,
        }
    )
    identity = checksum(canonical(subjects))
    created = (
        max(observed_times).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    files["sbom.spdx.json"] = canonical(
        {
            "spdxVersion": "SPDX-2.3",
            "dataLicense": "CC0-1.0",
            "SPDXID": "SPDXRef-DOCUMENT",
            "name": f"realm-base-{version}-platform-evidence-index",
            "documentNamespace": f"https://github.com/egohygiene/realm/evidence/{revision}/{identity}/sbom",
            "creationInfo": {
                "created": created,
                "creators": ["Tool: realm-container-release/1.0.0"],
            },
            "externalDocumentRefs": external_documents,
            "relationships": [
                {
                    "spdxElementId": "SPDXRef-DOCUMENT",
                    "relationshipType": "DESCRIBES",
                    "relatedSpdxElement": item["externalDocumentId"]
                    + ":SPDXRef-DOCUMENT",
                }
                for item in external_documents
            ],
            "comment": "Index of exact per-platform installed-image SBOMs, not a merged installed package inventory. Created is the latest platform observation time for deterministic indexing. Local identities are not registry digests or authentication.",
        }
    )
    return files


def bundle(repository: Path, arguments: argparse.Namespace) -> dict:
    version_tag(arguments.version)
    source_revision(arguments.source_revision)
    if not 1 <= len(arguments.image_evidence) <= 2:
        fail("bundle supports one or two observed platform receipts")
    check(repository)
    output = Path(os.path.abspath(arguments.output))
    for directory in arguments.image_evidence:
        source = directory.resolve()
        if (
            output == source
            or output.is_relative_to(source)
            or source.is_relative_to(output)
        ):
            fail("bundle output must not overlap image evidence inputs")
    images = [verified_image(directory) for directory in arguments.image_evidence]
    files = bundle_files(arguments.version, arguments.source_revision, images)
    write_exclusive(arguments.output, repository, files)
    return {
        "status": "prepared-local-bundle",
        "tag": arguments.version,
        "source_revision": arguments.source_revision,
        "profile": "container-image",
        "observed_platforms": sorted(item[0]["subject"]["platform"] for item in images),
        "artifact_count": len(files),
        "signature": "unavailable",
        "provenance_authentication": "not-performed",
    }


def verify(repository: Path, arguments: argparse.Namespace) -> dict:
    check(repository)
    version_tag(arguments.version)
    source_revision(arguments.source_revision)
    files = inventory(arguments.bundle)
    verify_checksums(files)
    required = {
        "image-digest.json",
        "provenance.json",
        "signature.json",
        "sbom.spdx.json",
    }
    if not required.issubset(files):
        fail("Relay container-image required records are missing")
    manifest = decode_object(files["image-digest.json"])
    closed(
        manifest,
        {
            "schema_version",
            "repository",
            "tag",
            "source_revision",
            "profile",
            "component",
            "images",
            "registry_index",
            "signature_authentication",
            "provenance_authentication",
            "release_ready",
            "publication",
        },
        "image digest record",
    )
    if (
        not isinstance(manifest["images"], list)
        or not 1 <= len(manifest["images"]) <= 2
    ):
        fail("image digest record requires one or two platform entries")
    images = []
    for item in manifest["images"]:
        closed(
            item,
            {
                "receipt",
                "receipt_sha256",
                "identity_kind",
                "local_config_digest",
                "scanner_manifest_digest",
                "platform",
                "execution",
                "registry_reference",
                "registry_manifest_digest",
                "index_digest",
            },
            "platform entry",
        )
        platform = item["platform"]
        if not isinstance(platform, str) or platform not in {
            "linux/amd64",
            "linux/arm64",
        }:
            fail("platform entry is unsupported")
        prefix = "image-evidence/" + platform.replace("/", "-")
        name = relative(item["receipt"])
        if PurePosixPath(name).parent.as_posix() != prefix:
            fail("image receipt path disagrees with its platform")
        images.append(verified_image(arguments.bundle / prefix))
    expected = bundle_files(arguments.version, arguments.source_revision, images)
    if set(files) != set(expected) | {"SHA256SUMS"}:
        fail("bundle contains missing or unexpected payloads")
    if any(files[name] != data for name, data in expected.items()):
        fail("bundle records disagree with verified source, tag or image evidence")
    if arguments.require_release_ready:
        raise UnavailableError(
            "local evidence cannot establish registry identity, native multiarch release qualification or cryptographic authentication"
        )
    return {
        "status": "verified-local-bundle",
        "tag": arguments.version,
        "source_revision": arguments.source_revision,
        "profile": "container-image",
        "observed_platforms": sorted(item[0]["subject"]["platform"] for item in images),
        "artifact_count": len(expected),
        "signature": "unavailable",
        "provenance_authentication": "not-performed",
        "network_access": "not-performed",
        "registry_credentials": "not-required-for-local-verification",
    }


def envelope(report: dict) -> dict:
    return {
        "schema_version": "realm.release-result/v1",
        **report,
        "release_ready": False,
        "publication": "not-performed",
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repository", type=Path, default=ROOT)
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "check", help="Check the selected Realm profile and exact owner inputs offline."
    )
    commands.add_parser(
        "plan", help="Inspect a local proposed tag without mutation."
    ).add_argument("--version", required=True)
    preparation = commands.add_parser(
        "prepare", help="Create an exclusive review packet, leaving sources untouched."
    )
    preparation.add_argument("--version", required=True)
    preparation.add_argument("--date", required=True)
    preparation.add_argument("--output", type=Path, required=True)
    bundle_parser = commands.add_parser(
        "bundle", help="Map verified local image evidence to a portable Relay bundle."
    )
    bundle_parser.add_argument("--version", required=True)
    bundle_parser.add_argument("--source-revision", required=True)
    bundle_parser.add_argument(
        "--image-evidence", type=Path, action="append", required=True
    )
    bundle_parser.add_argument("--output", type=Path, required=True)
    verification = commands.add_parser(
        "verify", help="Check a portable local bundle without registry credentials."
    )
    verification.add_argument("--version", required=True)
    verification.add_argument("--source-revision", required=True)
    verification.add_argument("--bundle", type=Path, required=True)
    verification.add_argument("--require-release-ready", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        repository = arguments.repository.resolve()
        if arguments.command == "check":
            report = check(repository)
        elif arguments.command == "plan":
            report = plan(repository, arguments.version)
        elif arguments.command == "prepare":
            report = prepare(repository, arguments)
        elif arguments.command == "bundle":
            report = bundle(repository, arguments)
        else:
            report = verify(repository, arguments)
        print(json.dumps(envelope(report), indent=2, sort_keys=True))
        return 0
    except (
        ValueError,
        OSError,
        UnicodeError,
        RecursionError,
        subprocess.SubprocessError,
    ) as error:
        # Raw exception text may contain caller paths or source values. Public
        # reports retain controlled diagnoses rather than arbitrary file data.
        message = (
            str(error)
            if isinstance(error, ValueError)
            and not isinstance(error, (UnicodeError, json.JSONDecodeError))
            else "input unavailable, malformed or outside supported limits"
        )
        status = "unavailable" if isinstance(error, UnavailableError) else "invalid"
        print(
            json.dumps(
                envelope({"status": status, "message": message[:240]}), sort_keys=True
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
