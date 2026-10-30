# Dev Container boundary

This candidate defines Realm's portable container-development boundary using the
open Dev Container Specification. Profiles and the deterministic resolved
manifest remain canonical. Dev Container JSON is an inspectable projection, not
VS Code configuration and not the source of Realm capability policy.

This is the standards and mapping checkpoint for [#39](https://github.com/egohygiene/realm/issues/39).
[#10](https://github.com/egohygiene/realm/issues/10) owns the emitted projection,
Features/templates and first generated canary. Return to #39 for host proof after
that input exists; complete host proof is not a prerequisite for defining this
mapping. Nix and workstation adapters remain separate #10 outcomes.

## Source and ownership

The versioned [mapping](../catalog/devcontainer-boundary.v1.json) selects the
[official base schema](../vendor/devcontainers/devContainer.base.schema.json) at
`devcontainers/spec@c95ffeed1d059abfe9ffbe79762dc2fa4e7c2421`.
Its SHA-256 is `a0883c0405ff433db188849d458fb20b9c0d73e0ba1a6e44c1d83f3b485408dd`.
The unmodified schema is CC-BY-4.0; [attribution](../vendor/devcontainers/NOTICE.md)
is retained. The reference CLI is version 0.90.0 at
`devcontainers/cli@d807cb27c195b6bc0e89d893fc20f44a30bf27ee`.
These immutable source selections are not claims that every host implements
every property or that a Realm release has been published.

The umbrella schema is not an offline authority: its editor schema references
use mutable upstream branches. Validate the pinned Draft 2019-09 base schema
separately; a future editor adapter must select its own immutable schema inputs.

Realm owns capability resolution, mapping, projection, evidence and host adapters.
Sanctuary consumes this boundary without copying an independent implementation;
Holon selects/materializes profiles; Mantle supplies portable shell behavior;
Relay owns CI/prebuild/publication mechanics. A consuming repository owns its
bounded application requirements and explicit overrides. No sibling has been
repinned, materialized or qualified by this checkpoint.

## Mapping and configuration roles

The mapping covers images, Dockerfiles, Compose, Features, environment, users,
mounts, lifecycle, ports, host requirements, editor customizations, host-specific
customizations/repository permissions, and prebuild/cache behavior. Each row
names the current Realm input or explicitly says that the resolved v1 manifest
does not contain that field. This does not add fictitious fields to the existing
capability or resolved-profile contracts.
Plain field paths name resolved-profile v1 fields; `projection:docker` names a
projection selector, and `profile-publication.v1:cache_key` belongs to the separate
publication contract rather than the resolved manifest.

Image and Feature references must be digest-bound in the authored reference
policy. Prefer reviewed reusable Features and released Realm images once they
exist. The official base schema accepts arbitrary Feature options; validating
it does not validate a Feature's own option contract, registry availability,
installation behavior or reproducibility.
The bounded policy accepts ordinary lowercase OCI repository components, an
optional registry/port and tag, and a SHA-256 digest. URL schemes, empty or dot
path components and mutable tags without a digest are rejected. Feature option
values must be objects under this Realm policy; their owner-defined data is not
interpreted. These restrictions do not implement the full OCI or Feature schema.

`containerEnv` applies to container processes; `remoteEnv` applies to processes
spawned by the remote tool. `containerUser` and `remoteUser` have different
scopes. UID/GID updating is Linux-specific. Host CPU/memory/storage/GPU fields
are requirements or hints, not allocation, machine-selection or device proof.
The reference policy rejects explicit root names and zero UID aliases, including
`user:group` forms, and disables UID mutation. It does not resolve user databases
or validate the image's default identity when a user field is absent.

`initializeCommand` executes on the host, including a cloud VM, and may repeat.
Later lifecycle hooks execute inside the container. Strings invoke a shell,
arrays execute directly, and objects run commands in parallel. Validation never
executes any of these commands. The authored reference policy rejects lifecycle
hooks and privileged/mount/run overrides; reviewed consumer and host adapters
remain later work. This restriction is Realm reference policy, not a declaration
that those standard properties are invalid.

Editor settings belong under `customizations.vscode`; Codespaces UI and
repository permission intent belongs under `customizations.codespaces`.
Namespace metadata does not grant permissions or authorize a paid resource.
Credentials remain injected by the host; no credential values belong in the
canonical manifests, generated configuration or proof reports.

## Reference and deterministic checks

The [authored reference](../tests/fixtures/devcontainer/reference/.devcontainer/devcontainer.json)
uses the existing digest-pinned Dev Containers base image. It has no Features,
lifecycle hooks, host mounts or UID mutation. It is not a Realm #10 emitter and
does not prove that resolved Realm capabilities, Task or Mantle are installed.

The dependency-free checker reads bounded strict JSON, validates the closed
Realm mapping contract, verifies pinned schema bytes and applies the bounded
Realm authored-reference policy. Strict JSON is a subset of JSONC; this command
does not implement a JSONC parser or a general Dev Container schema engine.
It does not download images, resolve Features, query Docker, run lifecycle
commands or contact a host.

```sh
python3 tools/realm_devcontainer_boundary.py check
python3 tools/realm_devcontainer_boundary.py check --require-layer cli-interpretation
```

The first command emits deterministic JSON. The second fails when that proof
was not performed by this checker. A valid mapping cannot manufacture host
qualification. Its [closed report contract](../schemas/devcontainer-boundary-report.v1.schema.json)
keeps mapping/reference-policy checks separate from official schema validation,
CLI interpretation, container execution, Task workflow, IDE and cloud evidence.
Independent proof receipts must name the exact reference digest, tool versions,
commands, outcome and limitations; they do not change this command's scope.

Validate the reference independently against the exact bundled official schema
with `Draft201909Validator` and registered format checks. Actual CLI
`read-configuration` discovers Docker containers; merged configuration may also
inspect images or resolve Features. It is not a Dockerless schema validator.

## Host conformance matrix

The four-host matrix in the mapping records documented expectations separately
from actual qualification. `supported` means the selected documented subset;
`degraded` names a limitation; `ignored` identifies a documented no-effect
setting; `host-specific` requires an adapter; `unavailable` preserves an unknown
or missing implementation/evidence. None of these expectations is a host test.

| Host | Documented boundary | Actual qualification required |
| --- | --- | --- |
| Reference CLI/local runtime | Portable configuration interpretation; editor settings may be ignored | Exact CLI, engine/platform, source digest, create/exec/rebuild and negative controls |
| VS Code Dev Containers | VS Code customizations; clone-in-volume changes workspace assumptions | Actual editor connection and shared tooling workflow |
| GitHub Codespaces | Cloud-host environment; ordinary bind mounts ignored, host:port forwarding unsupported, shutdown behavior differs | Authorized create, machine requirements, editor/browser connection and rebuild |
| DevPod/remote implementation | Supporting-tool listing establishes no blanket field parity | Reviewed implementation/provider/version and the same generated canary |

These limitations come from the pinned
[supporting-tools reference](https://github.com/devcontainers/spec/blob/c95ffeed1d059abfe9ffbe79762dc2fa4e7c2421/docs/specs/supporting-tools.md).
No paid Codespaces resource or remote provider is required for the bounded
mapping checkpoint. All full-issue host acceptance remains open until actually
exercised against the generated #10 projection.

To add a host, retain the same portable configuration, add its namespaced
adapter and immutable source selection, extend the versioned matrix, and run
the shared canary with explicit limitations. Do not fork Sanctuary's foundation
or redefine the canonical profiles to match one host.
