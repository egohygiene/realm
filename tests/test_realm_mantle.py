"""Offline boundary controls; real pinned-source activation is a separate canary."""

from pathlib import Path
import hashlib
import gzip
import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/realm_mantle.py"
SPEC = importlib.util.spec_from_file_location("realm_mantle", TOOL)
mantle = importlib.util.module_from_spec(SPEC)
if TOOL.is_file():
    SPEC.loader.exec_module(mantle)


class RealmMantleTests(unittest.TestCase):
    def invoke(self, *arguments):
        return subprocess.run(
            [sys.executable, str(TOOL), *map(str, arguments)],
            capture_output=True, text=True, check=False,
        )

    def test_documentation_uses_the_public_source_entrypoints(self):
        guide = (ROOT / "docs/mantle-shell.md").read_text()
        self.assertNotIn('SHELL ["/usr/local/bin/mantle", "--execute"]', guide)
        self.assertIn("runtime/shells/fish/runtime.fish", guide)
        self.assertIn(".shellrc", guide)

    def test_source_canary_pin_is_not_a_release_claim(self):
        pin_path = ROOT / "config/mantle-source-canary.json"
        self.assertTrue(pin_path.is_file(), "immutable source canary pin is missing")
        pin = json.loads(pin_path.read_text())
        self.assertEqual(pin["revision"], "0f54fa6e100c5b86af64aa383e41eed8c64e363a")
        self.assertEqual(pin["sha256"], "9461d47e66e274e6bdaeb04b77eb069a82d5e5a528139e765211c01c477449ca")
        self.assertEqual(pin["kind"], "source-canary")
        self.assertFalse(pin["released_integration"])

    def test_canary_rejects_unverified_bytes_before_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "untrusted.tar.gz"
            archive.write_bytes(b"not the reviewed Mantle archive")
            result = self.invoke("canary", "--archive", archive)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("SHA-256 mismatch", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_fetch_never_replaces_an_existing_destination(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "existing.tar.gz"
            archive.write_bytes(b"existing owned bytes")
            result = self.invoke("fetch", "--output", archive)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("already exists", result.stderr)
            self.assertEqual(archive.read_bytes(), b"existing owned bytes")

    def synthetic_archive(self, members):
        """Trusted checksum seam, not a Mantle distribution or activation proof."""
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w:gz") as archive:
            for name, kind, payload in members:
                info = tarfile.TarInfo(name)
                info.type = kind
                info.size = len(payload) if kind == tarfile.REGTYPE else 0
                info.linkname = "../../outside"
                archive.addfile(info, io.BytesIO(payload))
        data = stream.getvalue()
        pin = mantle.load_pin()
        pin["sha256"] = hashlib.sha256(data).hexdigest()
        return data, pin

    def test_pin_rejects_mutable_or_misbound_inputs(self):
        pin = mantle.load_pin()
        mutations = {"revision": "main", "url": "https://example.invalid/source",
                     "sha256": "not-a-hash", "released_integration": True,
                     "source_version": "1.0.0", "secret": "synthetic"}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "pin.json"
            for key, value in mutations.items():
                with self.subTest(key=key):
                    path.write_text(json.dumps(dict(pin, **{key: value})))
                    with self.assertRaises(ValueError):
                        mantle.load_pin(path)

    def test_unsafe_archives_reject_before_any_member_is_written(self):
        top = "mantle-" + mantle.load_pin()["revision"]
        cases = {
            "traversal": [(top + "/../../outside", tarfile.REGTYPE, b"bad")],
            "absolute": [("/outside", tarfile.REGTYPE, b"bad")],
            "symlink": [(top + "/link", tarfile.SYMTYPE, b"")],
            "hardlink": [(top + "/link", tarfile.LNKTYPE, b"")],
            "device": [(top + "/device", tarfile.CHRTYPE, b"")],
            "duplicate": [(top + "/same", tarfile.REGTYPE, b"first"),
                          (top + "/same", tarfile.REGTYPE, b"second")],
            "foreign-root": [("different/source", tarfile.REGTYPE, b"bad")],
        }
        with tempfile.TemporaryDirectory() as temporary:
            for label, members in cases.items():
                with self.subTest(case=label):
                    data, pin = self.synthetic_archive(members)
                    output = Path(temporary) / label
                    with self.assertRaisesRegex(ValueError, "unsafe or duplicate"):
                        mantle.unpack(data, pin, output)
                    self.assertFalse(output.exists())
            self.assertFalse((Path(temporary) / "outside").exists())

    def test_acquisition_checks_bytes_and_preserves_racing_destination(self):
        data, pin = self.synthetic_archive([])

        def response():
            stream = io.BytesIO(data)
            stream.geturl = lambda: pin["url"]
            return stream

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "archive.tar.gz"
            with mock.patch.object(mantle.urllib.request, "urlopen", return_value=response()):
                mantle.fetch(pin, output)
            self.assertEqual(output.read_bytes(), data)
            output.unlink()
            original = os.link

            def collision(source, destination):
                Path(destination).write_bytes(b"another publisher won")
                original(source, destination)

            with mock.patch.object(mantle.urllib.request, "urlopen", return_value=response()), \
                    mock.patch.object(mantle.os, "link", side_effect=collision):
                with self.assertRaises(FileExistsError):
                    mantle.fetch(pin, output)
            self.assertEqual(output.read_bytes(), b"another publisher won")
            self.assertEqual(sorted(path.name for path in Path(temporary).iterdir()), [output.name])

    def test_corrupt_acquisition_does_not_publish_or_execute(self):
        stream = io.BytesIO(b"unreviewed source")
        pin = mantle.load_pin()
        stream.geturl = lambda: pin["url"]
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "archive.tar.gz"
            with mock.patch.object(mantle.urllib.request, "urlopen", return_value=stream), \
                    mock.patch.object(mantle.subprocess, "run") as execute:
                with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                    mantle.fetch(pin, output)
            self.assertFalse(output.exists())
            execute.assert_not_called()

    def test_missing_required_shell_is_a_failure_before_source_execution(self):
        data, pin = self.synthetic_archive([])
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "archive.tar.gz"
            archive.write_bytes(data)
            with mock.patch.object(mantle.shutil, "which", side_effect=lambda name: None if name == "fish" else "/bin/" + name), \
                    mock.patch.object(mantle.subprocess, "Popen") as execute:
                with self.assertRaisesRegex(ValueError, "unavailable: fish"):
                    mantle.canary(pin, archive)
            execute.assert_not_called()

    def test_hidden_tar_metadata_cannot_bypass_expansion_limit(self):
        stream = io.BytesIO()
        top = "mantle-" + mantle.load_pin()["revision"]
        with tarfile.open(fileobj=stream, mode="w:gz", format=tarfile.PAX_FORMAT,
                          pax_headers={"comment": "synthetic metadata " * 16384}) as archive:
            member = tarfile.TarInfo(top + "/VERSION")
            member.size = 10
            archive.addfile(member, io.BytesIO(b"0.1.0-dev\n"))
        data = stream.getvalue()
        pin = dict(mantle.load_pin(), sha256=hashlib.sha256(data).hexdigest())
        self.assertLess(len(data), 4096)
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(mantle, "MAX_BYTES", 4096):
            output = Path(temporary) / "source"
            with self.assertRaisesRegex(ValueError, "expanded source archive"):
                mantle.unpack(data, pin, output)
            self.assertFalse(output.exists())

    def test_malformed_gzip_and_oversized_tar_headers_reject_cleanly(self):
        member = tarfile.TarInfo("mantle-" + mantle.load_pin()["revision"] + "/huge")
        member.size = mantle.MAX_BYTES + 1
        data, _ = self.synthetic_archive([])
        invalid_deflate = bytes.fromhex("1f8b0800") + bytes(6) + bytes([255]) * 12 + bytes(8)
        cases = (data[:-4], gzip.compress(member.tobuf()), invalid_deflate)
        with tempfile.TemporaryDirectory() as temporary:
            for index, malformed in enumerate(cases):
                with self.subTest(case=index):
                    pin = dict(mantle.load_pin(), sha256=hashlib.sha256(malformed).hexdigest())
                    output = Path(temporary) / str(index)
                    with self.assertRaises(ValueError):
                        mantle.unpack(malformed, pin, output)
                    self.assertFalse(output.exists())

    @unittest.skipUnless(sys.platform.startswith("linux"), "owned Linux process-group probe")
    def test_deadline_stops_owned_descendant_that_retains_output_pipes(self):
        with tempfile.TemporaryDirectory() as temporary:
            pidfile = Path(temporary) / "child.pid"
            started = time.monotonic()
            with self.assertRaisesRegex(ValueError, "canary deadline"):
                mantle.run_case("synthetic-owned-timeout", ["/bin/sh", "-c",
                                'sleep 60 & printf "%s" "$!" >"$1"; wait', "fixture", str(pidfile)],
                                {"PATH": os.defpath}, [], deadline=0.5)
            self.assertLess(time.monotonic() - started, 4)
            pid = int(pidfile.read_text())
            process_status = Path(f"/proc/{pid}/stat")
            if process_status.exists():
                # A killed orphan can briefly await its parent's reaper.
                self.assertEqual(process_status.read_text().split()[2], "Z")


if __name__ == "__main__":
    unittest.main()
