"""Behavioral evidence for Realm's static Dev Container boundary checker.

The authored reference is independent of Realm's future projection. These tests
never start a container, execute lifecycle hooks or qualify an editor/cloud host.
"""
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "realm_devcontainer_boundary.py"
MAPPING = ROOT / "catalog" / "devcontainer-boundary.v1.json"
REFERENCE = (
    ROOT / "tests/fixtures/devcontainer/reference/.devcontainer/devcontainer.json"
)

CAPABILITIES = {
    "images",
    "dockerfiles",
    "compose",
    "features",
    "environment",
    "users",
    "mounts",
    "lifecycle",
    "ports",
    "host-requirements",
    "editor-customizations",
    "host-customizations",
    "prebuild-cache",
}
HOSTS = {"devcontainer-cli", "vscode", "codespaces", "devpod"}
EXTERNAL_LAYERS = {
    "official_schema",
    "cli_interpretation",
    "container_execution",
    "task_workflow",
    "vscode",
    "codespaces",
    "devpod",
}
REPORT_KEYS = {
    "schema_version",
    "contract",
    "scope",
    "state",
    "input_digests",
    "checks",
    "evidence_layers",
    "host_qualification",
    "required_layer",
}


class RealmDevcontainerBoundaryTests(unittest.TestCase):
    def run_check(
        self,
        *,
        mapping: Path | None = None,
        reference: Path | None = None,
        require_layer: str | None = None,
        cwd: Path = ROOT,
        env: dict[str, str] | None = None,
        tool: Path = TOOL,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        arguments = [sys.executable, str(tool), "check"]
        for option, value in [
            ("--mapping", mapping),
            ("--reference", reference),
            ("--require-layer", require_layer),
        ]:
            if value is not None:
                arguments.extend([option, str(value)])
        result = subprocess.run(
            arguments,
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        self.assertNotIn("Traceback", result.stdout + result.stderr)
        try:
            report = json.loads(result.stdout)
        except json.JSONDecodeError:
            self.fail(
                f"checker did not emit structured JSON: {result.stdout!r}; {result.stderr!r}"
            )
        self.assertIsInstance(report, dict)
        self.assertEqual(set(report), REPORT_KEYS)
        self.assertEqual(report["contract"], "realm.devcontainer-boundary-report/v1")
        self.assertEqual(report["scope"], "mapping-and-reference-policy-only")
        self.assertIn(report["state"], {"valid", "invalid", "unavailable"})
        self.assertEqual(
            set(report["evidence_layers"]),
            {"mapping", "reference_policy"} | EXTERNAL_LAYERS,
        )
        for layer in EXTERNAL_LAYERS:
            self.assertEqual(report["evidence_layers"][layer], "not-performed", layer)
        self.assertEqual(
            set(report["input_digests"]), {"mapping", "reference", "spec_schema"}
        )
        for digest in report["input_digests"].values():
            if digest is not None:
                self.assertRegex(digest, r"^[a-f0-9]{64}$")
        self.assertLess(len(result.stdout), 32_768)
        return result, report

    def authored_inputs(self) -> tuple[dict[str, Any], dict[str, Any]]:
        return json.loads(MAPPING.read_text()), json.loads(REFERENCE.read_text())

    def check_documents(
        self, mapping: Any, reference: Any
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mapping_path, reference_path = (
                root / "mapping.json",
                root / "reference.json",
            )
            mapping_path.write_text(json.dumps(mapping), encoding="utf-8")
            reference_path.write_text(json.dumps(reference), encoding="utf-8")
            before = mapping_path.read_bytes(), reference_path.read_bytes()
            result, report = self.run_check(
                mapping=mapping_path, reference=reference_path
            )
            self.assertEqual(
                before, (mapping_path.read_bytes(), reference_path.read_bytes())
            )
            self.assertEqual(
                {path.name for path in root.iterdir()},
                {"mapping.json", "reference.json"},
            )
            return result, report

    def assert_invalid(
        self, result: subprocess.CompletedProcess[str], report: dict[str, Any]
    ) -> None:
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["state"], "invalid")
        self.assertTrue(any(check["status"] == "failed" for check in report["checks"]))

    def test_default_check_distinguishes_policy_from_runtime_proof(self) -> None:
        result, report = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["state"], "valid")
        self.assertEqual(report["evidence_layers"]["mapping"], "passed")
        self.assertEqual(report["evidence_layers"]["reference_policy"], "passed")
        self.assertIsNone(report["required_layer"])
        qualifications = report["host_qualification"]
        self.assertEqual({item["id"] for item in qualifications}, HOSTS)
        self.assertEqual(len(qualifications), len(HOSTS))
        for item in qualifications:
            self.assertEqual(item["observed"], "unavailable")
            self.assertTrue(item["reason"])

    def test_source_mapping_covers_each_capability_and_host_once(self) -> None:
        mapping, _ = self.authored_inputs()
        self.assertEqual(mapping["canonical_input"], "resolved-profile.v1")
        self.assertEqual(
            mapping["projection_issue"], "https://github.com/egohygiene/realm/issues/10"
        )
        self.assertEqual({item["id"] for item in mapping["capabilities"]}, CAPABILITIES)
        self.assertEqual(len(mapping["capabilities"]), len(CAPABILITIES))
        self.assertEqual({item["id"] for item in mapping["hosts"]}, HOSTS)
        for host in mapping["hosts"]:
            self.assertEqual(set(host["expected"]), CAPABILITIES)
        self.assertEqual(mapping["reference"]["kind"], "authored-reference-only")
        self.assertIs(mapping["reference"]["realm_profile_applied"], False)

    def test_recorded_reference_evidence_matches_subject_and_retains_limits(
        self,
    ) -> None:
        mapping, reference = self.authored_inputs()
        receipt = json.loads(
            (ROOT / "docs/evidence/devcontainer-authored-reference.v1.json").read_text()
        )
        self.assertEqual(receipt["schema_version"], "1.0.0")
        self.assertEqual(
            receipt["contract"], "realm.devcontainer-reference-evidence/v1"
        )
        self.assertEqual(receipt["state"], "limited")
        self.assertEqual(receipt["scope"], "authored-reference-only/local-linux-amd64")
        self.assertEqual(
            receipt["subject"],
            {
                "reference_path": REFERENCE.relative_to(ROOT).as_posix(),
                "reference_sha256": hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),
                "image": reference["image"],
            },
            "Changing authored reference bytes requires fresh observation evidence.",
        )
        for receipt_field, mapping_field in [
            ("repository", "repository"),
            ("revision", "revision"),
            ("path", "schema_path"),
            ("sha256", "sha256"),
        ]:
            self.assertEqual(
                receipt["official_schema"][receipt_field],
                mapping["spec"][mapping_field],
            )
        self.assertEqual(receipt["tools"]["cli"]["version"], mapping["cli"]["version"])
        self.assertEqual(
            receipt["tools"]["cli"]["source_revision"], mapping["cli"]["revision"]
        )
        self.assertTrue(
            {
                "realm-profile-generation",
                "task-workflow",
                "mantle-integration",
                "vscode",
                "codespaces",
                "devpod",
            }.issubset(receipt["unproven"])
        )
        result, report = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["state"], "valid")
        # run_check also requires every external proof layer to be not-performed;
        # the separate observation receipt must not authenticate the checker.

    def test_requested_unperformed_proof_cannot_become_a_passing_check(self) -> None:
        for layer in sorted(EXTERNAL_LAYERS):
            with self.subTest(layer=layer):
                result, report = self.run_check(require_layer=layer.replace("_", "-"))
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(report["state"], "unavailable")
                self.assertEqual(report["evidence_layers"]["mapping"], "passed")
                self.assertEqual(
                    report["evidence_layers"]["reference_policy"], "passed"
                )

    def test_policy_layers_can_be_requested_without_external_runtime(self) -> None:
        for layer in ["mapping", "reference-policy"]:
            with self.subTest(layer=layer):
                result, report = self.run_check(require_layer=layer)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(report["state"], "valid")

    def test_unknown_fields_and_wrong_scalar_types_are_controlled(self) -> None:
        mapping, reference = self.authored_inputs()
        cases: list[tuple[str, Any]] = [
            ("null", None),
            ("array", []),
            ("boolean", False),
        ]
        for name, path, value in [
            ("unknown-root", (), ("unsupported", True)),
            ("wrong-version", (), ("schema_version", 1)),
            ("unknown-spec", ("spec",), ("unsupported", True)),
            (
                "wrong-reference-kind",
                ("reference",),
                ("kind", "generated-realm-projection"),
            ),
            ("unknown-reference", ("reference",), ("unsupported", True)),
            ("unknown-cli", ("cli",), ("unsupported", True)),
            ("wrong-owner", ("capabilities", 0), ("owner", 42)),
            (
                "wrong-property-elements",
                ("capabilities", 0),
                ("spec_properties", [True]),
            ),
            ("wrong-realm-inputs", ("capabilities", 0), ("realm_inputs", "image")),
            ("wrong-limitations", ("capabilities", 0), ("limitations", "none")),
            ("unknown-capability-field", ("capabilities", 0), ("unsupported", True)),
            ("unknown-host-field", ("hosts", 0), ("unsupported", True)),
            ("wrong-host-limitations", ("hosts", 0), ("limitations", None)),
        ]:
            mutated = copy.deepcopy(mapping)
            parent = mutated
            for field in path:
                parent = parent[field]
            parent[value[0]] = value[1]
            cases.append((name, mutated))
        for name, mutated in cases:
            with self.subTest(case=name):
                result, report = self.check_documents(mutated, reference)
                self.assert_invalid(result, report)
                self.assertEqual(report["evidence_layers"]["mapping"], "failed")

    def test_reference_cannot_claim_a_realm_projection_through_truthy_values(
        self,
    ) -> None:
        mapping, reference = self.authored_inputs()
        for claim in [True, 0, 1, "false", "true", None]:
            with self.subTest(claim=claim):
                mutated = copy.deepcopy(mapping)
                mutated["reference"]["realm_profile_applied"] = claim
                result, report = self.check_documents(mutated, reference)
                self.assert_invalid(result, report)

    def test_missing_duplicate_or_unsupported_coverage_is_rejected(self) -> None:
        mapping, reference = self.authored_inputs()
        cases = []
        for collection in ["capabilities", "hosts"]:
            missing = copy.deepcopy(mapping)
            missing[collection].pop()
            cases.append((f"missing-{collection}", missing))
            duplicate = copy.deepcopy(mapping)
            duplicate[collection].append(copy.deepcopy(duplicate[collection][0]))
            cases.append((f"duplicate-{collection}", duplicate))
            unknown = copy.deepcopy(mapping)
            unknown[collection][0]["id"] = "unsupported"
            cases.append((f"unsupported-{collection}", unknown))
        for state in ["verified", "pending", True, None]:
            unknown_state = copy.deepcopy(mapping)
            host = unknown_state["hosts"][0]
            host["expected"][next(iter(host["expected"]))] = state
            cases.append((f"unsupported-state-{state}", unknown_state))
        missing_expected = copy.deepcopy(mapping)
        missing_expected["hosts"][0]["expected"].pop(next(iter(CAPABILITIES)))
        cases.append(("missing-host-capability", missing_expected))
        extra_expected = copy.deepcopy(mapping)
        extra_expected["hosts"][0]["expected"]["unsupported"] = "supported"
        cases.append(("unknown-host-capability", extra_expected))
        for name, mutated in cases:
            with self.subTest(case=name):
                result, report = self.check_documents(mutated, reference)
                self.assert_invalid(result, report)

    def test_owner_pins_and_schema_digest_cannot_drift(self) -> None:
        mapping, reference = self.authored_inputs()
        for section, field, value in [
            ("spec", "repository", "example/spec"),
            ("spec", "revision", "main"),
            ("spec", "revision", "0" * 40),
            ("spec", "sha256", "0" * 64),
            ("spec", "schema_path", "../outside.schema.json"),
            ("spec", "license", "MIT"),
            ("cli", "revision", "main"),
            (
                "cli",
                "source",
                "https://github.com/devcontainers/cli/blob/main/README.md",
            ),
        ]:
            with self.subTest(section=section, field=field, value=value):
                mutated = copy.deepcopy(mapping)
                mutated[section][field] = value
                result, report = self.check_documents(mutated, reference)
                self.assert_invalid(result, report)

    def test_reference_policy_refuses_mutable_images_and_features(self) -> None:
        mapping, reference = self.authored_inputs()
        mutations = [
            ("image", "ghcr.io/example/reference:latest"),
            ("image", "ghcr.io/example/reference@sha256:not-a-digest"),
            ("image", "ghcr.io/example/reference@sha256:" + "a" * 63),
            ("features", {"ghcr.io/example/features/tool:1": {}}),
            ("features", {"ghcr.io/example/features/tool@sha256:bad": {}}),
        ]
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                mutated = copy.deepcopy(reference)
                mutated[field] = value
                result, report = self.check_documents(mapping, mutated)
                self.assert_invalid(result, report)
                self.assertEqual(
                    report["evidence_layers"]["reference_policy"], "failed"
                )

    def test_digest_pinned_features_are_policy_data_without_remote_proof(self) -> None:
        mapping, reference = self.authored_inputs()
        reference["features"] = {
            "ghcr.io/example/features/tool@sha256:" + "a" * 64: {
                "version": "1.2.3",
                "enabled": True,
                "owner-defined": {"data": "not-interpreted-by-the-policy-checker"},
            }
        }
        result, report = self.check_documents(mapping, reference)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["state"], "valid")
        self.assertEqual(report["evidence_layers"]["reference_policy"], "passed")

    def test_reference_policy_rejects_non_object_feature_options(self) -> None:
        mapping, reference = self.authored_inputs()
        feature = "ghcr.io/example/features/tool@sha256:" + "a" * 64
        for options in [None, True, 1, "latest", []]:
            with self.subTest(options=options):
                mutated = copy.deepcopy(reference)
                mutated["features"] = {feature: options}
                result, report = self.check_documents(mapping, mutated)
                self.assert_invalid(result, report)
                self.assertEqual(
                    report["evidence_layers"]["reference_policy"], "failed"
                )

    def test_reference_policy_rejects_non_oci_digest_strings(self) -> None:
        mapping, reference = self.authored_inputs()
        for repository in [
            "https://ghcr.io/example/reference",
            "ghcr.io/example/./reference",
            "ghcr.io/example/../reference",
            "ghcr.io/example//reference",
        ]:
            pinned = repository + "@sha256:" + "a" * 64
            for field, value in [("image", pinned), ("features", {pinned: {}})]:
                with self.subTest(repository=repository, field=field):
                    mutated = copy.deepcopy(reference)
                    mutated[field] = value
                    result, report = self.check_documents(mapping, mutated)
                    self.assert_invalid(result, report)
                    self.assertEqual(
                        report["evidence_layers"]["reference_policy"], "failed"
                    )

    def test_reference_user_policy_checks_user_component_without_claiming_existence(
        self,
    ) -> None:
        mapping, reference = self.authored_inputs()
        for field in ["remoteUser", "containerUser"]:
            for user in ["root:root", "0:0", "00"]:
                with self.subTest(field=field, rejected_user=user):
                    mutated = copy.deepcopy(reference)
                    mutated[field] = user
                    result, report = self.check_documents(mapping, mutated)
                    self.assert_invalid(result, report)
                    self.assertEqual(
                        report["evidence_layers"]["reference_policy"], "failed"
                    )
            for user in ["vscode", "1000", "1000:1000"]:
                with self.subTest(field=field, declared_user=user):
                    mutated = copy.deepcopy(reference)
                    mutated[field] = user
                    result, report = self.check_documents(mapping, mutated)
                    self.assertEqual(
                        result.returncode, 0, result.stdout + result.stderr
                    )
                    self.assertEqual(report["state"], "valid")
                    self.assertEqual(
                        report["evidence_layers"]["reference_policy"], "passed"
                    )

    def test_local_schema_byte_drift_fails_in_an_isolated_checker_copy(self) -> None:
        mapping, _ = self.authored_inputs()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for source in [
                TOOL,
                MAPPING,
                REFERENCE,
                ROOT / mapping["spec"]["schema_path"],
            ]:
                destination = root / source.relative_to(ROOT)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
            schema_path = root / mapping["spec"]["schema_path"]
            schema_path.write_bytes(schema_path.read_bytes() + b"\n")
            result, report = self.run_check(
                tool=root / TOOL.relative_to(ROOT), cwd=root
            )
            self.assert_invalid(result, report)
            self.assertEqual(report["evidence_layers"]["mapping"], "failed")

    def test_editor_and_host_namespaces_cannot_leak_to_the_top_level(self) -> None:
        mapping, reference = self.authored_inputs()
        for field, value in [
            ("vscode", {}),
            ("settings", {"editor.tabSize": 2}),
            ("extensions", ["example.extension"]),
            ("codespaces", {}),
        ]:
            with self.subTest(field=field):
                mutated = copy.deepcopy(reference)
                mutated[field] = value
                result, report = self.check_documents(mapping, mutated)
                self.assert_invalid(result, report)

    def test_host_commands_are_rejected_as_data_and_never_executed(self) -> None:
        mapping, reference = self.authored_inputs()
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "host-command-executed"
            mutated = copy.deepcopy(reference)
            mutated["initializeCommand"] = [
                sys.executable,
                "-c",
                f"from pathlib import Path; Path({str(marker)!r}).touch()",
            ]
            result, report = self.check_documents(mapping, mutated)
            self.assert_invalid(result, report)
            self.assertFalse(marker.exists())

    def test_duplicate_json_keys_are_not_silently_overwritten(self) -> None:
        mapping, reference = self.authored_inputs()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for target in ["mapping", "reference"]:
                with self.subTest(target=target):
                    mapping_path, reference_path = (
                        root / "mapping.json",
                        root / "reference.json",
                    )
                    mapping_path.write_text(json.dumps(mapping), encoding="utf-8")
                    reference_path.write_text(json.dumps(reference), encoding="utf-8")
                    if target == "mapping":
                        mapping_path.write_text(
                            '{"contract":"realm.devcontainer-boundary/v1",'
                            + json.dumps(mapping)[1:],
                            encoding="utf-8",
                        )
                    else:
                        reference_path.write_text(
                            '{"image":'
                            + json.dumps(reference["image"])
                            + ","
                            + json.dumps(reference)[1:],
                            encoding="utf-8",
                        )
                    result, report = self.run_check(
                        mapping=mapping_path, reference=reference_path
                    )
                    self.assert_invalid(result, report)

    def test_missing_malformed_and_oversized_files_return_controlled_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            malformed = root / "malformed.json"
            malformed.write_text('{"broken":', encoding="utf-8")
            oversized = root / "oversized.json"
            oversized.write_text(
                '{"padding":"' + "x" * (2 * 1024 * 1024) + '"}', encoding="utf-8"
            )
            for target in ["mapping", "reference"]:
                for path in [root / "missing.json", malformed, oversized]:
                    with self.subTest(target=target, path=path.name):
                        before = path.read_bytes() if path.exists() else None
                        result, report = self.run_check(**{target: path})
                        self.assert_invalid(result, report)
                        self.assertEqual(
                            before, path.read_bytes() if path.exists() else None
                        )
                        if path == oversized:
                            self.assertRegex(
                                " ".join(
                                    check["message"] for check in report["checks"]
                                ),
                                r"(?i)large|limit|bytes",
                            )

    def test_check_is_deterministic_read_only_and_needs_no_runtime(self) -> None:
        mapping, _ = self.authored_inputs()
        paths = [MAPPING, REFERENCE, ROOT / mapping["spec"]["schema_path"]]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = {**os.environ, "PATH": str(root), "PYTHONDONTWRITEBYTECODE": "1"}
            first, first_report = self.run_check(cwd=root, env=env)
            second, second_report = self.run_check(cwd=root, env=env)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertEqual(first.stdout, second.stdout)
            self.assertEqual(first_report, second_report)
            self.assertEqual(list(root.iterdir()), [])
        self.assertEqual(
            before,
            {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
        )


if __name__ == "__main__":
    unittest.main()
