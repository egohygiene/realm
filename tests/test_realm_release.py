"""Behavioral regressions for Realm-owned local release preparation.

Temporary repositories and authored evidence fixtures prove local mechanics,
never registry publication, signing or actual supported-platform qualification.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "realm_release.py"


class RealmReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.repository = self.directory / "repository"
        shutil.copytree(
            ROOT,
            self.repository,
            ignore=shutil.ignore_patterns(".git", ".cache", "__pycache__", ".reports"),
        )
        self.git("init", "--quiet", "--initial-branch=main")
        self.git("config", "user.name", "Realm fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", "fixture [skip ci]")

    def git(self, *arguments: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.repository), *arguments],
            text=True,
            capture_output=True,
            check=True,
        )
        return result.stdout.strip()

    def run_release(self, *arguments: str, success: bool = True) -> dict:
        result = subprocess.run(
            [
                sys.executable,
                str(self.repository / "tools" / "realm_release.py"),
                "--repository",
                str(self.repository),
                *arguments,
            ],
            text=True,
            capture_output=True,
            timeout=15,
        )
        self.assertEqual(result.returncode, 0 if success else 2, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        report = json.loads(result.stdout)
        self.assertIsInstance(report, dict)
        self.assertEqual(report["publication"], "not-performed")
        self.assertFalse(report["release_ready"])
        return report

    def test_declaration_selects_one_unreleased_container_authority(self) -> None:
        self.assertTrue(SCRIPT.is_file(), "missing Realm-owned release adapter")
        declaration = json.loads((ROOT / ".egohygiene" / "release.json").read_text())
        self.assertEqual(declaration["repository"]["id"], "egohygiene/realm")
        self.assertEqual(declaration["repository"]["release_profile"], "container-image")
        self.assertEqual(declaration["release"]["state"], "unreleased")
        self.assertIs(declaration["release"]["immutable_tags"], True)
        self.assertEqual(
            declaration["components"],
            [{"id": "realm-base", "kind": "container-image", "version_authority": {"kind": "git-tag"}}],
        )
        self.assertIn("## [Unreleased]\n", (ROOT / "CHANGELOG.md").read_text())

    def test_plan_is_read_only_and_represents_exact_local_source(self) -> None:
        before = self.git("status", "--porcelain=v1")
        report = self.run_release("plan", "--version", "v0.1.0")
        self.assertEqual(report["source_revision"], self.git("rev-parse", "HEAD"))
        self.assertEqual(report["tag"], "v0.1.0")
        self.assertEqual(report["default_branch"], "not-authenticated-locally")
        self.assertEqual(before, self.git("status", "--porcelain=v1"))

    def test_malformed_tags_reject_with_controlled_json(self) -> None:
        for version in ("1.2.3", "v01.2.3", "v1.2.3-rc1", "v1.2.3\n", "main", "v1.2.3;id"):
            with self.subTest(version=version):
                self.run_release("plan", "--version", version, success=False)
        self.run_release("plan", "--version", "v1.2.3")

    def test_prepare_emits_exclusive_review_patch_without_mutating_sources(self) -> None:
        changelog = self.repository / "CHANGELOG.md"
        before = changelog.read_bytes()
        output = self.directory / "prepared"
        report = self.run_release(
            "prepare", "--version", "v0.1.0", "--date", "2026-10-30", "--output", str(output)
        )
        self.assertEqual(report["status"], "prepared-local-review")
        self.assertEqual(changelog.read_bytes(), before)
        self.assertIn("+## [0.1.0] - 2026-10-30", (output / "CHANGELOG.patch").read_text())
        inventory = (output / "SHA256SUMS").read_bytes()
        self.run_release(
            "prepare", "--version", "v0.1.0", "--date", "2026-10-30", "--output", str(output),
            success=False,
        )
        self.assertEqual((output / "SHA256SUMS").read_bytes(), inventory)

    def test_prepare_rejects_bad_date_and_source_output_collision(self) -> None:
        output = self.directory / "bad-date"
        self.run_release(
            "prepare", "--version", "v0.1.0", "--date", "2026-02-30", "--output", str(output),
            success=False,
        )
        self.assertFalse(output.exists())
        self.run_release(
            "prepare", "--version", "v0.1.0", "--date", "2026-10-30",
            "--output", str(self.repository / "tools"), success=False,
        )

    def test_duplicate_local_tag_cannot_be_prepared_again(self) -> None:
        self.git("tag", "v0.1.0")
        self.run_release("plan", "--version", "v0.1.0", success=False)
        self.run_release("plan", "--version", "v0.2.0")

    def test_invalid_declaration_does_not_become_a_clean_plan(self) -> None:
        path = self.repository / ".egohygiene" / "release.json"
        original = path.read_text()
        cases = []
        for field, value in (("components", None), ("release", []), ("repository", "realm")):
            candidate = json.loads(original)
            candidate[field] = value
            cases.append(json.dumps(candidate))
        candidate = json.loads(original)
        candidate["release"]["immutable_tags"] = 1
        cases.extend([json.dumps(candidate), original[:-2] + ',"components":[]}'])
        for text in cases:
            with self.subTest(text=text[:50]):
                path.write_text(text)
                self.run_release("plan", "--version", "v0.1.0", success=False)
        path.write_text(original)
        self.run_release("plan", "--version", "v0.1.0")

    def test_check_binds_exact_contract_bytes(self) -> None:
        self.run_release("check")
        path = self.repository / "vendor" / "aether" / "aether.repository-release.v1.schema.json"
        path.write_bytes(path.read_bytes() + b"\n")
        self.run_release("check", success=False)

    def test_publish_handoff_is_literal_and_workflow_has_no_registry_authority(self) -> None:
        task = (ROOT / "Taskfile.yml").read_text()
        self.assertIn("gh workflow run .github/workflows/release.yml", task)
        workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("  push:", workflow)
        self.assertNotIn("  pull_request:", workflow)
        self.assertNotIn("packages: write", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("id-token: write", workflow)


if __name__ == "__main__":
    unittest.main()
