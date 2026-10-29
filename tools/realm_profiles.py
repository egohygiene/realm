#!/usr/bin/env python3
"""Validate and deterministically resolve Realm capability profiles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any


SCHEMA_VERSION = "1.0.0"
MUTABLE_REFS = {"main", "master", "head", "latest", "edge", "dev", "snapshot"}
FORBIDDEN_KEY_PARTS = (
    "api_key",
    "access_key",
    "credential",
    "password",
    "private_key",
    "secret_value",
    "token",
)
PACKAGE_MANAGER = {
    "docker": "apt",
    "devcontainer": "apt",
    "nix": "nix",
    "workstation": "nix",
}
CATALOG_FIELDS = {
    "schema_version",
    "catalog_version",
    "platforms",
    "projections",
    "source_pins",
    "capabilities",
}
CAPABILITY_FIELDS = {
    "version",
    "kind",
    "owner",
    "requires",
    "conflicts",
    "platforms",
    "projections",
    "packages",
    "artifacts",
    "constraints",
}
PROFILE_FIELDS = {
    "schema_version",
    "name",
    "description",
    "extends",
    "include",
    "exclude",
    "platforms",
    "projections",
    "constraints",
}

# Structural vocabulary mirrors the two published v1 schemas; semantics stay below.
VERSION_PATTERN = r"^[0-9]+\.[0-9]+\.[0-9]+$"
OWNER_PATTERN = r"^[a-z0-9_.-]+/[a-z0-9_.-]+$"
PROFILE_NAME_PATTERN = r"^[a-z][a-z0-9-]*$"
CAPABILITY_KINDS = ("foundation", "toolset", "language", "shell", "service")
PACKAGE_FIELDS = {"apt", "nix", "brew"}
ARTIFACT_FIELDS = {"name", "version", "source"}
CAPABILITY_CONSTRAINT_FIELDS = {"privileged", "services"}
PROFILE_CONSTRAINT_FIELDS = {"allow_privileged", "allow_services", "secrets"}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def load_profiles(directory: Path) -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.glob("*.profile.json")):
        profile = load_json(path)
        name = profile.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"{path} has no valid profile name")
        if name in profiles:
            raise ValueError(f"duplicate profile name: {name}")
        profiles[name] = profile
    if not profiles:
        raise ValueError(f"no profiles found in {directory}")
    return profiles


def _strings(value: Any, path: str) -> tuple[list[str], list[str]]:
    if not isinstance(value, list):
        return [], [f"{path} must be an array"]
    if any(not isinstance(item, str) or not item for item in value):
        return [], [f"{path} must contain non-empty strings"]
    if len(value) != len(set(value)):
        return value, [f"{path} must not contain duplicates"]
    return value, []


def _object_errors(value: Any, path: str, fields: set[str]) -> list[str]:
    """Check an exact object shape before callers inspect its members."""
    if not isinstance(value, dict):
        return [f"{path} must be an object"]
    errors: list[str] = []
    missing = fields - set(value)
    unexpected = set(value) - fields
    if missing:
        errors.append(f"{path} is missing required fields: {', '.join(sorted(missing))}")
    if unexpected:
        errors.append(
            f"{path} has unexpected fields: "
            + ", ".join(sorted(str(field) for field in unexpected))
        )
    return errors


def _string_errors(value: Any, path: str, pattern: str | None = None) -> list[str]:
    """Apply the v1 schemas' string type, minimum length, and optional pattern."""
    if not isinstance(value, str) or not value:
        return [f"{path} must be a non-empty string"]
    # JSON Schema patterns use search semantics, including the published anchors.
    if pattern is not None and re.search(pattern, value) is None:
        return [f"{path} must match pattern {pattern}"]
    return []


def _boolean_errors(value: Any, path: str) -> list[str]:
    """Reject numeric/string truthiness rather than coercing safety constraints."""
    if not isinstance(value, bool):
        return [f"{path} must be a boolean"]
    return []


def _catalog_structure_errors(catalog: Any) -> list[str]:
    """Enforce capability-catalog.v1.schema.json using only the standard library."""
    errors = _object_errors(catalog, "catalog", CATALOG_FIELDS)
    if not isinstance(catalog, dict):
        return errors
    if catalog.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"catalog schema_version must be {SCHEMA_VERSION}")
    errors.extend(_string_errors(catalog.get("catalog_version"), "catalog.catalog_version", VERSION_PATTERN))
    for field in ("platforms", "projections"):
        errors.extend(_strings(catalog.get(field), f"catalog.{field}")[1])
    sources = catalog.get("source_pins")
    if not isinstance(sources, dict) or not sources:
        errors.append("catalog.source_pins must be a non-empty object")
    else:
        for name, source in sources.items():
            errors.extend(_string_errors(source, f"catalog.source_pins.{name}"))
    capabilities = catalog.get("capabilities")
    if not isinstance(capabilities, dict) or not capabilities:
        return errors + ["catalog.capabilities must be a non-empty object"]
    for name, capability in capabilities.items():
        path = f"capability {name}"
        errors.extend(_object_errors(capability, path, CAPABILITY_FIELDS))
        if not isinstance(capability, dict):
            continue
        errors.extend(_string_errors(capability.get("version"), f"{path}.version", VERSION_PATTERN))
        errors.extend(_string_errors(capability.get("owner"), f"{path}.owner", OWNER_PATTERN))
        if capability.get("kind") not in CAPABILITY_KINDS:
            errors.append(f"{path}.kind must be one of: {', '.join(CAPABILITY_KINDS)}")
        for field in ("requires", "conflicts", "platforms", "projections"):
            errors.extend(_strings(capability.get(field), f"{name}.{field}")[1])
        packages = capability.get("packages")
        errors.extend(_object_errors(packages, f"{path}.packages", PACKAGE_FIELDS))
        if isinstance(packages, dict):
            for manager in sorted(PACKAGE_FIELDS):
                errors.extend(_strings(packages.get(manager), f"{name}.packages.{manager}")[1])
        artifacts = capability.get("artifacts")
        if not isinstance(artifacts, list):
            errors.append(f"{path}.artifacts must be an array")
        else:
            for index, artifact in enumerate(artifacts):
                artifact_path = f"{path}.artifacts[{index}]"
                errors.extend(_object_errors(artifact, artifact_path, ARTIFACT_FIELDS))
                if isinstance(artifact, dict):
                    for field in sorted(ARTIFACT_FIELDS):
                        errors.extend(_string_errors(artifact.get(field), f"{artifact_path}.{field}"))
        constraints = capability.get("constraints")
        errors.extend(_object_errors(constraints, f"{path}.constraints", CAPABILITY_CONSTRAINT_FIELDS))
        if isinstance(constraints, dict):
            for field in sorted(CAPABILITY_CONSTRAINT_FIELDS):
                errors.extend(_boolean_errors(constraints.get(field), f"{path}.constraints.{field}"))
    return errors


def _profiles_structure_errors(profiles: Any) -> list[str]:
    """Enforce profile.v1.schema.json for each profile before semantic traversal."""
    if not isinstance(profiles, dict):
        return ["profiles must be an object"]
    errors: list[str] = []
    for name, profile in profiles.items():
        path = f"profile {name}"
        errors.extend(_object_errors(profile, path, PROFILE_FIELDS))
        if not isinstance(profile, dict):
            continue
        if profile.get("schema_version") != SCHEMA_VERSION:
            errors.append(f"{path} schema_version must be {SCHEMA_VERSION}")
        errors.extend(_string_errors(profile.get("name"), f"{path}.name", PROFILE_NAME_PATTERN))
        errors.extend(_string_errors(profile.get("description"), f"{path}.description"))
        for field in ("extends", "include", "exclude", "platforms", "projections"):
            errors.extend(_strings(profile.get(field), f"{path}.{field}")[1])
        constraints = profile.get("constraints")
        errors.extend(_object_errors(constraints, f"{path}.constraints", PROFILE_CONSTRAINT_FIELDS))
        if isinstance(constraints, dict):
            for field in ("allow_privileged", "allow_services"):
                errors.extend(_boolean_errors(constraints.get(field), f"{path}.constraints.{field}"))
            if constraints.get("secrets") != "forbidden":
                errors.append(f"{path} must explicitly forbid secrets")
    return errors


def _secret_material_errors(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = re.sub(r"[^a-z0-9]+", "_", str(key).lower()).strip("_")
            if any(part in normalized for part in FORBIDDEN_KEY_PARTS):
                errors.append(f"secret-bearing field is forbidden: {path}.{key}")
            if normalized == "secrets" and child != "forbidden":
                errors.append(f"{path}.{key} must be the literal 'forbidden'")
            errors.extend(_secret_material_errors(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_secret_material_errors(child, f"{path}[{index}]"))
    return errors


def immutable_source(value: Any) -> bool:
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
        or re.fullmatch(r"v?[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?", reference)
    )


def _cycles(graph: dict[str, list[str]], kind: str) -> list[str]:
    errors: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str, stack: list[str]) -> None:
        if name in visiting:
            start = stack.index(name)
            errors.append(f"{kind} cycle: {' -> '.join(stack[start:] + [name])}")
            return
        if name in visited:
            return
        visiting.add(name)
        for dependency in graph.get(name, []):
            if dependency in graph:
                visit(dependency, stack + [name])
        visiting.remove(name)
        visited.add(name)

    for name in sorted(graph):
        visit(name, [])
    return errors


def validate_catalog(catalog: Any) -> list[str]:
    """Validate the complete v1 shape before catalog graph and source semantics."""
    errors = _catalog_structure_errors(catalog) + _secret_material_errors(catalog)
    if errors:
        return sorted(set(errors))
    platforms = catalog["platforms"]
    projections = catalog["projections"]
    for name, source in catalog["source_pins"].items():
        if not immutable_source(source):
            errors.append(f"source pin {name} must be immutable")
    capabilities = catalog["capabilities"]
    names = set(capabilities)
    graph: dict[str, list[str]] = {}
    for name, capability in capabilities.items():
        requires = capability["requires"]
        conflicts = capability["conflicts"]
        graph[name] = requires
        unknown = (set(requires) | set(conflicts)) - names
        if unknown:
            errors.append(f"capability {name} references unknown capabilities: {', '.join(sorted(unknown))}")
        if name in requires or name in conflicts:
            errors.append(f"capability {name} cannot require or conflict with itself")
        unknown_platforms = set(capability["platforms"]) - set(platforms)
        unknown_projections = set(capability["projections"]) - set(projections)
        if unknown_platforms:
            errors.append(f"capability {name} has unknown platforms: {', '.join(sorted(unknown_platforms))}")
        if unknown_projections:
            errors.append(f"capability {name} has unknown projections: {', '.join(sorted(unknown_projections))}")
        for index, artifact in enumerate(capability["artifacts"]):
            if not immutable_source(artifact["source"]):
                errors.append(f"capability {name} artifact {index} must use an immutable source")
        if capability["kind"] == "service" and not capability["constraints"]["services"]:
            errors.append(f"service capability {name} must declare services=true")
    errors.extend(_cycles(graph, "capability dependency"))
    return sorted(set(errors))


def validate_profiles(catalog: Any, profiles: Any) -> list[str]:
    """Validate catalog/profile structures before their cross-reference semantics."""
    errors = validate_catalog(catalog) + _profiles_structure_errors(profiles)
    if isinstance(profiles, dict):
        for name, profile in profiles.items():
            errors.extend(_secret_material_errors(profile, f"profile.{name}"))
    if errors:
        return sorted(set(errors))
    capability_names = set(catalog["capabilities"])
    graph: dict[str, list[str]] = {}
    for name, profile in profiles.items():
        if profile["name"] != name:
            errors.append(f"profile key {name} does not match its name field")
        parents = profile["extends"]
        included = profile["include"]
        excluded = profile["exclude"]
        graph[name] = parents
        unknown_parents = set(parents) - set(profiles)
        unknown_capabilities = (set(included) | set(excluded)) - capability_names
        if unknown_parents:
            errors.append(f"profile {name} extends unknown profiles: {', '.join(sorted(unknown_parents))}")
        if unknown_capabilities:
            errors.append(f"profile {name} references unknown capabilities: {', '.join(sorted(unknown_capabilities))}")
        if set(included) & set(excluded):
            errors.append(f"profile {name} includes and excludes the same capability")
        if set(profile["platforms"]) - set(catalog["platforms"]):
            errors.append(f"profile {name} references an unknown platform")
        if set(profile["projections"]) - set(catalog["projections"]):
            errors.append(f"profile {name} references an unknown projection")
    errors.extend(_cycles(graph, "profile inheritance"))
    return sorted(set(errors))


def resolve_profile(
    catalog: dict[str, Any],
    profiles: dict[str, dict[str, Any]],
    profile_name: str,
    platform: str,
    projection: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    errors = validate_profiles(catalog, profiles)
    if not isinstance(catalog, dict) or not isinstance(profiles, dict):
        return None, errors
    if profile_name not in profiles:
        return None, sorted(set(errors + [f"unknown profile: {profile_name}"]))
    if isinstance(catalog.get("platforms"), list) and platform not in catalog["platforms"]:
        errors.append(f"unknown platform: {platform}")
    if isinstance(catalog.get("projections"), list) and projection not in catalog["projections"]:
        errors.append(f"unknown projection: {projection}")

    # Invalid inheritance and metadata must never reach graph traversal.
    if errors:
        return None, sorted(set(errors))

    lineage: list[str] = []
    seen_profiles: set[str] = set()

    def add_profile(name: str) -> None:
        if name in seen_profiles:
            return
        for parent in sorted(profiles[name]["extends"]):
            if parent in profiles:
                add_profile(parent)
        seen_profiles.add(name)
        lineage.append(name)

    add_profile(profile_name)
    selected: set[str] = set()
    excluded: set[str] = set()
    for name in lineage:
        profile = profiles[name]
        if platform not in profile["platforms"]:
            errors.append(f"profile {name} does not support platform {platform}")
        if projection not in profile["projections"]:
            errors.append(f"profile {name} does not support projection {projection}")
        selected.update(profile["include"])
        excluded.update(profile["exclude"])
        selected.difference_update(profile["exclude"])

    capabilities = catalog.get("capabilities", {})
    queue = list(sorted(selected))
    while queue:
        name = queue.pop(0)
        capability = capabilities.get(name)
        if not isinstance(capability, dict):
            continue
        for dependency in capability["requires"]:
            if dependency in excluded:
                errors.append(f"excluded capability {dependency} is required by {name}")
            elif dependency not in selected:
                selected.add(dependency)
                queue.append(dependency)

    root_constraints = profiles[profile_name].get("constraints", {})
    for name in sorted(selected):
        capability = capabilities.get(name)
        if not isinstance(capability, dict):
            continue
        if platform not in capability["platforms"]:
            errors.append(f"capability {name} does not support platform {platform}")
        if projection not in capability["projections"]:
            errors.append(f"capability {name} does not support projection {projection}")
        conflicts = set(capability["conflicts"]) & selected
        if conflicts:
            errors.append(f"capability {name} conflicts with: {', '.join(sorted(conflicts))}")
        if capability["constraints"]["privileged"] and not root_constraints.get("allow_privileged"):
            errors.append(f"profile {profile_name} does not allow privileged capability {name}")
        if capability["constraints"]["services"] and not root_constraints.get("allow_services"):
            errors.append(f"profile {profile_name} does not allow service capability {name}")

    if errors:
        return None, sorted(set(errors))

    ordered_capabilities: list[str] = []
    seen_capabilities: set[str] = set()

    def add_capability(name: str) -> None:
        if name in seen_capabilities:
            return
        for dependency in sorted(capabilities[name]["requires"]):
            if dependency in selected:
                add_capability(dependency)
        seen_capabilities.add(name)
        ordered_capabilities.append(name)

    for name in sorted(selected):
        add_capability(name)

    manager = PACKAGE_MANAGER[projection]
    packages = sorted(
        {
            f"{manager}:{package}"
            for name in ordered_capabilities
            for package in capabilities[name]["packages"][manager]
        }
    )
    artifacts = sorted(
        (
            {**artifact, "capability": name}
            for name in ordered_capabilities
            for artifact in capabilities[name]["artifacts"]
        ),
        key=lambda artifact: (artifact["name"], artifact["version"], artifact["capability"]),
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "catalog_version": catalog["catalog_version"],
        "profile": profile_name,
        "lineage": lineage,
        "platform": platform,
        "projection": projection,
        "capabilities": ordered_capabilities,
        "packages": packages,
        "artifacts": artifacts,
        "source_pins": {name: catalog["source_pins"][name] for name in sorted(catalog["source_pins"])},
        "constraints": {
            "privileged": any(capabilities[name]["constraints"]["privileged"] for name in selected),
            "services": any(capabilities[name]["constraints"]["services"] for name in selected),
            "secrets": "forbidden",
        },
    }, []


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("catalog/capabilities.json"))
    parser.add_argument("--profiles", type=Path, default=Path("profiles"))
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate-catalog")
    subparsers.add_parser("validate-profiles")
    resolve = subparsers.add_parser("resolve")
    resolve.add_argument("--profile", required=True)
    resolve.add_argument("--platform", required=True)
    resolve.add_argument("--projection", required=True)
    resolve.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        catalog = load_json(arguments.catalog)
        profiles = load_profiles(arguments.profiles)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"contract load failed: {error}", file=sys.stderr)
        return 2
    if arguments.command == "validate-catalog":
        errors = validate_catalog(catalog)
    elif arguments.command == "validate-profiles":
        errors = validate_profiles(catalog, profiles)
    else:
        resolved, errors = resolve_profile(
            catalog,
            profiles,
            arguments.profile,
            arguments.platform,
            arguments.projection,
        )
        if not errors:
            assert resolved is not None
            arguments.output.parent.mkdir(parents=True, exist_ok=True)
            arguments.output.write_text(
                json.dumps(resolved, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            print(f"wrote {arguments.output}")
            return 0
    if errors:
        for error in errors:
            print(f"contract validation failed: {error}", file=sys.stderr)
        return 1
    print(
        f"contract valid: {len(catalog['capabilities'])} capabilities, "
        f"{len(profiles)} profiles"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
