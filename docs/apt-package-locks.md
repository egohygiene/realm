# Debian apt package locks

Status: **v1 base-image contract**

Owner: `egohygiene/realm`

This document defines how Realm turns the minimal `base` profile into a
reviewable Debian Trixie package transaction for `linux/amd64` and
`linux/arm64`.

## Design

```text
capability catalog + base profile
                |
                v
immutable base and Debian snapshot configuration
                |
                v
signed snapshot resolution per architecture
                |
                v
committed exact-version lock
                |
                v
image install -> inventory -> offline verification
```

The sources of truth have separate responsibilities:

| Artifact | Responsibility |
| --- | --- |
| `catalog/capabilities.json` and `profiles/base.profile.json` | Human-reviewed package intent and capability ownership |
| `config/debian-trixie.json` | Base-image, platform, archive, security, signed-metadata, and keyring pins |
| `images/base/packages/locks/*.lock.json` | Generated exact candidates for one architecture |
| `tools/realm_apt_packages.py` | Validation, resolution, replay, and refresh preview |
| `images/base/scripts/install-apt-packages` | Exact-version installation and evidence generation |
| `images/base/scripts/verify-apt-packages` | Installed-image verification without repository access |

The Dockerfile must consume these artifacts. It must not contain an independent
hand-maintained package list.

The supported maintainer surface is deliberately small:

| Command | Effect |
| --- | --- |
| `task packages:check` | Validate configuration and committed locks offline |
| `task packages:verify-lock ARCH="amd64"` | Replay one lock against its signed snapshot |
| `task packages:refresh SNAPSHOT="..." SECURITY_SNAPSHOT="..."` | Write candidate locks and a change report without promotion |
| `task packages:resolve ARCH="amd64"` | Regenerate one canonical lock after review |
| `task packages:verify ARCH="amd64"` | Replay, build, verify, and smoke-test one native image |

## What is pinned

The base uses a readable Debian Trixie tag together with its immutable
multi-architecture OCI index digest. Each lock also records the platform
manifest digest so a build cannot silently select a different child image.

Archive and security repositories are pinned independently to explicit Debian
Snapshot timestamps. Realm retains normal Debian signature verification,
records the expected signed `InRelease` hashes, and forces by-hash index access.
`Check-Valid-Until` is disabled only for the timestamped historical snapshot
stanzas; this does not disable signatures or package-hash verification.

Every requested root is installed as one exact `package=version` argument with
`--no-install-recommends`. Required packages that are unavailable, resolve for
the wrong architecture, or disagree with the catalog fail the operation.

## Offline validation

Run this after any catalog, profile, configuration, schema, or lock change:

```bash
task check
```

The `packages:check` step does not contact Debian or modify locks. It verifies
configuration, source-pin agreement, the 13-package base boundary, both lock
structures, catalog checksums, deterministic ordering, architecture metadata,
and lock checksums. The aggregate task also validates profiles, scripts, and
the unit suite.

## Networked lock replay

Prepare the checksum-pinned Debian archive keyring in a disposable local cache:

```bash
task packages:keyring
```

Then replay both committed locks against their exact signed snapshots:

```bash
task packages:verify-lock ARCH="amd64"
task packages:verify-lock ARCH="arm64"
```

Replay must produce no diff. Run architecture-native image builds and smoke
tests after replay; foreign-architecture metadata alone does not prove that an
image matches its selected platform base.

## Refresh and review

A refresh is an intentional supply-chain change, not a routine build side
effect. Never edit package versions inside a generated lock and never fall back
to live Debian mirrors when a snapshot is unavailable.

Generate candidate locks and a machine-readable change report outside the
canonical lock directory:

```bash
task packages:refresh \
  SNAPSHOT="YYYYMMDDTHHMMSSZ" \
  SECURITY_SNAPSHOT="YYYYMMDDTHHMMSSZ" \
  OUTPUT_DIRECTORY="/tmp/realm-package-refresh"
```

The command previews candidates; it does not update canonical configuration or
publish artifacts. Before promoting a refresh, review and update the base-image
and signed snapshot metadata together, then require:

- the archive and security timestamps and catalog source pins to agree;
- expected `InRelease` hashes to match signature-verified metadata;
- the OCI index to contain the recorded `amd64` and `arm64` manifests;
- `change-report.json` to explain every addition, removal, or version change;
- candidate package sets to remain the same 13 roots with explicit capability
  owners;
- offline validation and networked replay to pass for both architectures;
- both images to build without a package downgrade or live-repository fallback;
- installed inventory, `apt-get check`, non-root smoke tests, and cache cleanup
  to pass; and
- the expanded base size, result size, and delta to be recorded in the pull
  request; and
- compressed size evidence to be added when a release artifact is produced.

Canonical config and locks must be promoted together in one reviewed change.
After that review, regenerate each canonical lock with
`task packages:resolve ARCH="amd64"` and `ARCH="arm64"`, then rerun the full
verification matrix. Refresh automation may open a pull request later, but it
must never commit or publish an update without review.

## Runtime evidence

The installer copies the consumed lock into the image, records locked and
installed versions in `apt-installed.tsv`, and binds build metadata to the
source revision, snapshots, base-image digests, and lock checksum. The
`realm-packages` command summarizes this evidence offline.

Verification also requires Debian's service-start policy to reject starts,
`apt-get check` to succeed, and apt indexes and downloaded archives to be absent
from the completed layer.

## Limitations

- The locks make package selection and requested versions reproducible; they do
  not guarantee byte-identical OCI layers. Maintainer scripts and generated
  build metadata may still vary.
- Microsoft Container Registry and Debian Snapshot are external availability
  dependencies. Disaster-proof rebuilds would require controlled mirrors of
  the base image and locked package artifacts.
- Snapshot pinning freezes security updates. A deliberate refresh cadence and
  vulnerability review remain necessary.
- This contract covers only the Debian Trixie minimal base on `amd64` and
  `arm64`. Language and workstation profile declarations are published in
  [`../dist/profiles/`](../dist/profiles/); the complete image and its size
  budget belong to
  [issue #6](https://github.com/egohygiene/realm/issues/6).
- Privileged monitoring, host daemons, background services, GUI forwarding,
  credentials, and project-specific dependencies are outside this base.
