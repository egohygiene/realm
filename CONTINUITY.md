# Realm continuity

## Current checkpoint

Observed 2026-10-30. This repository-owned prose snapshot records context, not
permission or a machine-enforced continuity contract. Live instructions,
canonical sources and verified work-tracker state outrank this handoff.

- Objective: review bounded installed-image evidence for [#7](https://github.com/egohygiene/realm/issues/7), [draft PR #58](https://github.com/egohygiene/realm/pull/58).
- Independent base: main `0ebdc4d3562a0af0f806876c5dd81d60e79f9e27`.
- Candidate: `feat/7-image-evidence`; the PR records its final pushed head.
- Reviewed producer source: `9e1a5151e0bc5b0729aae5f46cc3e5eb232cf47a`, SHA-256 `6bbeb3b54193f9319f3a45d984929b35f6cf4cb4426988df8ea82a789ebe84d2`.
- Canonical context: docs/image-evidence.md, tool pins, closed receipt schema, image scripts/locks, Taskfile.yml and [roadmap #25](https://github.com/egohygiene/realm/issues/25).

## Material behavior and boundaries

The explicit stdlib producer binds actual native image/configuration identity to
selected source inputs, runs installed-lock/non-root smoke checks, uses pinned
Syft/Grype bytes and an existing fresh database, and atomically publishes a new
limited evidence directory without replacement. The read-only API
`verify_evidence(directory)` hashes and re-derives available facts from the same
checked bytes; it authenticates no producer or registry. Configuration IDs,
scanner manifests and published registry digests remain distinct.

Producer bytes are frozen during capture. Container creation has its own deadline,
returns a full ID before the execution deadline starts, and actual exit status is
checked. Cleanup requires exact name/nonce/image/ID proof. Indeterminate creation
uses bounded scoped polling and remains non-success with an owned-name recovery
action; immediate absence cannot prove a queued create will never complete.
All package/finding/ignored-match data survives runtime-configuration redaction.

## Actual validation and review

- Baseline 97 tests passed. The first four regressions exposed the missing producer/schema (one expected failure, three expected missing-file errors); all are repaired.
- Implementation check passed 114 tests. Further review guards passed 122 tests; the final source-bound observation test adds one method. Exact final Task and lint results are recorded in PR #58.
- Independent reviews cleared the original implementation and the exact final create/start producer. Reviewer replayed focused tests and actual-artifact positives plus rehashed SPDX/Grype/source-lock/overflow/malformed/auth-promotion negatives. Review repairs retain positive controls.
- Initial unmodified Docker build failed apt TLS verification. Standalone commit `d6f3604d0f787cc8a2b6c97d70bd3122f81a8203` adds optional ephemeral BuildKit CA trust. Its clean native AMD64 image build, installed-version/lock/snapshot verification, default-user smoke, source metadata and CA/config absence probes passed. Locks, pins and base policy are preserved.
- Actual resource probing exposed late daemon creation after a short run-client timeout. Two newly owned Created sleep containers were verified and removed; the failed observation is retained. The repair then passed actual explicit-create/start testing: full ID before execution, Running observed before the two-second command deadline, matching running container removed after client timeout, and final absence. Network none, read-only root, non-root UID 1000 and dropped capabilities were used.
- Final actual producer capture at `2026-10-30T20:00:56Z` exited zero, bound the exact reviewed producer hash above, verified all artifacts and recorded 293 installed packages, 294 SPDX packages including the container root, and 13 locked roots.
- Grype reported 1,689 matches and 3,015 ignored matches: 76 Critical, 412 High, 276 Medium, 77 Low, 799 Negligible, 49 Unknown. This is not a clean-image verdict or exploitability assessment. Database v6.1.10 was built `2026-10-30T06:23:28Z`; its exact file/archive hashes and age are recorded.
- A separate actual capture in an owned three-file code capsule received an ordinary comment edit after capture began. It rejected with controlled exit 1, published no final directory, cleaned temporary staging and left canonical source unchanged. It did not relabel old running code with new source bytes.
- Independent Draft202012/meta/registered-format checks pass for the closed receipt; the actual installed-image SPDX passes the immutable official SPDX 2.3 Draft7 schema and formats. All nine exported files pass private-path/runtime-marker checks. Python 3.9 grammar checks pass; actual runtime qualification is Linux AMD64 only.

The safe [observation receipt](docs/evidence/image-local-capture.v1.json) binds the
source, producer, tools and artifact hashes. It is an index, not the full portable
bundle or authentication. Full actual artifacts remain with validation evidence.
Official tool archive checksums were verified; Sigstore/provenance were not.

## Parallel work, gates and recovery

[#10 / draft PR #57](https://github.com/egohygiene/realm/pull/57) owns the generated
Dev Container slice and reuses the exact CA commit. [#17 / draft PR #59](https://github.com/egohygiene/realm/pull/59)
stacks on #7 and consumes the same artifact verifier. Reconcile Taskfile and
competing handoffs semantically; preserve historical audit and creative bytes.

Keep full #7 open for native ARM64 scanner/build qualification, reviewed finding
disposition, accepted producer compatibility, real image signatures/provenance
and separately approved registry distribution. Hosted Actions remain deferred.
No merge, release/tag, signing, publication, workflow dispatch, bot review request,
paid resource or manual issue closure occurred. Every new checkpoint uses
`[skip ci]`.

Next: verify final remote heads, review #57 then #58 then stacked #59 and their
combined checks. Before later image/source changes, refresh source-bound local
capture; before publication, satisfy the owning release/crypto/host gates.
Keep private paths, credentials, environment values and raw logs out of public
source. This handoff grants no additional authority.
