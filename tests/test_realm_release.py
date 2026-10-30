"""Behavioral regressions for Realm-owned local release preparation.

Temporary repositories and authored evidence fixtures prove local mechanics,
never registry publication, signing or actual supported-platform qualification.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

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

    def run_release(
        self, *arguments: str, success: bool = True, environment=None
    ) -> dict:
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
            check=False,
            env=environment,
        )
        self.assertEqual(
            result.returncode, 0 if success else 2, result.stdout + result.stderr
        )
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
        self.assertEqual(
            declaration["repository"]["release_profile"], "container-image"
        )
        self.assertEqual(declaration["release"]["state"], "unreleased")
        self.assertIs(declaration["release"]["immutable_tags"], True)
        self.assertEqual(
            declaration["components"],
            [
                {
                    "id": "realm-base",
                    "kind": "container-image",
                    "version_authority": {"kind": "git-tag"},
                }
            ],
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
        for version in (
            "1.2.3",
            "v01.2.3",
            "v1.2.3-rc1",
            "v1.2.3\n",
            "main",
            "v1.2.3;id",
        ):
            with self.subTest(version=version):
                self.run_release("plan", "--version", version, success=False)
        self.run_release("plan", "--version", "v1.2.3")

    def test_dirty_input_plan_records_bytes_separately_from_head(self) -> None:
        first = self.run_release("plan", "--version", "v0.1.0")
        path = self.repository / "CHANGELOG.md"
        path.write_text(
            path.read_text() + "\n- An uncommitted authored fixture entry.\n"
        )
        second = self.run_release("plan", "--version", "v0.1.0")
        self.assertEqual(first["source_revision"], second["source_revision"])
        self.assertEqual(first["working_tree"], "clean")
        self.assertEqual(second["working_tree"], "dirty")
        self.assertEqual(second["source_binding"], "head-plus-working-input-checksums")
        self.assertNotEqual(
            first["input_sha256"]["CHANGELOG.md"],
            second["input_sha256"]["CHANGELOG.md"],
        )
        self.assertEqual(
            second["input_sha256"]["CHANGELOG.md"],
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )

    def test_prepare_emits_exclusive_review_patch_without_mutating_sources(
        self,
    ) -> None:
        changelog = self.repository / "CHANGELOG.md"
        before = changelog.read_bytes()
        output = self.directory / "prepared"
        report = self.run_release(
            "prepare",
            "--version",
            "v0.1.0",
            "--date",
            "2026-10-30",
            "--output",
            str(output),
        )
        self.assertEqual(report["status"], "prepared-local-review")
        self.assertEqual(changelog.read_bytes(), before)
        self.assertIn(
            "+## [0.1.0] - 2026-10-30", (output / "CHANGELOG.patch").read_text()
        )
        inventory = (output / "SHA256SUMS").read_bytes()
        self.run_release(
            "prepare",
            "--version",
            "v0.1.0",
            "--date",
            "2026-10-30",
            "--output",
            str(output),
            success=False,
        )
        self.assertEqual((output / "SHA256SUMS").read_bytes(), inventory)

    def test_prepare_rejects_bad_date_and_source_output_collision(self) -> None:
        output = self.directory / "bad-date"
        self.run_release(
            "prepare",
            "--version",
            "v0.1.0",
            "--date",
            "2026-02-30",
            "--output",
            str(output),
            success=False,
        )
        self.assertFalse(output.exists())
        self.run_release(
            "prepare",
            "--version",
            "v0.1.0",
            "--date",
            "2026-10-30",
            "--output",
            str(self.repository / "tools"),
            success=False,
        )
        target = self.repository / "tools" / "unintended-output"
        self.run_release(
            "prepare",
            "--version",
            "v0.1.0",
            "--date",
            "2026-10-30",
            "--output",
            str(self.repository / ".cache/realm/../../tools/unintended-output"),
            success=False,
        )
        self.assertFalse(target.exists())

    def test_duplicate_local_tag_cannot_be_prepared_again(self) -> None:
        self.git("tag", "v0.1.0")
        self.run_release("plan", "--version", "v0.1.0", success=False)
        self.run_release("plan", "--version", "v0.2.0")

    def test_invalid_declaration_does_not_become_a_clean_plan(self) -> None:
        path = self.repository / ".egohygiene" / "release.json"
        original = path.read_text()
        cases = []
        for field, value in (
            ("components", None),
            ("release", []),
            ("repository", "realm"),
        ):
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
        path = (
            self.repository
            / "vendor"
            / "aether"
            / "aether.repository-release.v1.schema.json"
        )
        path.write_bytes(path.read_bytes() + b"\n")
        self.run_release("check", success=False)

    def test_publish_handoff_is_literal_and_workflow_has_no_registry_authority(
        self,
    ) -> None:
        task = (ROOT / "Taskfile.yml").read_text()
        self.assertIn("gh workflow run .github/workflows/release.yml", task)
        workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("  push:", workflow)
        self.assertNotIn("  pull_request:", workflow)
        self.assertNotIn("packages: write", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("id-token: write", workflow)

    def release_module(self):
        specification = importlib.util.spec_from_file_location("realm_release", SCRIPT)
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
        return module

    def mapping_fixture(self, platform="linux/amd64", revision="a" * 40):
        """Authored pure-mapping seam; deliberately not image-owner qualification."""
        sbom = json.dumps(
            {
                "spdxVersion": "SPDX-2.3",
                "documentNamespace": "https://example.invalid/sbom/"
                + platform.replace("/", "-"),
            }
        ).encode()
        receipt = {
            "source": {
                "repository": "egohygiene/realm",
                "revision": revision,
                "inputs": {"images/base/Dockerfile": "f" * 64},
            },
            "subject": {
                "identity_kind": "local-config",
                "platform": platform,
                "execution": "native",
                "local_config_digest": "sha256:" + "b" * 64,
                "scanner_manifest_digest": "sha256:" + "c" * 64,
                "registry_reference": None,
                "registry_manifest_digest": None,
                "index_digest": None,
            },
            "observed_at": "2026-10-30T12:00:00Z",
            "artifacts": {
                "sbom": {
                    "path": "sbom.spdx.json",
                    "sha256": hashlib.sha256(sbom).hexdigest(),
                }
            },
        }
        payloads = {
            "sbom.spdx.json": sbom,
            "fixture-receipt.json": json.dumps(receipt).encode(),
        }
        return receipt, payloads, "fixture-receipt.json"

    def test_pure_mapping_indexes_supplied_bytes_without_authentication(self) -> None:
        tool = self.release_module()
        fixture = self.mapping_fixture()
        files = tool.bundle_files("v0.1.0", "a" * 40, [fixture])
        manifest = json.loads(files["image-digest.json"])
        self.assertFalse(manifest["release_ready"])
        self.assertIsNone(manifest["registry_index"])
        self.assertIsNone(manifest["images"][0]["registry_manifest_digest"])
        index = json.loads(files["sbom.spdx.json"])
        self.assertEqual(
            index["externalDocumentRefs"][0]["checksum"]["checksumValue"],
            hashlib.sha256(fixture[1]["sbom.spdx.json"]).hexdigest(),
        )
        self.assertNotIn("packages", index)
        self.assertEqual(tool.bundle_files("v0.1.0", "a" * 40, [fixture]), files)

    def test_pure_mapping_rejects_subject_contradictions_before_writes(self) -> None:
        tool = self.release_module()
        for field, value in (
            ("platform", []),
            ("registry_manifest_digest", "sha256:" + "d" * 64),
            ("execution", "emulated"),
        ):
            fixture = self.mapping_fixture()
            fixture[0]["subject"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                tool.bundle_files("v0.1.0", "a" * 40, [fixture])
        with self.assertRaises(ValueError):
            tool.bundle_files(
                "v0.1.0", "a" * 40, [self.mapping_fixture(revision="e" * 40)]
            )
        fixture = self.mapping_fixture()
        with self.assertRaises(ValueError):
            tool.bundle_files("v0.1.0", "a" * 40, [fixture, fixture])

    def test_pure_mapping_accepts_owner_lowercase_rfc3339(self) -> None:
        tool = self.release_module()
        fixture = self.mapping_fixture()
        fixture[0]["observed_at"] = "2026-10-30t12:00:00z"
        files = tool.bundle_files("v0.1.0", "a" * 40, [fixture])
        index = json.loads(files["sbom.spdx.json"])
        self.assertEqual(index["creationInfo"]["created"], "2026-10-30T12:00:00Z")

    def test_namespace_consumer_policy_has_uri_controls_without_network(self) -> None:
        tool = self.release_module()
        for value in (
            "https://example.invalid/sbom/abc",
            "HTTP://example.invalid/a%20b",
            "urn:uuid:12345678-abcd-1234-abcd-123456789abc",
        ):
            with self.subTest(value=value):
                self.assertEqual(tool.namespace_uri(value), value)
        for value in (
            "not a uri",
            "https:///missing-host",
            "https://example.invalid/a#fragment",
            "https://example.invalid/%GG",
            "urn::missing-nid",
            "https://example.invalid/[bad]",
            "file:///private/sbom",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                tool.namespace_uri(value)

    def test_checksum_complete_arbitrary_records_are_not_image_proof(self) -> None:
        tool = self.release_module()
        output = self.directory / "untrusted-bundle"
        files = {
            name: b"{}\n"
            for name in (
                "image-digest.json",
                "provenance.json",
                "signature.json",
                "sbom.spdx.json",
            )
        }
        tool.write_exclusive(output, self.repository, files)
        self.run_release(
            "verify",
            "--version",
            "v0.1.0",
            "--source-revision",
            "a" * 40,
            "--bundle",
            str(output),
            success=False,
        )
        self.assertEqual(
            set(output.iterdir()), {output / name for name in (*files, "SHA256SUMS")}
        )

    def test_malformed_platform_record_is_controlled_even_when_checksums_match(
        self,
    ) -> None:
        tool = self.release_module()
        files = tool.bundle_files("v0.1.0", "a" * 40, [self.mapping_fixture()])
        manifest = json.loads(files["image-digest.json"])
        manifest["images"][0]["platform"] = []
        files["image-digest.json"] = tool.canonical(manifest)
        output = self.directory / "bad-platform"
        tool.write_exclusive(output, self.repository, files)
        self.run_release(
            "verify",
            "--version",
            "v0.1.0",
            "--source-revision",
            "a" * 40,
            "--bundle",
            str(output),
            success=False,
        )

    def owner_fixture(self, directory):
        """Use the actual image-owner verifier with explicitly authored payloads."""
        specification = importlib.util.spec_from_file_location(
            "owner_evidence_fixtures", ROOT / "tests/test_realm_image_evidence.py"
        )
        fixtures = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(fixtures)
        directory.mkdir()
        helper = fixtures.PortableEvidenceTests()
        tool, receipt = helper.fixture(directory)
        # The owner's fixture proves its bounded semantic subset. The release
        # SPDX index also needs an external document URI; this remains a
        # synthetic fixture, not actual scanner or platform evidence.
        sbom_path = directory / "sbom.spdx.json"
        sbom = json.loads(sbom_path.read_text())
        sbom["documentNamespace"] = (
            "https://example.invalid/realm-installed-image-fixture"
        )
        data = tool.encode(sbom)
        sbom_path.write_bytes(data)
        receipt["artifacts"]["sbom"]["sha256"] = tool.digest(data)
        receipt["artifacts"]["sbom"]["bytes"] = len(data)
        (directory / "image-evidence.json").write_bytes(tool.encode(receipt))
        self.assertEqual(tool.verify_evidence(directory), receipt)
        return helper, tool, receipt

    def local_bundle(self):
        evidence = self.directory / "owner-evidence"
        self.owner_fixture(evidence)
        output = self.directory / "local-bundle"
        self.run_release(
            "bundle",
            "--version",
            "v0.1.0",
            "--source-revision",
            "b" * 40,
            "--image-evidence",
            str(evidence),
            "--output",
            str(output),
        )
        return output

    def verify_local(self, output, **kwargs):
        return self.run_release(
            "verify",
            "--version",
            "v0.1.0",
            "--source-revision",
            "b" * 40,
            "--bundle",
            str(output),
            **kwargs,
        )

    def rewrite_checksums(self, directory):
        files = {
            path.relative_to(directory).as_posix(): path.read_bytes()
            for path in directory.rglob("*")
            if path.is_file() and path.name != "SHA256SUMS"
        }
        (directory / "SHA256SUMS").write_text(
            "".join(
                f"{hashlib.sha256(data).hexdigest()}  {name}\n"
                for name, data in sorted(files.items())
            )
        )

    def test_actual_owner_contract_roundtrip_stays_local_and_exclusive(self) -> None:
        output = self.local_bundle()
        report = self.verify_local(output)
        self.assertEqual(report["status"], "verified-local-bundle")
        self.assertEqual(report["observed_platforms"], ["linux/amd64"])
        self.assertEqual(
            report["registry_credentials"], "not-required-for-local-verification"
        )
        self.run_release(
            "verify",
            "--version",
            "v0.1.0",
            "--source-revision",
            "b" * 40,
            "--bundle",
            str(output),
            "--require-release-ready",
            success=False,
        )
        before = (output / "SHA256SUMS").read_bytes()
        self.run_release(
            "bundle",
            "--version",
            "v0.1.0",
            "--source-revision",
            "b" * 40,
            "--image-evidence",
            str(self.directory / "owner-evidence"),
            "--output",
            str(output),
            success=False,
        )
        self.assertEqual(before, (output / "SHA256SUMS").read_bytes())
        self.verify_local(output)

    def test_owner_receipt_escaped_solidus_is_a_semantic_json_control(self) -> None:
        evidence = self.directory / "owner-evidence"
        _helper, owner, receipt = self.owner_fixture(evidence)
        path = evidence / "image-evidence.json"
        path.write_bytes(
            path.read_bytes().replace(
                b"realm.image-evidence/v1", b"realm.image-evidence\\/v1"
            )
        )
        self.assertEqual(owner.verify_evidence(evidence), receipt)
        output = self.directory / "escaped-receipt-bundle"
        self.run_release(
            "bundle",
            "--version",
            "v0.1.0",
            "--source-revision",
            "b" * 40,
            "--image-evidence",
            str(evidence),
            "--output",
            str(output),
        )
        self.verify_local(output)

    def test_rehashed_root_forgeries_fail_while_owner_payloads_remain_valid(
        self,
    ) -> None:
        original = self.local_bundle()
        cases = [
            (
                "image-digest.json",
                lambda value: value.__setitem__("release_ready", True),
            ),
            (
                "provenance.json",
                lambda value: value.__setitem__("source_revision", "c" * 40),
            ),
            ("signature.json", lambda value: value.__setitem__("state", "verified")),
            (
                "sbom.spdx.json",
                lambda value: value["externalDocumentRefs"][0]["checksum"].__setitem__(
                    "checksumValue", "d" * 64
                ),
            ),
        ]
        for number, (name, change) in enumerate(cases):
            with self.subTest(name=name):
                forged = self.directory / f"forged-{number}"
                shutil.copytree(original, forged)
                path = forged / name
                value = json.loads(path.read_text())
                change(value)
                path.write_bytes(self.release_module().canonical(value))
                self.rewrite_checksums(forged)
                self.verify_local(forged, success=False)
        self.verify_local(original)

    def test_rehashed_owner_subject_forgery_is_rejected_before_output(self) -> None:
        evidence = self.directory / "owner-evidence"
        helper, _tool, _receipt = self.owner_fixture(evidence)
        helper.rewrite(
            evidence,
            "syft.json",
            lambda value: value["source"]["metadata"].__setitem__(
                "architecture", "arm64"
            ),
        )
        output = self.directory / "rejected-owner-output"
        self.run_release(
            "bundle",
            "--version",
            "v0.1.0",
            "--source-revision",
            "b" * 40,
            "--image-evidence",
            str(evidence),
            "--output",
            str(output),
            success=False,
        )
        self.assertFalse(output.exists())

    def test_owner_valid_invalid_namespace_rejects_before_output_without_value_leak(
        self,
    ) -> None:
        for number, namespace in enumerate(
            (
                "not a uri",
                "https://example.invalid:private-port/sbom",
                "https://example.invalid/a#fragment",
            )
        ):
            with self.subTest(number=number):
                evidence = self.directory / f"owner-evidence-{number}"
                helper, owner, _receipt = self.owner_fixture(evidence)
                helper.rewrite(
                    evidence,
                    "sbom.spdx.json",
                    lambda value, namespace=namespace: value.__setitem__(
                        "documentNamespace", namespace
                    ),
                )
                self.assertIsInstance(owner.verify_evidence(evidence), dict)
                output = self.directory / f"invalid-namespace-output-{number}"
                report = self.run_release(
                    "bundle",
                    "--version",
                    "v0.1.0",
                    "--source-revision",
                    "b" * 40,
                    "--image-evidence",
                    str(evidence),
                    "--output",
                    str(output),
                    success=False,
                )
                self.assertFalse(output.exists())
                self.assertNotIn(namespace, report["message"])
                self.assertNotIn("private-port", report["message"])

    def test_portable_verification_initializes_no_registry_or_scanner_tool(
        self,
    ) -> None:
        output = self.local_bundle()
        trap = self.directory / "trap"
        trap.mkdir()
        marker = self.directory / "unexpected-tool"
        for name in ("docker", "syft", "grype", "gh", "git"):
            path = trap / name
            path.write_text(f"#!/bin/sh\nprintf x > '{marker}'\nexit 95\n")
            path.chmod(0o755)
        environment = dict(os.environ)
        environment["PATH"] = str(trap)
        self.verify_local(output, environment=environment)
        self.assertFalse(marker.exists())

    def test_bundle_output_cannot_be_nested_inside_its_image_inputs(self) -> None:
        evidence = self.directory / "owner-evidence"
        self.owner_fixture(evidence)
        output = evidence / "nested-output"
        before = sorted(path.name for path in evidence.iterdir())
        self.run_release(
            "bundle",
            "--version",
            "v0.1.0",
            "--source-revision",
            "b" * 40,
            "--image-evidence",
            str(evidence),
            "--output",
            str(output),
            success=False,
        )
        self.assertFalse(output.exists())
        self.assertEqual(before, sorted(path.name for path in evidence.iterdir()))

    def test_captured_copy_must_still_match_the_owner_verified_snapshot(self) -> None:
        """Deterministic mutation seam, not an assertion about real concurrency."""
        evidence = self.directory / "owner-evidence"
        _helper, owner, _receipt = self.owner_fixture(evidence)

        def verified_then_mutated(directory):
            receipt = owner.verify_evidence(directory)
            path = directory / "syft.json"
            path.write_bytes(path.read_bytes() + b"\n")
            return receipt

        seam = types.SimpleNamespace(verify_evidence=verified_then_mutated)
        with (
            mock.patch.dict(sys.modules, {"realm_image_evidence": seam}),
            self.assertRaisesRegex(ValueError, "captured image artifact"),
        ):
            self.release_module().verified_image(evidence)

    def test_pure_two_platform_mapping_is_order_independent_not_native_proof(
        self,
    ) -> None:
        tool = self.release_module()
        amd64 = self.mapping_fixture()
        arm64 = self.mapping_fixture(platform="linux/arm64")
        arm64[0]["subject"]["local_config_digest"] = "sha256:" + "d" * 64
        first = tool.bundle_files("v0.1.0", "a" * 40, [amd64, arm64])
        second = tool.bundle_files("v0.1.0", "a" * 40, [arm64, amd64])
        self.assertEqual(first, second)
        manifest = json.loads(first["image-digest.json"])
        self.assertEqual(
            [item["platform"] for item in manifest["images"]],
            ["linux/amd64", "linux/arm64"],
        )
        self.assertFalse(manifest["release_ready"])
        arm64[0]["source"]["inputs"]["images/base/Dockerfile"] = "e" * 64
        with self.assertRaisesRegex(ValueError, "shared source-input"):
            tool.bundle_files("v0.1.0", "a" * 40, [amd64, arm64])


if __name__ == "__main__":
    unittest.main()
