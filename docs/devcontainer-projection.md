# Generated base Dev Container

Realm emits a local base Dev Container template from the same validated
capability model as its Docker projection. This is the bounded first slice of
[#10](https://github.com/egohygiene/realm/issues/10), using the standards mapping
from [#39](devcontainer-boundary.md). It does not publish an OCI Feature/template,
implement Nix/workstation adapters or complete the supported-host matrix.

## Canonical input and supported intent

`tools/realm_devcontainer.py` uses the existing resolver for `base` on
`linux/amd64` and `linux/arm64`, with projection `devcontainer`. It validates the
whole profile graph, snapshot configuration and selected apt lock. Resolved
intent must match the Docker base after the projection label changes and contain
no artifact, privilege or service requirement. Other profiles/platforms are
explicitly unsupported; the emitter never drops runtimes to make JSON look valid.

Profiles, catalog identities and resolved-profile v1 remain unchanged. No editor,
environment, mount, lifecycle or host field is invented in that manifest. The
adapter supplies only its build contract and the existing non-root image
identity, with UID updating disabled. No reviewed published Feature mapping is
available for this slice.

## Relocatable source bundle

Examples under `dist/devcontainers/base-linux-amd64` and
`dist/devcontainers/base-linux-arm64` are complete local build contexts:

- `.devcontainer/devcontainer.json` binds relative paths and the target platform;
- exact Realm-owned base recipe/scripts, selected lock, catalog/config/base profile and MIT license;
- `resolved-profile.v1.json` retains the existing resolver output;
- `projection.v1.json` follows the closed [source-bundle schema](../schemas/devcontainer-projection.v1.schema.json), binding generator/input/file hashes, executable roles and limitations;
- a narrow `.dockerignore` and generated usage note.

The recipe installs only the canonical thirteen package roots using the existing
immutable frontend/base-image and signed Debian snapshot pins. The optional
`realm_build_ca` BuildKit secret supplies local transport trust without copying
it into the image. Recipe and lock bytes remain part of bundle identity.

Identity excludes timestamps and machine paths. It binds the executed
generator/resolver/lock-validator bytes, full canonical profile graph, selected
lock and other inputs. Git's owner-executable role becomes 0644 or 0755; input
and checked output use that same role so checkout umasks do not cause drift.
Owner-executable changes and special permission bits reject. Host read/write,
group and other permission bits are outside Git's source contract; actual
runtime access needs a separate user/container check. Inventory and bytes are
compared exactly. No sibling implementation is vendored.

This receipt is source identity, not an OCI digest, signature, release attestation
or installed-image SBOM. Image evidence belongs to #7 and the release adapter to
#17. A build's source-input revision label identifies bundle inputs; it is not
represented as a Git commit or published release.

## Generate, check and use

Ordinary checks are offline and execute no Docker or lifecycle hooks:

```sh
task devcontainers:check
python3 tools/realm_devcontainer.py check --platform linux/amd64
python3 tools/realm_devcontainer.py check --platform linux/arm64
```

Render into a new directory whose parent already exists:

```sh
python3 tools/realm_devcontainer.py render --platform linux/amd64 --output /tmp/realm-base-amd64
task devcontainers:render ARCH=arm64 OUTPUT=/tmp/realm-base-arm64
```

The emitter bounds strict JSON, rejects duplicate/non-finite fields and symlinks,
and opens source/output parents without following links. It creates output
exclusively, preserving existing/racing destinations. Interrupted writes may
leave an incomplete new directory; `check` rejects it. No cleanup deletes prior
output. To refresh examples, render fresh bundles, inspect replacement diffs and
explicitly replace only reviewed generated content.

Source reading permits at most 128 profile-directory entries and eight MiB of
aggregate canonical inputs, including non-emitted profiles. Each source file is
limited to one MiB; checked output traversal/error collection stops at 64 members.
These bounds reject before rendering rather than treating a small output bundle
as evidence that its complete source graph was small.

On a matching native architecture, select the generated configuration and a
workspace with the official Dev Container CLI:

```sh
devcontainer up --workspace-folder "$PWD" --config "$PWD/dist/devcontainers/base-linux-amd64/.devcontainer/devcontainer.json"
devcontainer exec --workspace-folder "$PWD" --config "$PWD/dist/devcontainers/base-linux-amd64/.devcontainer/devcontainer.json" /usr/local/libexec/realm/smoke
```

These perform actual image/container work; source checks do not. Workspace
mounting belongs to the selected CLI/host. A host needing private CA transport
must supply a BuildKit secret through an explicit local consumer overlay. Bind
the untouched generated JSON and transport overlay separately; do not commit
machine paths or call modified JSON byte-identical generated configuration.

## Conformance and limits

Focused tests cover both architectures against the same resolver/recipe, target
binding, deterministic relocation, no overwrite, malformed source/stale locks,
symlinks and read-only rejection of damaged/missing/extra/executable-role-drifted
output. Official schema and actual CLI/container observations are separate
evidence. ARM64 generation does not establish a native ARM64 build or runtime.

Task, Python/ShellCheck test prerequisites and unreleased Mantle are not base
capabilities. A disposable canary may supply explicitly checksum-recorded tools
and the verified #8 source archive, then run the same repository Task and native
Mantle paths. It must distinguish installed packages from test/source overlays;
it proves neither a released Mantle integration nor stable Feature installation.

Full #10 remains open for reviewed Feature/template distribution, Nix/workstation
dry-run/uninstall adapters and broad same-manifest conformance. Return to #39
for actual VS Code, Codespaces, DevPod and sibling-consumer proof. Native
non-Linux, hosted qualification, signatures/provenance and registry publication
remain separate gates. No paid/cloud host is required for this local slice.
