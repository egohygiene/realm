"""Offline boundary controls; real pinned-source activation is a separate canary."""

from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/realm_mantle.py"


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


if __name__ == "__main__":
    unittest.main()
