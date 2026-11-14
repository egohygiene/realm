# Capability and profile contract

Status: **v1 draft, executable**  
Owner: `egohygiene/realm`

## Model

Realm separates intent from output format:

```text
capability catalog + inherited profile + target platform + projection
                                  |
                                  v
             deterministic resolved environment manifest
                                  |
                  +---------------+---------------+
                  |               |               |
               Docker        Dev Container      Nix/workstation
```

A capability owns a coherent unit such as a language toolchain or shell. It
declares dependencies, conflicts, supported platforms and projections, package
identifiers, immutable artifacts, and whether it requires services or elevated
privilege.

A profile composes capabilities and may inherit other profiles. Resolution is a
stable topological order: parent profiles first, capability dependencies before
their consumers, and lexical ordering for otherwise independent nodes.

## Profiles

| Profile | Inherits | Adds | Service/privilege policy |
|---|---|---|---|
| `base` | — | base OS and common CLI | forbidden |
| `rust` | `base` | build and Rust toolchains | forbidden |
| `node` | `base` | build and Node.js toolchains | forbidden |
| `python` | `base` | build and Python toolchains | forbidden |
| `flutter` | `base` | pinned Flutter SDK | forbidden |
| `git` | `base` | Git and a bounded terminal diff tool | forbidden |
| `cloud` | `base` | pinned OpenTofu and Pulumi clients | forbidden |
| `media` | `base` | FFmpeg and ImageMagick | forbidden |
| `local-ci` | `base` | checksum-pinned `act` client | external Docker connection is explicit; no daemon or socket provisioned |
| `reference` | `base` | pinned cheat and upstream Bash completion | explicit user-owned bootstrap; no privileged install or services |
| `full` | curated general-purpose non-service profiles | Mantle shell environment | forbidden |
| `services` | `base` | container host service | explicit opt-in |

`full` composes the general-purpose development toolsets listed in its profile.
The `local-ci` execution capability is a separate explicit opt-in because running
workflows requires a deliberately supplied Docker endpoint and repository/job
selection. It adds no Docker daemon, socket mount or privileged container, and
is not inherited by `base` or `full`. Host daemons, databases, credentials and
product dependencies belong in explicit service profiles or consuming
application orchestration.
This definition keeps `full` portable enough for CI and Dev Containers.

The current stable profile family is `base`, `rust`, `node`, `python`,
`flutter`, `git`, `cloud`, `media`, and `full`. `services` remains the explicit
privileged/service boundary and is not inherited by `full`. Candidate tools
remain visible in the tool registry but cannot enter this family until the
stable-admission contract maps them to a reviewed capability.

The `local-ci` client is admitted separately with upstream release archive pins
in `config/act.v1.json`. Install it into an explicit user-owned destination with
`python3 tools/realm_act.py install --output .cache/realm/local-ci/bin/act`.
An optional `--archive` path permits offline installation from already fetched
bytes. The installer checks the archive checksum and Linux ELF architecture,
creates the binary atomically, preserves existing different binaries, and
does not start Docker or execute workflows. Add the output's `bin` directory to
the calling process's `PATH`, then follow [local CI](local-ci.md).

Both Linux architectures have reviewed archive pins. Native AMD64, native
ARM64, AMD64 emulation and an Apple Silicon Linux Dev Container are separate
runtime qualifications. Archive verification alone does not prove a workflow
can execute on a particular host. The current Dev Container emitter remains
base-only; declaring `local-ci` does not claim that a new generated image or
Dev Container Feature is available. Nix/workstation entries remain resolved
artifact intent, not implemented installation adapters. Upstream SHA-256 values
bind bytes; publisher-signature verification is not claimed.

## Projections

The optional `reference` capability has an implemented native Linux user-owned
bootstrap, documented in [the cheat reference guide](cheat-reference.md). Its
other projection entries describe artifact intent, not available optional image,
Dev Container or Nix renderers. Base/full profiles do not inherit it.

- `docker` produces packages and artifacts for an OCI build.
- `devcontainer` produces the image/features inputs and editor integration.
- `nix` produces the pinned package/module inputs for declarative systems.
- `workstation` produces a host-safe plan; the current Linux projection uses
  Nix package identifiers.

The v1 platform set is `linux/amd64` and `linux/arm64`. The catalog already
records Homebrew identifiers to support a future Darwin platform, but Darwin is
not advertised until it has its own tested platform contract.

## Reproducibility and provenance

- Source catalogs and downloaded artifacts must use immutable timestamps,
  version tags, commit hashes, or OCI digests.
- `main`, `latest`, `edge`, and similar moving references are rejected.
- The zero hashes in this draft are fixture pins. Stable releases must replace
  them with verified upstream or Ego Hygiene revisions.
- Resolved manifests contain no credential values. Secret-bearing fields are
  rejected, and every profile explicitly declares `secrets: forbidden`.
- Runtime credentials are injected by the consuming platform and are never
  baked into images, Nix closures, profile files, or build arguments.

## Deterministic resolver failures

The [catalog schema](../schemas/capability-catalog.v1.schema.json) and
[profile schema](../schemas/profile.v1.schema.json) define the v1 structural
contract. The dependency-free validator checks required and allowed fields,
nested object/array shapes, string forms, capability kinds, and constraint
types before checking references and graph semantics. Privilege and service
flags require actual JSON booleans: strings such as `"false"` and numbers such
as `0` or `1` are rejected rather than coerced.

Resolution fails for unknown or cyclic profile inheritance, missing or cyclic
capability dependencies, explicit exclusions that break dependencies,
capability conflicts, incompatible platforms/projections, forbidden service or
privileged capabilities, mutable sources, and secret-bearing data.

Reported contract errors stop resolution before profile inheritance is traversed.
The CLI prints validation diagnostics to standard error and exits nonzero without
creating or replacing the requested manifest when resolution fails.

## Release path

1. Replace fixture pins with verified revisions.
2. Add a renderer for each projection using resolved JSON as its only policy
   input.
3. Add image builds for `base`, language variants, and `full` on both Linux
   architectures.
4. Run smoke, non-root, size, SBOM, provenance, and vulnerability checks.
5. Publish semantic tags and immutable digests through Relay-owned workflows.
6. Add Darwin only after Nix/Homebrew workstation projections have cross-host
   tests.

## Publication declarations

`dist/profiles/` contains deterministic manifests, declared-intent SPDX
documents, cache identities, and a platform support matrix for every profile.
They are reviewable planning and release inputs, not claims that a profile OCI
image has been built. See [profile-publications.md](profile-publications.md)
for the exact evidence boundaries and regeneration commands.
