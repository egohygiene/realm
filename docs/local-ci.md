# Local GitHub Actions validation

Realm provides an opt-in, local-first developer capability for
[issue #48](https://github.com/egohygiene/realm/issues/48). Use the same source
checks as CI, then use `act` to exercise selected workflow wiring. Neither path
dispatches GitHub Actions or consumes hosted Actions minutes. Workflow code can
still contact external services; review the selected commands and dependencies.

## Install and preflight

Requirements are Python 3.10+, Git, the repository's declared development tools,
and a reachable Linux Docker engine. `act` is a development requirement for the
local-workflow capability, not a dependency of the minimal Realm runtime.

The optional `local-ci` profile declares the pinned client. The existing
base-only Dev Container emitter does not yet install arbitrary optional
profiles: install this client explicitly in your workspace after resolving the
profile. No daemon or Docker socket is installed or mounted by that selection.

```sh
python3 tools/realm_act.py install --output .cache/realm/local-ci/bin/act
export PATH="$PWD/.cache/realm/local-ci/bin:$PATH"
act --version
docker version
python3 tools/realm_local_ci.py doctor --act "$PWD/.cache/realm/local-ci/bin/act"
```

The installer selects `linux/amd64` or `linux/arm64`, checks the committed
release archive digest, and refuses to overwrite a different executable. An
already downloaded official archive can be supplied with `--archive PATH` for
offline installation. The current selection is act **0.2.97**. Task and
ShellCheck remain prerequisites of Realm's existing `task check` command.

Docker Desktop on Apple Silicon can run a Linux ARM64 Dev Container connected
to its engine. Use the appropriate Docker context/socket and verify the engine
architecture. An AMD64 container on that machine is emulation, not native ARM64
qualification. The act runner image pin is a multi-architecture OCI index;
native execution on each architecture still needs its own evidence.

## Plan, run, and sweep

The checked-in selection is `config/local-ci.json`. Planning reads the manifest
and selected files without executing repository commands:

```sh
python3 tools/realm_local_ci.py plan --repository .
python3 tools/realm_local_ci.py run --repository . \
  --act "$PWD/.cache/realm/local-ci/bin/act" \
  --output .cache/realm/local-ci/review-001
```

In a managed cloud workspace requiring its configured proxy and CA, append
`--cloud-network` to `run` or `sweep`. This is an explicit opt-in; ordinary
desktop Docker installations use the commands above without it.

Output directories are exclusive: use a new name for each run. The JSON and
Markdown reports record revision, dirty state, selection, commands, exit codes,
runner identity, timings and bounded logs. They distinguish passed, failed,
blocked, skipped and unsupported checks. Required incomplete checks return a
nonzero result. A failed checkout does not stop a sweep collecting evidence for
the remaining selected checkouts.

```sh
python3 /path/to/realm/tools/realm_local_ci.py sweep \
  --repositories /path/to/realm /path/to/reflector \
  --act /path/to/act --output /path/to/private-local-reports/sweep-001
```

Every checkout supplies its own explicit manifest. A missing or empty selection
is incomplete, never a passing zero-test run. The launcher does not clone,
update, repair, commit, publish reports, or scan arbitrary checkout directories.
An agent can inspect a failed report, fix the selected repository, and rerun
into a new output directory. Reports are local development artifacts, not
verified hosted check results. Review logs before sharing them.

## The `.actrc` contract

The root `.actrc` contains only runner mappings and ordinary cleanup/pull
defaults. Runner labels resolve to an immutable reviewed image digest, not to
the old Node 16 Buster image proposed by Reflector's historical issue #123.

act 0.2.97 restricts flags accepted from a project `.actrc`; it also does not
expand environment variables in an untrusted project config. Options such as
network selection, cache paths and Docker socket handling must be passed by the
launcher or deliberately selected by the developer. Do not solve ignored
settings by globally enabling `--trust-project-actrc`. The process must run
with the repository as its working directory: `act -C PATH` alone does not
load that repository's `.actrc`.

The launcher uses an isolated user act configuration, explicitly disables
automatic `.env`, `.vars`, `.input` and `.secrets` discovery, chooses bridge
networking, and disables the Docker socket inside ordinary job containers.
It sets real process timeouts; act does not implement all hosted controls.
Initial image and remote Action downloads require network and disk space;
cached images are reused without an implicit fresh pull.

Direct manual example for the portable test fixture:

```sh
act workflow_dispatch -W .github/act/local-validation.yml -j offline-tests \
  --network bridge --container-daemon-socket - \
  --container-options-policy restrict --no-cache-server \
  --env-file /dev/null --secret-file /dev/null \
  --var-file /dev/null --input-file /dev/null
```

That fixture lives outside `.github/workflows`, so GitHub will not schedule it.
Its pinned checkout step uses act's local working-tree copy emulation. The
remote checkout Action itself is not qualified by that emulation.
It invokes the same dependency-free unittest command as `task test`. The full
offline contract gate is separately exercised by the direct `task check`
selection; fixture success does not prove remote setup Actions work.

## Selection and coverage

Each manifest uses `realm.local-ci/v1` and has a nonempty `checks` array:

- `direct`: an argv array invoking the repository's canonical command.
- `act`: an explicit workflow, job, event, optional inputs/matrix filters,
  immutable runner mappings and a bounded timeout.
- `unsupported`: the named unexercised check and its reason.

Every entry declares whether it is required. Optional omissions remain visible;
the summary is scoped to the declared required selection, not all CI. An act
job can include its `needs` dependency jobs: review the whole workflow before
admission. The selection is a developer review boundary, not a sandbox for
untrusted repository code. Keep release, deployment, signing, registry push and
other remote mutations outside this validation manifest. Credentials are never
granted merely because a workflow declares GitHub `permissions`.

Realm currently selects the complete direct offline gate and the portable act
test fixture. Normal `validate.yml/contracts` additionally bootstraps pinned
checkout and Task Actions: its remote-action and provider-context behavior is a
separate coverage gap. Native image AMD64/ARM64 checks require eligible native
Docker hosts and snapshot replay; the release review workflow is outside the
local validation selection. No image-build or release-readiness result is
inferred from unit-test success.

Missing credentials are blocked. This first launcher deliberately does not
inject production secrets; `required_secrets` records that prerequisite. Review
and add a bounded owner adapter when a check genuinely requires credentials.
Do not weaken assertions or turn a missing native runner/provider into a pass.

## Managed cloud workspaces and Dev Containers

Check both the Docker client and server, free disk space, selected platform and
the host path seen by the engine. A socket inside a Dev Container controls its
Docker host; bind paths refer to the engine's filesystem, which may differ from
the workspace filesystem. Prefer act's default workspace copy for simple jobs.
Explicit Docker-dependent checks need reviewed socket and nested-path handling.

Managed workspaces can require their supplied proxy and CA trust inside job
containers. Outer-workspace proxy hostnames are not necessarily reachable from
Docker. Use the launcher's explicit cloud-network option when available; it
reads Docker's configured container proxy settings and mounts the supplied CA
read-only. Keep any generated proxy env file private and outside source. TLS
verification stays enabled. A proxy denial or absent runtime remains a reported
blocker; configuration must be fixed before retrying the dependent check.

Linux runner containers do not qualify native macOS, Windows or device-specific
tests. GitHub OIDC, environments, concurrency, job permissions, hosted service
identity, deployment and artifact/cache services have partial or absent local
equivalents. Use direct/native checks where useful and retain the workflow gap.
Cancellation cleanup is qualified for these simple job containers. Service
containers and containers launched by Docker Actions require separate ownership
and cleanup proof before being added to this selection.
Cloud checkouts using Git extensions unsupported by act's embedded Git library
can also lack accurate simulated GitHub context even when workspace-copy tests
run; the launcher separately records Git identity through the native Git CLI.

## Qualification checkpoint

The Linux AMD64 local sweep passed Realm's complete direct `task check` and its
act unit-test job, each with 208 tests, plus the selected Reflector consumer's
act runtime suite and direct metadata/version/release-source validators.
An earlier failed sweep is retained locally: it exposed a process-termination
test race and a fixture missing checkout emulation, both repaired before the
passing repeat. A failed repository correctly kept that sweep's aggregate
status nonzero while the other repository's results were retained.

The full act runner image is pinned by multiarch index; AMD64 execution, output
propagation, job-success records and TLS-verified network access were exercised.
ARM64 act download/ELF identity was verified without native execution.
This source checkpoint qualifies the selected local jobs only. It does not
publish a Realm environment, qualify every workflow, or refresh the historical
base-image runtime receipts after their catalog-source bindings changed.

## References

- [act installation](https://nektosact.com/installation/index.html)
- [Runner environments](https://nektosact.com/usage/runners.html)
- [Unsupported functionality](https://nektosact.com/not_supported.html)
- [act v0.2.97](https://github.com/nektos/act/releases/tag/v0.2.97)
- [Realm local validation issue](https://github.com/egohygiene/realm/issues/48)
