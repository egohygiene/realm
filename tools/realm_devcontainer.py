#!/usr/bin/env python3
"""Generate and check a faithful, relocatable local Realm base Dev Container."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from realm_apt_packages import validate_configuration, validate_lock
from realm_profiles import resolve_profile, validate_profiles

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.0"
PLATFORMS = ("linux/amd64", "linux/arm64")
MAX_FILE_BYTES = 1024 * 1024
MAX_BUNDLE_BYTES = 8 * MAX_FILE_BYTES
MAX_SOURCE_ENTRIES = 128
MAX_SOURCE_BYTES = 8 * MAX_FILE_BYTES
MAX_BUNDLE_MEMBERS = 64
COPY_PATHS = (
    "LICENSE",
    "catalog/capabilities.json",
    "config/debian-trixie.json",
    "profiles/base.profile.json",
    "images/base/Dockerfile",
    "images/base/scripts/install-apt-packages",
    "images/base/scripts/verify-apt-packages",
    "images/base/scripts/realm-packages",
    "images/base/tests/smoke.sh",
)
LIMITATIONS = (
    "local-unpublished-template",
    "base-profile-only",
    "no-feature-distribution",
    "nix-and-workstation-not-emitted",
    "task-and-mantle-not-installed-base-capabilities",
    "runtime-and-host-proof-recorded-separately",
)


class ProjectionError(ValueError):
    """Reject an unavailable or unsafe projection without partial intent."""


@dataclass(frozen=True)
class BundleFile:
    data: bytes
    mode: int = 0o644


def json_bytes(value: Any) -> bytes:
    """Stable JSON serialization excludes timestamps and machine paths."""
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@contextmanager
def directory_fd(path: Path) -> Iterator[int]:
    """Open every directory component without following a symlink."""
    absolute = Path(os.path.abspath(path))
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in absolute.parts[1:]:
            child = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = child
        yield descriptor
    except OSError as error:
        raise ProjectionError(
            "symlink or inaccessible directory in selected path"
        ) from error
    finally:
        os.close(descriptor)


def read_regular(root: Path, relative: str) -> BundleFile:
    """Read one bounded regular source file using a non-following directory handle."""
    path = Path(relative)
    with directory_fd(root / path.parent) as parent:
        try:
            descriptor = os.open(
                path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent
            )
        except OSError as error:
            raise ProjectionError(
                f"source file is unavailable or a symlink: {relative}"
            ) from error
        with os.fdopen(descriptor, "rb") as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_FILE_BYTES:
                raise ProjectionError(
                    f"source file is not a bounded regular file: {relative}"
                )
            actual_mode = stat.S_IMODE(metadata.st_mode)
            if actual_mode & 0o7000:
                raise ProjectionError(
                    f"source file has unsupported permissions: {relative}"
                )
            # Git tracks owner execution, not checkout umask/group/read/write bits.
            mode = 0o755 if actual_mode & stat.S_IXUSR else 0o644
            data = stream.read(MAX_FILE_BYTES + 1)
            if len(data) > MAX_FILE_BYTES:
                raise ProjectionError(f"source file exceeds the byte limit: {relative}")
            return BundleFile(data, mode)


def strict_json(data: bytes) -> dict[str, Any]:
    """Reject duplicate members, non-finite values and non-object inputs."""

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in items:
            if key in value:
                raise ProjectionError("JSON has a duplicate member")
            value[key] = item
        return value

    def constant(_value: str) -> None:
        raise ProjectionError("JSON has a non-finite value")

    value = json.loads(data, object_pairs_hook=pairs, parse_constant=constant)
    if not isinstance(value, dict):
        raise ProjectionError("canonical JSON must contain an object")
    return value


def projection_files(
    source: Path, profile: str, platform: str
) -> dict[str, BundleFile]:
    """Resolve canonical intent and retain the existing lock-backed base recipe."""
    if profile != "base" or platform not in PLATFORMS:
        raise ProjectionError(
            "unsupported projection: only base on linux/amd64 and linux/arm64 is implemented"
        )
    architecture = platform.split("/")[1]
    lock_path = f"images/base/packages/locks/debian-trixie-{architecture}.lock.json"
    inputs: dict[str, BundleFile] = {}
    source_bytes = 0

    def add_input(name: str) -> BundleFile:
        nonlocal source_bytes
        item = read_regular(source, name)
        source_bytes += len(item.data) - len(
            inputs[name].data if name in inputs else b""
        )
        if source_bytes > MAX_SOURCE_BYTES:
            raise ProjectionError("canonical source aggregate exceeds its byte budget")
        inputs[name] = item
        return item

    for name in (*COPY_PATHS, lock_path):
        add_input(name)
    # Validate the complete profile graph using the existing canonical resolver.
    with directory_fd(source / "profiles") as profile_directory:
        profile_names: list[str] = []
        with os.scandir(profile_directory) as entries:
            for entry in entries:
                if len(profile_names) >= MAX_SOURCE_ENTRIES:
                    raise ProjectionError("profile directory exceeds its entry budget")
                profile_names.append(entry.name)
    profiles: dict[str, dict[str, Any]] = {}
    for name in sorted(profile_names):
        if not name.endswith(".profile.json"):
            continue
        relative = f"profiles/{name}"
        item = add_input(relative)
        value = strict_json(item.data)
        key = name.removesuffix(".profile.json")
        if value.get("name") != key:
            raise ProjectionError("profile filename and canonical name disagree")
        profiles[key] = value
    catalog = strict_json(inputs["catalog/capabilities.json"].data)
    config = strict_json(inputs["config/debian-trixie.json"].data)
    errors = validate_profiles(catalog, profiles)
    if errors:
        raise ProjectionError("invalid canonical profiles: " + "; ".join(errors))
    errors = validate_configuration(config, catalog)
    if errors:
        raise ProjectionError("invalid base configuration: " + "; ".join(errors))
    lock = strict_json(inputs[lock_path].data)
    errors = validate_lock(lock, config, catalog, profiles, architecture)
    if errors:
        raise ProjectionError("invalid package lock: " + "; ".join(errors))
    resolved, errors = resolve_profile(
        catalog, profiles, profile, platform, "devcontainer"
    )
    if errors or resolved is None:
        raise ProjectionError("profile does not resolve: " + "; ".join(errors))
    docker_resolved, errors = resolve_profile(
        catalog, profiles, profile, platform, "docker"
    )
    if errors or docker_resolved is None:
        raise ProjectionError("base image intent does not resolve")
    docker_resolved["projection"] = "devcontainer"
    if (
        resolved != docker_resolved
        or resolved["artifacts"]
        or resolved["constraints"]
        != {
            "privileged": False,
            "services": False,
            "secrets": "forbidden",
        }
    ):
        raise ProjectionError(
            "unsupported base intent: artifacts, services or projection differences cannot be dropped"
        )
    if any(
        not re.fullmatch(r"apt:[a-z0-9][a-z0-9+.-]*", name)
        for name in resolved["packages"]
    ):
        raise ProjectionError("unsupported base package name")

    recipe = inputs["images/base/Dockerfile"].data.decode("utf-8")
    base_pin = catalog["source_pins"][config["source_pins"]["base_image"]]
    if re.findall(r"^FROM\s+(\S+)\s+AS\s+realm-base\s*$", recipe, re.MULTILINE) != [
        base_pin
    ]:
        raise ProjectionError(
            "Dockerfile does not bind the exact configured base image"
        )
    if not recipe.startswith(
        f"# syntax={catalog['source_pins']['dockerfile-frontend']}\n"
    ):
        raise ProjectionError("Dockerfile does not bind the exact frontend pin")
    if "debian-trixie-${TARGETARCH}.lock.json" not in recipe:
        raise ProjectionError("Dockerfile does not select an architecture lock")
    for name in (
        "catalog/capabilities.json",
        "config/debian-trixie.json",
        "images/base/Dockerfile",
        "profiles/base.profile.json",
    ):
        if f"COPY {name} " not in recipe:
            raise ProjectionError(f"Dockerfile does not retain canonical input: {name}")

    generator = {
        "id": "realm-devcontainer",
        "version": VERSION,
        "sources": {
            name: sha256(read_regular(ROOT, name).data)
            for name in (
                "tools/realm_devcontainer.py",
                "tools/realm_profiles.py",
                "tools/realm_apt_packages.py",
            )
        },
    }
    source_records = {
        name: {"sha256": sha256(item.data), "mode": f"{item.mode:04o}"}
        for name, item in sorted(inputs.items())
    }
    identity = sha256(
        json_bytes(
            {"generator": generator, "inputs": source_records, "resolved": resolved}
        )
    )
    configuration = {
        "name": f"Realm base ({platform}; generated source)",
        "build": {
            "dockerfile": "../images/base/Dockerfile",
            "context": "..",
            "args": {
                "IMAGE_REVISION": f"source-input-sha256:{identity}",
                "IMAGE_VERSION": "0.0.0-dev",
            },
            "options": [f"--platform={platform}"],
        },
        "remoteUser": "vscode",
        "updateRemoteUserUID": False,
    }
    files = {name: inputs[name] for name in (*COPY_PATHS, lock_path)}
    files[".devcontainer/devcontainer.json"] = BundleFile(json_bytes(configuration))
    files["resolved-profile.v1.json"] = BundleFile(json_bytes(resolved))
    files[".dockerignore"] = BundleFile(
        b".devcontainer\nprojection.v1.json\nresolved-profile.v1.json\nREADME.md\n"
    )
    files["README.md"] = BundleFile(
        (
            f"# Generated Realm base ({platform})\n\n"
            "This relocatable local template retains the exact Realm-owned base recipe,\n"
            "snapshot lock and canonical inputs. `.devcontainer/devcontainer.json` builds\n"
            "from this directory; select the same native architecture or explicitly\n"
            "qualify an emulator separately. The default remote user remains vscode.\n\n"
            "`resolved-profile.v1.json` is the canonical resolver output.\n"
            "`projection.v1.json` binds generator/input/file hashes and limitations.\n"
            "Source generation proves no image build, registry publication or IDE/cloud\n"
            "conformance. Task, Python/ShellCheck test tooling and unreleased Mantle are\n"
            "not installed base capabilities; qualify any explicit overlay separately.\n"
        ).encode()
    )
    manifest = {
        "schema_version": "1.0.0",
        "generator": generator,
        "profile": profile,
        "platform": platform,
        "projection": "devcontainer",
        "status": "generated-source",
        "published": False,
        "source_identity": f"sha256:{identity}",
        "inputs": source_records,
        "resolved_sha256": sha256(files["resolved-profile.v1.json"].data),
        "files": [
            {"path": name, "sha256": sha256(item.data), "mode": f"{item.mode:04o}"}
            for name, item in sorted(files.items())
        ],
        "limitations": list(LIMITATIONS),
    }
    files["projection.v1.json"] = BundleFile(json_bytes(manifest))
    if sum(len(item.data) for item in files.values()) > MAX_BUNDLE_BYTES:
        raise ProjectionError("generated bundle exceeds its byte limit")
    return files


def write_bundle(output: Path, files: dict[str, BundleFile]) -> None:
    """Create an exclusive new bundle; never replace authored or racing output."""
    for name in files:
        path = Path(name)
        if (
            path.is_absolute()
            or not path.parts
            or ".." in path.parts
            or "\\" in name
            or str(path) != name
        ):
            raise ProjectionError("generated member must be a safe relative path")
    with directory_fd(output.parent) as parent:
        try:
            os.mkdir(output.name, 0o755, dir_fd=parent)
        except FileExistsError as error:
            raise ProjectionError(
                "output exists; choose a new directory instead of overwriting it"
            ) from error
        descriptor = os.open(
            output.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent
        )
        try:
            os.fchmod(descriptor, 0o755)
            for name, item in sorted(files.items()):
                parts = Path(name).parts
                directory = os.dup(descriptor)
                try:
                    for component in parts[:-1]:
                        try:
                            os.mkdir(component, 0o755, dir_fd=directory)
                        except FileExistsError:
                            pass
                        child = os.open(
                            component,
                            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=directory,
                        )
                        os.fchmod(child, 0o755)
                        os.close(directory)
                        directory = child
                    target = os.open(
                        parts[-1],
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                        item.mode,
                        dir_fd=directory,
                    )
                    with os.fdopen(target, "wb") as stream:
                        os.fchmod(stream.fileno(), item.mode)
                        stream.write(item.data)
                finally:
                    os.close(directory)
        finally:
            os.close(descriptor)


def check_bundle(output: Path, files: dict[str, BundleFile]) -> list[str]:
    """Compare bounded inventory, exact bytes and Git executable roles without writes."""
    errors: list[str] = []
    expected_directories = {
        str(parent)
        for name in files
        for parent in Path(name).parents
        if str(parent) != "."
    }
    seen: set[str] = set()
    member_count = 0

    def inspect(directory: int, prefix: Path) -> None:
        nonlocal member_count
        with os.scandir(directory) as entries:
            for entry in entries:
                member_count += 1
                if member_count > MAX_BUNDLE_MEMBERS:
                    raise ProjectionError(
                        "generated bundle exceeds its inventory budget"
                    )
                relative = str(prefix / entry.name)
                metadata = entry.stat(follow_symlinks=False)
                if stat.S_ISDIR(metadata.st_mode):
                    if relative not in expected_directories:
                        raise ProjectionError(
                            "unexpected directory in generated bundle"
                        )
                    child = os.open(
                        entry.name,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                        dir_fd=directory,
                    )
                    try:
                        inspect(child, Path(relative))
                    finally:
                        os.close(child)
                elif relative not in files:
                    errors.append(f"unexpected generated file: {relative}")
                else:
                    seen.add(relative)
                    actual = read_regular(output, relative)
                    if actual != files[relative]:
                        errors.append(f"generated file is different: {relative}")

    with directory_fd(output) as root:
        inspect(root, Path())
    errors.extend(
        f"generated file is missing: {name}" for name in sorted(set(files) - seen)
    )
    return sorted(errors)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("render", "check"))
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--profile", default="base")
    parser.add_argument("--platform", default="linux/amd64")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args(argv)
    try:
        files = projection_files(
            arguments.source_root, arguments.profile, arguments.platform
        )
        architecture = arguments.platform.split("/")[1]
        output = (
            arguments.output
            or ROOT / "dist/devcontainers" / f"base-linux-{architecture}"
        )
        if arguments.command == "render":
            write_bundle(output, files)
        else:
            errors = check_bundle(output, files)
            if errors:
                raise ProjectionError("; ".join(errors))
        print(
            json.dumps(
                {
                    "status": "generated"
                    if arguments.command == "render"
                    else "current",
                    "profile": arguments.profile,
                    "platform": arguments.platform,
                    "files": len(files),
                    "published": False,
                },
                sort_keys=True,
            )
        )
        return 0
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        RecursionError,
    ) as error:
        print(f"Dev Container projection unavailable: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
