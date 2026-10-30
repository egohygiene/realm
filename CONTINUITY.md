# Realm continuity

## Current integration checkpoint

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
