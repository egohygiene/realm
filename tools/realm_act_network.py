"""Opt-in, ephemeral proxy and CA arguments for act in managed cloud workspaces."""

from __future__ import annotations

import json
import os
import shlex
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit

CA_TARGET = "/run/realm-act-ca.pem"
CA_VARIABLES = (
    "CURL_CA_BUNDLE",
    "GIT_SSL_CAINFO",
    "SSL_CERT_FILE",
    "REQUESTS_CA_BUNDLE",
    "PIP_CERT",
    "NODE_EXTRA_CA_CERTS",
)


class CloudNetworkError(ValueError):
    """The selected cloud proxy/CA configuration cannot be used safely."""


def _proxy_environment(config_path: Path) -> dict[str, str]:
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        defaults = config["proxies"]["default"]
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
        raise CloudNetworkError(
            "Cloud networking needs readable Docker config proxies.default settings; "
            "configure the managed Docker proxy or run without --cloud-network."
        ) from error
    if not isinstance(defaults, dict):
        raise CloudNetworkError("Docker proxies.default must be an object.")
    result: dict[str, str] = {}
    for source, destination in (
        ("httpProxy", "HTTP_PROXY"),
        ("httpsProxy", "HTTPS_PROXY"),
        ("noProxy", "NO_PROXY"),
    ):
        value = defaults.get(source, "" if source == "noProxy" else None)
        if (
            not isinstance(value, str)
            or len(value) > 65536
            or any(character in value for character in "\r\n\0'")
        ):
            raise CloudNetworkError(f"Docker default {source} is missing or invalid.")
        if source != "noProxy":
            try:
                parsed = urlsplit(value)
                valid = parsed.scheme in ("http", "https") and bool(parsed.hostname)
                parsed.port
            except ValueError:
                valid = False
            if not valid:
                raise CloudNetworkError(
                    f"Docker default {source} must be an HTTP(S) proxy URL."
                )
        result[destination] = value
        result[destination.lower()] = value
    result.update(dict.fromkeys(CA_VARIABLES, CA_TARGET))
    result["NODE_USE_ENV_PROXY"] = "1"
    return result


@contextmanager
def cloud_network_args(
    directory: Path,
    docker_config_path: Path | None = None,
    ca_path: Path | None = None,
) -> Iterator[list[str]]:
    """Yield CLI arguments only after an explicit cloud-network opt-in.

    The caller supplies an ignored run-output directory or external scratch,
    never a tracked checkout path. Only Docker's reachable container proxy
    defaults are projected; registry credentials and ambient host variables
    are excluded. The CA stays read-only on the host and is not copied into an
    image. Temporary proxy settings are removed even when act fails.
    """
    config_path = docker_config_path or (
        Path(os.environ.get("DOCKER_CONFIG", str(Path.home() / ".docker")))
        / "config.json"
    )
    environment = _proxy_environment(config_path)
    ca = (ca_path or Path("/etc/ssl/certs/ca-certificates.crt")).absolute()
    if any(character in str(ca) for character in ",\r\n\0"):
        raise CloudNetworkError("The cloud CA path cannot contain commas or newlines.")
    try:
        if not ca.is_file() or b"-----BEGIN CERTIFICATE-----" not in ca.read_bytes():
            raise CloudNetworkError("Cloud networking needs a readable PEM CA bundle.")
    except OSError as error:
        raise CloudNetworkError(
            "Cloud networking needs a readable PEM CA bundle."
        ) from error
    if not directory.is_dir():
        raise CloudNetworkError("The cloud-network run-output directory must exist.")
    with tempfile.TemporaryDirectory(prefix=".realm-act-network-", dir=directory) as root:
        temporary = Path(root)
        env_path = temporary / "proxy.env"
        descriptor = os.open(env_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            for name, value in environment.items():
                # Single quotes suppress godotenv's $VARIABLE expansion. Literal
                # single quotes and line breaks were rejected before file creation.
                handle.write(f"{name}='{value}'\n")
        mount = f"type=bind,source={ca},target={CA_TARGET},readonly"
        yield [
            "--env-file",
            str(env_path),
            "--container-options",
            f"--mount {shlex.quote(mount)}",
        ]
