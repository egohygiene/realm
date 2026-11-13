#!/usr/bin/env python3
"""Install Realm's checksum-pinned act client into an explicit local destination.

Copyright 2026 Ego Hygiene
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import stat
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
import zlib


ROOT = Path(__file__).resolve().parents[1]
PIN = ROOT / "config/act.v1.json"
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_EXPANDED_BYTES = 128 * 1024 * 1024
TARGETS = {
    "linux/amd64": ("x86_64", 62),
    "linux/arm64": ("arm64", 183),
}


def checksum(data: bytes) -> str:
    """Return the lowercase SHA-256 of exactly these bytes."""
    return hashlib.sha256(data).hexdigest()


def load_pin(path: Path = PIN) -> dict:
    """Read a closed, platform-complete official release pin."""
    pin = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(pin, dict) or set(pin) != {
        "schema_version", "repository", "version", "license", "artifacts", "source_revision"
    }:
        raise ValueError("act pin must contain exactly the documented fields")
    if (pin["schema_version"] != "realm.act-install/v1"
            or pin["repository"] != "nektos/act" or pin["license"] != "MIT"
            or not isinstance(pin["version"], str)
            or re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", pin["version"]) is None
            or not isinstance(pin["source_revision"], str)
            or re.fullmatch(r"[a-f0-9]{40}", pin["source_revision"]) is None):
        raise ValueError("act pin has an unsupported identity, license or version")
    if not isinstance(pin["artifacts"], dict) or set(pin["artifacts"]) != set(TARGETS):
        raise ValueError("act pin must cover exactly Linux AMD64 and ARM64")
    for target, (architecture, _) in TARGETS.items():
        artifact = pin["artifacts"][target]
        expected_url = (
            f'https://github.com/nektos/act/releases/download/v{pin["version"]}/'
            f"act_Linux_{architecture}.tar.gz"
        )
        if (not isinstance(artifact, dict) or set(artifact) != {"url", "sha256"}
                or artifact["url"] != expected_url
                or not isinstance(artifact["sha256"], str)
                or re.fullmatch(r"[a-f0-9]{64}", artifact["sha256"]) is None):
            raise ValueError(f"act pin has invalid source or checksum for {target}")
    return pin


def native_platform() -> str:
    """Select a native Linux archive without claiming Darwin or emulation support."""
    architecture = {"x86_64": "amd64", "amd64": "amd64",
                    "aarch64": "arm64", "arm64": "arm64"}.get(platform.machine().lower())
    if platform.system() != "Linux" or architecture is None:
        raise ValueError("Realm installer supports Linux AMD64/ARM64; use a Linux Dev Container on macOS")
    return f"linux/{architecture}"


def read_archive(path: Path) -> bytes:
    """Read an ordinary bounded local archive for offline installation."""
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= MAX_ARCHIVE_BYTES:
        raise ValueError("act archive must be a bounded regular non-symlink file")
    with path.open("rb") as stream:
        data = stream.read(MAX_ARCHIVE_BYTES + 1)
    if len(data) != info.st_size or len(data) > MAX_ARCHIVE_BYTES:
        raise ValueError("act archive changed or exceeded the size limit")
    return data


def download(artifact: dict) -> bytes:
    """Fetch a fixed official release asset using inherited proxy and CA settings."""
    with urllib.request.urlopen(artifact["url"], timeout=30) as response:
        data = response.read(MAX_ARCHIVE_BYTES + 1)
    if not 0 < len(data) <= MAX_ARCHIVE_BYTES:
        raise ValueError("act archive is empty or exceeds the size limit")
    return data


def executable(data: bytes, artifact: dict, target: str) -> bytes:
    """Check the release digest and archive before extracting only its act executable."""
    if not 0 < len(data) <= MAX_ARCHIVE_BYTES or checksum(data) != artifact["sha256"]:
        raise ValueError("act archive SHA-256 mismatch; no executable installed")
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
        expanded = stream.read(MAX_EXPANDED_BYTES + 1)
    if len(expanded) > MAX_EXPANDED_BYTES:
        raise ValueError("expanded act archive exceeds the size limit")
    payload = None
    seen = set()
    with tarfile.open(fileobj=io.BytesIO(expanded), mode="r:") as archive:
        for member in archive:
            name = member.name.rstrip("/")
            path = PurePosixPath(name)
            if (not name or "\\" in name or path.is_absolute()
                    or any(part in ("", ".", "..") for part in name.split("/"))
                    or name in seen or len(seen) >= 100
                    or not (member.isfile() or member.isdir())
                    or member.size < 0 or member.size > MAX_EXPANDED_BYTES):
                raise ValueError("unsafe or duplicate member in act archive")
            seen.add(name)
            if name == "act" and member.isfile():
                with archive.extractfile(member) as stream:
                    payload = stream.read(MAX_EXPANDED_BYTES + 1)
    if (payload is None or len(payload) < 20
            or payload[:6] != b"\x7fELF\x02\x01"
            or int.from_bytes(payload[18:20], "little") != TARGETS[target][1]):
        raise ValueError("act archive has no matching 64-bit Linux executable")
    return payload


def install(payload: bytes, output: Path) -> str:
    """Atomically create the client; an identical executable is a no-op."""
    if os.path.lexists(output):
        info = output.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_size != len(payload)
                or not info.st_mode & 0o111 or checksum(output.read_bytes()) != checksum(payload)):
            raise ValueError("act destination exists with different bytes or unsafe type; choose a new path")
        return "unchanged"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix=".realm-act-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
        temporary.chmod(0o755)
        os.link(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return "installed"


def main(argv: list[str] | None = None) -> int:
    """Install one declared client without starting Docker or executing a workflow."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("install",))
    parser.add_argument("--output", type=Path, required=True, help="Explicit destination executable path")
    parser.add_argument("--archive", type=Path, help="Use an already downloaded archive without network")
    parser.add_argument("--platform", choices=tuple(TARGETS), help="Defaults to the native Linux platform")
    parser.add_argument("--pin", type=Path, default=PIN)
    arguments = parser.parse_args(argv)
    try:
        pin = load_pin(arguments.pin)
        target = arguments.platform or native_platform()
        artifact = pin["artifacts"][target]
        data = read_archive(arguments.archive) if arguments.archive else download(artifact)
        payload = executable(data, artifact, target)
        status = install(payload, arguments.output)
    except (OSError, ValueError, tarfile.TarError, EOFError, urllib.error.URLError, zlib.error) as error:
        print(f"act installation failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"status": status, "version": pin["version"], "platform": target,
                      "archive_sha256": artifact["sha256"], "executable_sha256": checksum(payload)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
