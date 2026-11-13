"""Exercise explicit local validation, incomplete coverage, and real deadlines."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "realm_local_ci.py"
SPEC = importlib.util.spec_from_file_location("realm_local_ci", SCRIPT)
local_ci = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(local_ci)
IMAGE = "example.invalid/runner@sha256:" + "1" * 64


class LocalCITests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.repository = self.base / "repository"
        self.repository.mkdir()
        (self.repository / "config").mkdir()
        workflows = self.repository / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "checks.yml").write_text(
            "name: fixture\non: push\njobs:\n  tests:\n    runs-on: ubuntu-24.04\n    steps:\n      - run: true\n"
        )
        subprocess.run(["git", "init", "--quiet", str(self.repository)], check=True)
        self.direct = {
            "id": "test",
            "kind": "direct",
            "required": True,
            "timeout_seconds": 5,
            "command": [sys.executable, "-c", "print('checked')"],
        }
        self.act_check = {
            "id": "workflow",
            "kind": "act",
            "required": True,
            "timeout_seconds": 5,
            "workflow": ".github/workflows/checks.yml",
            "job": "tests",
            "event": "push",
            "matrix": [],
            "inputs": {},
            "platforms": {"ubuntu-24.04": IMAGE},
            "required_secrets": [],
        }
        self.write_manifest([self.direct])

    def write_manifest(self, checks, repository=None):
        root = repository or self.repository
        path = root / "config" / "local-ci.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"schema_version": "realm.local-ci/v1", "checks": checks}))

    def cli(self, *args, expected=0, environment=None):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--repository", str(self.repository), *args],
            text=True,
            capture_output=True,
            env=environment,
            timeout=20,
        )
        self.assertEqual(expected, result.returncode, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        return json.loads(result.stdout)

    def fake_act(self, completion=True, selected=True, exit_code=0):
        patcher = mock.patch.object(
            local_ci, "owned_container_cleanup", return_value={"complete": True, "removed": []}
        )
        self.cleanup_mock = patcher.start()
        self.addCleanup(patcher.stop)
        path = self.base / "act"
        code = f"""#!{sys.executable}
import json, os, sys
if '--version' in sys.argv:
    print('act version 0.2.97')
elif '--list' in sys.argv:
    print({"0 tests Tests Checks checks.yml push" if selected else "Stage Job-ID Job-name Workflow File Events"!r})
else:
    assert not os.environ.get('GITHUB_TOKEN')
    assert '--secret-file' in sys.argv and '--env-file' in sys.argv
    assert '--trust-project-actrc' not in sys.argv
    assert '--container-daemon-socket' in sys.argv
    print(json.dumps({{'level':'info','jobID':'tests','jobResult':{"success" if completion else "skipped"!r},'dryrun':False,'matrix':{{}},'msg':{"🏁 Job succeeded" if completion else "No jobs run"!r}}}))
    sys.exit({exit_code})
"""
        path.write_text(code)
        path.chmod(0o755)
        return str(path)

    def run_manifest(self, name="results", act="act"):
        return local_ci.run_repository(
            self.repository, "config/local-ci.json", self.base / name, act
        )

    def test_plan_does_not_run_command_or_make_report(self):
        marker = self.repository / "unexpected"
        self.direct["command"] = [sys.executable, "-c", f"open({str(marker)!r}, 'w').close()"]
        self.write_manifest([self.direct])
        report = self.cli("plan")
        self.assertEqual("not-performed", report["execution"])
        self.assertFalse(marker.exists())
        self.assertIn("manifest_sha256", report)

    def test_real_pass_fail_continue_and_required_aggregate(self):
        failed = dict(
            self.direct, id="failed", command=[sys.executable, "-c", "raise SystemExit(7)"]
        )
        self.write_manifest(
            [
                failed,
                self.direct,
                {
                    "id": "native",
                    "kind": "unsupported",
                    "required": False,
                    "reason": "needs native ARM64",
                },
            ]
        )
        report = self.run_manifest()
        self.assertEqual(
            ["failed", "passed", "unsupported"], [c["status"] for c in report["checks"]]
        )
        self.assertFalse(report["complete"])
        self.assertEqual(7, report["checks"][0]["exit_code"])
        self.assertTrue((self.base / "results" / "report.md").is_file())

    def test_optional_unsupported_is_visible_without_failing_required_pass(self):
        self.write_manifest(
            [
                self.direct,
                {
                    "id": "oidc",
                    "kind": "unsupported",
                    "required": False,
                    "reason": "OIDC requires provider",
                },
            ]
        )
        report = self.run_manifest()
        self.assertTrue(report["complete"])
        self.assertEqual("unsupported", report["checks"][1]["status"])

    def test_required_skipped_and_unsupported_remain_incomplete(self):
        self.write_manifest(
            [
                self.direct,
                dict(self.direct, id="skipped", skip_reason="prerequisite unavailable"),
                {"id": "hosted", "kind": "unsupported", "required": True, "reason": "hosted-only"},
            ]
        )
        report = self.run_manifest()
        self.assertFalse(report["complete"])
        self.assertEqual(
            ["passed", "skipped", "unsupported"], [c["status"] for c in report["checks"]]
        )

    def test_timeout_terminates_real_process_group(self):
        self.direct.update(
            command=[
                sys.executable,
                "-c",
                "import time; print('start', flush=True); time.sleep(30)",
            ],
            timeout_seconds=1,
        )
        self.write_manifest([self.direct])
        report = self.run_manifest()
        self.assertTrue(report["checks"][0]["timed_out"])
        self.assertEqual("failed", report["checks"][0]["status"])
        self.assertLess(report["checks"][0]["seconds"], 4)

    def test_missing_program_is_blocked(self):
        self.direct["command"] = ["/missing/local-ci-command"]
        self.write_manifest([self.direct])
        report = self.run_manifest()
        self.assertEqual("blocked", report["checks"][0]["status"])

    def test_act_preflight_failure_is_blocked(self):
        self.write_manifest([self.act_check])
        with mock.patch.object(local_ci, "doctor", return_value={"ready": False}):
            report = self.run_manifest()
        self.assertEqual("blocked", report["checks"][0]["status"])

    def test_credentials_are_blocked_without_secret_prompt(self):
        self.act_check["required_secrets"] = ["GITHUB_TOKEN"]
        self.write_manifest([self.act_check])
        with mock.patch.object(local_ci, "doctor", return_value={"ready": True}):
            report = self.run_manifest()
        self.assertEqual("blocked", report["checks"][0]["status"])

    def test_real_fake_act_selection_and_completion(self):
        self.write_manifest([self.act_check])
        with (
            mock.patch.object(local_ci, "doctor", return_value={"ready": True}),
            mock.patch.dict(os.environ, {"GITHUB_TOKEN": "synthetic-sensitive-value"}),
        ):
            report = self.run_manifest(act=self.fake_act())
        self.assertTrue(report["complete"])
        command = report["checks"][0]["command"]
        self.assertIn("--container-options-policy", command)
        self.assertNotIn("--trust-project-actrc", command)
        self.assertFalse(report["credentials_forwarded"])

    def test_zero_exit_without_selected_job_completion_is_incomplete(self):
        self.write_manifest([self.act_check])
        with mock.patch.object(local_ci, "doctor", return_value={"ready": True}):
            report = self.run_manifest(act=self.fake_act(completion=False))
        self.assertEqual("blocked", report["checks"][0]["status"])
        self.assertFalse(report["complete"])

    def test_unknown_job_is_not_run(self):
        self.write_manifest([self.act_check])
        with mock.patch.object(local_ci, "doctor", return_value={"ready": True}):
            report = self.run_manifest(act=self.fake_act(selected=False))
        self.assertEqual("blocked", report["checks"][0]["status"])
        self.assertIn("inventoried", report["checks"][0]["reason"])

    def test_act_failure_is_preserved(self):
        self.write_manifest([self.act_check])
        with mock.patch.object(local_ci, "doctor", return_value={"ready": True}):
            report = self.run_manifest(act=self.fake_act(exit_code=9))
        self.assertEqual("failed", report["checks"][0]["status"])
        self.assertEqual(9, report["checks"][0]["exit_code"])

    def test_mutable_runner_image_rejects_before_execution(self):
        self.act_check["platforms"] = {"ubuntu-latest": "node:latest"}
        self.write_manifest([self.act_check])
        report = self.cli("plan", expected=2)
        self.assertIn("immutable", report["error"])

    def test_unsafe_and_symlink_workflow_paths_reject(self):
        self.act_check["workflow"] = "../outside.yml"
        self.write_manifest([self.act_check])
        self.cli("plan", expected=2)
        selected = self.repository / ".github/workflows/checks.yml"
        selected.unlink()
        outside = self.base / "outside.yml"
        outside.write_text("jobs: {}")
        selected.symlink_to(outside)
        self.act_check["workflow"] = ".github/workflows/checks.yml"
        self.write_manifest([self.act_check])
        self.cli("plan", expected=2)

    def test_empty_duplicate_unknown_and_nonexecutable_manifests_reject(self):
        invalid = [
            [],
            [self.direct, self.direct],
            [dict(self.direct, unknown=True)],
            [dict(self.direct, kind=[])],
            [
                {
                    "id": "unsupported",
                    "kind": "unsupported",
                    "required": True,
                    "reason": "nothing can run",
                }
            ],
        ]
        for checks in invalid:
            with self.subTest(checks=checks):
                self.write_manifest(checks)
                self.cli("plan", expected=2)

    def test_secret_redaction_and_environment_removal(self):
        self.direct["command"] = [
            sys.executable,
            "-c",
            "import os; print(os.environ.get('GITHUB_TOKEN', 'no credential')); print('synthetic-sensitive-value')",
        ]
        self.write_manifest([self.direct])
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "synthetic-sensitive-value"}):
            self.run_manifest()
        log = (self.base / "results" / "test.log").read_text()
        self.assertIn("no credential", log)
        self.assertIn("[REDACTED]", log)
        self.assertNotIn("synthetic-sensitive-value", log)

    def test_output_cannot_overwrite_existing_directory(self):
        output = self.base / "existing"
        output.mkdir()
        marker = output / "preserved"
        marker.write_text("keep")
        self.cli("run", "--output", str(output), expected=2)
        self.assertEqual("keep", marker.read_text())

    def test_sweep_preserves_failed_repository_and_runs_next(self):
        second = self.base / "other"
        second.mkdir()
        self.write_manifest(
            [dict(self.direct, command=[sys.executable, "-c", "raise SystemExit(3)"])]
        )
        self.write_manifest([self.direct], second)
        report = self.cli(
            "sweep",
            "--repositories",
            str(self.repository),
            str(second),
            "--output",
            str(self.base / "sweep"),
            expected=1,
        )
        self.assertEqual([False, True], [r["complete"] for r in report["repositories"]])
        self.assertEqual([1, 0], [r["exit_code"] for r in report["repositories"]])
        markdown = (self.base / "sweep" / "report.md").read_text()
        self.assertIn("incomplete", markdown)
        self.assertIn("001-other/report.json", markdown)

    def test_missing_manifest_does_not_prevent_later_sweep_results(self):
        second = self.base / "missing-manifest"
        second.mkdir()
        report = self.cli(
            "sweep",
            "--repositories",
            str(second),
            str(self.repository),
            "--output",
            str(self.base / "sweep"),
            expected=1,
        )
        self.assertEqual([2, 0], [r["exit_code"] for r in report["repositories"]])

    def test_doctor_rejects_wrong_act_version_and_missing_docker(self):
        with mock.patch.object(
            local_ci,
            "execute",
            side_effect=[
                {"exit_code": 0, "output": "act version 0.2.80"},
                {"exit_code": None, "output": "Docker unavailable"},
            ],
        ):
            report = local_ci.doctor(self.repository, "act")
        self.assertFalse(report["ready"])
        self.assertIn("0.2.97", report["diagnostics"][0])

    def test_dependent_job_success_does_not_count_as_selected_job(self):
        text = json.dumps({"jobID": "dependency", "jobResult": "success", "dryrun": False})
        self.assertFalse(local_ci.completed_selection(text, self.act_check))

    def test_dryrun_and_incomplete_matrix_cannot_count_as_success(self):
        self.act_check["matrix"] = ["version:1", "version:2"]
        record = {
            "jobID": "tests",
            "jobResult": "success",
            "dryrun": False,
            "matrix": {"version": 1},
        }
        text = json.dumps(record)
        self.assertFalse(local_ci.completed_selection(text, self.act_check))
        record["matrix"]["version"] = 2
        self.assertTrue(
            local_ci.completed_selection(text + "\n" + json.dumps(record), self.act_check)
        )
        record["dryrun"] = True
        self.assertFalse(local_ci.completed_selection(json.dumps(record), self.act_check))

    def test_explicit_local_workflow_path_is_supported(self):
        local = self.repository / ".github" / "act"
        local.mkdir()
        (local / "checks.yml").write_text("on: push\njobs: {}")
        self.act_check["workflow"] = ".github/act/checks.yml"
        self.write_manifest([self.act_check])
        self.cli("plan")

    def test_owned_cleanup_reverifies_exact_label_and_never_removes_other_identity(self):
        identifier = "fixture-run"
        container = "a" * 12
        with mock.patch.object(
            local_ci,
            "execute",
            side_effect=[
                {"exit_code": 0, "output": container},
                {"exit_code": 0, "output": "other-run"},
            ],
        ) as execute:
            result = local_ci.owned_container_cleanup(self.repository, identifier)
        self.assertFalse(result["complete"])
        self.assertEqual(2, execute.call_count)
        self.assertEqual(
            "label=realm.local-ci.run=fixture-run", execute.call_args_list[0].args[0][-3]
        )

    def test_owned_cleanup_removes_only_reverified_container(self):
        container = "a" * 12
        with mock.patch.object(
            local_ci,
            "execute",
            side_effect=[
                {"exit_code": 0, "output": container},
                {"exit_code": 0, "output": "fixture-run"},
                {"exit_code": 0, "output": container},
            ],
        ) as execute:
            result = local_ci.owned_container_cleanup(self.repository, "fixture-run")
        self.assertTrue(result["complete"])
        self.assertEqual([container], result["removed"])
        self.assertEqual(["docker", "rm", "--force", container], execute.call_args_list[-1].args[0])

    def test_owned_cleanup_unavailable_docker_is_incomplete(self):
        with mock.patch.object(
            local_ci, "execute", return_value={"exit_code": None, "output": "unavailable"}
        ):
            result = local_ci.owned_container_cleanup(self.repository, "fixture-run")
        self.assertFalse(result["complete"])

    def test_cloud_mount_and_run_label_share_single_container_options(self):
        command = local_ci.invocation_options(
            ["act", "--rm"],
            [
                "--env-file",
                "/tmp/private.env",
                "--container-options",
                "--mount type=bind,source=/ca,target=/ca,readonly",
            ],
            "fixture",
        )
        self.assertEqual(1, command.count("--container-options"))
        self.assertIn("--label realm.local-ci.run=fixture", command[-1])
        self.assertIn("--mount type=bind", command[-1])

    def test_closed_stdout_process_still_has_a_deadline(self):
        self.direct.update(
            command=[
                sys.executable,
                "-c",
                "import os,time; os.close(1); os.close(2); time.sleep(30)",
            ],
            timeout_seconds=1,
        )
        self.write_manifest([self.direct])
        report = self.run_manifest()
        self.assertTrue(report["checks"][0]["timed_out"])
        self.assertEqual("failed", report["checks"][0]["status"])

    def test_sigterm_unwinds_child_group_and_saves_incomplete_report(self):
        marker = self.base / "child-started"
        self.direct.update(
            command=[
                sys.executable,
                "-c",
                f"import pathlib,time; pathlib.Path({str(marker)!r}).write_text('started'); time.sleep(30)",
            ]
        )
        self.write_manifest([self.direct])
        output = self.base / "cancelled"
        child = subprocess.Popen(
            [
                sys.executable,
                str(SCRIPT),
                "run",
                "--repository",
                str(self.repository),
                "--output",
                str(output),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            deadline = time.monotonic() + 5
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(marker.exists(), "child command did not start")
            child.terminate()
            stdout, stderr = child.communicate(timeout=5)
            self.assertEqual(143, child.returncode, stdout + stderr)
            report = json.loads((output / "report.json").read_text())
            self.assertFalse(report["complete"])
            self.assertEqual("cancelled", report["execution"])
            self.assertEqual("blocked", report["checks"][0]["status"])
        finally:
            if child.poll() is None:
                child.kill()
                child.communicate(timeout=5)


if __name__ == "__main__":
    unittest.main()
