#!/usr/bin/env python3
"""Validate and summarize Realm's curated tool evaluation registry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any


SCHEMA_VERSION = "1.0.0"
CANONICAL_STATUSES = [
    "accepted",
    "experimental",
    "deferred",
    "rejected",
    "superseded",
]
REQUIRED_TOOL_FIELDS = {
    "display_name",
    "purpose",
    "category",
    "source",
    "version_source",
    "license",
    "platforms",
    "security",
    "maintenance",
    "overlap",
    "profile_candidate",
    "stable_capability",
    "status",
    "owner",
    "rationale",
    "tests",
}
MUTABLE_REFS = {"main", "master", "head", "latest", "edge", "dev", "snapshot"}


def load_registry(path: Path) -> dict[str, Any]:
    """Load a registry JSON object from disk."""
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def immutable_source(value: Any) -> bool:
    """Return whether a source reference is pinned to an immutable revision."""
    if not isinstance(value, str) or not value:
        return False
    if "snapshot.debian.org/archive/" in value:
        return bool(
            re.fullmatch(
                r"https://snapshot\.debian\.org/archive/"
                r"(?:debian|debian-security)/[0-9]{8}T[0-9]{6}Z/",
                value,
            )
        )
    if "@" not in value:
        return False
    source, reference = value.rsplit("@", 1)
    if not source or not reference or reference.lower() in MUTABLE_REFS:
        return False
    return bool(
        re.fullmatch(r"[0-9a-f]{40}", reference)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", reference)
        or re.fullmatch(
            r"v?[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?",
            reference,
        )
    )


def _string_list(value: Any, path: str, *, allow_empty: bool = True) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, list):
        return [f"{path} must be an array"]
    if not allow_empty and not value:
        errors.append(f"{path} must not be empty")
    if any(not isinstance(item, str) or not item for item in value):
        errors.append(f"{path} must contain non-empty strings")
    if len(value) != len(set(value)):
        errors.append(f"{path} must not contain duplicates")
    return errors


def validate_registry(registry: dict[str, Any]) -> list[str]:
    """Validate the registry's policy semantics without third-party packages."""
    errors: list[str] = []

    if registry.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if registry.get("statuses") != CANONICAL_STATUSES:
        errors.append("statuses must match the canonical ordered status list")

    tools = registry.get("tools")
    if not isinstance(tools, dict) or not tools:
        return sorted(set(errors + ["tools must be a non-empty object"]))

    if list(tools) != sorted(tools):
        errors.append("tools must be sorted by identifier for deterministic review")

    tool_names = set(tools)
    for tool_id, tool in tools.items():
        path = f"tools.{tool_id}"
        if not isinstance(tool, dict):
            errors.append(f"{path} must be an object")
            continue

        missing = REQUIRED_TOOL_FIELDS - set(tool)
        unexpected = set(tool) - REQUIRED_TOOL_FIELDS
        if missing:
            errors.append(f"{path} is missing fields: {', '.join(sorted(missing))}")
        if unexpected:
            errors.append(
                f"{path} has unexpected fields: {', '.join(sorted(unexpected))}"
            )
        if missing:
            continue

        for field in (
            "display_name",
            "purpose",
            "category",
            "source",
            "license",
            "profile_candidate",
            "owner",
            "rationale",
        ):
            if not isinstance(tool[field], str) or not tool[field].strip():
                errors.append(f"{path}.{field} must be a non-empty string")

        status = tool.get("status")
        if status not in CANONICAL_STATUSES:
            errors.append(f"{path}.status is not recognized: {status!r}")

        stable_capability = tool.get("stable_capability")
        if stable_capability is not None and (
            not isinstance(stable_capability, str) or not stable_capability.strip()
        ):
            errors.append(f"{path}.stable_capability must be a non-empty string or null")

        errors.extend(_string_list(tool.get("platforms"), f"{path}.platforms", allow_empty=False))
        errors.extend(_string_list(tool.get("overlap"), f"{path}.overlap"))
        errors.extend(_string_list(tool.get("tests"), f"{path}.tests"))

        unknown_overlap = set(tool.get("overlap", [])) - tool_names
        if unknown_overlap:
            errors.append(
                f"{path}.overlap references unknown tools: {', '.join(sorted(unknown_overlap))}"
            )
        if tool_id in tool.get("overlap", []):
            errors.append(f"{path}.overlap cannot reference itself")

        security = tool.get("security")
        if not isinstance(security, dict):
            errors.append(f"{path}.security must be an object")
        else:
            expected = {"risk", "privileged", "network_access", "notes"}
            if set(security) != expected:
                errors.append(f"{path}.security must contain exactly {sorted(expected)}")
            if security.get("risk") not in {"low", "medium", "high"}:
                errors.append(f"{path}.security.risk must be low, medium, or high")
            if not isinstance(security.get("privileged"), bool):
                errors.append(f"{path}.security.privileged must be boolean")
            if not isinstance(security.get("network_access"), bool):
                errors.append(f"{path}.security.network_access must be boolean")
            if not isinstance(security.get("notes"), str) or not security.get("notes"):
                errors.append(f"{path}.security.notes must be a non-empty string")

        maintenance = tool.get("maintenance")
        if not isinstance(maintenance, dict):
            errors.append(f"{path}.maintenance must be an object")
        else:
            expected = {"upstream", "review_cadence", "last_reviewed"}
            if set(maintenance) != expected:
                errors.append(
                    f"{path}.maintenance must contain exactly {sorted(expected)}"
                )
            for field in expected:
                if not isinstance(maintenance.get(field), str) or not maintenance.get(field):
                    errors.append(f"{path}.maintenance.{field} must be a non-empty string")

        if status == "accepted":
            if not immutable_source(tool.get("version_source")):
                errors.append(
                    f"{path} is accepted but version_source is not immutable"
                )
            if not tool.get("tests"):
                errors.append(f"{path} is accepted but has no owning test evidence")
            if not tool.get("profile_candidate"):
                errors.append(f"{path} is accepted but has no owning profile")
            if str(tool.get("license", "")).strip().lower() in {"", "unknown", "tbd"}:
                errors.append(f"{path} is accepted but its license is unresolved")
            if not isinstance(stable_capability, str) or not stable_capability:
                errors.append(f"{path} is accepted but has no stable capability")

        if status != "accepted" and stable_capability is not None:
            errors.append(f"{path} is not accepted but names a stable capability")

        if status in {"rejected", "superseded", "deferred"} and not tool.get("rationale"):
            errors.append(f"{path} requires a decision rationale")

    return sorted(set(errors))


def render_report(registry: dict[str, Any], status_filter: str | None = None) -> str:
    """Render a deterministic Markdown review queue."""
    tools = registry.get("tools", {})
    rows: list[str] = []
    for tool_id in sorted(tools):
        tool = tools[tool_id]
        if status_filter and tool.get("status") != status_filter:
            continue
        rows.append(
            "| {id} | {status} | {category} | {profile} | {risk} | {reviewed} |".format(
                id=tool_id,
                status=tool.get("status", "?"),
                category=tool.get("category", "?"),
                profile=tool.get("profile_candidate", "?"),
                risk=tool.get("security", {}).get("risk", "?"),
                reviewed=tool.get("maintenance", {}).get("last_reviewed", "?"),
            )
        )

    heading = "# Realm Tool Evaluation Registry"
    if status_filter:
        heading += f" — {status_filter}"
    header = [
        heading,
        "",
        "| Tool | Status | Category | Profile candidate | Risk | Last reviewed |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    return "\n".join(header + rows) + "\n"


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line interface."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("catalog/tool-evaluations.json"),
        help="Path to the tool evaluation registry.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="Validate registry structure and policy.")
    report = subparsers.add_parser("report", help="Render the review queue as Markdown.")
    report.add_argument(
        "--status",
        choices=CANONICAL_STATUSES,
        help="Optionally render only one lifecycle status.",
    )
    return parser


def main() -> int:
    """Run the registry command-line interface."""
    arguments = build_parser().parse_args()
    try:
        registry = load_registry(arguments.registry)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    errors = validate_registry(registry)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    if arguments.command == "validate":
        print(f"validated {len(registry['tools'])} tool evaluations")
        return 0
    if arguments.command == "report":
        sys.stdout.write(render_report(registry, arguments.status))
        return 0
    raise AssertionError(f"unhandled command: {arguments.command}")


if __name__ == "__main__":
    raise SystemExit(main())
