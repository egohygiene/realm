"""Conformance tests for Realm's generated profile release declarations."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from realm_profile_publications import (  # noqa: E402
    build_profile_publication,
    check_publications,
    load_inputs,
    publication_files,
    validate_profile_publications,
    write_publications,
)


class RealmProfilePublicationTests(unittest.TestCase):
    """Ensure stable-tool policy and published profile artifacts cannot drift."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.profiles, cls.registry = load_inputs(
            ROOT / "catalog" / "capabilities.json",
            ROOT / "profiles",
            ROOT / "catalog" / "tool-evaluations.json",
        )

    def test_repository_publication_contract_is_valid(self) -> None:
        self.assertEqual(
            validate_profile_publications(
                self.catalog, self.profiles, self.registry
            ),
            [],
        )

    def test_every_stable_tool_maps_to_its_profile(self) -> None:
        for tool_id, tool in self.registry["tools"].items():
            if tool["status"] != "accepted":
                continue
            with self.subTest(tool=tool_id):
                self.assertIsInstance(tool["stable_capability"], str)
                self.assertIn(tool["profile_candidate"], self.profiles)
                manifest, _ = build_profile_publication(
                    self.catalog,
                    self.profiles,
                    self.registry,
                    tool["profile_candidate"],
                )
                self.assertIn(
                    tool["stable_capability"], manifest["contents"]["capabilities"]
                )

    def test_experimental_tool_cannot_name_a_stable_capability(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["tools"]["aws-cli"]["stable_capability"] = "cloud-cli"
        errors = validate_profile_publications(self.catalog, self.profiles, registry)
        self.assertTrue(any("not accepted but names a stable capability" in error for error in errors))

    def test_unknown_stable_capability_is_rejected(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["tools"]["node"]["stable_capability"] = "does-not-exist"
        errors = validate_profile_publications(self.catalog, self.profiles, registry)
        self.assertTrue(any("names unknown capability" in error for error in errors))

    def test_full_composes_all_stable_non_service_profiles(self) -> None:
        manifest, _ = build_profile_publication(
            self.catalog, self.profiles, self.registry, "full"
        )
        self.assertTrue(
            {
                "cloud-cli",
                "flutter-toolchain",
                "git-toolchain",
                "media-toolchain",
                "node-toolchain",
                "python-toolchain",
                "rust-toolchain",
            }.issubset(manifest["contents"]["capabilities"])
        )
        self.assertNotIn("container-host", manifest["contents"]["capabilities"])
        self.assertEqual(manifest["size"]["status"], "unmeasured")

    def test_cache_key_is_stable_and_tracks_registry_changes(self) -> None:
        first, _ = build_profile_publication(
            self.catalog, self.profiles, self.registry, "full"
        )
        second, _ = build_profile_publication(
            self.catalog, self.profiles, self.registry, "full"
        )
        self.assertEqual(first["cache_key"], second["cache_key"])
        registry = copy.deepcopy(self.registry)
        registry["tools"]["node"]["maintenance"]["last_reviewed"] = "2026-09-01"
        changed, _ = build_profile_publication(
            self.catalog, self.profiles, registry, "full"
        )
        self.assertNotEqual(first["cache_key"], changed["cache_key"])

    def test_generated_sbom_checksum_and_publication_files_are_deterministic(self) -> None:
        files = publication_files(self.catalog, self.profiles, self.registry)
        self.assertIn(Path("full") / "manifest.v1.json", files)
        manifest = json.loads(files[Path("full") / "manifest.v1.json"])
        self.assertTrue(manifest["sbom"]["sha256"].startswith("sha256:"))
        self.assertEqual(check_publications(ROOT / "dist" / "profiles", files), [])
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "profiles"
            write_publications(output, files)
            self.assertEqual(check_publications(output, files), [])


if __name__ == "__main__":
    unittest.main()
