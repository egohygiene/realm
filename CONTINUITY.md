# Realm continuity

## Reference bootstrap checkpoint — 2026-11-13

The maintainer selected [issue40](https://github.com/egohygiene/realm/issues/40)
for an optional command-reference capability. Base main is
`75c1b2e1475b972a0ce1c8594e8daba2e1cf8686` (merged local-CI foundation);
candidate branch is `feat/40-cheat-cli`.

- The `reference` profile admits checksum-pinned cheat 5.1.0 and its exact
  upstream Bash completion/helper sources with separate preserved licenses.
  `task cheat:bootstrap` explicitly provisions a versioned user-owned prefix,
  default XDG configuration, personal-sheet directory and guarded Bash hook.
- Startup is interactive-only, performs no network/install/configuration writes,
  tolerates missing optional files and preserves existing completion. Repeated
  bootstrap and sourcing are stable; existing configuration, personal sheets and
  local Bash prose survive. Unsafe managed paths, modes and markers fail closed.
- Native Linux AMD64 online/offline bootstrap, actual version/list/example and
  real PTY Tab completion passed under temporary HOME. Repeated activation is
  warning-free and registration stays unchanged. Both architecture gzip hashes
  and Linux ELF identities passed; native ARM64 execution remains unrun.
- Focused controls and the complete offline Task gate are recorded in the PR.
  The guide records install paths, community-sheet opt-in, upgrades, rollback,
  removal and recoverable partial-bootstrap behavior.
- Adding catalog intent refreshes profile/Dev Container declarations and lock
  fingerprints. The 13 APT package records per architecture, snapshots, base
  recipe and package intent are unchanged. Historical qualification receipts
  and their original fixtures stay unchanged; no refreshed image runtime proof
  is inferred from regenerated metadata.
- Other projection entries remain artifact intent. The current Dev Container
  emitter is base-only; no optional image/Nix/workstation renderer, hosted job,
  release publication, new-batch merge or fleet adoption was performed.

Next: independently review this draft and its exact-head receipts. Preserve
issue40 until review/integration; keep native ARM64 and optional projection
qualification explicit. Other Realm acceptance remains in #60 and its owners.

## Previous local-CI implementation checkpoint — 2026-11-13 (historical)

The maintainer selected [#48](https://github.com/egohygiene/realm/issues/48) for
implementation. Candidate branch: `feat/48-local-ci-act`, based on verified main
`0a3bbdc379b54db07dc5103887af0dfe05f97a0a`. This checkpoint records source and
local validation; it grants no merge, hosted-dispatch or publication authority.

- Added optional `local-ci` profile, checksum-pinned act 0.2.97 installer,
  digest-pinned `.actrc`, explicit validation manifest, Task entry points and
  local doctor/plan/run/sweep reports. Base and full capability selections stay
  unchanged; no daemon/socket is provisioned implicitly.
- The launcher isolates act user config and default secret/env files. It has
  real process deadlines, controlled SIGTERM cancellation, exact-label owned
  job-container cleanup, persistent local action caches and opt-in cloud proxy/CA
  transport. Service and Docker-action child cleanup remains unqualified.
- A two-checkout sweep passed: Realm's full `task check` and actual act unittest
  fixture each passed 208 tests; Reflector's runtime act job and three direct
  validators passed at its candidate `ea359549218b74164164299e9cdb24cb3191d8a3`.
  The Reflector branch is being reconciled with newer main independently; use
  that consumer PR for its final integrated qualification.
- Real Docker/act execution and TLS-verified HTTPS inside the runner passed on
  Linux AMD64. Online/offline AMD64 act installation passed; ARM64 archive/ELF
  verification passed, with native ARM64 execution still unproven.
- The original Realm workflow failed fetching its pinned remote Task setup
  Action. The local fixture uses checkout emulation and the canonical unittest
  command; hosted Action/bootstrap/context parity is explicitly unproven.
  Native image checks, release/provider jobs and platform gaps remain visible.
- Catalog fingerprints required regenerated profile/projection declarations and
  lock metadata. Package entries, snapshots, base-image pins and historical
  qualification receipts are unchanged. Frozen original-source fixtures verify
  the old receipts; tests explicitly detect current source drift. No new base
  image runtime qualification is claimed.
- Independent review corrected malformed-manifest handling, aggregate Markdown,
  closed-output timeouts and cancellation cleanup. An asynchronous Mantle
  cancellation test now waits within a bounded window for kernel termination.

Next: review the draft source change and its local evidence, then qualify native
ARM64/Apple Silicon and eligible native image jobs separately. Keep #48 open for
those remaining acceptance gates. Published capability/adapter availability and
organization-wide file adoption are not inferred from this source candidate.
See [local CI](docs/local-ci.md) for commands, coverage and recovery. Raw reports,
logs, downloaded tools, proxy files and credentials stay outside public source.

## Previous integration checkpoint

Observed 2026-10-30. This repository-owned prose snapshot records context, not
permission or an adopted machine continuity contract. Live instructions,
canonical source and verified work-tracker state outrank this handoff.

- Verified main before the final release-preparation integration: `6f5ee06989492a627f9c4e8bc32e3eb9d733cc10`.
- Generated base Dev Container [PR #57](https://github.com/egohygiene/realm/pull/57) merged at `3154e80e2a3903555f791dc3c80e33af6100d126` from reviewed head `d9030a6aa33f12746af77d57321888d340e16e3f`.
- Installed-image evidence [PR #58](https://github.com/egohygiene/realm/pull/58) merged at `6f5ee06989492a627f9c4e8bc32e3eb9d733cc10` from reconciled head `c3bc7819db5d74151244037cac6a4695ad4cf684`, preserving qualified source `5042d4d05a9b1e9f31e69a50612abaf6f41bfe53`.
- [PR #59](https://github.com/egohygiene/realm/pull/59) integrates the reviewed release-preparation source `3c5cd1c7a360acef46b9cf273250a2cca403551b` with that main. Its base was explicitly retargeted from #58's branch to main. The PR records the containing reconciliation head and final merge state.
- Next implementation batch: not selected. Read the requested owning issue and live [roadmap #25](https://github.com/egohygiene/realm/issues/25) before choosing a new branch from updated main.

## Canonical source and behavior

`tools/realm_devcontainer.py`, its projection schema and generated bundles own the
bounded base-profile Dev Container slice. It preserves resolved-profile v1,
existing package intent and recipe/lock bytes, bounds the source graph, and checks
source bytes plus Git executable roles. Unsupported profiles and unsafe or
preexisting outputs reject. AMD64/ARM64 generation is distinct from runtime or
Feature publication. docs/devcontainer-projection.md records the actual scope.

`tools/realm_image_evidence.py` and its closed schema own limited native local
image observations. Exact source inputs, installed locks, pinned Syft/Grype
executables and a separately selected fresh database bind the artifact snapshot.
The offline verifier re-derives available facts from exact hashed bytes; registry
identity, producer authentication and release readiness remain unavailable.
Creation and execution deadlines are separate; full ID/name/nonce/image checks
scope cleanup. Indeterminate creation remains non-success with bounded recovery.
Producer edits during capture reject before final directory publication.

The release declaration selects one git-tag authority, Unreleased changelog,
incubating/advisory profile and planned distribution channels. AGENTS.md,
docs/releasing.md and Taskfile.yml own the local preparation/review handoffs.
The release adapter consumes verified #7 snapshots, freezes the copied bytes,
reconstructs root records and binds every payload checksum. Its SPDX root indexes
actual platform SBOMs. Recorded crypto or edited booleans cannot promote local
v1 evidence to release-ready. The manual workflow has read-only permissions;
its literal Task handoff reviews current-main source and publishes nothing.

## Verification and observed subjects

- Qualified source heads listed above had independent final reviews and passed combined `task check`: 162 tests and all offline gates. All 62 changed files outside shared README/Task/handoffs matched exact qualified source and Git roles. Task variables, every task/check, command order and README additions were preserved; 39 selected canonical/audit/lock files remained unchanged.
- Fresh ordered merge checks passed 110 tests for #57, 136 for reconciled #58 and 162 for the final #59 reconciliation, with all declared offline gates. The final 64 changed non-handoff files, including README and Taskfile, are byte-identical to the original fully qualified integration. Each preceding merged main tree matched its checked source candidate. PR #59 records its exact reconciliation head and explicit successful Task exit.
- Source-bound generated-container proof passed official schema/CLI interpretation, actual native AMD64 build/start, installed-lock/default-user smoke, 109 Task tests and 24 actual Bash/Zsh/Fish Mantle source cases. Reopen/recreation and cleanup passed. Python/Fish/ShellCheck and pinned Task were explicit disposable qualification tools, not installed base capabilities. Three environment-provisioning failures remain recorded separately.
- Actual installed-image evidence binds source `d6f3604d0f787cc8a2b6c97d70bd3122f81a8203`, local config ID `sha256:c3bb59a8ddbaac91ce808da1077b4704cdb3069f986cad0701a542d773a9ad7e` and reviewed producer SHA-256 `6bbeb3b54193f9319f3a45d984929b35f6cf4cb4426988df8ea82a789ebe84d2`. Native build, package/source/CA-cleanup checks, running-before-deadline removal and mid-capture source-edit rejection passed. These are distinct from the generated image subject in its own receipt.
- The capture records 293 installed packages, 294 SPDX entries and 13 locked roots. Grype retains 1,689 active and 3,015 ignored matches, including 76 Critical and 412 High. Capture-time database freshness is recorded; this is neither a current clean-image nor exploitability verdict.
- Actual owner-to-release bundle creation/verification passed: 14 files, 13 payload checksums, 74,957,539 bytes. The exact published Relay v1.5.0 mechanics and official SPDX index validation passed. Required readiness returned exit 2/unavailable.
- Current native EgoLint `f14f7fd3ab0ce9e87c367352fcb3af11a32eda59` passed all seven release checks under advisory rollout. The qualified combined aggregate exited 1 with thirteen unchanged predecessor portability findings and eighteen GNU-command warnings from identical generated script copies. No rule/mode was weakened and no aggregate clean result is claimed.

Safe source-bound records are docs/evidence/devcontainer-generated-base.v1.json,
docs/evidence/image-local-capture.v1.json and
docs/evidence/container-release-local.v1.json. Exact checks, mutations and
limitations live in the owning PRs/guides. Raw logs and full local artifacts stay
outside public repository content.

## Remaining acceptance and recovery

Keep #10 open for Feature distribution, Nix/workstation adapters and broader
conformance; keep #7 open for native ARM64 scanner/build proof and finding
triage. #17 retains compatible released producer inputs, public registry
manifest/index identity, verified signatures/provenance and an approved owner
publication adapter. #8/#39 retain published Mantle and remaining host/TTY gates;
the generated local source canary does not establish those broader outcomes.

Aether `8a2a3d08f3aa9da3847bd5277843506ab855192e` remains draft source and Hygiene
`28f9d6c7519d820644572634ba4476614f418d83` proposed source; their release acceptance
is not inferred. Published Relay v1.5.0 is pinned at
`1eada5142f7fc7da7862f335589e3b8f5884ffaf`; tag-signature verification is unproved.
Hosted qualification remains deferred and all new commits use `[skip ci]`.
Source merges create no tag, release, signature, registry publication or workflow
dispatch. Full issue acceptance remains open.

Before resuming, verify the linked PR states and current remote main, then apply
the next selected issue scope. Preserve immutable audit/creative bytes, package
locks and canonical profile identities. The historical audit describes its
original source and tracker state. Exclude private paths, credentials,
environment values and raw logs from public source. This snapshot grants no
additional authority and selects no further implementation.
