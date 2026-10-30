# Realm continuity

## Current checkpoint

Observed 2026-10-30. This repository-owned prose handoff records context, not
permission or a new machine-enforced continuity contract. Live instructions,
canonical source and verified work-tracker state outrank this snapshot.

- Main includes generated Dev Container [PR #57](https://github.com/egohygiene/realm/pull/57), merged at `3154e80e2a3903555f791dc3c80e33af6100d126` from reviewed head `d9030a6aa33f12746af77d57321888d340e16e3f`.
- Installed-image evidence [PR #58](https://github.com/egohygiene/realm/pull/58), branch `feat/7-image-evidence`, is reconciled with that main for merge. Reviewed source head: `5042d4d05a9b1e9f31e69a50612abaf6f41bfe53`; its PR records the containing reconciled head.
- Release preparation [PR #59](https://github.com/egohygiene/realm/pull/59) remains open/draft at `3c5cd1c7a360acef46b9cf273250a2cca403551b`. It targets #58's branch; after #58 merges, retarget it to main before its own reconciliation and merge.
- Canonical sources: [roadmap #25](https://github.com/egohygiene/realm/issues/25), owning issues #10/#7/#17, docs/devcontainer-projection.md, docs/image-evidence.md, Taskfile.yml and the source-bound receipts below.

## Integrated source and ownership

The deterministic base generator preserves resolved-profile v1 and emits faithful
AMD64/ARM64 local Dev Container bundles from the existing recipe/locks. It bounds
source graphs and checks exact source bytes plus Git executable roles. Unsupported
profiles and unsafe/overwriting output reject. The generated receipt records
source/input/generator hashes; generation does not install other profiles or
publish Features. The optional caller-reviewed BuildKit CA secret affects only
build transport and leaves no CA/configuration in the finished layer.

The image-evidence producer accepts an exact local image configuration ID, binds
selected immutable source inputs and installed locks, and runs pinned Syft/Grype
with a separately selected fresh database. Its offline verifier re-derives local
facts from the exact checked artifact bytes. Config IDs, scanner manifests and
registry index/platform digests have distinct meanings. The local contract keeps
registry identity null and release readiness false.

Creation and execution have separate deadlines. A full container ID and exact
name/nonce/image ownership precede start/attach; cleanup removes only the verified
ID. Indeterminate creation uses bounded scoped recovery and remains non-success.
Producer bytes are frozen across capture; an ordinary mid-run edit rejects before
publishing a final local directory. All findings survive runtime-data redaction.

## Actual qualification

- Exact independent #57/#58/#59 source heads previously passed combined `task check`: 162 tests and all offline gates. All three had independent final source/metadata review with no remaining source blocker. Operational handoffs were checked separately.
- Fresh pre-merge #57 replay passed all 110 tests and offline gates. Its merged main tree equals the reviewed candidate tree. The #58 reconciliation passed all 136 tests and offline gates; its 43 changed source files outside README/Task/handoff match the qualified source bytes and Git roles, the Task/README union is preserved, and 39 original canonical/audit/lock files remain unchanged. PR #58 records the exact reconciled head.
- The generated configuration passed the exact official schema and CLI interpretation, actual native AMD64 image build/start, installed-lock/default-user smoke, 109 Task tests and 24 real Bash/Zsh/Fish Mantle source cases inside its container. Reopen/recreation and owned-container cleanup passed. Three failed qualification-environment attempts remain recorded. Python/Fish/ShellCheck and pinned Task were explicit disposable qualification inputs, not installed base capabilities.
- Independent #7 final checks passed 123 Task tests, including 26 focused methods. Actual clean source `d6f3604d0f787cc8a2b6c97d70bd3122f81a8203` built and passed installed-lock/non-root/source/CA-cleanup probes. The actual producer SHA-256 is `6bbeb3b54193f9319f3a45d984929b35f6cf4cb4426988df8ea82a789ebe84d2`.
- Its actual native image capture, running-before-deadline removal and mid-capture source-edit rejection passed. The closed receipt and official SPDX schema validate; 293 installed packages, 294 SPDX entries and 13 locked roots are bound to the captured subject.
- Grype retains 1,689 matches and 3,015 ignored matches, including 76 Critical and 412 High. This observation is not a clean-image or exploitability verdict. Snapshot/database hashes and capture-time freshness remain in the evidence.

Safe records: docs/evidence/devcontainer-generated-base.v1.json and
docs/evidence/image-local-capture.v1.json. Raw logs and full artifacts remain
outside public source. The two observed images are distinct local subjects.

## Acceptance, preservation and next action

Keep #10 open for Features distribution, Nix/workstation adapters and broader
conformance. Keep #7 open for native ARM64 scanner/build proof, finding
disposition, compatible producer evidence, cryptographic authentication and
approved distribution. #8/#39 retain published Mantle and remaining host gates;
source-only Mantle activation is not a released integration. Hosted Actions
qualification remains deferred; every new commit uses `[skip ci]`.

Finish #58's checked merge, retarget #59 to resulting main, reconcile its handoff
and complete the ordered source merge. No further implementation batch is selected.
Merging source performs no release, tag, workflow dispatch, signing or registry
publication. Preserve historical audits, creative bytes, canonical profile
identity and package locks. Keep credentials, private paths, environment values
and raw logs out of public repository content.
