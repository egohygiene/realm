# Realm container release preparation

Realm's current-v1 `container-image` convention is incubating/advisory. It can
prepare a local review packet and map verified local image evidence into a
portable Relay bundle. The configured manual workflow reviews current-main
source with read-only permissions. Registry publication and immutable GitHub
Release creation remain planned, and this preparation does not complete #17.

## Authority and version selection

[`.egohygiene/release.json`](../.egohygiene/release.json) owns repository facts.
The sole `realm-base` component uses a reviewed exact `vMAJOR.MINOR.PATCH` Git tag
as version authority. No version is derived from an OCI tag, local Docker image
ID, commit message or a second manifest. Moving major aliases are disabled.

Before 1.0, a breaking supported-interface change requires a reviewed minor bump
and explicit changelog entry; compatible fixes may use a patch bump. At 1.0 and
later, incompatible supported changes require a major decision. Keep
`## [Unreleased]` and promote authored notes through review. Announce deprecation
with a replacement and a removal horizon where known; retain historical entries.

[The source lock](../config/release-inputs.v1.json) selects Aether release schema
1.0.0 at `8a2a3d08f3aa9da3847bd5277843506ab855192e`, Hygiene applicability
1.0.0-alpha.1 at `28f9d6c7519d820644572634ba4476614f418d83`, and Relay v1.5.0 at
`1eada5142f7fc7da7862f335589e3b8f5884ffaf`. Exact public contract data and licenses
are vendored for offline checks. Aether is draft and Hygiene proposed, with no
published owner releases when checked 2026-10-30. Immutable source compatibility
does not ratify those inputs or adopt the separate successor-policy lane.

The stdlib checker enforces this narrow Realm selection and exact pinned bytes.
It is not a general JSON Schema engine or a replacement for Aether's reference
validator or EgoLint's policy-aware native consumer. The handoff records those
separate conformance checks.

## Local review

```sh
task release:plan VERSION=v0.1.0
task release:prepare VERSION=v0.1.0 RELEASE_DATE=2026-10-30 OUTPUT=.cache/realm/release-review-v0.1.0
```

Planning is read-only. Its source binding distinguishes Git HEAD from a clean or
dirty working tree and records exact SHA-256 checksums of the release inputs.
Uncommitted authored changes remain inspectable instead of being attributed to
HEAD alone. Preparation creates an exclusive packet with a proposed changelog
patch, that input-bound plan and complete SHA-256 inventory. It does not
apply the patch or select a bump. Existing output directories, source overlap,
invalid dates/tags and locally existing exact tags reject. Local tag inspection
does not establish remote tag availability or current default-branch identity.

After obtaining [actual installed-image evidence](image-evidence.md), map one
or two supported platform receipts with the same represented image-source SHA:

```sh
python3 tools/realm_release.py bundle --version v0.1.0 \
  --source-revision "$IMAGE_SOURCE_REVISION" \
  --image-evidence "$AMD64_EVIDENCE" \
  --output .cache/realm/realm-v0.1.0
task release:verify VERSION=v0.1.0 SOURCE_REVISION="$IMAGE_SOURCE_REVISION" BUNDLE=.cache/realm/realm-v0.1.0
```

Repeat `--image-evidence` for ARM64 when actual evidence exists. Each #7 receipt
and its exact artifact bytes are verified before copying. Source revisions and
platforms cannot conflict. A local config digest and a locally computed scanner
manifest digest remain local identities; neither is relabelled as a registry
index or platform-manifest digest.

This consumer bounds each file to 64 MiB, each complete bundle to 256 MiB and
512 regular files, and root metadata to 1 MiB. Larger image-owner evidence is
unavailable to this adapter until a reviewed streaming/resource-bound change.

The root `sbom.spdx.json` is a checksum-bound SPDX index of the actual per-platform
installed-image SBOMs, which remain in their evidence directories. It does not
invent a merged installed inventory or reuse `dist/profiles` declared-intent
SBOMs. `provenance.json` records local input mapping; `signature.json` records
unavailable authentication. The complete sorted `SHA256SUMS` inventory covers
every payload exactly once. The selected Relay `container-image` required paths
are present and can be inspected by the exact published Relay validator.

Successful local verification means the source/receipt/artifact/checksum joins
are complete. It always reports `release_ready: false` and publication not
performed. `verify --require-release-ready` returns nonzero/unavailable. Editing
JSON booleans, adding a recorded crypto file or renaming a config ID cannot
promote local evidence. The v1 local receipt contract deliberately has no
authenticated registry/publication path.

## Manual review and future publication boundary

`release:publish` is the literal handoff to the real manual
[release-review workflow](../.github/workflows/release.yml). The command prompts
for a version and exact current default-branch SHA. The workflow rechecks branch,
source, tag grammar and live default-branch identity before inspecting source,
then preserves bounded success/failure evidence for 30 days. It grants no
registry, OIDC, release or content-write permission. This workflow has not been
dispatched as part of source preparation.

A later repository-owned GHCR/Docker Hub adapter must bind genuine native AMD64
and ARM64 qualification, the exact OCI index and platform manifests, installed
SBOM/vulnerability evidence and independently verified signatures/provenance to
the reviewed current-main source and changelog. It must independently verify
compatible producer inputs, public anonymous digest availability and approved
registry identity before a separate explicit publication approval. Preserve the
image manifest bytes, signature/trust inputs and verification commands in the
portable public evidence so verification needs no registry credentials.

Only then may a reviewed write-enabled job delegate the complete bundle to
Relay's pinned `semantic-release.yml` using `profile: container-image`,
`component-id: realm-base`, the exact tag/source and `update-major-alias: false`.
Relay's current profile verifier checks files and complete checksums; it does
not cryptographically verify arbitrary `signature.json` or prove registry
delivery. Its green result alone cannot authorize publication.

## Failure, rollback and retention

- Publish an exact version tag and image version mapping once. Consumers pin
  immutable registry index/platform digests. Human-readable image tags and any
  later discovery channels remain convenience metadata.
- A partial registry push, failed signature/attestation, missing architecture
  or failed anonymous verification leaves the release unaccepted. Preserve its
  bounded failure evidence, stop channel promotion and require a fresh review.
  Do not create a success record to complete an incomplete upload.
- A retry may resume only identical bytes and digests. A conflicting prior
  immutable record, output directory, tag or asset rejects; it is never replaced.
- Revoke affected discovery channels through the owner adapter, retain the
  immutable digest/evidence and update consumers by review to a verified prior
  digest or a corrective successor. Never retag an existing release or rewrite
  its historical changelog.
- Keep immutable published release evidence for the supported lifetime of its
  consumers; no automated deletion policy is introduced. Keep transient workflow
  review evidence for 30 days and copy reviewed qualification into the eventual
  immutable bundle. Document any later registry garbage-collection policy and
  protect rollback digests before enabling it.

Nix/workstation adapters, full images, registry credentials and optional tools
remain with their owning issues. This release boundary expands no base profile.
