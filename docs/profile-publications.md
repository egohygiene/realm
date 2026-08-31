# Profile publication declarations

Realm publishes a deterministic declaration for every supported profile under
[`dist/profiles/`](../dist/profiles/). These files make the proposed contents,
supported targets, supply-chain inputs, and cache identity reviewable before a
renderer or OCI image exists.

## Authority and boundaries

The canonical inputs remain the capability catalog, profile files, and curated
tool registry:

```text
accepted tool + stable capability
              ↓
profile resolution for each supported target
              ↓
publication manifest + declared-intent SPDX document
              ↓
renderer build, smoke test, image SBOM, provenance, and size measurement
```

`schemas/profile-publication.v1.schema.json` defines the manifest. Each profile
directory contains:

- `manifest.v1.json` — resolved contents, source checksums, cache key, support
  matrix, and an explicit size-evidence state;
- `sbom.spdx.json` — an SPDX 2.3 *declared-intent* inventory of requested
  package-manager inputs and accepted tools;
  and
- `../support-matrix.v1.md` — the human-reviewable aggregate matrix.

The declared-intent SPDX document is deliberately not presented as a build
attestation. It records only reviewed, pinned profile inputs. A released OCI
image still needs its own installed-package SBOM, provenance attestation,
non-root smoke test, and image-size evidence.

## Stable admission

The tool registry has a `stable_capability` field. Only an `accepted` tool may
set it; an accepted tool must name a real capability and a profile that resolves
that capability for every advertised target. Conversely, `experimental`,
`deferred`, `rejected`, and `superseded` entries must leave it `null`.

This makes the important boundary executable: a candidate such as AWS CLI,
Google Cloud CLI, or Compose v2 can remain visible in the registry without
silently entering a stable Realm profile. The stable `cloud` profile contains
the independently pinned OpenTofu and Pulumi clients only.

## Cache identity

Each profile manifest contains a `cache_key`. It is the SHA-256 checksum of the
canonical catalog and registry, every inherited profile file, and every
resolved platform/projection target. A renderer may reuse a prior result only
when this key and its own renderer version are unchanged.

The cache key is not a container digest and must not be used as one.

## Size status

The profile manifests publish `size.status: "unmeasured"` until an OCI image
has actually been built. This is intentional: package names and source
artifacts do not reveal compressed or expanded image size. Realm issue #6 owns
the built-profile union, its size budget, and release-size evidence. Use:

```bash
task image:size ARCH="amd64" IMAGE="<published-image>"
```

only after the relevant profile image exists.

## Commands

Validate the policy-to-profile join:

```bash
python3 tools/realm_profile_publications.py validate
```

Regenerate the checked-in declarations after a reviewed source change:

```bash
python3 tools/realm_profile_publications.py render
```

Verify the declarations are current without modifying the worktree:

```bash
python3 tools/realm_profile_publications.py check
```
