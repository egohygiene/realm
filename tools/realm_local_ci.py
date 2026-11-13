#!/usr/bin/env python3
"""Run explicitly selected local checks and act jobs; preserve incomplete coverage.

The manifest selects trusted repository code, not a sandbox or a policy engine.
No hosted workflow is dispatched. Plans do not execute repository commands.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import os
import platform
import re
import selectors
import signal
import subprocess
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA = "realm.local-ci/v1"
ACT_VERSION = "0.2.97"
MAX_LOG = 2 * 1024 * 1024
SECRET_NAME = re.compile(r"token|password|secret|credential|private.?key", re.I)
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
DIGEST_IMAGE = re.compile(r"[^\s]+@sha256:[0-9a-f]{64}\Z")


class RunCancelled(KeyboardInterrupt):
    """A termination signal must unwind process and Docker cleanup."""

    def __init__(self, signum: int):
        self.signum = signum
        super().__init__(f"cancelled by signal {signum}")


def termination_requested(signum, _frame) -> None:
    raise RunCancelled(signum)


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def bounded_path(root: Path, relative: str) -> Path:
    """Select only a real repository file; never follow a symlink out of scope."""
    if not isinstance(relative, str) or not relative:
        raise ValueError("file paths must be nonempty strings")
    parts = PurePosixPath(relative)
    if parts.is_absolute() or ".." in parts.parts or "\\" in relative:
        raise ValueError(f"unsafe repository path: {relative}")
    path = root
    for part in parts.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError(f"symlink is not a selected source file: {relative}")
    if not path.is_file() or not path.resolve().is_relative_to(root):
        raise ValueError(f"missing repository file: {relative}")
    return path


def load_manifest(repository: Path, relative: str) -> dict[str, Any]:
    path = bounded_path(repository, relative)
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("manifest exceeds 1 MiB")
    raw = path.read_bytes()
    manifest = json.loads(raw)
    if not isinstance(manifest, dict) or set(manifest) != {"schema_version", "checks"}:
        raise ValueError("manifest requires exactly schema_version and checks")
    if manifest["schema_version"] != SCHEMA:
        raise ValueError(f"unsupported manifest schema; expected {SCHEMA}")
    checks = manifest["checks"]
    if not isinstance(checks, list) or not checks:
        raise ValueError("manifest must select at least one check")
    identifiers: set[str] = set()
    executable_required = False
    common = {"id", "kind", "required", "timeout_seconds", "skip_reason"}
    for check in checks:
        if not isinstance(check, dict):
            raise ValueError("each check must be an object")
        identifier = check.get("id")
        if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier):
            raise ValueError("invalid check id")
        if identifier in identifiers:
            raise ValueError(f"duplicate check id: {identifier}")
        identifiers.add(identifier)
        if type(check.get("required")) is not bool:
            raise ValueError(f"{identifier}: required must be boolean")
        kind = check.get("kind")
        if not isinstance(kind, str):
            raise ValueError(f"{identifier}: kind must be a supported string")
        allowed = common | {
            "direct": {"command"},
            "act": {
                "workflow",
                "job",
                "event",
                "matrix",
                "inputs",
                "platforms",
                "required_secrets",
                "docker_socket",
            },
            "unsupported": {"reason"},
        }.get(kind, set())
        if kind not in {"direct", "act", "unsupported"} or set(check) - allowed:
            raise ValueError(f"{identifier}: unsupported kind or fields")
        if "skip_reason" in check and (
            not isinstance(check["skip_reason"], str) or not check["skip_reason"].strip()
        ):
            raise ValueError(f"{identifier}: skip_reason must explain the omission")
        if kind == "unsupported":
            if not isinstance(check.get("reason"), str) or not check["reason"].strip():
                raise ValueError(f"{identifier}: unsupported check needs a reason")
            continue
        timeout = check.get("timeout_seconds")
        if type(timeout) is not int or not 1 <= timeout <= 7200:
            raise ValueError(f"{identifier}: timeout_seconds must be 1..7200")
        executable_required |= check["required"] and "skip_reason" not in check
        if kind == "direct":
            command = check.get("command")
            if (
                not isinstance(command, list)
                or not command
                or any(not isinstance(arg, str) or not arg or "\x00" in arg for arg in command)
            ):
                raise ValueError(f"{identifier}: command must be a nonempty argv list")
            continue
        bounded_path(repository, check.get("workflow", ""))
        if not check["workflow"].startswith((".github/workflows/", ".github/act/")) or not check[
            "workflow"
        ].endswith((".yml", ".yaml")):
            raise ValueError(f"{identifier}: select a GitHub workflow file")
        for key in ("job", "event"):
            if not isinstance(check.get(key), str) or not IDENTIFIER.fullmatch(check[key]):
                raise ValueError(f"{identifier}: invalid {key}")
        platforms = check.get("platforms")
        if (
            not isinstance(platforms, dict)
            or not platforms
            or any(
                not isinstance(k, str)
                or not IDENTIFIER.fullmatch(k)
                or not isinstance(v, str)
                or not DIGEST_IMAGE.fullmatch(v)
                for k, v in platforms.items()
            )
        ):
            raise ValueError(
                f"{identifier}: runner mappings require immutable sha256 image digests"
            )
        matrix = check.get("matrix", [])
        if not isinstance(matrix, list) or any(
            not isinstance(value, str)
            or ":" not in value
            or not IDENTIFIER.fullmatch(value.split(":", 1)[0])
            or not value.split(":", 1)[1]
            or "\n" in value
            for value in matrix
        ):
            raise ValueError(f"{identifier}: matrix must contain key:value strings")
        inputs = check.get("inputs", {})
        if not isinstance(inputs, dict) or any(
            not isinstance(k, str)
            or not IDENTIFIER.fullmatch(k)
            or SECRET_NAME.search(k)
            or not isinstance(v, str)
            or "\n" in v
            for k, v in inputs.items()
        ):
            raise ValueError(f"{identifier}: inputs must be non-secret string values")
        secrets = check.get("required_secrets", [])
        if not isinstance(secrets, list) or any(
            not isinstance(k, str) or not IDENTIFIER.fullmatch(k) for k in secrets
        ):
            raise ValueError(f"{identifier}: required_secrets must be names only")
        if "docker_socket" in check and type(check["docker_socket"]) is not bool:
            raise ValueError(f"{identifier}: docker_socket must be boolean")
    if not executable_required:
        raise ValueError("manifest must select at least one required executable check")
    return {
        "schema_version": SCHEMA,
        "checks": checks,
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
    }


def metadata(repository: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"path": str(repository)}
    for key, arguments in (
        ("revision", ["rev-parse", "HEAD"]),
        ("status", ["status", "--porcelain", "--untracked-files=normal"]),
    ):
        completed = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        result[key] = completed.stdout.strip() if completed.returncode == 0 else None
    result["dirty"] = bool(result.pop("status")) if result["revision"] else None
    return result


def clean_environment() -> dict[str, str]:
    """Keep tool/proxy configuration but omit ambient application credentials."""
    return {key: value for key, value in os.environ.items() if not SECRET_NAME.search(key)}


def redact(text: str) -> str:
    for key, value in os.environ.items():
        if SECRET_NAME.search(key) and len(value) >= 5:
            text = text.replace(value, "[REDACTED]")
    return re.sub(r"(https?://)[^\s/@:]+:[^\s/@]+@", r"\1[REDACTED]@", text)


def execute(
    command: list[str], cwd: Path, timeout: int, environment: dict[str, str]
) -> dict[str, Any]:
    """Enforce a process-group deadline and retain at most MAX_LOG output bytes."""
    started = time.monotonic()
    try:
        child = subprocess.Popen(
            command,
            cwd=cwd,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    except OSError as error:
        return {
            "exit_code": None,
            "timed_out": False,
            "seconds": 0,
            "output": str(error),
            "unavailable": True,
        }
    output = bytearray()
    truncated = False
    timed_out = False
    selector = selectors.DefaultSelector()
    assert child.stdout is not None
    selector.register(child.stdout, selectors.EVENT_READ)
    deadline = started + timeout
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            for key, _ in selector.select(min(remaining, 0.2)):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                else:
                    room = MAX_LOG - len(output)
                    output.extend(chunk[:room])
                    truncated |= len(chunk) > room
        if timed_out:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=1)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
        try:
            child.wait(timeout=max(0.01, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()
    except BaseException:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.wait()
        raise
    finally:
        selector.close()
        child.stdout.close()
    return {
        "exit_code": child.returncode,
        "timed_out": timed_out,
        "seconds": round(time.monotonic() - started, 3),
        "output": redact(output.decode("utf-8", errors="replace"))
        + ("\n[output truncated]\n" if truncated else ""),
        "output_truncated": truncated,
        "unavailable": False,
    }


def doctor(repository: Path, act: str) -> dict[str, Any]:
    environment = clean_environment()
    version = execute([act, "--version"], repository, 15, environment)
    docker = execute(
        ["docker", "version", "--format", "{{json .Server}}"], repository, 15, environment
    )
    ready = (
        version["exit_code"] == 0
        and re.search(rf"\b{re.escape(ACT_VERSION)}\b", version["output"]) is not None
        and docker["exit_code"] == 0
    )
    server = None
    if docker["exit_code"] == 0:
        try:
            server = json.loads(docker["output"])
        except json.JSONDecodeError:
            ready = False
    return {
        "ready": ready,
        "act_required": ACT_VERSION,
        "act_version": version["output"].strip(),
        "host_platform": f"{platform.system().lower()}/{platform.machine()}",
        "docker": server,
        "docker_platform": f"{server.get('Os', 'unknown')}/{server.get('Arch', 'unknown')}"
        if isinstance(server, dict)
        else None,
        "diagnostics": []
        if ready
        else [
            f"Install act {ACT_VERSION} and connect an explicit Docker engine; inspect the act and Docker errors.",
            version["output"].strip(),
            docker["output"].strip(),
        ],
    }


def act_command(check: dict[str, Any], act: str) -> list[str]:
    arguments = [
        act,
        check["event"],
        "--workflows",
        check["workflow"],
        "--job",
        check["job"],
        "--json",
        "--rm",
        "--network",
        "bridge",
        "--container-options-policy",
        "restrict",
        "--container-daemon-socket",
        "/var/run/docker.sock" if check.get("docker_socket") else "-",
        "--no-cache-server",
        "--concurrent-jobs",
        "1",
        "--pull=false",
        "--secret-file",
        os.devnull,
        "--env-file",
        os.devnull,
        "--var-file",
        os.devnull,
        "--input-file",
        os.devnull,
    ]
    for runner, image in sorted(check["platforms"].items()):
        arguments += ["--platform", f"{runner}={image}"]
    for selection in check.get("matrix", []):
        arguments += ["--matrix", selection]
    for key, value in sorted(check.get("inputs", {}).items()):
        arguments += ["--input", f"{key}={value}"]
    return arguments


def owned_container_cleanup(repository: Path, identifier: str) -> dict[str, Any]:
    """Stop only containers reverified to carry this opaque run's exact label."""
    environment = clean_environment()
    label = f"realm.local-ci.run={identifier}"
    listing = execute(
        ["docker", "ps", "--all", "--filter", f"label={label}", "--format", "{{.ID}}"],
        repository,
        10,
        environment,
    )
    if listing["exit_code"] != 0:
        return {
            "complete": False,
            "removed": [],
            "reason": "Docker could not enumerate run-owned containers; inspect them before retrying",
        }
    removed = []
    for container in listing["output"].splitlines():
        if not re.fullmatch(r"[0-9a-f]{12,64}", container):
            return {
                "complete": False,
                "removed": removed,
                "reason": "Docker returned an invalid container identity",
            }
        observed = execute(
            [
                "docker",
                "inspect",
                "--format",
                '{{ index .Config.Labels "realm.local-ci.run" }}',
                container,
            ],
            repository,
            10,
            environment,
        )
        if observed["exit_code"] != 0 or observed["output"].strip() != identifier:
            return {
                "complete": False,
                "removed": removed,
                "reason": "Container identity/ownership changed; no unverified removal was attempted",
            }
        deletion = execute(["docker", "rm", "--force", container], repository, 15, environment)
        if deletion["exit_code"] != 0:
            return {
                "complete": False,
                "removed": removed,
                "reason": "Run-owned container removal failed; manual recovery is required",
            }
        removed.append(container)
    return {"complete": True, "removed": removed}


def invocation_options(
    command: list[str], network_arguments: list[str], identifier: str
) -> list[str]:
    """Combine the optional read-only CA mount with the exact run-ownership label."""
    arguments = list(command)
    container_options = f"--label realm.local-ci.run={identifier}"
    index = 0
    while index < len(network_arguments):
        if network_arguments[index] == "--container-options":
            container_options += " " + network_arguments[index + 1]
            index += 2
        else:
            arguments.append(network_arguments[index])
            index += 1
    return arguments + ["--container-options", container_options]


@contextmanager
def cloud_context(directory: Path, enabled: bool):
    """Load the optional adjacent cloud adapter only on explicit request."""
    if not enabled:
        yield []
        return
    source = Path(__file__).with_name("realm_act_network.py")
    specification = importlib.util.spec_from_file_location("realm_act_network", source)
    if specification is None or specification.loader is None:
        raise ValueError("cloud network adapter unavailable")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    with module.cloud_network_args(directory) as arguments:
        yield arguments


def completed_selection(text: str, check: dict[str, Any]) -> bool:
    """Require actual selected-job results, including declared matrix values."""
    matrices = []
    for line in text.splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            isinstance(record, dict)
            and record.get("jobID") == check["job"]
            and record.get("jobResult") == "success"
            and record.get("dryrun") is False
        ):
            matrices.append(record.get("matrix", {}))
    if not matrices:
        return False
    selected: dict[str, set[str]] = {}
    for value in check.get("matrix", []):
        key, option = value.split(":", 1)
        selected.setdefault(key, set()).add(option)
    if not selected:
        return True
    keys = list(selected)
    return all(
        any(
            all(str(matrix.get(key)) == value for key, value in zip(keys, combination))
            for matrix in matrices
        )
        for combination in itertools.product(*(selected[key] for key in keys))
    )


def run_repository(
    repository: Path, manifest_path: str, output: Path, act: str, cloud_network: bool = False
) -> dict[str, Any]:
    manifest = load_manifest(repository, manifest_path)
    source = metadata(repository)
    output.mkdir(parents=True, exist_ok=False)
    report: dict[str, Any] = {
        "schema_version": SCHEMA,
        "started_at": timestamp(),
        "repository": source,
        "manifest_sha256": manifest["manifest_sha256"],
        "checks": [],
        "publication": "not-performed",
        "credentials_forwarded": False,
        "cloud_network": cloud_network,
        "complete": False,
        "exit_code": 1,
    }
    write_report(output, report)
    environment = clean_environment()
    preflight = (
        doctor(repository, act)
        if any(c["kind"] == "act" and "skip_reason" not in c for c in manifest["checks"])
        else None
    )
    report["preflight"] = preflight
    with tempfile.TemporaryDirectory(prefix="realm-local-ci-") as isolated:
        act_environment = dict(environment, HOME=isolated, XDG_CONFIG_HOME=isolated)
        # An explicit Docker config directory remains usable without reading global act settings.
        if "DOCKER_CONFIG" not in act_environment:
            act_environment["DOCKER_CONFIG"] = str(Path.home() / ".docker")
        for check in manifest["checks"]:
            item = dict(check)
            item["started_at"] = timestamp()
            item.update(status="blocked", reason="Execution has not completed")
            report["checks"].append(item)
            write_report(output, report)
            if check["kind"] == "unsupported":
                item.update(status="unsupported", reason=check["reason"])
            elif "skip_reason" in check:
                item.update(status="skipped", reason=check["skip_reason"])
            elif check["kind"] == "act" and check.get("required_secrets"):
                item.update(
                    status="blocked",
                    reason="Required credentials must be supplied through a separately reviewed credential adapter; no ambient credentials are forwarded.",
                )
            elif check["kind"] == "act" and not preflight["ready"]:
                item.update(
                    status="blocked",
                    reason="act/Docker preflight unavailable; see preflight diagnostics",
                )
            else:
                command = check["command"] if check["kind"] == "direct" else act_command(check, act)
                item["command"] = command
                outcome = None
                if check["kind"] == "act":
                    run_identifier = uuid.uuid4().hex
                    item["run_identifier"] = run_identifier
                    write_report(output, report)
                    try:
                        cache = repository
                        for part in (".cache", "realm", "local-ci", "actions"):
                            cache = cache / part
                            if cache.is_symlink():
                                raise ValueError("Action cache must not traverse symlinks")
                        cache.mkdir(parents=True, exist_ok=True)
                        command += ["--action-cache-path", str(cache)]
                        with cloud_context(Path(isolated), cloud_network) as network_arguments:
                            invocation = invocation_options(
                                command, network_arguments, run_identifier
                            )
                            listing = execute(
                                invocation + ["--list"],
                                repository,
                                min(check["timeout_seconds"], 30),
                                act_environment,
                            )
                            selected = any(
                                len(parts := line.split()) >= 2
                                and parts[0].isdigit()
                                and parts[1] == check["job"]
                                for line in listing["output"].splitlines()
                            )
                            if listing["exit_code"] != 0 or not selected:
                                outcome = dict(listing, unavailable=True)
                                item["reason"] = (
                                    "Selected workflow/job/event could not be inventoried; no execution claimed"
                                )
                            else:
                                try:
                                    outcome = execute(
                                        invocation,
                                        repository,
                                        check["timeout_seconds"],
                                        act_environment,
                                    )
                                finally:
                                    item["cleanup"] = owned_container_cleanup(
                                        repository, run_identifier
                                    )
                                    write_report(output, report)
                    except (ValueError, OSError) as error:
                        outcome = {
                            "exit_code": None,
                            "timed_out": False,
                            "seconds": 0,
                            "output": redact(str(error)),
                            "unavailable": True,
                        }
                if outcome is None:
                    outcome = execute(command, repository, check["timeout_seconds"], environment)
                text = outcome.pop("output")
                log_name = f"{check['id']}.log"
                (output / log_name).write_text(text, encoding="utf-8")
                item.update(outcome, log=log_name)
                if item.get("reason") == "Execution has not completed":
                    item.pop("reason")
                if outcome["unavailable"]:
                    item["status"] = "blocked"
                elif outcome["timed_out"] or outcome["exit_code"] != 0:
                    item["status"] = "failed"
                elif check["kind"] == "act" and not completed_selection(text, check):
                    item.update(
                        status="blocked",
                        reason="act returned zero without a successful job completion record; empty or filtered execution is incomplete",
                    )
                elif check["kind"] == "act" and not item.get("cleanup", {}).get("complete"):
                    item.update(
                        status="blocked",
                        reason="Run-owned Docker cleanup is incomplete; inspect cleanup diagnostics",
                    )
                else:
                    item["status"] = "passed"
                    item.pop("reason", None)
            write_report(output, report)
    report["finished_at"] = timestamp()
    report["complete"] = all(c["status"] == "passed" for c in report["checks"] if c["required"])
    report["exit_code"] = 0 if report["complete"] else 1
    write_report(output, report)
    return report


def write_report(output: Path, report: dict[str, Any]) -> None:
    pending = output / ".report.json.pending"
    pending.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    pending.replace(output / "report.json")
    lines = ["# Local CI results", "", f"Required coverage complete: **{report['complete']}**", ""]
    if "repositories" in report:
        lines.extend(
            ["| Repository | Required coverage | Result | Evidence |", "| --- | --- | --- | --- |"]
        )
        for row in report["repositories"]:
            name = str(row["repository"]["path"]).replace("|", "\\|")
            detail = str(row.get("error", "")).replace("|", "\\|").replace("\n", " ")
            if row.get("report"):
                detail = f"[JSON report]({row['report']})"
            lines.append(
                f"| {name} | {'complete' if row['complete'] else 'incomplete'} | exit {row['exit_code']} | {detail} |"
            )
    else:
        lines.extend(["| Check | Required | Status | Detail |", "| --- | --- | --- | --- |"])
    for check in report.get("checks", []):
        detail = (
            str(check.get("reason", check.get("log", ""))).replace("|", "\\|").replace("\n", " ")
        )
        lines.append(f"| {check['id']} | {check['required']} | {check['status']} | {detail} |")
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)

    def options(target: argparse.ArgumentParser, suppress: bool = False) -> None:
        defaults = argparse.SUPPRESS if suppress else None
        target.add_argument("--repository", default=defaults)
        target.add_argument(
            "--manifest", default=argparse.SUPPRESS if suppress else "config/local-ci.json"
        )
        target.add_argument("--output", default=defaults)
        target.add_argument(
            "--act", default=argparse.SUPPRESS if suppress else os.environ.get("REALM_ACT", "act")
        )
        target.add_argument(
            "--cloud-network", action="store_true", default=argparse.SUPPRESS if suppress else False
        )

    options(parser)
    commands = parser.add_subparsers(dest="operation", required=True)
    for name in ("doctor", "plan", "run", "sweep"):
        command = commands.add_parser(name)
        options(command, True)
        if name == "sweep":
            command.add_argument("--repositories", nargs="+", required=True)
    return parser.parse_args(argv)


def _main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    output = None
    try:
        repository = Path(args.repository or ".").resolve(strict=True)
        if args.operation == "doctor":
            result = doctor(repository, args.act)
            if (repository / args.manifest).is_file():
                manifest = load_manifest(repository, args.manifest)
                result["runner_images"] = [
                    c["platforms"] for c in manifest["checks"] if c["kind"] == "act"
                ]
            print(json.dumps(result, indent=2))
            return 0 if result["ready"] else 2
        if args.operation == "plan":
            manifest = load_manifest(repository, args.manifest)
            print(
                json.dumps(
                    {**manifest, "repository": metadata(repository), "execution": "not-performed"},
                    indent=2,
                )
            )
            return 0
        if not args.output:
            raise ValueError("run and sweep require --output naming a new local report directory")
        output = Path(args.output).absolute()
        if output.is_symlink() or output.exists():
            raise ValueError("report output must not already exist")
        if args.operation == "run":
            result = run_repository(repository, args.manifest, output, args.act, args.cloud_network)
        else:
            roots = [Path(path).resolve(strict=True) for path in args.repositories]
            if len(set(roots)) != len(roots):
                raise ValueError("sweep repositories must be distinct")
            output.mkdir(parents=True, exist_ok=False)
            rows = []
            for index, root in enumerate(roots):
                try:
                    child = run_repository(
                        root,
                        args.manifest,
                        output / f"{index:03d}-{root.name}",
                        args.act,
                        args.cloud_network,
                    )
                    rows.append(
                        {
                            "repository": child["repository"],
                            "complete": child["complete"],
                            "exit_code": child["exit_code"],
                            "report": f"{index:03d}-{root.name}/report.json",
                        }
                    )
                except (ValueError, OSError) as error:
                    rows.append(
                        {
                            "repository": {"path": str(root)},
                            "complete": False,
                            "exit_code": 2,
                            "error": redact(str(error)),
                        }
                    )
            result = {
                "schema_version": SCHEMA,
                "repositories": rows,
                "complete": all(row["complete"] for row in rows),
                "publication": "not-performed",
            }
            result["exit_code"] = 0 if result["complete"] else 1
            write_report(output, result)
        print(json.dumps(result, indent=2))
        return result["exit_code"]
    except KeyboardInterrupt as error:
        code = 128 + getattr(error, "signum", signal.SIGINT)
        result = {
            "schema_version": SCHEMA,
            "complete": False,
            "exit_code": code,
            "execution": "cancelled",
            "checks": [],
            "publication": "not-performed",
        }
        if output is not None and output.is_dir():
            checkpoint = output / "report.json"
            if checkpoint.is_file():
                result = {
                    **json.loads(checkpoint.read_text()),
                    **{key: value for key, value in result.items() if key != "checks"},
                }
            write_report(output, result)
        print(json.dumps(result, indent=2))
        return code
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(
            json.dumps(
                {
                    "schema_version": SCHEMA,
                    "complete": False,
                    "error": redact(str(error)),
                    "execution": "incomplete",
                },
                indent=2,
            )
        )
        return 2


def main(argv: list[str] | None = None) -> int:
    previous = signal.signal(signal.SIGTERM, termination_requested)
    try:
        return _main(argv)
    finally:
        signal.signal(signal.SIGTERM, previous)


if __name__ == "__main__":
    raise SystemExit(main())
