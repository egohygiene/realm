#!/usr/bin/env python3
"""Check Realm's bounded mapping and authored-reference policy without execution.

This dependency-free checker does not implement the Dev Container JSON Schema.
Official schema, CLI, container, Task and host qualification are separate proofs.
"""
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MAPPING_PATH = "catalog/devcontainer-boundary.v1.json"
REFERENCE_PATH = "tests/fixtures/devcontainer/reference/.devcontainer/devcontainer.json"
SPEC_PATH = "vendor/devcontainers/devContainer.base.schema.json"
SPEC = {
    "repository": "devcontainers/spec",
    "revision": "c95ffeed1d059abfe9ffbe79762dc2fa4e7c2421",
    "schema_path": SPEC_PATH,
    "sha256": "a0883c0405ff433db188849d458fb20b9c0d73e0ba1a6e44c1d83f3b485408dd",
    "license": "CC-BY-4.0",
}
CLI = {
    "version": "0.90.0",
    "revision": "d807cb27c195b6bc0e89d893fc20f44a30bf27ee",
    "source": "https://github.com/devcontainers/cli/tree/d807cb27c195b6bc0e89d893fc20f44a30bf27ee",
}
CAPABILITIES = {
    "images",
    "dockerfiles",
    "compose",
    "features",
    "environment",
    "users",
    "mounts",
    "lifecycle",
    "ports",
    "host-requirements",
    "editor-customizations",
    "host-customizations",
    "prebuild-cache",
}
HOSTS = ("devcontainer-cli", "vscode", "codespaces", "devpod")
SUPPORT = {"supported", "degraded", "ignored", "host-specific", "unavailable"}
LAYERS = (
    "mapping",
    "reference_policy",
    "official_schema",
    "cli_interpretation",
    "container_execution",
    "task_workflow",
    "vscode",
    "codespaces",
    "devpod",
)
MAPPING_FIELDS = {
    "schema_version",
    "contract",
    "canonical_input",
    "projection_issue",
    "spec",
    "cli",
    "reference",
    "capabilities",
    "hosts",
}
CAPABILITY_FIELDS = {
    "id",
    "owner",
    "spec_properties",
    "realm_inputs",
    "handling",
    "limitations",
}
REFERENCE_FIELDS = {
    "$schema",
    "name",
    "image",
    "remoteUser",
    "containerUser",
    "updateRemoteUserUID",
    "containerEnv",
    "remoteEnv",
    "forwardPorts",
    "hostRequirements",
    "customizations",
    "features",
}
OCI_COMPONENT = re.compile(r"[a-z0-9]+(?:(?:[._]|__|-+)[a-z0-9]+)*")
REGISTRY = re.compile(r"[a-z0-9]+(?:[.-][a-z0-9]+)*(?::[0-9]{1,5})?")
USER_COMPONENT = re.compile(r"(?:[A-Za-z_][A-Za-z0-9_.-]*|[0-9]+)")


class BoundaryInputError(ValueError):
    """An input is outside the bounded, strict JSON reference contract."""


def read_bytes(path: Path, limit: int) -> bytes:
    """Read one regular, non-symlink file without trusting its reported size."""
    if not stat.S_ISREG(path.lstat().st_mode):
        raise BoundaryInputError(
            "Input must be a regular file within the bounded byte limit."
        )
    with path.open("rb") as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise BoundaryInputError("Input exceeds the bounded byte limit.")
    return data


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value = {}
    for key, item in pairs:
        if key in value:
            raise BoundaryInputError(
                "Duplicate JSON object keys are outside the reference policy."
            )
        value[key] = item
    return value


def reject_constant(_value: str) -> None:
    raise BoundaryInputError("Nonfinite JSON numbers are outside the reference policy.")


def read_json(path: Path, limit: int) -> tuple[Any, str]:
    data = read_bytes(path, limit)
    value = json.loads(
        data, object_pairs_hook=unique_object, parse_constant=reject_constant
    )
    return value, hashlib.sha256(data).hexdigest()


def object_shape(value: Any, fields: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == fields


def text(value: Any) -> bool:
    return isinstance(value, str) and 0 < len(value) <= 4096


def strings(value: Any) -> bool:
    return (
        isinstance(value, list)
        and 0 < len(value) <= 32
        and all(text(item) for item in value)
        and len(set(value)) == len(value)
    )


def add(checks: list[dict], code: str, passed: bool, message: str) -> None:
    checks.append(
        {"id": code, "status": "passed" if passed else "failed", "message": message}
    )


def mapping_checks(value: Any, checks: list[dict]) -> None:
    """Validate Realm's own closed mapping grammar, not the upstream schema."""
    shape = object_shape(value, MAPPING_FIELDS)
    add(
        checks,
        "mapping-shape",
        shape,
        "The Realm mapping has its supported closed object shape.",
    )
    if not shape:
        return
    identity = (
        value["schema_version"] == "1.0.0"
        and value["contract"] == "realm.devcontainer-boundary/v1"
        and value["canonical_input"] == "resolved-profile.v1"
        and value["projection_issue"] == "https://github.com/egohygiene/realm/issues/10"
    )
    add(
        checks,
        "mapping-identity",
        identity,
        "Canonical profiles and the separate projection owner are explicit.",
    )
    add(
        checks,
        "spec-selection",
        value["spec"] == SPEC,
        "The official schema selection and attribution match the reviewed pin.",
    )
    add(
        checks,
        "cli-selection",
        value["cli"] == CLI,
        "The reference CLI uses the reviewed immutable source selection.",
    )
    reference = value["reference"]
    reference_valid = (
        object_shape(reference, {"path", "kind", "realm_profile_applied"})
        and reference["path"] == REFERENCE_PATH
        and reference["kind"] == "authored-reference-only"
        and reference["realm_profile_applied"] is False
    )
    add(
        checks,
        "reference-role",
        reference_valid,
        "An authored reference does not claim an emitted Realm profile.",
    )
    capabilities = value["capabilities"]
    records_valid = isinstance(capabilities, list) and len(capabilities) == len(
        CAPABILITIES
    )
    found = []
    if records_valid:
        for row in capabilities:
            row_valid = (
                object_shape(row, CAPABILITY_FIELDS)
                and text(row["id"])
                and text(row["owner"])
                and row["owner"] in {"realm", "consumer", "host", "relay"}
                and strings(row["spec_properties"])
                and strings(row["realm_inputs"])
                and text(row["handling"])
                and strings(row["limitations"])
            )
            records_valid = records_valid and row_valid
            if row_valid:
                found.append(row["id"])
    coverage = (
        records_valid
        and len(set(found)) == len(CAPABILITIES)
        and set(found) == CAPABILITIES
    )
    add(
        checks,
        "capability-coverage",
        coverage,
        "All thirteen property families have typed, unique mapping and limitation records.",
    )
    hosts = value["hosts"]
    hosts_valid = isinstance(hosts, list) and len(hosts) == len(HOSTS)
    found_hosts = []
    if hosts_valid:
        for row in hosts:
            row_valid = (
                object_shape(row, {"id", "expected", "limitations"})
                and text(row["id"])
                and object_shape(row["expected"], CAPABILITIES)
                and all(
                    isinstance(status, str) and status in SUPPORT
                    for status in row["expected"].values()
                )
                and strings(row["limitations"])
            )
            hosts_valid = hosts_valid and row_valid
            if row_valid:
                found_hosts.append(row["id"])
    hosts_valid = (
        hosts_valid
        and len(set(found_hosts)) == len(HOSTS)
        and set(found_hosts) == set(HOSTS)
    )
    add(
        checks,
        "host-coverage",
        hosts_valid,
        "Four documented host expectations remain separate from execution evidence.",
    )


def environment(value: Any, nullable: bool = False) -> bool:
    return (
        isinstance(value, dict)
        and len(value) <= 128
        and all(
            re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key)
            and (isinstance(item, str) or (nullable and item is None))
            for key, item in value.items()
        )
    )


def digest_reference(value: Any) -> bool:
    """Accept a bounded OCI name/tag plus digest, without registry access."""
    if not isinstance(value, str) or len(value) > 4096 or value.count("@") != 1:
        return False
    name, digest = value.split("@")
    if re.fullmatch(r"sha256:[a-f0-9]{64}", digest) is None:
        return False
    components = name.split("/")
    if len(components) > 1 and (
        "." in components[0] or ":" in components[0] or components[0] == "localhost"
    ):
        registry = components.pop(0)
        if REGISTRY.fullmatch(registry) is None:
            return False
        if ":" in registry and not 1 <= int(registry.rsplit(":", 1)[1]) <= 65535:
            return False
    if ":" in components[-1]:
        components[-1], tag = components[-1].rsplit(":", 1)
        if re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}", tag) is None:
            return False
    return all(
        OCI_COMPONENT.fullmatch(component) is not None for component in components
    )


def explicit_nonroot_user(value: Any) -> bool:
    """Reject explicit root name/UID aliases; do not resolve image user databases."""
    if not text(value):
        return False
    components = value.split(":")
    if len(components) > 2 or any(
        USER_COMPONENT.fullmatch(item) is None for item in components
    ):
        return False
    user = components[0]
    return user != "root" and not (user.isdecimal() and int(user) == 0)


def reference_checks(value: Any, checks: list[dict]) -> None:
    """Apply a small authored-reference policy; never interpret or execute hooks."""
    shape = (
        isinstance(value, dict) and "image" in value and set(value) <= REFERENCE_FIELDS
    )
    add(
        checks,
        "reference-shape",
        shape,
        "The authored reference uses the bounded Realm policy subset, with no lifecycle or host-execution overrides.",
    )
    if not shape:
        return
    add(
        checks,
        "reference-image",
        digest_reference(value["image"]),
        "The reference image uses the bounded OCI name/tag and digest grammar; availability is not checked.",
    )
    users_valid = all(
        name not in value or explicit_nonroot_user(value[name])
        for name in ("remoteUser", "containerUser")
    ) and ("updateRemoteUserUID" not in value or value["updateRemoteUserUID"] is False)
    add(
        checks,
        "reference-users",
        users_valid,
        "Declared users avoid explicit root aliases and UID mutation; image defaults and user existence are not validated.",
    )
    env_valid = (
        "containerEnv" not in value or environment(value["containerEnv"])
    ) and ("remoteEnv" not in value or environment(value["remoteEnv"], nullable=True))
    add(
        checks,
        "reference-environment",
        env_valid,
        "Container and remote environment data retain their separate scopes.",
    )
    customizations = value.get("customizations", {})
    customization_valid = (
        isinstance(customizations, dict)
        and len(customizations) <= 16
        and all(
            text(name) and isinstance(settings, dict)
            for name, settings in customizations.items()
        )
    )
    add(
        checks,
        "reference-customizations",
        customization_valid,
        "Tool settings remain inside named host customization objects; permissions are not granted.",
    )
    features = value.get("features", {})
    features_valid = (
        isinstance(features, dict)
        and len(features) <= 32
        and all(
            digest_reference(name) and isinstance(options, dict)
            for name, options in features.items()
        )
    )
    add(
        checks,
        "reference-features",
        features_valid,
        "Feature identities use bounded digest references and object options; option schemas, installation and registry reachability are not validated.",
    )
    ports = value.get("forwardPorts", [])
    ports_valid = (
        isinstance(ports, list)
        and len(ports) <= 128
        and all(type(port) is int and 0 <= port <= 65535 for port in ports)
    )
    add(
        checks,
        "reference-ports",
        ports_valid,
        "The bounded reference uses numeric port declarations, without forwarding or reachability claims.",
    )
    requirements = value.get("hostRequirements", {})
    requirements_valid = isinstance(requirements, dict) and set(requirements) <= {
        "cpus",
        "memory",
        "storage",
        "gpu",
    }
    if requirements_valid:
        requirements_valid = (
            (
                "cpus" not in requirements
                or (type(requirements["cpus"]) is int and requirements["cpus"] >= 1)
            )
            and all(
                name not in requirements
                or (
                    isinstance(requirements[name], str)
                    and re.fullmatch(r"[0-9]+(?:[tgmk]b)?", requirements[name])
                    is not None
                )
                for name in ("memory", "storage")
            )
            and (
                "gpu" not in requirements
                or type(requirements["gpu"]) is bool
                or requirements["gpu"] == "optional"
            )
        )
    add(
        checks,
        "reference-requirements",
        requirements_valid,
        "Host requirements remain declared hints, without allocation or GPU proof.",
    )
    strings_valid = all(
        name not in value or text(value[name]) for name in ("$schema", "name")
    )
    add(
        checks,
        "reference-labels",
        strings_valid,
        "Reference labels remain bounded textual metadata.",
    )


def evaluate(arguments: argparse.Namespace) -> dict:
    checks: list[dict] = []
    digests = {"mapping": None, "reference": None, "spec_schema": None}
    for name, path, limit in (
        ("mapping", arguments.mapping, 131_072),
        ("reference", arguments.reference, 65_536),
    ):
        try:
            value, digests[name] = read_json(path, limit)
            (mapping_checks if name == "mapping" else reference_checks)(value, checks)
        except (OSError, UnicodeError, ValueError, RecursionError):
            add(
                checks,
                f"{name}-io",
                False,
                "A bounded regular input must contain unique-key strict JSON within its byte limit.",
            )
    try:
        path = ROOT / SPEC_PATH
        if not path.resolve().is_relative_to(ROOT):
            raise BoundaryInputError("Vendored input must remain inside the checkout.")
        digests["spec_schema"] = hashlib.sha256(read_bytes(path, 131_072)).hexdigest()
        add(
            checks,
            "mapping-schema-digest",
            digests["spec_schema"] == SPEC["sha256"],
            "The unmodified official base schema matches its pinned digest; full schema validation is separate.",
        )
    except (OSError, ValueError):
        add(
            checks,
            "mapping-schema-digest",
            False,
            "The pinned official schema must be a bounded regular local file.",
        )
    layers = dict.fromkeys(LAYERS, "not-performed")
    mapping_ids = {
        "mapping-shape",
        "mapping-identity",
        "mapping-io",
        "spec-selection",
        "cli-selection",
        "reference-role",
        "capability-coverage",
        "host-coverage",
        "mapping-schema-digest",
    }
    for layer in ("mapping", "reference_policy"):
        related = [
            check
            for check in checks
            if (check["id"] in mapping_ids) == (layer == "mapping")
        ]
        layers[layer] = (
            "failed"
            if any(check["status"] == "failed" for check in related)
            else "passed"
        )
    state = (
        "invalid" if any(check["status"] == "failed" for check in checks) else "valid"
    )
    if arguments.require_layer:
        required = arguments.require_layer.replace("-", "_")
        if state == "valid" and layers[required] != "passed":
            state = "unavailable"
    return {
        "schema_version": "1.0.0",
        "contract": "realm.devcontainer-boundary-report/v1",
        "scope": "mapping-and-reference-policy-only",
        "state": state,
        "input_digests": digests,
        "checks": checks,
        "evidence_layers": layers,
        "host_qualification": [
            {
                "id": host,
                "observed": "unavailable",
                "reason": "This read-only checker does not execute or qualify a host.",
            }
            for host in HOSTS
        ],
        "required_layer": arguments.require_layer,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check"])
    parser.add_argument("--mapping", type=Path, default=ROOT / MAPPING_PATH)
    parser.add_argument("--reference", type=Path, default=ROOT / REFERENCE_PATH)
    parser.add_argument(
        "--require-layer", choices=[layer.replace("_", "-") for layer in LAYERS]
    )
    report = evaluate(parser.parse_args())
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["state"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
