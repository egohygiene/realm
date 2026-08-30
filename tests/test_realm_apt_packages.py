"""Conformance tests for Realm's deterministic apt package contracts."""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from realm_apt_packages import (  # noqa: E402
    ARCHITECTURES,
    ContractError,
    _apt_options,
    _initialize_resolver_root,
    _read_inrelease_hashes,
    _resolver_environment,
    _safe_keyring_cache_directory,
    base_package_intent,
    build_lock,
    classify_package_changes,
    cross_architecture_version_differences,
    load_json,
    load_profiles,
    lock_checksum,
    object_checksum,
    repository_records,
    validate_configuration,
    validate_dockerfile,
    validate_lock,
    validate_oci_index,
    verify_resolver_keyring,
)


class RealmAptPackageTests(unittest.TestCase):
    """Verify that locks remain derived from the canonical base profile."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_json(ROOT / "catalog" / "capabilities.json")
        cls.profiles = load_profiles(ROOT / "profiles")
        cls.config = load_json(ROOT / "config" / "debian-trixie.json")

    def candidates(self, architecture: str) -> dict[str, tuple[str, str]]:
        intent, _ = base_package_intent(
            self.catalog, self.profiles, ARCHITECTURES[architecture]
        )
        return {
            entry["name"]: (
                f"1.0.0+realm.{index}",
                "all" if index % 4 == 0 else architecture,
            )
            for index, entry in enumerate(intent)
        }

    def test_repository_configuration_is_valid(self) -> None:
        self.assertEqual(validate_configuration(self.config, self.catalog), [])

    def test_dockerfile_consumes_the_immutable_canonical_inputs(self) -> None:
        self.assertEqual(validate_dockerfile(self.config, self.catalog), [])

    def test_base_package_intent_is_exact_and_owned(self) -> None:
        intent, resolved = base_package_intent(
            self.catalog, self.profiles, "linux/amd64"
        )
        self.assertEqual(len(intent), 13)
        self.assertEqual(
            [entry["name"] for entry in intent],
            [
                "ca-certificates",
                "curl",
                "file",
                "git-lfs",
                "gnupg",
                "jq",
                "openssh-client",
                "rsync",
                "tree",
                "unzip",
                "wget",
                "xz-utils",
                "zip",
            ],
        )
        self.assertEqual(resolved["capabilities"], ["realm-base", "common-cli"])
        self.assertFalse(resolved["constraints"]["privileged"])
        self.assertFalse(resolved["constraints"]["services"])

    def test_lock_serialization_and_checksum_are_deterministic(self) -> None:
        first = build_lock(
            self.config,
            self.catalog,
            self.profiles,
            "amd64",
            self.candidates("amd64"),
        )
        second = build_lock(
            self.config,
            self.catalog,
            self.profiles,
            "amd64",
            dict(reversed(list(self.candidates("amd64").items()))),
        )
        self.assertEqual(first, second)
        self.assertEqual(first["lock_checksum"], lock_checksum(first))
        self.assertEqual(first["catalog_checksum"], object_checksum(self.catalog))
        self.assertEqual(
            first["configuration_checksum"], object_checksum(self.config)
        )
        self.assertEqual(
            first["profile_checksum"], object_checksum(self.profiles["base"])
        )
        self.assertEqual(
            validate_lock(
                first, self.config, self.catalog, self.profiles, "amd64"
            ),
            [],
        )

    def test_lock_checksum_detects_content_changes(self) -> None:
        lock = build_lock(
            self.config,
            self.catalog,
            self.profiles,
            "amd64",
            self.candidates("amd64"),
        )
        lock["packages"][0]["version"] = "changed"
        errors = validate_lock(
            lock, self.config, self.catalog, self.profiles, "amd64"
        )
        self.assertIn("lock checksum does not match lock content", errors)

    def test_required_package_unavailability_is_rejected(self) -> None:
        candidates = self.candidates("amd64")
        candidates.pop("jq")
        with self.assertRaisesRegex(ContractError, "required packages did not resolve: jq"):
            build_lock(
                self.config,
                self.catalog,
                self.profiles,
                "amd64",
                candidates,
            )

    def test_foreign_candidate_architecture_is_rejected(self) -> None:
        candidates = self.candidates("amd64")
        version, _ = candidates["jq"]
        candidates["jq"] = (version, "arm64")
        with self.assertRaisesRegex(ContractError, "not amd64"):
            build_lock(
                self.config,
                self.catalog,
                self.profiles,
                "amd64",
                candidates,
            )

    def test_duplicate_capability_ownership_is_rejected(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["capabilities"]["common-cli"]["packages"]["apt"].append(
            "ca-certificates"
        )
        with self.assertRaisesRegex(ContractError, "selected by both"):
            base_package_intent(catalog, self.profiles, "linux/amd64")

    def test_snapshot_and_source_pin_mismatch_is_rejected(self) -> None:
        config = copy.deepcopy(self.config)
        config["snapshot"] = "20260830T000000Z"
        errors = validate_configuration(config, self.catalog)
        self.assertIn(
            "Debian archive source pin and configured snapshot disagree", errors
        )

    def test_malformed_repository_returns_errors_instead_of_raising(self) -> None:
        config = copy.deepcopy(self.config)
        config["repositories"]["archive"]["suites"] = None
        errors = validate_configuration(config, self.catalog)
        self.assertIn("archive.suites must be a non-empty array", errors)
        self.assertIn(
            "repository archive must pin every suite InRelease hash", errors
        )

    def test_signed_metadata_hashes_are_bound_to_each_suite(self) -> None:
        repositories = repository_records(self.config, self.catalog)
        with tempfile.TemporaryDirectory() as temporary:
            lists_directory = Path(temporary)
            expected: dict[str, dict[str, str]] = {}
            for repository in repositories:
                expected[repository["name"]] = {}
                for suite in repository["suites"]:
                    content = f"signed metadata for {suite}\n".encode("utf-8")
                    (lists_directory / f"realm_dists_{suite}_InRelease").write_bytes(
                        content
                    )
                    expected[repository["name"]][suite] = hashlib.sha256(
                        content
                    ).hexdigest()
            self.assertEqual(
                _read_inrelease_hashes(lists_directory, repositories), expected
            )

    def test_keyring_cache_rejects_broad_output_directories(self) -> None:
        with self.assertRaisesRegex(ContractError, "keyring output must be below"):
            _safe_keyring_cache_directory(Path("/"))

    def test_resolver_rechecks_the_extracted_keyring(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            keyring = Path(temporary) / "keyring.pgp"
            keyring.write_bytes(b"tampered")
            with self.assertRaisesRegex(ContractError, "keyring checksum mismatch"):
                verify_resolver_keyring(self.config, keyring)

    def test_resolver_bootstrap_replaces_host_apt_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _initialize_resolver_root(root)
            with mock.patch.dict(
                os.environ,
                {"APT_CONFIG": "/host/apt.conf", "UNRELATED_HOST_VALUE": "unsafe"},
                clear=True,
            ):
                environment = _resolver_environment(root)
            self.assertEqual(environment["APT_CONFIG"], str(root / "bootstrap.conf"))
            self.assertNotIn("UNRELATED_HOST_VALUE", environment)
            self.assertIn(
                f'Dir::Etc::parts "{root / "apt.conf.d"}";',
                (root / "resolver.conf").read_text(encoding="utf-8"),
            )
            sources = root / "sources.list"
            sources.write_text("", encoding="utf-8")
            result = subprocess.run(
                ["apt-config", *_apt_options(root, sources, "amd64"), "dump"],
                check=True,
                capture_output=True,
                text=True,
                env=environment,
            )
            self.assertNotIn("rm -f /var/cache/apt", result.stdout)
            self.assertNotIn("DPkg::Pre-Install-Pkgs::", result.stdout)
            self.assertIn(
                f'Dir::Etc::parts "{root / "apt.conf.d"}";', result.stdout
            )

    def test_oci_index_must_contain_both_configured_platform_digests(self) -> None:
        manifests = [
            {
                "digest": record["base_image_digest"],
                "platform": {"os": "linux", "architecture": architecture},
            }
            for architecture, record in self.config["architectures"].items()
        ]
        index = {"schemaVersion": 2, "manifests": manifests}
        self.assertEqual(validate_oci_index(index, self.config), [])
        index["manifests"][0]["digest"] = "sha256:" + ("0" * 64)
        self.assertIn(
            "base-image index linux/amd64 digest differs from config",
            validate_oci_index(index, self.config),
        )

    def test_installer_rejects_a_self_checksummed_out_of_profile_package(self) -> None:
        lock = load_json(
            ROOT
            / "images"
            / "base"
            / "packages"
            / "locks"
            / "debian-trixie-amd64.lock.json"
        )
        lock["packages"].append(
            {
                "name": "unexpected-package",
                "version": "1.0",
                "architecture": "amd64",
                "capability": "common-cli",
                "required": True,
            }
        )
        lock["packages"].sort(key=lambda package: package["name"])
        lock["lock_checksum"] = lock_checksum(lock)
        with tempfile.TemporaryDirectory() as temporary:
            tampered_lock = Path(temporary) / "tampered.lock.json"
            tampered_lock.write_text(json.dumps(lock), encoding="utf-8")
            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    'source "$1"; verify_lock_projection "$2" "$3" "$4" "$5"',
                    "realm-test",
                    str(ROOT / "images" / "base" / "scripts" / "install-apt-packages"),
                    str(tampered_lock),
                    str(ROOT / "catalog" / "capabilities.json"),
                    str(ROOT / "config" / "debian-trixie.json"),
                    str(ROOT / "profiles" / "base.profile.json"),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("canonical base projection", result.stderr)

    def test_refresh_classifies_upgrades_downgrades_and_architecture_drift(
        self,
    ) -> None:
        current = {
            "packages": [
                {"name": "added-later", "version": "1.0"},
                {"name": "downgrade", "version": "2:1.0-1"},
                {"name": "removed-later", "version": "1.0"},
                {"name": "upgrade", "version": "1.0~rc1-1"},
            ],
            "aliases": [],
            "transitional_packages": [],
            "unavailable_packages": [],
        }
        candidate = {
            "packages": [
                {"name": "added-later", "version": "1.0"},
                {"name": "downgrade", "version": "1:9.0-1"},
                {"name": "new-package", "version": "1.0"},
                {"name": "upgrade", "version": "1.0-1"},
            ],
            "aliases": [],
            "transitional_packages": [],
            "unavailable_packages": [],
        }
        changes = classify_package_changes(current, candidate)
        self.assertEqual(changes["added"], ["new-package"])
        self.assertEqual(changes["removed"], ["removed-later"])
        self.assertEqual([entry["name"] for entry in changes["upgrades"]], ["upgrade"])
        self.assertEqual(
            [entry["name"] for entry in changes["downgrades"]], ["downgrade"]
        )

        arm_candidate = copy.deepcopy(candidate)
        arm_candidate["packages"][0]["version"] = "1.1"
        differences = cross_architecture_version_differences(
            {"amd64": candidate, "arm64": arm_candidate}
        )
        self.assertEqual(
            differences,
            [
                {
                    "name": "added-later",
                    "versions": {"amd64": "1.0", "arm64": "1.1"},
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
