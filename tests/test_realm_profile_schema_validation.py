"""Schema-derived negative fixtures for dependency-free profile validation."""
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Iterator
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


DELETE = object()


def schema_nodes(
    schema: dict[str, Any], document: Any, root: dict[str, Any], path: tuple = ()
) -> Iterator[tuple[tuple, dict[str, Any], Any]]:
    """Walk representative actual values according to the published schema."""
    if "$ref" in schema:
        resolved = root
        for part in schema["$ref"].removeprefix("#/").split("/"):
            resolved = resolved[part]
        yield from schema_nodes(resolved, document, root, path)
        return
    yield path, schema, document
    if schema.get("type") == "object":
        for name, child in schema.get("properties", {}).items():
            if name in document:
                yield from schema_nodes(child, document[name], root, path + (name,))
        additional = schema.get("additionalProperties")
        if isinstance(additional, dict) and document:
            name = "mantle-shell" if "mantle-shell" in document else next(iter(document))
            yield from schema_nodes(additional, document[name], root, path + (name,))
    elif schema.get("type") == "array" and document:
        yield from schema_nodes(schema["items"], document[0], root, path + (0,))


def malformed_values(schema: dict[str, Any], document: Any) -> Iterator[tuple[str, Any]]:
    """Produce violations from schema keywords rather than validator constants."""
    expected = schema.get("type")
    types = {"object": dict, "array": list, "string": str, "boolean": bool}
    if expected:
        for value in (None, 0, 1, "false", [], {}):
            if not isinstance(value, types[expected]):
                yield "wrong-type", value
    if "const" in schema:
        yield "wrong-constant", "unexpected-constant"
    if "enum" in schema:
        yield "unsupported-enum", "unsupported-kind"
    if "pattern" in schema:
        yield "wrong-pattern", "invalid value"
    if schema.get("minLength"):
        yield "empty-string", ""
    if schema.get("minProperties"):
        yield "empty-object", {}
    if expected == "array" and schema.get("uniqueItems"):
        yield "duplicates", ["duplicate", "duplicate"]
        for value in (None, {}, [], 0, ""):
            yield "invalid-array-item", [value]


def schema_mutations(
    schema: dict[str, Any], document: dict[str, Any]
) -> Iterator[tuple[str, Any]]:
    """Mutate every required field and representative nested schema surface."""
    for path, node, value in schema_nodes(schema, document, schema):
        replacements = [
            (path, reason, replacement)
            for reason, replacement in malformed_values(node, value)
        ]
        if node.get("type") == "object":
            replacements.extend(
                (path + (name,), "missing-required", DELETE)
                for name in node.get("required", [])
            )
            if node.get("additionalProperties") is False:
                replacements.append(
                    (path + ("unexpected_field",), "unknown-field", "unexpected")
                )
        for target, reason, replacement in replacements:
            result = copy.deepcopy(document)
            if not target:
                result = replacement
            else:
                parent = result
                for part in target[:-1]:
                    parent = parent[part]
                if replacement is DELETE:
                    del parent[target[-1]]
                else:
                    parent[target[-1]] = replacement
            description = "<missing>" if replacement is DELETE else repr(replacement)
            label = f"{'.'.join(map(str, target)) or '<root>'}: {reason} {description}"
            yield label, result


class RealmProfileSchemaValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_json(ROOT / "catalog/capabilities.json")
        cls.profiles = load_profiles(ROOT / "profiles")
        cls.catalog_schema = load_json(ROOT / "schemas/capability-catalog.v1.schema.json")
        cls.profile_schema = load_json(ROOT / "schemas/profile.v1.schema.json")

    def assert_diagnostics(self, errors: list[str]) -> None:
        self.assertTrue(errors)
        self.assertTrue(all(isinstance(error, str) and error for error in errors))
        self.assertLess(len("\n".join(errors)), 8192)

    def test_catalog_schema_mutations_return_errors_before_resolution(self) -> None:
        for label, catalog in schema_mutations(self.catalog_schema, self.catalog):
            with self.subTest(case=label):
                self.assert_diagnostics(validate_catalog(catalog))
                self.assert_diagnostics(validate_profiles(catalog, self.profiles))
                manifest, errors = resolve_profile(
                    catalog, self.profiles, "base", "linux/amd64", "docker"
                )
                self.assertIsNone(manifest)
                self.assert_diagnostics(errors)

    def test_profile_schema_mutations_return_errors_before_resolution(self) -> None:
        for label, profile in schema_mutations(self.profile_schema, self.profiles["base"]):
            with self.subTest(case=label):
                profiles = {"base": profile}
                self.assert_diagnostics(validate_profiles(self.catalog, profiles))
                manifest, errors = resolve_profile(
                    self.catalog, profiles, "base", "linux/amd64", "docker"
                )
                self.assertIsNone(manifest)
                self.assert_diagnostics(errors)

    def test_profile_map_and_entries_reject_nonobjects(self) -> None:
        for value in (None, 0, "invalid", [], ["base"]):
            with self.subTest(value=value):
                self.assert_diagnostics(validate_profiles(self.catalog, value))
                manifest, errors = resolve_profile(
                    self.catalog, value, "base", "linux/amd64", "docker"
                )
                self.assertIsNone(manifest)
                self.assert_diagnostics(errors)

    def test_profile_name_pattern_is_checked_even_when_dictionary_key_matches(self) -> None:
        for name in ("Base", "1base", "base_name", "base.name", "base/name"):
            with self.subTest(name=name):
                profile = copy.deepcopy(self.profiles["base"])
                profile["name"] = name
                self.assert_diagnostics(validate_profiles(self.catalog, {name: profile}))

    def test_real_booleans_are_accepted_without_coercion(self) -> None:
        for value in (False, True):
            with self.subTest(value=value):
                catalog = copy.deepcopy(self.catalog)
                profiles = {"base": copy.deepcopy(self.profiles["base"])}
                for name in ("privileged", "services"):
                    catalog["capabilities"]["mantle-shell"]["constraints"][name] = value
                for name in ("allow_privileged", "allow_services"):
                    profiles["base"]["constraints"][name] = value
                self.assertEqual(validate_catalog(catalog), [])
                self.assertEqual(validate_profiles(catalog, profiles), [])

    def test_schema_permitted_values_are_not_overrestricted(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        profile = copy.deepcopy(self.profiles["base"])
        catalog["source_pins"]["Unrestricted map/key"] = next(
            iter(catalog["source_pins"].values())
        )
        capability = copy.deepcopy(catalog["capabilities"]["realm-base"])
        capability["requires"] = []
        capability["conflicts"] = []
        catalog["capabilities"]["Unrestricted capability/key"] = capability
        profile["description"] = " "
        profile["include"] = ["Unrestricted capability/key"]
        self.assertEqual(validate_profiles(catalog, {"base": profile}), [])
        self.assertEqual(validate_profiles(self.catalog, self.profiles), [])

    def run_cli(
        self, catalog: Any, profiles: dict[str, Any], command: str
    ) -> tuple[subprocess.CompletedProcess[str], bool, bool]:
        """Run an actual CLI command against disposable JSON contract files."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog_path = root / "catalog.json"
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
            profiles_path = root / "profiles"
            profiles_path.mkdir()
            for name, profile in profiles.items():
                (profiles_path / f"{name}.profile.json").write_text(
                    json.dumps(profile), encoding="utf-8"
                )
            output = root / "output" / "manifest.json"
            arguments = [
                sys.executable,
                str(ROOT / "tools/realm_profiles.py"),
                "--catalog",
                str(catalog_path),
                "--profiles",
                str(profiles_path),
                command,
            ]
            if command == "resolve":
                arguments.extend(
                    [
                        "--profile", "base",
                        "--platform", "linux/amd64",
                        "--projection", "docker",
                        "--output", str(output),
                    ]
                )
            result = subprocess.run(
                arguments, capture_output=True, text=True, timeout=5, check=False
            )
            return result, output.exists(), output.parent.exists()

    def test_cli_validation_and_resolution_reject_malformed_fixtures(self) -> None:
        cases = []
        for name, path, value in (
            ("kind", ("capabilities", "realm-base", "kind"), "unsupported"),
            ("boolean", ("capabilities", "realm-base", "constraints", "privileged"), "false"),
            ("capabilities-object", ("capabilities",), None),
            ("packages-object", ("capabilities", "realm-base", "packages"), []),
            ("artifact-field", ("capabilities", "mantle-shell", "artifacts", 0, "version"), None),
        ):
            catalog = copy.deepcopy(self.catalog)
            parent = catalog
            for part in path[:-1]:
                parent = parent[part]
            parent[path[-1]] = value
            cases.append(
                (name, catalog, self.profiles, ("validate-catalog", "validate-profiles", "resolve"))
            )
        profiles = copy.deepcopy(self.profiles)
        profiles["base"]["constraints"]["allow_privileged"] = "false"
        cases.append(("profile-boolean", self.catalog, profiles, ("validate-profiles", "resolve")))
        for name, catalog, profiles, commands in cases:
            for command in commands:
                with self.subTest(case=name, command=command):
                    result, output_exists, parent_exists = self.run_cli(
                        catalog, profiles, command
                    )
                    diagnostics = result.stderr
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("failed", diagnostics)
                    self.assertNotIn("Traceback", diagnostics)
                    self.assertLess(len(diagnostics), 8192)
                    self.assertFalse(output_exists)
                    self.assertFalse(parent_exists)


if __name__ == "__main__":
    unittest.main()
