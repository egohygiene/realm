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
| `full` | all language profiles | cloud, media, and Mantle tools | forbidden |
| `services` | `base` | container host service | explicit opt-in |

`full` means every supported non-service development toolset. It does not mean
every possible host daemon, database, credential, or product dependency. Those
belong in explicit service profiles or consuming application orchestration.
This definition keeps `full` portable enough for CI and Dev Containers.

## Projections

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

Resolution fails for unknown or cyclic profile inheritance, missing or cyclic
capability dependencies, explicit exclusions that break dependencies,
capability conflicts, incompatible platforms/projections, forbidden service or
privileged capabilities, mutable sources, and secret-bearing data.

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
