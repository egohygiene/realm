# Realm continuity

## Current checkpoint

Observed 2026-10-30. This repository-owned prose handoff records context, not
permission or a new machine-enforced continuity contract. Live instructions,
canonical sources and verified work-tracker state outrank it.

- Objective: prepare bounded installed-image evidence for [#7](https://github.com/egohygiene/realm/issues/7), [draft PR #58](https://github.com/egohygiene/realm/pull/58).
- Base: main `0ebdc4d3562a0af0f806876c5dd81d60e79f9e27`.
- Candidate: `feat/7-image-evidence`; the PR records exact pushed checkpoint heads.
- Canonical context: docs/image-evidence.md, config/image-evidence-tools.v1.json, schemas/image-evidence.v1.schema.json, image scripts/locks, Taskfile.yml and [roadmap #25](https://github.com/egohygiene/realm/issues/25).

## Implemented boundary and actual checks

The stdlib producer validates exact source/build inputs, local configuration
identity and native platform; runs installed lock/non-root smoke; uses exact
pinned Syft/Grype executables and a fresh explicit database; and publishes a new
checksummed limited bundle without replacement. The portable verifier re-derives
available image/package/scanner/database facts from checked bytes. Declared-intent
SPDX, mutable tags and configuration IDs cannot become registry/signature proof.
All findings and ignored matches remain visible. Runtime configuration and
private paths are removed from portable tool reports; raw hashes remain labelled.

The four first-checkpoint regressions failed as expected (one failure, three
missing-file errors); baseline 97 tests had passed. Implementation checkpoint guards passed 17 methods; review hardening now passes
25 methods, including actual no-replace filesystem and owned-child deadline
controls plus synthetic creation/execution/ownership/late-timeout seams.
Ruff check/format pass after initial routine context-manager/import corrections.
Early independent review found finite-overflow/type seams and deeper package/
source bindings; the implementation repairs them and adds focused regressions.
The reviewed implementation checkpoint passed 114 full Task tests. Review
hardening freezes producer bytes during capture and separates daemon creation
from execution deadlines, retaining the full owned container ID for cleanup. Exact current full checks are recorded in
PR #58; code changes require a fresh actual capture before the final receipt.

Initial actual unmodified Docker build failed apt TLS verification. A standalone
Dockerfile-only repair `d6f3604d0f787cc8a2b6c97d70bd3122f81a8203` supplies optional
BuildKit CA trust for that RUN without persisting trust material or changing
locks/source pins. Root's exact clean native AMD64 build and installed-lock,
non-root smoke, CA/config absence and source-metadata probes passed.

An actual timeout probe exposed late Docker creation after initial absence. Two
newly owned Created sleep-test containers were verified and removed by exact
name/nonce/image/command/ID; no unrelated resources were changed. The repaired
create/start state machine requires fresh actual execution proof before its final
receipt. Indeterminate creation remains non-success with bounded recovery.

The first actual producer prototype then passed on that exact image with Syft
1.55.0 and Grype 0.121.0: 293 installed packages plus the SPDX container root,
1,689 reported matches and 3,015 ignored matches. This is not a clean-image or
release verdict. Review changes require final committed-code capture before
promoting a current receipt; the prototype remains attributed to its own code.

## Parallel work, remaining gates and next action

#10 owns generated Dev Container output and reuses the exact small CA commit.
#17 stacks on #7's evidence interface, verifies its actual artifacts and keeps
crypto/registry publication independent. Reconcile Taskfile and competing prose
handoffs semantically at integration; preserve historical audit/creative bytes.

Next: remotely checkpoint the implementation, finish independent exact-head
review, rerun actual capture at the reviewed code hash, add a safe limited
receipt and final checks, then leave PR #58 draft for maintainer review.
Full #7 remains open for native ARM64, signatures/provenance, accepted producer
compatibility and actual approved distribution. Hosted Actions are deferred;
every checkpoint includes `[skip ci]`. No release/tag/publication, signing,
workflow dispatch, paid resource, issue closure or merge occurred.

Keep private paths, credentials, environment values and unrestricted logs out
of public evidence. Refresh this snapshot after validation and before handoff.
