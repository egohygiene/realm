"""Regression controls for local image evidence, not fixture authentication."""
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def module():
    spec = importlib.util.spec_from_file_location(
        "realm_image_evidence", ROOT / "tools/realm_image_evidence.py"
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class RealmImageEvidenceTests(unittest.TestCase):
    def test_plan_is_read_only_and_does_not_claim_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run(
                [
                    "python3",
                    str(ROOT / "tools/realm_image_evidence.py"),
                    "plan",
                    "--image",
                    "sha256:" + "a" * 64,
                    "--source-revision",
                    "b" * 40,
                ],
                cwd=temp,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            plan = json.loads(result.stdout)
            self.assertEqual(plan["status"], "planned")
            self.assertFalse(plan["release_ready"])
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_mutable_tags_are_rejected_before_execution(self):
        tool = module()
        for image in (
            "realm-base:latest",
            "realm-base:v1.2.3",
            "sha256:" + "A" * 64,
            "sha256:" + "a" * 63,
        ):
            with self.subTest(image=image):
                with self.assertRaises(ValueError):
                    tool.build_plan(image, "b" * 40)

    def test_profile_intent_spdx_cannot_be_installed_image_evidence(self):
        tool = module()
        declared = json.loads((ROOT / "dist/profiles/base/sbom.spdx.json").read_text())
        with self.assertRaisesRegex(ValueError, "installed.image"):
            tool.spdx_summary(declared, "sha256:" + "a" * 64)

    def test_receipt_contract_explicitly_distinguishes_image_identities(self):
        schema = json.loads(
            (ROOT / "schemas/image-evidence.v1.schema.json").read_text()
        )
        subject = schema["$defs"]["subject"]["properties"]
        self.assertEqual(subject["identity_kind"]["const"], "local-config")
        for name in ("registry_reference", "registry_manifest_digest", "index_digest"):
            self.assertEqual(subject[name]["type"], "null")


if __name__ == "__main__":
    unittest.main()
