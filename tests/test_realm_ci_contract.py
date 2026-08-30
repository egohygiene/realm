"""Network-free conformance tests for Realm's Task and CI contracts."""

from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
TASKFILE = ROOT / "Taskfile.yml"
WORKFLOW_DIRECTORY = ROOT / ".github" / "workflows"
VALIDATION_WORKFLOW = WORKFLOW_DIRECTORY / "validate.yml"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
ACTION_REFERENCE = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)", re.MULTILINE)


class RealmCiContractTests(unittest.TestCase):
    """Keep validation read-only, immutable, and locally reproducible."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.taskfile = TASKFILE.read_text(encoding="utf-8")
        cls.workflow = VALIDATION_WORKFLOW.read_text(encoding="utf-8")

    def test_required_task_surface_exists(self) -> None:
        tasks = set(
            re.findall(r"^  ([a-z][a-z0-9:-]+):\s*$", self.taskfile, re.MULTILINE)
        )
        self.assertTrue(
            {
                "check",
                "packages:check",
                "packages:resolve",
                "packages:refresh",
                "packages:verify-lock",
                "packages:verify",
                "image:build",
                "image:verify-base",
                "image:verify",
                "image:smoke",
                "image:size",
                "ci:contracts",
                "ci:architecture",
            }.issubset(tasks)
        )

    def test_taskfile_uses_the_canonical_package_resolver(self) -> None:
        self.assertIn("tools/realm_apt_packages.py check", self.taskfile)
        self.assertIn("tools/realm_apt_packages.py resolve", self.taskfile)
        self.assertIn("tools/realm_apt_packages.py verify-lock", self.taskfile)
        self.assertNotIn("apt-get install", self.taskfile)

    def test_image_checks_execute_the_embedded_scripts(self) -> None:
        self.assertIn(
            '--entrypoint "/usr/local/libexec/realm/verify-apt-packages"',
            self.taskfile,
        )
        self.assertIn(
            '--entrypoint "/usr/local/libexec/realm/smoke"', self.taskfile
        )
        self.assertNotIn("--volume", self.taskfile)
        self.assertGreaterEqual(self.taskfile.count('--network "none"'), 2)

    def test_every_external_action_uses_a_full_commit_sha(self) -> None:
        workflow_paths = sorted(WORKFLOW_DIRECTORY.glob("*.y*ml"))
        self.assertTrue(workflow_paths)
        for path in workflow_paths:
            workflow = path.read_text(encoding="utf-8")
            for reference in ACTION_REFERENCE.findall(workflow):
                if reference.startswith("./"):
                    continue
                with self.subTest(path=path.name, reference=reference):
                    self.assertIn("@", reference)
                    _, revision = reference.rsplit("@", 1)
                    self.assertRegex(revision, FULL_SHA)

    def test_reviewed_action_pins_remain_explicit(self) -> None:
        self.assertIn(
            "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
            self.workflow,
        )
        self.assertIn(
            "go-task/setup-task@a00fbb05ce67b35648be3c78cbc9fd85354c757e",
            self.workflow,
        )
        self.assertIn('version: "3.53.1"', self.workflow)

    def test_workflow_has_a_read_only_permission_ceiling(self) -> None:
        self.assertRegex(
            self.workflow,
            re.compile(r"^permissions:\n  contents: read$", re.MULTILINE),
        )
        for forbidden in (
            "packages: write",
            "contents: write",
            "id-token: write",
            "pull_request_target:",
            "docker/login-action",
            "docker push",
            "push: true",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.workflow)

    def test_pull_requests_never_publish_images(self) -> None:
        self.assertIn("pull_request:", self.workflow)
        self.assertNotIn("ghcr.io", self.workflow)
        self.assertNotRegex(self.workflow, re.compile(r"\bpublish\b", re.IGNORECASE))

    def test_both_architectures_use_native_runners(self) -> None:
        self.assertIn('architecture: "amd64"', self.workflow)
        self.assertIn('runner: "ubuntu-24.04"', self.workflow)
        self.assertIn('architecture: "arm64"', self.workflow)
        self.assertIn('runner: "ubuntu-24.04-arm"', self.workflow)
        self.assertIn("dpkg --print-architecture", self.workflow)
        self.assertIn("fail-fast: false", self.workflow)
        self.assertNotIn("setup-qemu", self.workflow)

    def test_ci_invokes_task_contracts_instead_of_duplicating_commands(self) -> None:
        self.assertIn("run: task ci:contracts", self.workflow)
        self.assertIn("task ci:architecture", self.workflow)
        self.assertNotIn("realm_apt_packages.py", self.workflow)


if __name__ == "__main__":
    unittest.main()
