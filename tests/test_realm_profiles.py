"""Conformance tests for Realm profile resolution."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from realm_profiles import (  # noqa: E402
    immutable_source,
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

    def invalid_resolution_cases(
        self,
    ) -> list[tuple[str, dict[str, Any], dict[str, dict[str, Any]], str]]:
        """Build isolated inputs whose existing validator returns actionable errors."""
        cases = []
        for name, field, value, diagnostic in (
            ("self-cycle", "extends", ["base"], "profile inheritance cycle: base -> base"),
            (
                "multi-profile-cycle",
                "extends",
                ["rust"],
                "profile inheritance cycle: base -> rust -> base",
            ),
            ("invalid-extends", "extends", None, "profile base.extends must be an array"),
            ("invalid-include", "include", None, "profile base.include must be an array"),
        ):
            profiles = copy.deepcopy(self.profiles)
            profiles["base"][field] = value
            cases.append((name, self.catalog, profiles, diagnostic))

        profiles = copy.deepcopy(self.profiles)
        del profiles["base"]["extends"]
        cases.append(
            ("missing-extends", self.catalog, profiles, "profile base.extends must be an array")
        )
        catalog = copy.deepcopy(self.catalog)
        catalog["capabilities"]["realm-base"]["requires"] = None
        cases.append(
            ("invalid-requires", catalog, self.profiles, "realm-base.requires must be an array")
        )
        return cases

    def run_resolution_cli(
        self,
        fixture_root: Path,
        catalog: dict[str, Any],
        profiles: dict[str, dict[str, Any]],
        output_path: Path,
    ) -> subprocess.CompletedProcess[str]:
        """Invoke the real CLI against temporary contract files with a deadline."""
        catalog_path = fixture_root / "catalog.json"
        catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
        profiles_directory = fixture_root / "profiles"
        profiles_directory.mkdir()
        for name, profile in profiles.items():
            (profiles_directory / f"{name}.profile.json").write_text(
                json.dumps(profile), encoding="utf-8"
            )
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "realm_profiles.py"),
                "--catalog",
                str(catalog_path),
                "--profiles",
                str(profiles_directory),
                "resolve",
                "--profile",
                "base",
                "--platform",
                "linux/amd64",
                "--projection",
                "docker",
                "--output",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

    def test_resolver_rejects_invalid_structures_before_traversal(self) -> None:
        for name, catalog, profiles, diagnostic in self.invalid_resolution_cases():
            with self.subTest(case=name):
                validation_errors = validate_profiles(catalog, profiles)
                self.assertIn(diagnostic, validation_errors)
                resolved, errors = resolve_profile(
                    catalog, profiles, "base", "linux/amd64", "docker"
                )
                self.assertIsNone(resolved)
                self.assertEqual(errors, validation_errors)

    def test_cli_rejects_invalid_structures_without_partial_output(self) -> None:
        for name, catalog, profiles, diagnostic in self.invalid_resolution_cases():
            with self.subTest(case=name), tempfile.TemporaryDirectory() as directory:
                fixture_root = Path(directory)
                output_path = fixture_root / "output" / "resolved.json"
                result = self.run_resolution_cli(fixture_root, catalog, profiles, output_path)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertIn(f"contract validation failed: {diagnostic}", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertNotIn("RecursionError", result.stderr)
                self.assertLess(len(result.stderr), 2048)
                self.assertFalse(output_path.exists())
                self.assertFalse(output_path.parent.exists())

    def test_cli_preserves_existing_output_when_resolution_is_invalid(self) -> None:
        profiles = copy.deepcopy(self.profiles)
        profiles["base"]["extends"] = ["base"]
        with tempfile.TemporaryDirectory() as directory:
            fixture_root = Path(directory)
            output_path = fixture_root / "resolved.json"
            output_path.write_text("existing manifest\n", encoding="utf-8")
            result = self.run_resolution_cli(fixture_root, self.catalog, profiles, output_path)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(output_path.read_text(encoding="utf-8"), "existing manifest\n")

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

    def test_debian_archive_and_security_snapshots_are_immutable(self) -> None:
        self.assertTrue(
            immutable_source(
                "https://snapshot.debian.org/archive/debian/20260827T120000Z/"
            )
        )
        self.assertTrue(
            immutable_source(
                "https://snapshot.debian.org/archive/"
                "debian-security/20260827T120000Z/"
            )
        )
        self.assertFalse(
            immutable_source("https://snapshot.debian.org/archive/debian/latest/")
        )

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
