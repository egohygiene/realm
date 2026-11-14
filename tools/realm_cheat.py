#!/usr/bin/env python3
"""Bootstrap Realm's pinned cheat reference capability without privileged setup.

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
from pathlib import Path
import platform
import re
import shlex
import stat
import sys
import tempfile
import urllib.error
import urllib.request
import zlib

ROOT = Path(__file__).resolve().parents[1]
PIN = ROOT / "config/cheat.v1.json"
TARGETS = {"linux/amd64": 62, "linux/arm64": 183}
MAX_ARCHIVE_BYTES = 16 * 1024 * 1024
MAX_EXECUTABLE_BYTES = 64 * 1024 * 1024
BEGIN = "# BEGIN REALM CHEAT"
END = "# END REALM CHEAT"


def checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_pin(path: Path = PIN) -> dict:
    pin = json.loads(path.read_text(encoding="utf-8"))
    fields = {"schema_version", "repository", "version", "license", "source_revision",
              "artifacts", "completion_sha256", "bash_completion"}
    if (not isinstance(pin, dict) or set(pin) != fields
            or pin["schema_version"] != "realm.cheat-install/v1"
            or pin["repository"] != "cheat/cheat" or pin["license"] != "MIT"
            or not isinstance(pin["version"], str)
            or re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", pin["version"]) is None
            or not isinstance(pin["source_revision"], str)
            or re.fullmatch(r"[0-9a-f]{40}", pin["source_revision"]) is None
            or not isinstance(pin["completion_sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", pin["completion_sha256"]) is None
            or not isinstance(pin["artifacts"], dict) or set(pin["artifacts"]) != set(TARGETS)):
        raise ValueError("cheat pin must declare the closed Linux AMD64/ARM64 release contract")
    library = pin["bash_completion"]
    if (not isinstance(library, dict) or set(library) != {
            "version", "source_revision", "library_sha256", "compatibility_sha256"}
            or library.get("version") != "2.17.0"
            or library.get("source_revision") != "47cc2eb87af2f95bc3a6b13ccebe6bd39b1b107a"
            or any(not isinstance(library.get(key), str)
                   or re.fullmatch(r"[0-9a-f]{64}", library[key]) is None
                   for key in ("library_sha256", "compatibility_sha256"))):
        raise ValueError("cheat pin has an invalid upstream Bash completion dependency")
    for target in TARGETS:
        architecture = target.split("/")[1]
        artifact = pin["artifacts"][target]
        expected = (f'https://github.com/cheat/cheat/releases/download/{pin["version"]}/'
                    f'cheat-linux-{architecture}.gz')
        if (not isinstance(artifact, dict) or set(artifact) != {"url", "sha256"}
                or artifact["url"] != expected or not isinstance(artifact["sha256"], str)
                or re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"]) is None):
            raise ValueError(f"cheat pin has an invalid URL/checksum for {target}")
    return pin


def native_platform() -> str:
    architecture = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64",
                    "arm64": "arm64"}.get(platform.machine().lower())
    if platform.system() != "Linux" or architecture is None:
        raise ValueError("cheat bootstrap supports native Linux AMD64/ARM64; use a Linux workspace")
    return "linux/" + architecture


def read_archive(path: Path) -> bytes:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= MAX_ARCHIVE_BYTES:
        raise ValueError("cheat archive must be a bounded regular non-symlink file")
    with path.open("rb") as stream:
        data = stream.read(MAX_ARCHIVE_BYTES + 1)
    if len(data) != info.st_size or len(data) > MAX_ARCHIVE_BYTES:
        raise ValueError("cheat archive changed or exceeded its size limit")
    return data


def executable(data: bytes, artifact: dict, target: str) -> bytes:
    if not 0 < len(data) <= MAX_ARCHIVE_BYTES or checksum(data) != artifact["sha256"]:
        raise ValueError("cheat archive SHA-256 mismatch; nothing installed")
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
        payload = stream.read(MAX_EXECUTABLE_BYTES + 1)
    if (not 64 <= len(payload) <= MAX_EXECUTABLE_BYTES
            or payload[:6] != b"\x7fELF\x02\x01"
            or int.from_bytes(payload[18:20], "little") != TARGETS[target]):
        raise ValueError("cheat payload is not the selected bounded 64-bit Linux executable")
    return payload


def absolute(path: Path) -> Path:
    path = path.expanduser()
    if not path.is_absolute() or ":" in str(path) or any(ord(c) < 32 for c in str(path)):
        raise ValueError("cheat paths must be absolute and contain no control characters or colon")
    return path


def managed_hook(before: str, activation: Path) -> str:
    if (before.count(BEGIN) != before.count(END) or before.count(BEGIN) > 1
            or before.count(BEGIN) != len(re.findall(r"^" + re.escape(BEGIN) + r"\r?$", before, re.M))
            or before.count(END) != len(re.findall(r"^" + re.escape(END) + r"\r?$", before, re.M))):
        raise ValueError("Bash startup has conflicting Realm cheat markers; review it before bootstrap")
    block = (f'{BEGIN}\nif [ -n "${{BASH_VERSION-}}" ] && [ -r {shlex.quote(str(activation))} ]; then\n'
             f'  . {shlex.quote(str(activation))}\nfi\n{END}')
    if BEGIN in before:
        start, end = before.index(BEGIN), before.index(END) + len(END)
        if end < start:
            raise ValueError("Bash startup has reversed Realm cheat markers")
        return before[:start] + block + before[end:]
    return before + ("" if not before or before.endswith("\n") else "\n") + block + "\n"


def activation_script(prefix: Path, config: Path, completion_library: Path | None) -> bytes:
    binary = shlex.quote(str(prefix / "bin"))
    completion = shlex.quote(str(prefix / "share/cheat/completion.bash"))
    compatibility = shlex.quote(str(prefix / "share/cheat/bash_completion_compat.bash"))
    library = (f'  if ! declare -F _get_comp_words_by_ref >/dev/null && [ -r {shlex.quote(str(completion_library))} ]; then\n'
               f'    . {shlex.quote(str(completion_library))}\n  fi\n') if completion_library else ""
    return ("# Generated by Realm cheat bootstrap; no network or installation at startup.\n"
            "# Copyright 2026 Ego Hygiene; SPDX-License-Identifier: MIT\n"
            'case "$-" in *i*) ;; *) return 0 ;; esac\n'
            f'if [ "${{_REALM_CHEAT_LOADED-}}" = {shlex.quote(str(prefix))} ]; then return 0; fi\n'
            f'if [ -x {shlex.quote(str(prefix / "bin/cheat"))} ]; then\n'
            f'  case ":${{PATH-}}:" in *:{binary}:*) ;; *) PATH={binary}${{PATH:+:$PATH}}; export PATH ;; esac\n'
            f'  if [ -z "${{CHEAT_CONFIG_PATH+x}}" ]; then CHEAT_CONFIG_PATH={shlex.quote(str(config))}; export CHEAT_CONFIG_PATH; fi\n'
            + library
            + '  if ! declare -F _get_comp_words_by_ref >/dev/null && declare -F _comp_deprecate_func >/dev/null; then\n'
            f'    if [ -r {compatibility} ]; then . {compatibility}; fi\n  fi\n'
            f'  if [ -r {completion} ] && declare -F _get_comp_words_by_ref >/dev/null && ! complete -p cheat >/dev/null 2>&1; then\n'
            f'    . {completion}\n  fi\n'
            f'  _REALM_CHEAT_LOADED={shlex.quote(str(prefix))}\nfi\n').encode()


def check_destination(path: Path, data: bytes, mode: int | None = None) -> None:
    if os.path.lexists(path):
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size != len(data) or path.read_bytes() != data:
            raise ValueError(f"Managed cheat destination exists with different bytes or unsafe type: {path.name}")
        if mode is not None and stat.S_IMODE(info.st_mode) != mode:
            raise ValueError(f"Managed cheat destination has unexpected permissions: {path.name}")


def create_file(path: Path, data: bytes, mode: int) -> str:
    check_destination(path, data, mode)
    if path.exists():
        return "unchanged"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".realm-cheat-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
        temporary.chmod(mode)
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return "created"


def bootstrap(pin: dict, payload: bytes, prefix: Path, *, no_shell_hook: bool = False,
              bash_completion: Path | None = None) -> dict:
    home = absolute(Path.home())
    data_home = absolute(Path(os.environ.get("XDG_DATA_HOME", str(home / ".local/share"))))
    config_home = absolute(Path(os.environ.get("XDG_CONFIG_HOME", str(home / ".config"))))
    prefix = absolute(prefix)
    if prefix.is_symlink() or (prefix.exists() and not prefix.is_dir()):
        raise ValueError("cheat prefix must be a regular directory, never a symlink")
    config = absolute(Path(os.environ.get("CHEAT_CONFIG_PATH", str(config_home / "cheat/conf.yml"))))
    if os.path.lexists(config) and not config.is_file():
        raise ValueError("Existing cheat configuration must resolve to a regular file; it is not replaced")
    personal = data_home / "cheat/personal"
    completion = (ROOT / "config/cheat/completion.bash").read_bytes()
    if checksum(completion) != pin["completion_sha256"]:
        raise ValueError("committed upstream completion checksum mismatch")
    library = (ROOT / "config/cheat/bash_completion").read_bytes()
    compatibility = (ROOT / "config/cheat/bash_completion_compat.bash").read_bytes()
    if (checksum(library) != pin["bash_completion"]["library_sha256"]
            or checksum(compatibility) != pin["bash_completion"]["compatibility_sha256"]):
        raise ValueError("committed upstream Bash completion dependency checksum mismatch")
    if bash_completion is None:
        bash_completion = next((path for path in (Path("/usr/share/bash-completion/bash_completion"),
                                                 Path("/etc/bash_completion")) if path.is_file()),
                               prefix / "share/cheat/bash_completion")
    else:
        bash_completion = absolute(bash_completion)
        if not bash_completion.is_file():
            raise ValueError("explicit Bash completion library is unavailable")
    bashrc = home / ".bashrc"
    before = ""
    after = None
    if not no_shell_hook:
        if os.path.lexists(bashrc):
            if not stat.S_ISREG(bashrc.lstat().st_mode) or bashrc.stat().st_size > 1024 * 1024:
                raise ValueError("Bash startup must be a bounded regular file; use --no-shell-hook for managed dotfiles")
            before = bashrc.read_text(encoding="utf-8")
        after = managed_hook(before, prefix / "activate.bash")
    files = {
        prefix / "bin/cheat": (payload, 0o755),
        prefix / "share/cheat/completion.bash": (completion, 0o644),
        prefix / "share/cheat/bash_completion": (library, 0o644),
        prefix / "share/cheat/bash_completion_compat.bash": (compatibility, 0o644),
        prefix / "activate.bash": (activation_script(prefix, config, bash_completion), 0o644),
        prefix / "share/cheat/realm/realm": (b"# Realm command reference\ncheat --list\ncheat realm\n", 0o644),
        prefix / "share/cheat/LICENSE.cheat": ((ROOT / "config/cheat/LICENSE.cheat").read_bytes(), 0o644),
        prefix / "share/cheat/LICENSE.cobra": ((ROOT / "config/cheat/LICENSE.cobra").read_bytes(), 0o644),
        prefix / "share/cheat/LICENSE.bash-completion": ((ROOT / "config/cheat/LICENSE.bash-completion").read_bytes(), 0o644),
    }
    # Validate existing managed content before changing any user configuration.
    for path, (content, mode) in files.items():
        for parent in path.parents:
            if parent == prefix.parent:
                break
            if parent.is_symlink():
                raise ValueError("Managed cheat directories cannot be symlinks")
        check_destination(path, content, mode)
    statuses = [create_file(path, content, mode) for path, (content, mode) in files.items()]
    personal.mkdir(parents=True, exist_ok=True, mode=0o700)
    config_status = "preserved"
    if not os.path.lexists(config):
        configuration = ('colorize: false\ncheatpaths:\n'
                         '  - name: realm\n    path: ' + json.dumps(str(prefix / "share/cheat/realm")) + '\n'
                         '    tags: [realm]\n    readonly: true\n'
                         '  - name: personal\n    path: ' + json.dumps(str(personal)) + '\n'
                         '    tags: [personal]\n    readonly: false\n').encode()
        config_status = create_file(config, configuration, 0o600)
    if after is not None and before != after:
        mode = stat.S_IMODE(bashrc.stat().st_mode) if bashrc.exists() else 0o600
        descriptor, temporary_name = tempfile.mkstemp(dir=home, prefix=".realm-cheat-bashrc-")
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(after)
            temporary.chmod(mode)
            # Reject a concurrent edit instead of replacing someone else's work.
            current = bashrc.read_text(encoding="utf-8") if bashrc.exists() else ""
            if bashrc.is_symlink() or current != before:
                raise ValueError("Bash startup changed during bootstrap; managed files are retained for retry")
            os.replace(temporary, bashrc)
        finally:
            temporary.unlink(missing_ok=True)
    return {"status": "unchanged" if all(s == "unchanged" for s in statuses) else "installed",
            "version": pin["version"], "configuration": config_status,
            "bash_hook": "omitted" if no_shell_hook else "managed",
            "bash_completion_library": "available" if bash_completion else "unavailable",
            "prefix": str(prefix), "activation": str(prefix / "activate.bash")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("bootstrap", "verify"))
    parser.add_argument("--archive", type=Path, help="Already downloaded gzip for offline acquisition")
    parser.add_argument("--platform", choices=tuple(TARGETS))
    parser.add_argument("--prefix", type=Path, help="Dedicated versioned user-owned installation directory")
    parser.add_argument("--no-shell-hook", action="store_true")
    parser.add_argument("--bash-completion", type=Path, help="Explicit existing upstream bash-completion library")
    parser.add_argument("--pin", type=Path, default=PIN)
    args = parser.parse_args(argv)
    try:
        pin = load_pin(args.pin)
        target = args.platform or native_platform()
        if args.command == "bootstrap" and target != native_platform():
            raise ValueError("bootstrap requires the native platform; use verify for cross-architecture archives")
        artifact = pin["artifacts"][target]
        if args.archive:
            data = read_archive(args.archive)
        else:
            with urllib.request.urlopen(artifact["url"], timeout=30) as response:
                data = response.read(MAX_ARCHIVE_BYTES + 1)
        payload = executable(data, artifact, target)
        report = {"status": "verified", "version": pin["version"], "platform": target,
                  "archive_sha256": artifact["sha256"], "executable_sha256": checksum(payload)}
        if args.command == "bootstrap":
            default = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
            prefix = args.prefix or default / "realm/cheat" / pin["version"]
            report.update(bootstrap(pin, payload, prefix, no_shell_hook=args.no_shell_hook,
                                    bash_completion=args.bash_completion))
    except (OSError, ValueError, EOFError, urllib.error.URLError, zlib.error) as error:
        print(f"cheat bootstrap failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
