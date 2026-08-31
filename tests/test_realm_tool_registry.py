"""Conformance tests for Realm's curated tool evaluation registry."""

from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from realm_tool_registry import (  # noqa: E402
    load_registry,
    render_report,
    validate_registry,
)


class RealmToolRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = load_registry(ROOT / "catalog" / "tool-evaluations.json")

    def test_repository_registry_is_valid(self) -> None:
        self.assertEqual(validate_registry(self.registry), [])

    def test_accepted_tool_requires_immutable_version_source(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["tools"]["rustup"]["version_source"] = (
            "https://github.com/rust-lang/rustup@main"
        )
        errors = validate_registry(registry)
        self.assertTrue(any("version_source is not immutable" in error for error in errors))

    def test_accepted_tool_requires_test_evidence(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["tools"]["node"]["tests"] = []
        errors = validate_registry(registry)
        self.assertTrue(any("has no owning test evidence" in error for error in errors))

    def test_experimental_tool_cannot_name_a_stable_capability(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["tools"]["aws-cli"]["stable_capability"] = "cloud-cli"
        errors = validate_registry(registry)
        self.assertTrue(
            any("not accepted but names a stable capability" in error for error in errors)
        )

    def test_snapshot_is_an_immutable_package_source(self) -> None:
        self.assertEqual(validate_registry(self.registry), [])
        self.assertEqual(
            self.registry["tools"]["ffmpeg"]["version_source"],
            "https://snapshot.debian.org/archive/debian/20260829T120000Z/",
        )

    def test_unknown_overlap_is_rejected(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["tools"]["opentofu"]["overlap"] = ["does-not-exist"]
        errors = validate_registry(registry)
        self.assertTrue(any("references unknown tools" in error for error in errors))

    def test_unknown_status_is_rejected(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["tools"]["sysdig"]["status"] = "maybe"
        errors = validate_registry(registry)
        self.assertTrue(any("status is not recognized" in error for error in errors))

    def test_registry_order_is_deterministic(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["tools"] = dict(reversed(list(registry["tools"].items())))
        errors = validate_registry(registry)
        self.assertTrue(any("sorted by identifier" in error for error in errors))

    def test_report_is_sorted_and_filterable(self) -> None:
        report = render_report(self.registry, "accepted")
        self.assertIn("Realm Tool Evaluation Registry — accepted", report)
        self.assertIn("| node | accepted |", report)
        self.assertIn("| rustup | accepted |", report)
        self.assertNotIn("| sysdig | deferred |", report)
        self.assertLess(report.index("| node |"), report.index("| rustup |"))


if __name__ == "__main__":
    unittest.main()
