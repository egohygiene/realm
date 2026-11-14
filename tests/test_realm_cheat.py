"""Exercise pinned acquisition, user-state preservation and guarded completion."""

from __future__ import annotations

import copy
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from realm_cheat import bootstrap, checksum, executable, load_pin, main, native_platform, read_archive
from realm_profile_publications import validate_profile_publications
from realm_profiles import load_json, load_profiles, resolve_profile
from realm_tool_registry import load_registry


def synthetic_executable(machine: int = 62) -> bytes:
    data = bytearray(64)
    data[:6] = b"\x7fELF\x02\x01"
    data[18:20] = machine.to_bytes(2, "little")
    return bytes(data) + b"synthetic-cheat-not-executed"


class RealmCheatTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.prefix = self.home / "tools with ' quote"
        self.environment = patch.dict(os.environ, {
            "HOME": str(self.home), "XDG_CONFIG_HOME": str(self.home / "config"),
            "XDG_DATA_HOME": str(self.home / "data"), "PATH": "/usr/bin:/bin", "TERM": "dumb",
        }, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.pin = load_pin()

    def install(self, **kwargs):
        return bootstrap(self.pin, synthetic_executable(), self.prefix, **kwargs)

    def test_reference_resolves_pinned_tools_without_changing_base_or_full(self) -> None:
        catalog = load_json(ROOT / "catalog/capabilities.json")
        profiles = load_profiles(ROOT / "profiles")
        registry = load_registry(ROOT / "catalog/tool-evaluations.json")
        self.assertEqual(validate_profile_publications(catalog, profiles, registry), [])
        for target in catalog["platforms"]:
            for projection in catalog["projections"]:
                resolved, errors = resolve_profile(catalog, profiles, "reference", target, projection)
                self.assertEqual(errors, [])
                self.assertIn("cheat-reference", resolved["capabilities"])
                self.assertFalse(resolved["constraints"]["privileged"])
        for name in ("base", "full"):
            resolved, errors = resolve_profile(catalog, profiles, name, "linux/amd64", "docker")
            self.assertEqual(errors, [])
            self.assertNotIn("cheat-reference", resolved["capabilities"])
        source = "https://github.com/cheat/cheat@" + self.pin["source_revision"]
        self.assertEqual(catalog["source_pins"]["cheat"], source)
        self.assertEqual(registry["tools"]["cheat"]["version_source"], source)

    def test_pin_rejects_mutable_or_substituted_release_inputs(self) -> None:
        for mutation in ("extra", "url", "platform", "helper"):
            with self.subTest(mutation=mutation):
                pin = copy.deepcopy(self.pin)
                if mutation == "extra":
                    pin["unknown"] = True
                elif mutation == "url":
                    pin["artifacts"]["linux/amd64"]["url"] = "https://example.invalid/cheat.gz"
                elif mutation == "platform":
                    del pin["artifacts"]["linux/arm64"]
                else:
                    pin["bash_completion"]["source_revision"] = "main"
                path = self.home / "pin.json"
                path.write_text(json.dumps(pin))
                with self.assertRaises(ValueError):
                    load_pin(path)

    def test_checksum_and_elf_architecture_are_required_before_installation(self) -> None:
        data = gzip.compress(synthetic_executable())
        artifact = {"sha256": checksum(data)}
        self.assertEqual(executable(data, artifact, "linux/amd64"), synthetic_executable())
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            executable(data, {"sha256": "0" * 64}, "linux/amd64")
        with self.assertRaisesRegex(ValueError, "selected bounded"):
            executable(data, artifact, "linux/arm64")
        with patch("realm_cheat.MAX_EXECUTABLE_BYTES", 64):
            with self.assertRaisesRegex(ValueError, "bounded"):
                executable(data, artifact, "linux/amd64")
        self.assertFalse(self.prefix.exists())

    def test_archive_input_rejects_symlink_directory_and_oversize(self) -> None:
        archive = self.home / "archive.gz"
        archive.write_bytes(b"bytes")
        link = self.home / "link.gz"
        link.symlink_to(archive)
        for invalid in (link, self.home):
            with self.subTest(path=invalid), self.assertRaisesRegex(ValueError, "bounded regular"):
                read_archive(invalid)
        with patch("realm_cheat.MAX_ARCHIVE_BYTES", 2):
            with self.assertRaisesRegex(ValueError, "bounded regular"):
                read_archive(archive)

    def test_bootstrap_is_idempotent_and_personal_state_survives(self) -> None:
        first = self.install()
        binary = self.prefix / "bin/cheat"
        inode = binary.stat().st_ino
        config = self.home / "config/cheat/conf.yml"
        config.write_text("# user-owned configuration\n")
        personal = self.home / "data/cheat/personal/local"
        personal.write_text("# preserve a private sheet\n")
        bashrc = self.home / ".bashrc"
        before = bashrc.read_bytes()
        second = self.install()
        self.assertEqual(first["status"], "installed")
        self.assertEqual(second["status"], "unchanged")
        self.assertEqual(second["configuration"], "preserved")
        self.assertEqual(binary.stat().st_ino, inode)
        self.assertEqual(config.read_text(), "# user-owned configuration\n")
        self.assertEqual(personal.read_text(), "# preserve a private sheet\n")
        self.assertEqual(bashrc.read_bytes(), before)
        self.assertEqual(before.count(b"# BEGIN REALM CHEAT"), 1)
        self.assertEqual(config.stat().st_mode & 0o777, 0o600)

    def test_existing_managed_conflict_fails_before_other_writes(self) -> None:
        target = self.prefix / "share/cheat/completion.bash"
        target.parent.mkdir(parents=True)
        target.write_text("# unrelated content\n")
        with self.assertRaisesRegex(ValueError, "different bytes"):
            self.install()
        self.assertFalse((self.prefix / "bin/cheat").exists())
        self.assertFalse((self.home / ".bashrc").exists())
        self.assertEqual(target.read_text(), "# unrelated content\n")

    def test_wrong_mode_fails_preflight_before_installing_another_file(self) -> None:
        target = self.prefix / "share/cheat/completion.bash"
        target.parent.mkdir(parents=True)
        target.write_bytes((ROOT / "config/cheat/completion.bash").read_bytes())
        target.chmod(0o600)
        with self.assertRaisesRegex(ValueError, "unexpected permissions"):
            self.install()
        self.assertFalse((self.prefix / "bin/cheat").exists())

    def test_nested_managed_symlink_cannot_escape_prefix(self) -> None:
        outside = self.home / "outside"
        outside.mkdir()
        self.prefix.mkdir()
        (self.prefix / "bin").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "directories cannot be symlinks"):
            self.install()
        self.assertEqual(list(outside.iterdir()), [])

    def test_malformed_startup_markers_are_rejected_without_losing_local_prose(self) -> None:
        startup = self.home / ".bashrc"
        for before in ("# local\n# BEGIN REALM CHEAT\n", "# END REALM CHEAT\n# BEGIN REALM CHEAT\n",
                       'printf "# BEGIN REALM CHEAT and # END REALM CHEAT"\n'):
            with self.subTest(before=before):
                startup.write_text(before)
                with self.assertRaisesRegex(ValueError, "markers"):
                    self.install()
                self.assertEqual(startup.read_text(), before)
                self.assertFalse(self.prefix.exists())

    def test_symlink_startup_requires_explicit_no_hook_mode(self) -> None:
        target = self.home / "owned-by-dotfile-manager"
        target.write_text("# preserve managed startup\n")
        (self.home / ".bashrc").symlink_to(target)
        with self.assertRaisesRegex(ValueError, "no-shell-hook"):
            self.install()
        report = self.install(no_shell_hook=True)
        self.assertEqual(report["bash_hook"], "omitted")
        self.assertEqual(target.read_text(), "# preserve managed startup\n")

    def test_existing_local_prose_and_explicit_config_selection_survive(self) -> None:
        startup = self.home / ".bashrc"
        startup.write_text("# local before\n")
        config = self.home / "explicit-config.yml"
        config.write_text("# do not replace\n")
        with patch.dict(os.environ, {"CHEAT_CONFIG_PATH": str(config)}):
            self.install()
        self.assertTrue(startup.read_text().startswith("# local before\n"))
        self.assertEqual(config.read_text(), "# do not replace\n")

    def test_missing_or_relative_configuration_inputs_fail_before_installation(self) -> None:
        for variable, value in (("XDG_CONFIG_HOME", "relative-config"),
                                ("XDG_DATA_HOME", "relative-data"),
                                ("CHEAT_CONFIG_PATH", str(self.home))):
            with self.subTest(variable=variable), patch.dict(os.environ, {variable: value}):
                with self.assertRaises(ValueError):
                    self.install()
                self.assertFalse(self.prefix.exists())

    def test_modified_upstream_completion_dependency_is_rejected(self) -> None:
        self.pin["bash_completion"]["library_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "dependency checksum mismatch"):
            self.install()
        self.assertFalse(self.prefix.exists())

    def test_noninteractive_activation_has_no_path_or_completion_effect(self) -> None:
        self.install()
        script = 'before=$PATH; . "$1"; test "$PATH" = "$before"; ! complete -p cheat >/dev/null 2>&1'
        result = subprocess.run(["/bin/bash", "--noprofile", "--norc", "-c", script,
                                 "check", str(self.prefix / "activate.bash")],
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")

    def test_interactive_activation_registers_upstream_once_and_tolerates_missing_files(self) -> None:
        self.install()
        activation = self.prefix / "activate.bash"
        script = '. "$1"; first=$(complete -p cheat); . "$1"; test "$(complete -p cheat)" = "$first"; printf "%s\\n" "$first"'
        result = subprocess.run(["/bin/bash", "--noprofile", "--norc", "-i", "-c", script,
                                 "check", str(activation)], text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("-F __start_cheat cheat", result.stdout)
        # The actual terminal qualification separately proves warning-free startup.
        allowed = ("cannot set terminal process group", "no job control in this shell")
        self.assertTrue(all(any(phrase in line for phrase in allowed)
                            for line in result.stderr.splitlines()), result.stderr)
        (self.prefix / "share/cheat/completion.bash").unlink()
        missing = subprocess.run(["/bin/bash", "--noprofile", "--norc", "-i", "-c", '. "$1"',
                                  "check", str(activation)], text=True, capture_output=True, timeout=10)
        self.assertEqual(missing.returncode, 0, missing.stderr)

    def test_offline_cli_rejects_changed_archive_without_network_or_install(self) -> None:
        archive = self.home / "cheat.gz"
        archive.write_bytes(b"corrupt")
        with patch("realm_cheat.urllib.request.urlopen", side_effect=AssertionError("network forbidden")):
            status = main(["bootstrap", "--archive", str(archive), "--prefix", str(self.prefix)])
        self.assertEqual(status, 2)
        self.assertFalse(self.prefix.exists())

    def test_native_platform_is_explicit_and_never_silently_emulated(self) -> None:
        for machine, target in (("x86_64", "linux/amd64"), ("aarch64", "linux/arm64")):
            with patch("realm_cheat.platform.system", return_value="Linux"), patch(
                    "realm_cheat.platform.machine", return_value=machine):
                self.assertEqual(native_platform(), target)
        with patch("realm_cheat.platform.system", return_value="Darwin"):
            with self.assertRaisesRegex(ValueError, "native Linux"):
                native_platform()


if __name__ == "__main__":
    unittest.main()
