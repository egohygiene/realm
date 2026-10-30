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
            with self.subTest(image=image), self.assertRaises(ValueError):
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


class PortableEvidenceTests(unittest.TestCase):
    """Synthetic payloads prove local guards, never actual scanner/image execution."""

    def fixture(self, directory):
        tool = module()
        image = "sha256:" + "a" * 64
        manifest = "sha256:" + "c" * 64
        revision = "b" * 40
        observed = "2026-10-30T12:00:00Z"
        lock = json.loads(
            (
                ROOT / "images/base/packages/locks/debian-trixie-amd64.lock.json"
            ).read_text()
        )
        metadata = {
            "schema_version": "1.0.0",
            "build_revision": revision,
            "lock_checksum": lock["lock_checksum"],
            "snapshot": lock["snapshot"],
            "security_snapshot": lock["security_snapshot"],
            "base_image_digest": lock["base_image"]["digest"],
            "base_platform_digest": lock["base_image"]["platform_digest"],
        }
        identity = {
            "local_config_digest": image,
            "platform": "linux/amd64",
            "source_revision": revision,
            "execution": "native",
        }
        target = {
            "imageID": image,
            "manifestDigest": manifest,
            "os": "linux",
            "architecture": "amd64",
        }
        packages = [
            {"id": f"package-{n}", "name": p["name"], "version": p["version"]}
            for n, p in enumerate(lock["packages"])
        ]
        syft = {
            "source": {"type": "image", "metadata": target.copy()},
            "descriptor": {"name": "syft", "version": "1.55.0"},
            "artifacts": packages,
        }
        spdx = {
            "spdxVersion": "SPDX-2.3",
            "creationInfo": {"creators": ["Tool: syft-1.55.0"]},
            "packages": [
                {
                    "name": "sha256",
                    "SPDXID": "SPDXRef-root",
                    "primaryPackagePurpose": "CONTAINER",
                    "versionInfo": image[7:],
                    "checksums": [
                        {"algorithm": "SHA256", "checksumValue": manifest[7:]}
                    ],
                },
                *[
                    {
                        "name": p["name"],
                        "SPDXID": "SPDXRef-" + p["id"],
                        "versionInfo": p["version"],
                    }
                    for p in packages
                ],
            ],
        }
        match = {
            "vulnerability": {"id": "SYNTHETIC-1", "severity": "High"},
            "artifact": packages[0].copy(),
        }
        grype = {
            "source": {"type": "image", "target": target.copy()},
            "descriptor": {
                "name": "grype",
                "version": "0.121.0",
                "db": {
                    "status": {
                        "schemaVersion": "v6.1.10",
                        "from": "https://grype.anchore.io/databases/v6/example.tar.zst?checksum=sha256%3A"
                        + "d" * 64,
                        "built": "2026-10-30T00:00:00Z",
                        "valid": True,
                    }
                },
            },
            "matches": [match],
            "ignoredMatches": [json.loads(json.dumps(match))],
        }
        verification = {
            name: {"status": "passed", "exit_code": 0}
            for name in ("installed_lock", "nonroot_smoke")
        }
        for name, value in (
            ("identity.json", identity),
            ("syft.json", syft),
            ("sbom.spdx.json", spdx),
            ("vulnerabilities.grype.json", grype),
            ("apt-lock.json", lock),
            ("build-metadata.json", metadata),
            ("verification.json", verification),
        ):
            (directory / name).write_bytes(tool.encode(value))
        rows = [
            "name\tlocked_version\tinstalled_version\tarchitecture\tcapability\tsnapshot\tsecurity_snapshot\tbase_image_digest\tbase_platform_digest\tbuild_revision\tlock_checksum"
        ]
        for p in lock["packages"]:
            rows.append(
                "\t".join(
                    (
                        p["name"],
                        p["version"],
                        p["version"],
                        p["architecture"],
                        p["capability"],
                        lock["snapshot"],
                        lock["security_snapshot"],
                        lock["base_image"]["digest"],
                        lock["base_image"]["platform_digest"],
                        revision,
                        lock["lock_checksum"],
                    )
                )
            )
        (directory / "apt-installed.tsv").write_text("\n".join(rows) + "\n")
        artifacts = {}
        for key, (name, fmt) in tool.ARTIFACTS.items():
            data = (directory / name).read_bytes()
            artifacts[key] = {
                "path": name,
                "sha256": tool.digest(data),
                "bytes": len(data),
                "format": fmt,
                "raw_sha256": None,
            }
        tools = {}
        for name, pin in tool.tool_pins()["tools"].items():
            tools[name] = {
                "version": pin["version"],
                "source_revision": pin["source_revision"],
                "archive_sha256": pin["linux/amd64"]["archive_sha256"],
                "executable_sha256": pin["linux/amd64"]["executable_sha256"],
                "signature_verification": "not-performed",
            }
        input_paths = tool.INPUTS + (
            "images/base/packages/locks/debian-trixie-amd64.lock.json",
        )
        receipt = {
            "schema_version": "1.0.0",
            "contract": "realm.image-evidence/v1",
            "state": "limited",
            "release_ready": False,
            "observed_at": observed,
            "source": {
                "repository": "egohygiene/realm",
                "revision": revision,
                "inputs": {
                    name: tool.digest((ROOT / name).read_bytes())
                    for name in input_paths
                },
            },
            "producer": {
                "name": "realm-image-evidence",
                "version": "1.0.0",
                "sha256": tool.digest(
                    (ROOT / "tools/realm_image_evidence.py").read_bytes()
                ),
            },
            "tools": tools,
            **tool.summaries(directory, revision, observed, "e" * 64),
            "artifacts": artifacts,
            "authentication": {
                name: "not-performed"
                for name in ("image_signatures", "provenance", "registry_publication")
            },
            "limitations": tool.LIMITATIONS.copy(),
        }
        (directory / "image-evidence.json").write_bytes(tool.encode(receipt))
        return tool, receipt

    def rewrite(self, directory, name, change):
        tool = module()
        value = json.loads((directory / name).read_text())
        change(value)
        data = tool.encode(value)
        (directory / name).write_bytes(data)
        receipt = json.loads((directory / "image-evidence.json").read_text())
        key = next(key for key, item in tool.ARTIFACTS.items() if item[0] == name)
        receipt["artifacts"][key]["sha256"] = tool.digest(data)
        receipt["artifacts"][key]["bytes"] = len(data)
        (directory / "image-evidence.json").write_bytes(tool.encode(receipt))

    def test_complete_local_bundle_preserves_findings_and_cannot_be_a_release(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            tool, receipt = self.fixture(directory)
            self.assertEqual(tool.validate_receipt(receipt), [])
            result = tool.verify_evidence(directory)
            self.assertEqual(result["vulnerabilities"]["matches"], 1)
            self.assertEqual(result["vulnerabilities"]["ignored_matches"], 1)
            self.assertEqual(result["vulnerabilities"]["severity_counts"]["High"], 1)
            self.assertFalse(result["release_ready"])
            self.assertTrue(
                all(v == "not-performed" for v in result["authentication"].values())
            )

    def test_registry_identity_and_boolean_claims_cannot_be_promoted(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            tool, receipt = self.fixture(directory)
            for fields, value in (
                (("subject", "registry_manifest_digest"), "sha256:" + "a" * 64),
                (("release_ready",), True),
                (("verification", "installed_lock", "exit_code"), False),
                (("authentication", "image_signatures"), "verified"),
            ):
                with self.subTest(fields=fields):
                    damaged = json.loads(json.dumps(receipt))
                    target = damaged
                    for field in fields[:-1]:
                        target = target[field]
                    target[fields[-1]] = value
                    self.assertTrue(tool.validate_receipt(damaged))

    def test_rehashed_cross_subject_and_version_inputs_are_rejected(self):
        cases = [
            (
                "syft.json",
                lambda x: x["source"]["metadata"].__setitem__(
                    "imageID", "sha256:" + "f" * 64
                ),
            ),
            (
                "vulnerabilities.grype.json",
                lambda x: x["source"]["target"].__setitem__("architecture", "arm64"),
            ),
            (
                "vulnerabilities.grype.json",
                lambda x: x["descriptor"].__setitem__("version", "0.0.0"),
            ),
            (
                "sbom.spdx.json",
                lambda x: x["packages"][0].__setitem__("versionInfo", "f" * 64),
            ),
        ]
        for name, change in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                directory = Path(temp)
                tool, _ = self.fixture(directory)
                self.rewrite(directory, name, change)
                with self.assertRaises(ValueError):
                    tool.verify_evidence(directory)

    def test_stale_future_and_invalid_database_results_are_rejected(self):
        for field, value in (
            ("built", "2020-01-01T00:00:00Z"),
            ("built", "2026-10-31T00:00:00Z"),
            ("valid", False),
            ("from", "https://example.invalid/latest"),
        ):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp:
                directory = Path(temp)
                tool, _ = self.fixture(directory)
                self.rewrite(
                    directory,
                    "vulnerabilities.grype.json",
                    lambda x, field=field, value=value: x["descriptor"]["db"][
                        "status"
                    ].__setitem__(field, value),
                )
                with self.assertRaises(ValueError):
                    tool.verify_evidence(directory)

    def test_malformed_nested_matches_return_controlled_errors(self):
        for replacement in (
            None,
            [],
            {"vulnerability": None},
            {
                "vulnerability": {"id": "x", "severity": "Clean"},
                "artifact": {"id": "package-0"},
            },
        ):
            with (
                self.subTest(replacement=replacement),
                tempfile.TemporaryDirectory() as temp,
            ):
                directory = Path(temp)
                tool, _ = self.fixture(directory)
                self.rewrite(
                    directory,
                    "vulnerabilities.grype.json",
                    lambda x, replacement=replacement: x.__setitem__(
                        "matches", [replacement]
                    ),
                )
                with self.assertRaises(ValueError):
                    tool.verify_evidence(directory)
                result = subprocess.run(
                    [
                        "python3",
                        str(ROOT / "tools/realm_image_evidence.py"),
                        "verify",
                        "--directory",
                        str(directory),
                    ],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(
                    json.loads(result.stdout)["status"], "invalid-or-unavailable"
                )
                self.assertNotIn("Traceback", result.stderr)

    def test_corrupt_missing_symlink_and_oversized_artifacts_are_rejected(self):
        for mode in ("corrupt", "missing", "symlink", "oversize"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                directory = Path(temp)
                tool, _ = self.fixture(directory)
                path = directory / "syft.json"
                if mode == "corrupt":
                    path.write_text("{}")
                elif mode == "missing":
                    path.unlink()
                elif mode == "symlink":
                    original = path.read_bytes()
                    path.unlink()
                    target = directory / "synthetic-target"
                    target.write_bytes(original)
                    path.symlink_to(target)
                else:
                    with path.open("wb") as stream:
                        stream.truncate(tool.MAX_BYTES + 1)
                with self.assertRaises(ValueError):
                    tool.verify_evidence(directory)

    def test_duplicate_nonfinite_and_deep_json_are_rejected(self):
        tool = module()
        for data in (
            b'{"x":1,"x":2}',
            b'{"x":NaN}',
            b'{"x":1e400}',
            b"[" * 5000 + b"]" * 5000,
        ):
            with self.subTest(data=data[:20]), self.assertRaises(ValueError):
                tool.decode(data)

    def test_publication_refuses_an_existing_destination_without_replacement(self):
        tool = module()
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            source = parent / "source"
            source.mkdir()
            (source / "new").write_text("new")
            target = parent / "target"
            target.mkdir()
            (target / "old").write_text("old")
            with self.assertRaisesRegex(ValueError, "already exists"):
                tool.publish_directory(source, target)
            self.assertEqual((target / "old").read_text(), "old")
            self.assertEqual((source / "new").read_text(), "new")

    def test_scanner_runtime_configuration_is_removed_without_dropping_findings(self):
        tool = module()
        raw = {
            "descriptor": {
                "name": "grype",
                "version": "0.121.0",
                "configuration": {"db": "/synthetic-private-cache"},
                "timestamp": "2026-10-30T12:00:00Z",
                "db": {
                    "status": {
                        "schemaVersion": "v6.1.10",
                        "from": "https://grype.anchore.io/example",
                        "built": "2026-10-30T00:00:00Z",
                        "valid": True,
                        "path": "/synthetic-private-cache",
                    }
                },
            },
            "source": {
                "target": {
                    "imageID": "sha256:" + "a" * 64,
                    "config": "SYNTHETIC-IMAGE-CONFIG",
                    "labels": {},
                    "manifest": "SYNTHETIC-MANIFEST",
                }
            },
            "matches": [{"kept": 1}],
            "ignoredMatches": [{"kept": 2}],
        }
        safe = tool.sanitized_tool_document(raw, "grype")
        self.assertEqual(safe["matches"], raw["matches"])
        self.assertEqual(safe["ignoredMatches"], raw["ignoredMatches"])
        self.assertNotIn("synthetic-private-cache", json.dumps(safe))
        self.assertNotIn("SYNTHETIC-IMAGE-CONFIG", json.dumps(safe))

    def test_existing_output_is_rejected_before_any_tool_execution(self):
        import argparse
        from unittest import mock

        tool = module()
        with (
            tempfile.TemporaryDirectory() as temp,
            mock.patch.object(tool, "run") as run,
        ):
            args = argparse.Namespace(
                image="sha256:" + "a" * 64, source_revision="b" * 40, output=Path(temp)
            )
            with self.assertRaisesRegex(ValueError, "output already exists"):
                tool.collect(args)
            run.assert_not_called()

    def test_same_count_spdx_and_same_id_grype_package_contradictions_reject(self):
        cases = [
            (
                "sbom.spdx.json",
                lambda x: x["packages"][1].__setitem__(
                    "versionInfo", "SYNTHETIC-WRONG"
                ),
            ),
            (
                "sbom.spdx.json",
                lambda x: x["packages"][1].__setitem__(
                    "SPDXID", x["packages"][0]["SPDXID"]
                ),
            ),
            (
                "vulnerabilities.grype.json",
                lambda x: x["matches"][0]["artifact"].__setitem__(
                    "name", "SYNTHETIC-WRONG"
                ),
            ),
        ]
        for name, change in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                directory = Path(temp)
                tool, _ = self.fixture(directory)
                self.rewrite(directory, name, change)
                with self.assertRaises(ValueError):
                    tool.verify_evidence(directory)

    def test_source_lock_checksum_and_tool_pins_are_checkable_claims(self):
        for path in (
            (
                "source",
                "inputs",
                "images/base/packages/locks/debian-trixie-amd64.lock.json",
            ),
            ("tools", "syft", "executable_sha256"),
        ):
            with self.subTest(path=path), tempfile.TemporaryDirectory() as temp:
                directory = Path(temp)
                tool, receipt = self.fixture(directory)
                target = receipt
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = "f" * 64
                (directory / "image-evidence.json").write_bytes(tool.encode(receipt))
                with self.assertRaises(ValueError):
                    tool.verify_evidence(directory)

    def test_pin_tools_collection_must_be_an_object(self):
        from unittest import mock

        tool = module()
        for value in (None, ["syft", "grype"], 1, True):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as temp:
                pins = json.loads(
                    (ROOT / "config/image-evidence-tools.v1.json").read_text()
                )
                pins["tools"] = value
                path = Path(temp) / "pins.json"
                path.write_text(json.dumps(pins))
                with (
                    mock.patch.object(tool, "PINS", path),
                    self.assertRaises(ValueError),
                ):
                    tool.tool_pins()

    def test_publication_is_atomic_and_preserves_an_empty_racing_directory(self):
        tool = module()
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            source = parent / "source"
            source.mkdir()
            (source / "new").write_text("new")
            target = parent / "target"
            target.mkdir()
            inode = target.stat().st_ino
            with self.assertRaisesRegex(ValueError, "already exists"):
                tool.publish_directory(source, target)
            self.assertEqual(target.stat().st_ino, inode)
            self.assertEqual(list(target.iterdir()), [])
            target.rmdir()
            tool.publish_directory(source, target)
            self.assertFalse(source.exists())
            self.assertEqual((target / "new").read_text(), "new")

    def test_verify_and_plan_never_execute_image_tools(self):
        from unittest import mock

        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            tool, receipt = self.fixture(directory)
            with mock.patch.object(
                tool, "run", side_effect=AssertionError("unexpected tool execution")
            ):
                self.assertEqual(tool.verify_evidence(directory), receipt)
                self.assertEqual(
                    tool.build_plan("sha256:" + "a" * 64, "b" * 40)["status"], "planned"
                )

    def test_tool_deadline_stops_an_owned_descendant_holding_pipes(self):
        import os
        import sys
        import time

        tool = module()
        with tempfile.TemporaryDirectory() as temp:
            marker = Path(temp) / "must-not-be-written"
            child = (
                "import time; from pathlib import Path; time.sleep(0.4); Path("
                + repr(str(marker))
                + ").write_text('unexpected')"
            )
            parent = (
                "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',"
                + repr(child)
                + "]); time.sleep(10)"
            )
            with self.assertRaisesRegex(ValueError, "deadline"):
                tool.run([sys.executable, "-c", parent], dict(os.environ), timeout=0.1)
            time.sleep(0.5)
            self.assertFalse(marker.exists())

    def test_execution_deadline_starts_after_create_and_removes_only_owned_id(self):
        from unittest import mock

        tool = module()
        state = {"started": False, "removed": False}

        def fake_run(argv, _env, timeout=300):
            operation = argv[1:3]
            if operation == ["container", "create"]:
                state["name"] = argv[argv.index("--name") + 1]
                state["label"] = argv[argv.index("--label") + 1]
                self.assertEqual(timeout, 120)
                return ("d" * 64 + "\n").encode()
            if operation == ["container", "inspect"]:
                if state["removed"]:
                    raise ValueError("synthetic absent container")
                key, token = state["label"].split("=", 1)
                return tool.encode(
                    {
                        "Id": "d" * 64,
                        "Name": "/" + state["name"],
                        "Image": "sha256:" + "a" * 64,
                        "Config": {"Labels": {key: token}},
                        "State": {
                            "Status": "running" if state["started"] else "created",
                            "ExitCode": 0,
                        },
                    }
                )
            if operation == ["container", "start"]:
                self.assertEqual(argv[-1], "d" * 64)
                self.assertEqual(timeout, 0.1)
                state["started"] = True
                raise ValueError("synthetic execution deadline")
            if operation == ["container", "rm"]:
                self.assertEqual(argv[-1], "d" * 64)
                state["removed"] = True
                return b""
            self.assertEqual(operation, ["container", "ls"])
            return b""

        with (
            mock.patch.object(tool, "run", side_effect=fake_run),
            self.assertRaisesRegex(ValueError, "synthetic execution deadline"),
        ):
            tool.run_container(
                ["docker"],
                ["--network", "none"],
                "sha256:" + "a" * 64,
                [],
                {},
                timeout=0.1,
            )
        self.assertTrue(state["started"] and state["removed"])

    def test_container_cleanup_refuses_unproved_ownership(self):
        from unittest import mock

        tool = module()
        for config in (None, {"Labels": None}, {"Labels": {"wrong": "label"}}):
            calls = []

            def fake_run(argv, _env, _timeout=300, config=config, calls=calls):
                calls.append(argv)
                if argv[1:3] == ["container", "create"]:
                    return ("d" * 64).encode()
                if argv[1:3] == ["container", "inspect"]:
                    name = calls[0][calls[0].index("--name") + 1]
                    return tool.encode(
                        {
                            "Id": "d" * 64,
                            "Name": "/" + name,
                            "Image": "sha256:" + "a" * 64,
                            "Config": config,
                        }
                    )
                self.fail("unproved container must not be started or removed")

            with (
                self.subTest(config=config),
                mock.patch.object(tool, "run", side_effect=fake_run),
                self.assertRaisesRegex(ValueError, "ownership"),
            ):
                tool.run_container(["docker"], [], "sha256:" + "a" * 64, [], {})
            self.assertFalse(any(call[1:3] == ["container", "rm"] for call in calls))

    def test_container_exit_status_is_checked_separately_from_client_success(self):
        from unittest import mock

        tool = module()
        for status in (0, 23, False):
            state = {"started": False, "removed": False}

            def fake_run(argv, _env, _timeout=300, status=status, state=state):
                operation = argv[1:3]
                if operation == ["container", "create"]:
                    state["name"] = argv[argv.index("--name") + 1]
                    state["label"] = argv[argv.index("--label") + 1]
                    return ("d" * 64).encode()
                if operation == ["container", "inspect"]:
                    if state["removed"]:
                        raise ValueError("synthetic absent container")
                    key, token = state["label"].split("=", 1)
                    return tool.encode(
                        {
                            "Id": "d" * 64,
                            "Name": "/" + state["name"],
                            "Image": "sha256:" + "a" * 64,
                            "Config": {"Labels": {key: token}},
                            "State": {
                                "Status": "exited" if state["started"] else "created",
                                "ExitCode": status,
                            },
                        }
                    )
                if operation == ["container", "start"]:
                    state["started"] = True
                    return b"synthetic stdout"
                if operation == ["container", "rm"]:
                    state["removed"] = True
                    return b""
                self.assertEqual(operation, ["container", "ls"])
                return b""

            with (
                self.subTest(status=status),
                mock.patch.object(tool, "run", side_effect=fake_run),
            ):
                if type(status) is int and status == 0:
                    self.assertEqual(
                        tool.run_container(
                            ["docker"], [], "sha256:" + "a" * 64, [], {}
                        ),
                        b"synthetic stdout",
                    )
                else:
                    with self.assertRaisesRegex(ValueError, "exit"):
                        tool.run_container(["docker"], [], "sha256:" + "a" * 64, [], {})
            self.assertTrue(state["removed"])

    def test_indeterminate_create_is_non_success_with_owned_name_recovery(self):
        from unittest import mock

        tool = module()

        def fake_run(argv, _env, _timeout=300):
            if argv[1:3] == ["container", "create"]:
                raise ValueError("synthetic creation timeout")
            if argv[1:3] == ["container", "inspect"]:
                raise ValueError("synthetic not observed yet")
            self.assertEqual(argv[1:3], ["container", "ls"])
            return b""

        with (
            mock.patch.object(tool, "run", side_effect=fake_run),
            self.assertRaisesRegex(
                ValueError, "not observed.*recovery name: realm-evidence-"
            ),
        ):
            tool.run_container(
                ["docker"], [], "sha256:" + "a" * 64, [], {}, late_poll_seconds=0
            )

    def test_late_created_container_is_owned_cleaned_and_still_non_success(self):
        from unittest import mock

        tool = module()
        state = {"removed": False}

        def fake_run(argv, _env, _timeout=300):
            operation = argv[1:3]
            if operation == ["container", "create"]:
                state["name"] = argv[argv.index("--name") + 1]
                state["label"] = argv[argv.index("--label") + 1]
                raise ValueError("synthetic creation timeout")
            if operation == ["container", "inspect"]:
                if state["removed"]:
                    raise ValueError("synthetic absent container")
                key, token = state["label"].split("=", 1)
                return tool.encode(
                    {
                        "Id": "d" * 64,
                        "Name": "/" + state["name"],
                        "Image": "sha256:" + "a" * 64,
                        "Config": {"Labels": {key: token}},
                    }
                )
            if operation == ["container", "rm"]:
                self.assertEqual(argv[-1], "d" * 64)
                state["removed"] = True
                return b""
            self.assertEqual(operation, ["container", "ls"])
            return b""

        with (
            mock.patch.object(tool, "run", side_effect=fake_run),
            self.assertRaisesRegex(
                ValueError, "late owned container removed.*recovery name"
            ),
        ):
            tool.run_container(
                ["docker"], [], "sha256:" + "a" * 64, [], {}, late_poll_seconds=0
            )
        self.assertTrue(state["removed"])

    def test_committed_capture_observation_binds_reviewed_source_and_producer(self):
        tool = module()
        receipt = json.loads(
            (ROOT / "docs/evidence/image-local-capture.v1.json").read_text()
        )
        self.assertEqual(tool.validate_receipt(receipt), [])
        self.assertEqual(
            receipt["producer"]["sha256"],
            tool.digest((ROOT / "tools/realm_image_evidence.py").read_bytes()),
        )
        for name, checksum in receipt["source"]["inputs"].items():
            with self.subTest(source=name):
                self.assertEqual(tool.digest((ROOT / name).read_bytes()), checksum)
        # This checks the committed observation's freshness. Full artifact
        # verification is separately exercised on the actual portable bundle.


if __name__ == "__main__":
    unittest.main()
