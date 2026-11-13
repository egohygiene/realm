"""Cloud networking preserves TLS trust and keeps runtime settings private."""

from __future__ import annotations

import json
import os
import shlex
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from realm_act_network import CA_TARGET, CloudNetworkError, cloud_network_args


class ActCloudNetworkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.config = self.root / "docker.json"
        self.ca = self.root / "public CA.pem"
        self.ca.write_text("-----BEGIN CERTIFICATE-----\ntest-fixture\n")
        self.settings = {
            "auths": {"registry.example": {"auth": "must-not-project"}},
            "proxies": {
                "default": {
                    "httpProxy": "http://proxy.example:8080",
                    "httpsProxy": "http://proxy.example:8080",
                    "noProxy": "localhost,127.0.0.1",
                }
            },
        }
        self.config.write_text(json.dumps(self.settings))

    def test_proxy_projection_is_private_readonly_and_removed(self) -> None:
        with cloud_network_args(self.root, self.config, self.ca) as args:
            env_path = Path(args[1])
            self.assertEqual(stat.S_IMODE(env_path.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(env_path.parent.stat().st_mode), 0o700)
            content = env_path.read_text()
            self.assertIn("HTTPS_PROXY='http://proxy.example:8080'", content)
            self.assertIn("https_proxy='http://proxy.example:8080'", content)
            self.assertIn(f"GIT_SSL_CAINFO='{CA_TARGET}'", content)
            self.assertIn("NODE_USE_ENV_PROXY='1'", content)
            self.assertNotIn("must-not-project", content)
            self.assertNotIn("auths", content)
            mount = shlex.split(args[3])
            self.assertEqual(mount[0], "--mount")
            self.assertIn(f"source={self.ca}", mount[1])
            self.assertTrue(mount[1].endswith(",readonly"))
        self.assertFalse(env_path.exists())
        self.assertFalse(env_path.parent.exists())

    def test_failed_workflow_still_removes_runtime_proxy_file(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "workflow failed"):
            with cloud_network_args(self.root, self.config, self.ca) as args:
                env_path = Path(args[1])
                raise RuntimeError("workflow failed")
        self.assertFalse(env_path.exists())

    def test_ambient_secrets_and_outer_proxy_are_not_projected(self) -> None:
        with patch.dict(
            os.environ,
            {"HTTP_PROXY": "http://outer-only.example", "GITHUB_TOKEN": "not-exported"},
        ):
            with cloud_network_args(self.root, self.config, self.ca) as args:
                content = Path(args[1]).read_text()
                self.assertNotIn("outer-only.example", content)
                self.assertNotIn("not-exported", content)
                self.assertNotIn("GITHUB_TOKEN", content)

    def test_invalid_configuration_is_actionable_without_values(self) -> None:
        for invalid in ("not JSON", "[]", "{}", '{"proxies":{"default":[]}}'):
            with self.subTest(invalid=invalid):
                self.config.write_text(invalid)
                with self.assertRaises(CloudNetworkError):
                    with cloud_network_args(self.root, self.config, self.ca):
                        self.fail("invalid proxy configuration was accepted")

    def test_missing_ca_and_non_pem_files_are_rejected(self) -> None:
        for content in (None, "this is not a certificate"):
            with self.subTest(content=content):
                if content is None:
                    self.ca.unlink(missing_ok=True)
                else:
                    self.ca.write_text(content)
                with self.assertRaisesRegex(CloudNetworkError, "PEM CA bundle"):
                    with cloud_network_args(self.root, self.config, self.ca):
                        self.fail("invalid CA was accepted")

    def test_unsafe_proxy_values_do_not_leak_into_error_messages(self) -> None:
        for value in (
            "http://private.example\nGITHUB_TOKEN=secret",
            "socks5://secret",
            "http://user:bad'quote@proxy.example:8080",
        ):
            with self.subTest(value=value):
                self.settings["proxies"]["default"]["httpsProxy"] = value
                self.config.write_text(json.dumps(self.settings))
                with self.assertRaises(CloudNetworkError) as raised:
                    with cloud_network_args(self.root, self.config, self.ca):
                        self.fail("unsafe proxy was accepted")
                self.assertNotIn(value, str(raised.exception))


if __name__ == "__main__":
    unittest.main()
