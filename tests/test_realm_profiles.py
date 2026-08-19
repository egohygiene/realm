"""Conformance tests for Realm profile resolution."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from realm_profiles import (  # noqa: E402
    load_json,
    load_profiles,
    resolve_profile,
    validate_catalog,
    validate_profiles,
)


class RealmProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_json(ROOT / "catalog" / "capabilities.json")
        cls.profiles = load_profiles(ROOT / "profiles")

    def resolve(
        self,
        profile: str = "full",
        projection: str = "docker",
        platform: str = "linux/amd64",
    ):
        return resolve_profile(self.catalog, self.profiles, profile, platform, projection)

    def test_catalog_and_profiles_are_valid(self) -> None:
        self.assertEqual(validate_catalog(self.catalog), [])
        self.assertEqual(validate_profiles(self.catalog, self.profiles), [])

    def test_full_is_deterministic_and_dependency_ordered(self) -> None:
        first, first_errors = self.resolve()
        second, second_errors = self.resolve()
        self.assertEqual(first_errors, second_errors)
        self.assertEqual(
            json.dumps(first, sort_keys=True, separators=(",", ":")),
            json.dumps(second, sort_keys=True, separators=(",", ":")),
        )
        self.assertLess(
            first["capabilities"].index("build-toolchain"),
            first["capabilities"].index("rust-toolchain"),
        )

    def test_full_contains_mantle_but_no_services_or_privilege(self) -> None:
        resolved, errors = self.resolve()
        self.assertEqual(errors, [])
        self.assertIn("mantle-shell", resolved["capabilities"])
        self.assertNotIn("container-host", resolved["capabilities"])
        self.assertEqual(
            resolved["constraints"],
            {"privileged": False, "services": False, "secrets": "forbidden"},
        )

    def test_language_profile_inherits_base(self) -> None:
        resolved, errors = self.resolve(profile="rust", projection="devcontainer")
        self.assertEqual(errors, [])
        self.assertEqual(resolved["lineage"], ["base", "rust"])
        self.assertIn("realm-base", resolved["capabilities"])
        self.assertIn("rust-toolchain", resolved["capabilities"])

    def test_services_are_explicit_and_not_a_docker_projection(self) -> None:
        resolved, errors = self.resolve(profile="services", projection="docker")
        self.assertIsNone(resolved)
        self.assertTrue(any("does not support projection" in error for error in errors))
        resolved, errors = self.resolve(profile="services", projection="workstation")
        self.assertEqual(errors, [])
        self.assertTrue(resolved["constraints"]["services"])
        self.assertTrue(resolved["constraints"]["privileged"])

    def test_profile_cycle_is_rejected(self) -> None:
        profiles = copy.deepcopy(self.profiles)
        profiles["base"]["extends"] = ["full"]
        errors = validate_profiles(self.catalog, profiles)
        self.assertTrue(any("profile inheritance cycle" in error for error in errors))

    def test_capability_cycle_is_rejected(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["capabilities"]["realm-base"]["requires"] = ["common-cli"]
        errors = validate_catalog(catalog)
        self.assertTrue(any("capability dependency cycle" in error for error in errors))

    def test_excluded_dependency_is_rejected(self) -> None:
        profiles = copy.deepcopy(self.profiles)
        profiles["rust"]["exclude"] = ["build-toolchain"]
        resolved, errors = resolve_profile(
            self.catalog, profiles, "rust", "linux/amd64", "docker"
        )
        self.assertIsNone(resolved)
        self.assertTrue(any("is required" in error for error in errors))

    def test_mutable_artifact_source_is_rejected(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["capabilities"]["mantle-shell"]["artifacts"][0]["source"] = (
            "https://github.com/egohygiene/mantle@main"
        )
        errors = validate_catalog(catalog)
        self.assertTrue(any("immutable source" in error for error in errors))

    def test_selected_capability_conflict_is_rejected(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["capabilities"]["mantle-shell"]["conflicts"] = ["media-toolchain"]
        resolved, errors = resolve_profile(
            catalog, self.profiles, "full", "linux/amd64", "docker"
        )
        self.assertIsNone(resolved)
        self.assertTrue(any("conflicts with" in error for error in errors))

    def test_secret_bearing_fields_are_rejected(self) -> None:
        profiles = copy.deepcopy(self.profiles)
        profiles["base"]["parameters"] = {"api_token": "do-not-store-this"}
        errors = validate_profiles(self.catalog, profiles)
        self.assertTrue(any("secret-bearing field" in error for error in errors))

    def test_unknown_platform_is_rejected(self) -> None:
        resolved, errors = self.resolve(platform="darwin/arm64")
        self.assertIsNone(resolved)
        self.assertTrue(any("unknown platform" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
