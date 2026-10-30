"""Acquire reviewed Mantle source and exercise its public runtime in temporary homes.

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
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zlib


ROOT = Path(__file__).resolve().parents[1]
PIN = ROOT / "config/mantle-source-canary.json"
MAX_BYTES = 32 * 1024 * 1024
SHELLS = ("bash", "zsh", "fish")


def load_pin(path: Path = PIN) -> dict:
    pin = json.loads(path.read_text(encoding="utf-8"))
    fields = {"schema_version", "kind", "repository", "revision", "url", "sha256",
              "source_version", "released_integration"}
    if not isinstance(pin, dict) or set(pin) != fields:
        raise ValueError("source pin must contain exactly the documented fields")
    if (pin["schema_version"] != "realm.mantle-source-canary/v1"
            or pin["kind"] != "source-canary"
            or pin["repository"] != "egohygiene/mantle"
            or pin["released_integration"] is not False
            or pin["source_version"] != "0.1.0-dev"):
        raise ValueError("source canary cannot claim a released integration")
    if not isinstance(pin["revision"], str) or not re.fullmatch(r"[0-9a-f]{40}", pin["revision"]):
        raise ValueError("source revision must be an exact commit")
    if not isinstance(pin["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", pin["sha256"]):
        raise ValueError("source checksum must be an exact SHA-256")
    if pin["url"] != f'https://codeload.github.com/egohygiene/mantle/tar.gz/{pin["revision"]}':
        raise ValueError("source URL must bind the reviewed Mantle commit")
    return pin


def verify_bytes(data: bytes, pin: dict) -> None:
    if len(data) > MAX_BYTES:
        raise ValueError("source archive exceeds the bounded size")
    if hashlib.sha256(data).hexdigest() != pin["sha256"]:
        raise ValueError("SHA-256 mismatch; source archive will not be executed")


def fetch(pin: dict, output: Path) -> None:
    # Check before opening a network connection; link() also closes the race.
    if os.path.lexists(output):
        raise ValueError("archive destination already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(pin["url"], timeout=60) as response:
        if response.geturl() != pin["url"]:
            raise ValueError("unexpected source archive redirect")
        data = response.read(MAX_BYTES + 1)
    verify_bytes(data, pin)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix=".mantle-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
        os.link(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def unpack(data: bytes, pin: dict, destination: Path) -> Path:
    """Reject unsafe members before writing; no archive-controlled links or modes."""
    verify_bytes(data, pin)
    top = f'mantle-{pin["revision"]}'
    # Tar parsers consume hidden PAX/GNU metadata before yielding members.
    # Bound the complete expanded stream before handing any of it to tarfile.
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as compressed:
            expanded = compressed.read(MAX_BYTES + 1)
    except (EOFError, OSError, zlib.error) as error:
        raise ValueError("invalid or truncated gzip source archive") from error
    if len(expanded) > MAX_BYTES:
        raise ValueError("expanded source archive exceeds the bounded size")
    with tarfile.open(fileobj=io.BytesIO(expanded), mode="r:") as archive:
        members = []
        total = 0
        for member in archive:
            members.append(member)
            total += member.size
            if len(members) > 2000 or member.size < 0 or total > MAX_BYTES:
                raise ValueError("source archive inventory exceeds the bounded size")
        seen = set()
        for member in members:
            name = member.name.rstrip("/")
            path = PurePosixPath(name)
            if (not name or "\\" in name or path.is_absolute()
                    or any(part in ("", ".", "..") for part in name.split("/"))
                    or path.parts[0] != top or name in seen
                    or not (member.isdir() or member.isfile())):
                raise ValueError("unsafe or duplicate source archive member")
            seen.add(name)
        for member in members:
            target = destination / member.name
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output)
                target.chmod(0o755 if member.mode & 0o111 else 0o644)
    source = destination / top
    for required in (".shellrc", "install.sh", "bin/mantle", "runtime/shells/fish/runtime.fish", "LICENSE", "VERSION"):
        if not (source / required).is_file():
            raise ValueError("source archive lacks a required public Mantle surface")
    if (source / "VERSION").read_text().strip() != pin["source_version"]:
        raise ValueError("source VERSION does not match the canary pin")
    return source


def run_case(name: str, arguments: list[str], environment: dict, checks: list,
             expected: int = 0, marker: bool = True, deadline: float = 30) -> None:
    process = subprocess.Popen(arguments, env=environment, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, start_new_session=True)
    try:
        stdout, _ = process.communicate(timeout=deadline)
    except subprocess.TimeoutExpired as error:
        # Descendants may retain output pipes after the direct shell exits.
        # Terminate only this newly created job, then collect its output.
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.communicate(timeout=0.5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
        raise ValueError(f"{name}: exceeded the canary deadline") from error
    if process.returncode != expected or (marker and stdout != "realm-mantle-ok\n"):
        # Shell output may include machine paths; keep it out of public receipts.
        raise ValueError(f"{name}: unexpected process outcome (exit {process.returncode})")
    checks.append({"case": name, "status": "passed", "exit_code": process.returncode})


def shell_command(shell: str, interactive: bool, body: str, home: Path) -> list[str]:
    if shell == "bash":
        flags = ["--noprofile", "--rcfile", str(home / ".bashrc"), "-i"] if interactive else ["--noprofile", "--norc"]
    elif shell == "zsh":
        flags = ["-d", "-i"] if interactive else ["-d", "-f"]
    else:
        flags = ["--private", "--interactive"] if interactive else ["--private", "--no-config"]
    return [shutil.which(shell), *flags, "-c", body]


def activation(shell: str) -> str:
    if shell == "fish":
        return ('set -gx MANTLE_ROOT "$REALM_EXPECTED_PREFIX"; '
                'source "$MANTLE_ROOT/runtime/shells/fish/runtime.fish"; or exit $status; ')
    return 'source "$REALM_EXPECTED_PREFIX/.shellrc" || exit $?; '


def observation(shell: str) -> str:
    if shell == "fish":
        return ('test "$MANTLE_ROOT" = "$REALM_EXPECTED_PREFIX"; and '
                'test "$MANTLE_ACTIVE_PROFILE" = "$MANTLE_PROFILE"; and '
                'test "$MANTLE_SHELL_NAME" = fish; and '
                'test (command -s mantle) = "$REALM_EXPECTED_PREFIX/bin/mantle"; and '
                'test (mantle version --short) = "$REALM_EXPECTED_VERSION"; and '
                'printf "realm-mantle-ok\\n"')
    return ('test "$MANTLE_ROOT" = "$REALM_EXPECTED_PREFIX" && '
            'test "$MANTLE_ACTIVE_PROFILE" = "$MANTLE_PROFILE" && '
            f'test "$MANTLE_SHELL_NAME" = {shell} && '
            'test "$(command -v mantle)" = "$REALM_EXPECTED_PREFIX/bin/mantle" && '
            'test "$(mantle version --short)" = "$REALM_EXPECTED_VERSION" && '
            'printf "realm-mantle-ok\\n"')


def canary(pin: dict, archive: Path) -> dict:
    # Read once: the verified bytes are exactly the bytes later extracted.
    if archive.is_symlink() or not archive.is_file() or archive.stat().st_size > MAX_BYTES:
        raise ValueError("source archive must be a bounded regular non-symlink file")
    with archive.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    verify_bytes(data, pin)
    for shell in SHELLS:
        if not shutil.which(shell):
            raise ValueError(f"required canary shell is unavailable: {shell}")
    checks = []
    with tempfile.TemporaryDirectory(prefix="realm-mantle-") as temporary:
        base = Path(temporary)
        source = unpack(data, pin, base / "source")
        home = base / "home"
        home.mkdir()
        prefix = base / "installed runtime"
        # No inherited startup hooks, credentials, Mantle settings or HOME/XDG.
        environment = {
            "PATH": os.environ.get("PATH", os.defpath), "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"), "XDG_DATA_HOME": str(home / ".local/share"),
            "XDG_CACHE_HOME": str(home / ".cache"), "XDG_STATE_HOME": str(home / ".local/state"),
            "XDG_RUNTIME_DIR": str(home / ".run"), "ZDOTDIR": str(home),
            "TERM": "dumb", "LC_ALL": "C", "MANTLE_PROFILE": "container",
            "MANTLE_STARTUP_DISPLAY": "0", "REALM_EXPECTED_PREFIX": str(prefix),
            "REALM_EXPECTED_VERSION": pin["source_version"],
        }
        run_case("copy-install", [shutil.which("bash"), str(source / "install.sh"),
                 "--prefix", str(prefix), "--shell", "all", "--pin", pin["source_version"]],
                 environment, checks, marker=False)
        for shell in SHELLS:
            run_case(f"{shell}-interactive-hook", shell_command(shell, True, observation(shell), home), environment, checks)
            run_case(f"{shell}-explicit-noninteractive", shell_command(shell, False, activation(shell) + observation(shell), home), environment, checks)
            ci = dict(environment, CI="1", MANTLE_PROFILE="ci")
            run_case(f"{shell}-ci-command", shell_command(shell, False, activation(shell) + observation(shell), home), ci, checks)
            run_case(f"{shell}-command-status", shell_command(shell, False, activation(shell) + "exit 23", home), ci, checks, expected=23, marker=False)
            invalid = dict(environment, MANTLE_PROFILE="not-a-profile")
            arguments = shell_command(shell, False, activation(shell) + observation(shell), home)
            run_case(f"{shell}-reject-invalid-profile", arguments, invalid, checks, expected=64, marker=False)
        # Installer hooks guard missing payloads; a plain shell must still open.
        displaced = base / "temporarily unavailable runtime"
        prefix.rename(displaced)
        recovery = 'test -z "${MANTLE_ROOT:-}" && printf "realm-mantle-ok\\n"'
        for shell in SHELLS:
            body = ('not set -q MANTLE_ROOT; and printf "realm-mantle-ok\\n"'
                    if shell == "fish" else recovery)
            run_case(f"{shell}-missing-runtime-recovery", shell_command(shell, True, body, home), environment, checks)
        displaced.rename(prefix)
        run_case("disable-hooks", [shutil.which("bash"), str(prefix / "install.sh"), "--disable",
                 "--prefix", str(prefix), "--shell", "all"], environment, checks, marker=False)
        for shell in SHELLS:
            body = ('not set -q MANTLE_ROOT; and printf "realm-mantle-ok\\n"'
                    if shell == "fish" else recovery)
            run_case(f"{shell}-disabled-hook-recovery", shell_command(shell, True, body, home), environment, checks)
        run_case("bash-without-activation-recovery", shell_command("bash", False, recovery, home), environment, checks)
    return {"schema_version": "realm.mantle-source-canary-result/v1", "status": "passed",
            "source_revision": pin["revision"], "archive_sha256": pin["sha256"],
            "scope": "actual-local-processes-in-synthetic-temporary-homes",
            "released_integration": False, "hosted_qualification": "not-performed", "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("check", help="validate the immutable source canary pin offline")
    acquire = subcommands.add_parser("fetch", help="explicitly acquire and verify the source archive")
    acquire.add_argument("--output", type=Path, required=True)
    test = subcommands.add_parser("canary", help="verify source then run isolated real Bash/Zsh/Fish checks")
    test.add_argument("--archive", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        pin = load_pin()
        if arguments.command == "fetch":
            fetch(pin, arguments.output)
            result = {"status": "source-checksum-verified", "revision": pin["revision"], "released_integration": False}
        elif arguments.command == "canary":
            result = canary(pin, arguments.archive)
        else:
            result = {"status": "source-pin-valid", "released_integration": False}
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, tarfile.TarError) as error:
        print(f"mantle source canary: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
