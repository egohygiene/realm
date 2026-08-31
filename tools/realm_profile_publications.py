#!/usr/bin/env python3
"""Validate and publish deterministic Realm profile release declarations."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from realm_profiles import load_json, load_profiles, resolve_profile, validate_profiles
from realm_tool_registry import load_registry, validate_registry


SCHEMA_VERSION = "1.0.0"
PUBLICATION_VERSION = "1.0.0"
SPDX_CREATED = "2026-08-31T00:00:00Z"
SIZE_OWNER = "Realm issue #6"
SIZE_COMMAND = 'task image:size ARCH="<amd64|arm64>" IMAGE="<published-image>"'


def canonical_json(value: Any) -> str:
    """Encode JSON canonically for reproducible checksums and files."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def object_checksum(value: Any) -> str:
    """Return the SHA-256 checksum for one canonical JSON value."""

    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def text_checksum(value: str) -> str:
    """Return the SHA-256 checksum for one rendered UTF-8 text value."""

    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_inputs(
    catalog_path: Path,
    profiles_path: Path,
    registry_path: Path,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, Any]]:
    """Load Realm's three canonical profile-publication inputs."""

    return load_json(catalog_path), load_profiles(profiles_path), load_registry(registry_path)


def profile_combinations(
    catalog: dict[str, Any], profile: dict[str, Any]
) -> list[tuple[str, str]]:
    """Return the supported platform/projection combinations in stable order."""

    return [
        (platform, projection)
        for platform in catalog["platforms"]
        if platform in profile["platforms"]
        for projection in catalog["projections"]
        if projection in profile["projections"]
    ]


def stable_tools_for_capabilities(
    registry: dict[str, Any], capabilities: list[str]
) -> list[tuple[str, dict[str, Any]]]:
    """Return stable registry records represented by a resolved profile."""

    selected = set(capabilities)
    return [
        (tool_id, tool)
        for tool_id, tool in sorted(registry["tools"].items())
        if tool["status"] == "accepted" and tool["stable_capability"] in selected
    ]


def validate_profile_publications(
    catalog: dict[str, Any],
    profiles: dict[str, dict[str, Any]],
    registry: dict[str, Any],
) -> list[str]:
    """Validate the join from accepted-tool policy to resolved profiles."""

    errors = validate_profiles(catalog, profiles) + validate_registry(registry)
    if errors:
        return sorted(set(errors))

    capabilities = catalog["capabilities"]
    for tool_id, tool in sorted(registry["tools"].items()):
        if tool["status"] != "accepted":
            continue
        capability_name = tool["stable_capability"]
        profile_name = tool["profile_candidate"]
        if capability_name not in capabilities:
            errors.append(
                f"accepted tool {tool_id} names unknown capability {capability_name}"
            )
            continue
        if profile_name not in profiles:
            errors.append(
                f"accepted tool {tool_id} names unknown profile {profile_name}"
            )
            continue
        capability = capabilities[capability_name]
        if not set(tool["platforms"]).issubset(capability["platforms"]):
            errors.append(
                f"accepted tool {tool_id} has platforms outside {capability_name}"
            )
        if not set(tool["platforms"]).issubset(profiles[profile_name]["platforms"]):
            errors.append(
                f"accepted tool {tool_id} has platforms outside profile {profile_name}"
            )
        for platform, projection in profile_combinations(catalog, profiles[profile_name]):
            resolved, resolution_errors = resolve_profile(
                catalog, profiles, profile_name, platform, projection
            )
            if resolution_errors or resolved is None:
                errors.append(
                    f"accepted tool {tool_id} cannot resolve {profile_name} "
                    f"for {platform}/{projection}: {'; '.join(resolution_errors)}"
                )
            elif capability_name not in resolved["capabilities"]:
                errors.append(
                    f"accepted tool {tool_id} capability {capability_name} is absent "
                    f"from {profile_name}"
                )
    return sorted(set(errors))


def _spdx_id(value: str) -> str:
    """Return a conservative SPDX identifier suffix from a Realm identifier."""

    return "".join(character if character.isalnum() else "-" for character in value)


def build_spdx(
    profile_name: str,
    cache_key: str,
    stable_tools: list[tuple[str, dict[str, Any]]],
    resolved_by_target: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build a declared-intent SPDX document, not a build attestation."""

    packages: list[dict[str, Any]] = []
    relationships: list[dict[str, str]] = []
    declared_packages = sorted(
        {
            package
            for resolved in resolved_by_target.values()
            for package in resolved["packages"]
        }
    )
    for package in declared_packages:
        manager, package_name = package.split(":", 1)
        spdx_id = f"SPDXRef-Package-{_spdx_id(manager)}-{_spdx_id(package_name)}"
        packages.append(
            {
                "SPDXID": spdx_id,
                "name": package,
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": "NOASSERTION",
                "supplier": "Organization: egohygiene/realm",
                "comment": (
                    "Declared Realm package intent. The projected build must attest "
                    "the resolved package version and installed license metadata."
                ),
            }
        )
        relationships.append(
            {
                "spdxElementId": "SPDXRef-DOCUMENT",
                "relationshipType": "DESCRIBES",
                "relatedSpdxElement": spdx_id,
            }
        )
    for tool_id, tool in stable_tools:
        spdx_id = f"SPDXRef-Tool-{_spdx_id(tool_id)}"
        packages.append(
            {
                "SPDXID": spdx_id,
                "name": tool["display_name"],
                "versionInfo": tool["version_source"],
                "downloadLocation": tool["version_source"],
                "filesAnalyzed": False,
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": "NOASSERTION",
                "supplier": f"Organization: {tool['owner']}",
                "comment": (
                    f"Realm tool id: {tool_id}; declared upstream license: "
                    f"{tool['license']}; capability: {tool['stable_capability']}."
                ),
            }
        )
        relationships.append(
            {
                "spdxElementId": "SPDXRef-DOCUMENT",
                "relationshipType": "DESCRIBES",
                "relatedSpdxElement": spdx_id,
            }
        )
    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"realm-profile-{profile_name}",
        "documentNamespace": (
            "https://schemas.egohygiene.io/realm/profile-sbom/"
            f"{profile_name}/{cache_key.removeprefix('sha256:')}"
        ),
        "creationInfo": {
            "created": SPDX_CREATED,
            "creators": ["Tool: realm-profile-publications/1.0.0"],
            "comment": (
                "Declared profile intent only. A published OCI image requires its "
                "own build-time SBOM and provenance attestation."
            ),
        },
        "documentDescribes": [package["SPDXID"] for package in packages],
        "packages": packages,
        "relationships": relationships,
    }


def build_profile_publication(
    catalog: dict[str, Any],
    profiles: dict[str, dict[str, Any]],
    registry: dict[str, Any],
    profile_name: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build one deterministic profile manifest and its declared-intent SBOM."""

    profile = profiles[profile_name]
    resolved_by_target: dict[str, dict[str, Any]] = {}
    for platform, projection in profile_combinations(catalog, profile):
        resolved, errors = resolve_profile(catalog, profiles, profile_name, platform, projection)
        if errors or resolved is None:
            raise ValueError(
                f"cannot resolve {profile_name} for {platform}/{projection}: "
                + "; ".join(errors)
            )
        resolved_by_target[f"{platform}/{projection}"] = resolved

    first = next(iter(resolved_by_target.values()))
    stable_tools = stable_tools_for_capabilities(registry, first["capabilities"])
    cache_inputs = {
        "catalog_checksum": object_checksum(catalog),
        "registry_checksum": object_checksum(registry),
        "profile_checksums": {
            name: object_checksum(profiles[name]) for name in first["lineage"]
        },
        "resolved_targets": resolved_by_target,
    }
    cache_key = object_checksum(cache_inputs)
    sbom = build_spdx(profile_name, cache_key, stable_tools, resolved_by_target)
    sbom_text = json.dumps(sbom, indent=2, ensure_ascii=False) + "\n"
    support = [
        {"platform": platform, "projections": [projection for candidate, projection in profile_combinations(catalog, profile) if candidate == platform]}
        for platform in catalog["platforms"]
        if platform in profile["platforms"]
    ]
    packages = {
        projection: sorted(
            {
                package
                for target, resolved in resolved_by_target.items()
                if target.endswith(f"/{projection}")
                for package in resolved["packages"]
            }
        )
        for projection in catalog["projections"]
        if projection in profile["projections"]
    }
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "publication_version": PUBLICATION_VERSION,
        "profile": profile_name,
        "description": profile["description"],
        "catalog_checksum": object_checksum(catalog),
        "registry_checksum": object_checksum(registry),
        "profile_checksum": object_checksum(profile),
        "cache_key": cache_key,
        "contents": {
            "capabilities": first["capabilities"],
            "packages": packages,
            "artifacts": first["artifacts"],
            "tools": [
                {
                    "id": tool_id,
                    "license": tool["license"],
                    "owner": tool["owner"],
                    "source": tool["version_source"],
                    "stable_capability": tool["stable_capability"],
                }
                for tool_id, tool in stable_tools
            ],
        },
        "support": support,
        "size": {
            "status": "unmeasured",
            "metric": "expanded OCI image bytes",
            "owner": SIZE_OWNER,
            "command": SIZE_COMMAND,
            "reason": (
                "No profile OCI image has been built or published. Do not infer an "
                "image size from declared package names."
            ),
        },
        "sbom": {
            "format": "SPDX-2.3 declared-intent",
            "path": "sbom.spdx.json",
            "sha256": text_checksum(sbom_text),
        },
    }
    return manifest, sbom


def render_support_matrix(
    catalog: dict[str, Any], profiles: dict[str, dict[str, Any]]
) -> str:
    """Render the human-reviewable profile/platform/projection matrix."""

    lines = [
        "# Realm Profile Support Matrix",
        "",
        "This matrix declares supported profile inputs. OCI build, size, SBOM, and "
        "provenance evidence become release claims only after the corresponding image "
        "is built and verified.",
        "",
        "| Profile | Platform | Docker | Dev Container | Nix | Workstation |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for profile_name, profile in sorted(profiles.items()):
        for platform in catalog["platforms"]:
            if platform not in profile["platforms"]:
                continue
            support = {
                projection: "yes" if projection in profile["projections"] else "—"
                for projection in catalog["projections"]
            }
            lines.append(
                "| {profile} | {platform} | {docker} | {devcontainer} | {nix} | {workstation} |".format(
                    profile=profile_name,
                    platform=platform,
                    **support,
                )
            )
    return "\n".join(lines) + "\n"


def publication_files(
    catalog: dict[str, Any],
    profiles: dict[str, dict[str, Any]],
    registry: dict[str, Any],
) -> dict[Path, str]:
    """Return all checked-in publication files keyed by relative path."""

    files = {
        Path("support-matrix.v1.md"): render_support_matrix(catalog, profiles),
    }
    for profile_name in sorted(profiles):
        manifest, sbom = build_profile_publication(catalog, profiles, registry, profile_name)
        directory = Path(profile_name)
        files[directory / "manifest.v1.json"] = (
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
        )
        files[directory / "sbom.spdx.json"] = json.dumps(sbom, indent=2, ensure_ascii=False) + "\n"
    return files


def write_publications(output: Path, files: dict[Path, str]) -> None:
    """Write deterministic publication artifacts without deleting unrelated files."""

    for relative_path, contents in files.items():
        path = output / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")


def check_publications(output: Path, files: dict[Path, str]) -> list[str]:
    """Return drift errors for a checked-in publication artifact directory."""

    errors: list[str] = []
    expected = set(files)
    if not output.exists():
        return [f"publication directory does not exist: {output}"]
    actual = {path.relative_to(output) for path in output.rglob("*") if path.is_file()}
    for path in sorted(expected - actual):
        errors.append(f"publication file is missing: {path}")
    for path in sorted(actual - expected):
        errors.append(f"publication file is stale or unexpected: {path}")
    for path in sorted(expected & actual):
        actual_text = (output / path).read_text(encoding="utf-8")
        if actual_text != files[path]:
            errors.append(f"publication file is out of date: {path}")
    return errors


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line interface."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("catalog/capabilities.json"))
    parser.add_argument("--profiles", type=Path, default=Path("profiles"))
    parser.add_argument("--registry", type=Path, default=Path("catalog/tool-evaluations.json"))
    parser.add_argument("--output", type=Path, default=Path("dist/profiles"))
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="Validate accepted-tool/profile admission.")
    subparsers.add_parser("render", help="Render checked-in profile publication artifacts.")
    subparsers.add_parser("check", help="Check checked-in publication artifacts for drift.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run profile-publication validation or rendering."""

    arguments = build_parser().parse_args(argv)
    try:
        catalog, profiles, registry = load_inputs(
            arguments.catalog, arguments.profiles, arguments.registry
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"publication input load failed: {error}", file=sys.stderr)
        return 2
    errors = validate_profile_publications(catalog, profiles, registry)
    if errors:
        for error in errors:
            print(f"publication validation failed: {error}", file=sys.stderr)
        return 1
    files = publication_files(catalog, profiles, registry)
    if arguments.command == "validate":
        print(f"publication contract valid: {len(profiles)} profiles")
        return 0
    if arguments.command == "render":
        write_publications(arguments.output, files)
        print(f"wrote {len(files)} publication files to {arguments.output}")
        return 0
    errors = check_publications(arguments.output, files)
    if errors:
        for error in errors:
            print(f"publication check failed: {error}", file=sys.stderr)
        return 1
    print(f"publication artifacts current: {len(files)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
