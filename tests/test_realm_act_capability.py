"""Verify pinned client acquisition and explicit local-CI profile composition."""

from __future__ import annotations

import copy
import gzip
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from realm_act import checksum, executable, install, load_pin, native_platform
from realm_profile_publications import validate_profile_publications
from realm_profiles import load_json, load_profiles, resolve_profile
from realm_tool_registry import load_registry


def synthetic_executable(machine: int = 62) -> bytes:
    data = bytearray(64)
    data[:6] = b"\x7fELF\x02\x01"
    data[18:20] = machine.to_bytes(2, "little")
    return bytes(data) + b"realm-act-fixture"


def archive_bytes(payload: bytes, extra: tarfile.TarInfo | None = None) -> bytes:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        member = tarfile.TarInfo("act")
        member.size = len(payload)
        member.mode = 0o755
        archive.addfile(member, io.BytesIO(payload))
        if extra is not None:
            archive.addfile(extra, io.BytesIO(b""))
    return gzip.compress(stream.getvalue(), mtime=0)


class RealmActCapabilityTests(unittest.TestCase):
    def test_local_ci_resolves_explicit_artifact_on_both_declared_platforms(self) -> None:
        catalog = load_json(ROOT / "catalog/capabilities.json")
        profiles = load_profiles(ROOT / "profiles")
        registry = load_registry(ROOT / "catalog/tool-evaluations.json")
        self.assertEqual(validate_profile_publications(catalog, profiles, registry), [])
        for target in ("linux/amd64", "linux/arm64"):
            for projection in catalog["projections"]:
                with self.subTest(target=target, projection=projection):
                    resolved, errors = resolve_profile(catalog, profiles, "local-ci", target, projection)
                    self.assertEqual(errors, [])
                    self.assertIn("act-local-ci", resolved["capabilities"])
                    self.assertNotIn("container-host", resolved["capabilities"])
                    self.assertFalse(resolved["constraints"]["services"])
                    self.assertFalse(resolved["constraints"]["privileged"])
        base, errors = resolve_profile(catalog, profiles, "base", "linux/amd64", "docker")
        self.assertEqual(errors, [])
        self.assertNotIn("act-local-ci", base["capabilities"])
        self.assertNotIn("container-host", base["capabilities"])

    def test_pin_is_consistent_with_the_catalog_and_registry(self) -> None:
        pin = load_pin()
        catalog = load_json(ROOT / "catalog/capabilities.json")
        registry = load_registry(ROOT / "catalog/tool-evaluations.json")
        source = f'https://github.com/nektos/act@{pin["source_revision"]}'
        self.assertEqual(catalog["source_pins"]["act"], source)
        self.assertEqual(registry["tools"]["act"]["version_source"], source)
        self.assertEqual(catalog["capabilities"]["act-local-ci"]["artifacts"],
                         [{"name": "act", "version": pin["version"], "source": source}])

    def test_pin_rejects_non_release_source_before_download(self) -> None:
        pin = load_pin()
        pin["artifacts"]["linux/amd64"]["url"] = "https://example.invalid/install.sh"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "pin.json"
            path.write_text(json.dumps(pin))
            with self.assertRaisesRegex(ValueError, "invalid source"):
                load_pin(path)

    def test_checksums_reject_changed_archive_before_extraction(self) -> None:
        data = archive_bytes(synthetic_executable())
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            executable(data, {"sha256": "0" * 64}, "linux/amd64")

    def test_archive_requires_matching_elf_architecture(self) -> None:
        data = archive_bytes(synthetic_executable())
        pin = {"sha256": checksum(data)}
        self.assertEqual(executable(data, pin, "linux/amd64"), synthetic_executable())
        with self.assertRaisesRegex(ValueError, "matching 64-bit Linux"):
            executable(data, pin, "linux/arm64")

    def test_archive_rejects_paths_links_and_duplicate_members(self) -> None:
        for name, kind in (("../outside", tarfile.REGTYPE), ("linked", tarfile.SYMTYPE),
                           ("act", tarfile.REGTYPE)):
            with self.subTest(name=name, kind=kind):
                member = tarfile.TarInfo(name)
                member.type = kind
                member.linkname = "act" if kind == tarfile.SYMTYPE else ""
                data = archive_bytes(synthetic_executable(), member)
                with self.assertRaisesRegex(ValueError, "unsafe or duplicate"):
                    executable(data, {"sha256": checksum(data)}, "linux/amd64")

    def test_installation_is_atomic_idempotent_and_preserves_other_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "bin/act"
            sibling = Path(temporary) / "unrelated"
            sibling.write_bytes(b"preserve")
            payload = synthetic_executable()
            self.assertEqual(install(payload, output), "installed")
            before = output.stat()
            self.assertEqual(install(payload, output), "unchanged")
            self.assertEqual(output.stat().st_ino, before.st_ino)
            self.assertEqual(output.read_bytes(), payload)
            self.assertEqual(output.stat().st_mode & 0o777, 0o755)
            self.assertEqual(sibling.read_bytes(), b"preserve")
            self.assertEqual(sorted(p.name for p in output.parent.iterdir()), ["act"])

    def test_existing_different_executable_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "act"
            output.write_bytes(b"old-version")
            output.chmod(0o755)
            with self.assertRaisesRegex(ValueError, "destination exists"):
                install(synthetic_executable(), output)
            self.assertEqual(output.read_bytes(), b"old-version")

    def test_symlink_destination_is_rejected_without_modifying_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "target"
            target.write_bytes(synthetic_executable())
            target.chmod(0o755)
            output = Path(temporary) / "act"
            output.symlink_to(target)
            with self.assertRaisesRegex(ValueError, "destination exists"):
                install(synthetic_executable(), output)
            self.assertEqual(target.read_bytes(), synthetic_executable())

    def test_native_platform_does_not_silently_select_darwin_or_emulation(self) -> None:
        for machine, target in (("x86_64", "linux/amd64"), ("aarch64", "linux/arm64")):
            with patch("realm_act.platform.system", return_value="Linux"), patch(
                "realm_act.platform.machine", return_value=machine
            ):
                self.assertEqual(native_platform(), target)
        with patch("realm_act.platform.system", return_value="Darwin"), patch(
            "realm_act.platform.machine", return_value="arm64"
        ):
            with self.assertRaisesRegex(ValueError, "Linux Dev Container"):
                native_platform()

    def test_public_install_cli_supports_offline_archive_and_reports_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            data = archive_bytes(synthetic_executable())
            archive = directory / "act.tar.gz"
            archive.write_bytes(data)
            pin = copy.deepcopy(load_pin())
            pin["artifacts"]["linux/amd64"]["sha256"] = checksum(data)
            pin_path = directory / "pin.json"
            pin_path.write_text(json.dumps(pin))
            output = directory / "bin/act"
            command = [sys.executable, str(ROOT / "tools/realm_act.py"), "install",
                       "--pin", str(pin_path), "--platform", "linux/amd64",
                       "--archive", str(archive), "--output", str(output)]
            result = subprocess.run(command, text=True, capture_output=True, check=False, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "installed")
            archive.write_bytes(b"corrupted")
            result = subprocess.run(command, text=True, capture_output=True, check=False, timeout=10)
            self.assertEqual(result.returncode, 2)
            self.assertIn("SHA-256 mismatch", result.stderr)
            self.assertEqual(output.read_bytes(), synthetic_executable())


if __name__ == "__main__":
    unittest.main()
