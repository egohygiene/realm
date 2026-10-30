"""Behavioral checks for the bounded, generated Realm base Dev Container."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from realm_profiles import load_json, load_profiles, resolve_profile


class RealmDevcontainerTests(unittest.TestCase):
    """A generated configuration must retain the selected canonical intent."""

    def run_cli(
        self, command: str, output: Path, *extra: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "realm_devcontainer.py"),
                command,
                "--output",
                str(output),
                *extra,
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )

    def test_generated_bundle_matches_same_resolved_manifest(self) -> None:
        catalog = load_json(ROOT / "catalog" / "capabilities.json")
        profiles = load_profiles(ROOT / "profiles")
        with tempfile.TemporaryDirectory() as temporary:
            for architecture in ("amd64", "arm64"):
                with self.subTest(architecture=architecture):
                    output = Path(temporary) / architecture
                    result = self.run_cli(
                        "render", output, "--platform", f"linux/{architecture}"
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    resolved, errors = resolve_profile(
                        catalog,
                        profiles,
                        "base",
                        f"linux/{architecture}",
                        "devcontainer",
                    )
                    self.assertEqual(errors, [])
                    self.assertEqual(
                        json.loads((output / "resolved-profile.v1.json").read_text()),
                        resolved,
                    )
                    self.assertEqual(
                        (output / "images/base/Dockerfile").read_bytes(),
                        (ROOT / "images/base/Dockerfile").read_bytes(),
                    )
                    config = json.loads(
                        (output / ".devcontainer/devcontainer.json").read_text()
                    )
                    self.assertEqual(
                        config["build"]["options"], [f"--platform=linux/{architecture}"]
                    )
                    self.assertEqual(config["remoteUser"], "vscode")
                    self.assertFalse(config["updateRemoteUserUID"])
                    self.assertNotIn("features", config)
                    self.assertNotIn("initializeCommand", config)
                    self.assertNotIn("mounts", config)
                    self.assertNotIn("runArgs", config)
                    config_root = output / ".devcontainer"
                    self.assertEqual(
                        (config_root / config["build"]["context"]).resolve(),
                        output.resolve(),
                    )
                    self.assertEqual(
                        (config_root / config["build"]["dockerfile"]).resolve(),
                        (output / "images/base/Dockerfile").resolve(),
                    )

    def test_independent_output_locations_have_identical_bytes_and_modes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            first, second = Path(temporary) / "one", Path(temporary) / "two"
            for output in (first, second):
                result = self.run_cli("render", output)
                self.assertEqual(result.returncode, 0, result.stderr)
            files = sorted(
                path.relative_to(first) for path in first.rglob("*") if path.is_file()
            )
            self.assertEqual(
                files,
                sorted(
                    path.relative_to(second)
                    for path in second.rglob("*")
                    if path.is_file()
                ),
            )
            for name in files:
                self.assertEqual(
                    (first / name).read_bytes(), (second / name).read_bytes(), str(name)
                )
                self.assertEqual(
                    (first / name).stat().st_mode,
                    (second / name).stat().st_mode,
                    str(name),
                )
            manifest = json.loads((first / "projection.v1.json").read_text())
            self.assertEqual(manifest["status"], "generated-source")
            self.assertFalse(manifest["published"])
            self.assertNotIn(temporary, (first / "projection.v1.json").read_text())
            for item in manifest["files"]:
                target = first / item["path"]
                self.assertEqual(
                    hashlib.sha256(target.read_bytes()).hexdigest(), item["sha256"]
                )
                self.assertEqual(f"{target.stat().st_mode & 0o777:04o}", item["mode"])

    def test_check_detects_damage_missing_extra_and_mode_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "bundle"
            self.assertEqual(self.run_cli("render", output).returncode, 0)
            self.assertEqual(self.run_cli("check", output).returncode, 0)
            script = output / "images/base/scripts/realm-packages"
            script.chmod(0o644)
            self.assertNotEqual(self.run_cli("check", output).returncode, 0)
            script.chmod(0o755)
            self.assertEqual(self.run_cli("check", output).returncode, 0)
            target = output / ".devcontainer/devcontainer.json"
            target.write_text('{"image":"unreviewed:latest"}\n')
            before = target.read_bytes()
            damaged = self.run_cli("check", output)
            self.assertNotEqual(damaged.returncode, 0)
            self.assertIn("different", damaged.stderr)
            self.assertEqual(target.read_bytes(), before)
            target.unlink()
            self.assertNotEqual(self.run_cli("check", output).returncode, 0)
            (output / "unexpected.txt").write_text(
                "consumer content must not be hidden"
            )
            self.assertIn("unexpected", self.run_cli("check", output).stderr)

    def test_existing_output_and_parent_symlinks_are_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            output = parent / "authored"
            output.mkdir()
            sentinel = output / "keep.txt"
            sentinel.write_text("keep")
            self.assertNotEqual(self.run_cli("render", output).returncode, 0)
            self.assertEqual(list(output.iterdir()), [sentinel])
            link = parent / "link"
            link.symlink_to(output, target_is_directory=True)
            for destination in (link, link / "new"):
                self.assertNotEqual(self.run_cli("render", destination).returncode, 0)
            self.assertEqual(sentinel.read_text(), "keep")
            self.assertFalse((output / "new").exists())

    def test_unsupported_profiles_or_platforms_do_not_emit_partial_intent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "bundle"
            for extra in (
                ("--profile", "full"),
                ("--profile", "python"),
                ("--profile", "services"),
                ("--profile", "unknown"),
                ("--platform", "linux/riscv64"),
            ):
                with self.subTest(extra=extra):
                    result = self.run_cli("render", output, *extra)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("unsupported", result.stderr.lower())
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertFalse(output.exists())

    def source_copy(self, temporary: str) -> Path:
        source = Path(temporary) / "source"
        source.mkdir()
        for directory in (
            "catalog",
            "config",
            "profiles",
            "images/base",
            "tools",
            "schemas",
        ):
            shutil.copytree(ROOT / directory, source / directory, dirs_exist_ok=True)
        shutil.copy2(ROOT / "LICENSE", source / "LICENSE")
        return source

    def test_stale_lock_or_malformed_source_is_controlled_before_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = self.source_copy(temporary)
            output = Path(temporary) / "bundle"
            lock_path = (
                source / "images/base/packages/locks/debian-trixie-amd64.lock.json"
            )
            lock = json.loads(lock_path.read_text())
            lock["packages"][0]["version"] = "0:unreviewed"
            lock_path.write_text(json.dumps(lock))
            result = self.run_cli("render", output, "--source-root", str(source))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("lock", result.stderr.lower())
            self.assertFalse(output.exists())
            catalog_path = source / "catalog/capabilities.json"
            catalog_path.write_text('{"schema_version":null}')
            result = self.run_cli("render", output, "--source-root", str(source))
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("Traceback", result.stderr)
            self.assertFalse(output.exists())

    def test_source_symlink_and_output_symlink_are_never_followed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = self.source_copy(temporary)
            path = source / "images/base/scripts/realm-packages"
            path.unlink()
            path.symlink_to(ROOT / "images/base/scripts/realm-packages")
            output = Path(temporary) / "bundle"
            result = self.run_cli("render", output, "--source-root", str(source))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symlink", result.stderr)
            self.assertFalse(output.exists())
            self.assertEqual(self.run_cli("render", output).returncode, 0)
            target = output / ".devcontainer/devcontainer.json"
            target.unlink()
            target.symlink_to(
                ROOT
                / "tests/fixtures/devcontainer/reference/.devcontainer/devcontainer.json"
            )
            self.assertNotEqual(self.run_cli("check", output).returncode, 0)

    def test_checked_in_generated_examples_are_current(self) -> None:
        for architecture in ("amd64", "arm64"):
            result = self.run_cli(
                "check",
                ROOT / "dist/devcontainers" / f"base-linux-{architecture}",
                "--platform",
                f"linux/{architecture}",
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_duplicate_nonfinite_oversized_and_special_inputs_reject(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = self.source_copy(temporary)
            output = Path(temporary) / "bundle"
            catalog = source / "catalog/capabilities.json"
            original = catalog.read_bytes()
            for content in (
                b'{"schema_version":"1.0.0","schema_version":"1.0.0"}',
                b'{"schema_version":NaN}',
                b" " * (1024 * 1024 + 1),
            ):
                with self.subTest(content_length=len(content)):
                    catalog.write_bytes(content)
                    result = self.run_cli(
                        "render", output, "--source-root", str(source)
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertFalse(output.exists())
            catalog.write_bytes(original)
            script = source / "images/base/scripts/realm-packages"
            script.unlink()
            os.mkfifo(script)
            result = self.run_cli("render", output, "--source-root", str(source))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("regular file", result.stderr)
            self.assertFalse(output.exists())

    def test_non_emitted_profile_graph_has_an_aggregate_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = self.source_copy(temporary)
            base = json.loads((source / "profiles/base.profile.json").read_text())
            for number in range(14):
                profile = dict(base, name=f"extra-{number}", description="x" * 600_000)
                (source / "profiles" / f"extra-{number}.profile.json").write_text(
                    json.dumps(profile)
                )
                if number == 2:
                    result = self.run_cli(
                        "render",
                        Path(temporary) / "within-budget",
                        "--source-root",
                        str(source),
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
            output = Path(temporary) / "over-budget"
            result = self.run_cli("render", output, "--source-root", str(source))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("aggregate", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertFalse(output.exists())

    def test_source_entries_and_output_inventory_are_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = self.source_copy(temporary)
            for number in range(129):
                (source / "profiles" / f"ignored-{number}.txt").write_text("unused")
            output = Path(temporary) / "source-overflow"
            result = self.run_cli("render", output, "--source-root", str(source))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("entry budget", result.stderr)
            self.assertFalse(output.exists())
            output = Path(temporary) / "bundle"
            self.assertEqual(self.run_cli("render", output).returncode, 0)
            for number in range(65):
                (output / f"unexpected-{number}.txt").write_text("keep")
            result = self.run_cli("check", output)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("inventory budget", result.stderr)
            self.assertTrue(
                all(
                    (output / f"unexpected-{number}.txt").read_text() == "keep"
                    for number in range(65)
                )
            )

    def test_limited_runtime_receipt_is_bound_to_generated_source(self) -> None:
        proof = json.loads(
            (ROOT / "docs/evidence/devcontainer-generated-base.v1.json").read_text()
        )
        bundle = ROOT / "dist/devcontainers/base-linux-amd64"
        manifest = json.loads((bundle / "projection.v1.json").read_text())
        paths = {
            "generator_sha256": ROOT / "tools/realm_devcontainer.py",
            "bundle_manifest_sha256": bundle / "projection.v1.json",
            "generated_configuration_sha256": bundle
            / ".devcontainer/devcontainer.json",
            "resolved_manifest_sha256": bundle / "resolved-profile.v1.json",
            "recipe_sha256": bundle / "images/base/Dockerfile",
            "selected_lock_sha256": bundle
            / "images/base/packages/locks/debian-trixie-amd64.lock.json",
            "official_schema_sha256": ROOT
            / "vendor/devcontainers/devContainer.base.schema.json",
        }
        for field, path in paths.items():
            self.assertEqual(
                proof["source"][field],
                hashlib.sha256(path.read_bytes()).hexdigest(),
                field,
            )
        self.assertEqual(
            proof["source"]["source_identity"], manifest["source_identity"]
        )
        self.assertEqual(proof["state"], "limited")
        self.assertEqual(proof["scope"], "generated-base/local-linux-amd64")
        self.assertFalse(proof["tools"]["docker"]["published"])
        self.assertFalse(
            proof["qualification_overlay"]["installed_base_capability_claim"]
        )
        self.assertFalse(
            proof["qualification_overlay"]["mantle"]["released_integration"]
        )
        self.assertNotEqual(
            proof["consumer_overlay"]["configuration_sha256"],
            proof["source"]["generated_configuration_sha256"],
        )
        self.assertTrue(
            {
                "arm64-runtime",
                "features",
                "nix-adapter",
                "workstation-adapter",
                "released-mantle",
                "vscode",
                "codespaces",
                "registry-publication",
            }.issubset(proof["unproven"])
        )
        self.assertEqual(manifest["status"], "generated-source")
        self.assertFalse(manifest["published"])

    def test_clean_private_umask_keeps_git_executable_roles(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "bundle"
            self.assertEqual(self.run_cli("render", output).returncode, 0)
            for path in output.rglob("*"):
                if path.is_file():
                    path.chmod(0o700 if path.stat().st_mode & 0o100 else 0o600)
            self.assertEqual(self.run_cli("check", output).returncode, 0)
            script = output / "images/base/scripts/realm-packages"
            script.chmod(0o611)
            self.assertNotEqual(self.run_cli("check", output).returncode, 0)
            script.chmod(0o700)
            config = output / ".devcontainer/devcontainer.json"
            config.chmod(0o611)
            self.assertEqual(self.run_cli("check", output).returncode, 0)
            config.chmod(0o700)
            self.assertNotEqual(self.run_cli("check", output).returncode, 0)


if __name__ == "__main__":
    unittest.main()
