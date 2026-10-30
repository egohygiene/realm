# Realm release checkpoint

Observed 2026-10-30. This concise prose handoff records context, not authority or
an adopted machine-enforced continuity contract. Live instructions, source and
work-tracker evidence outrank this snapshot.

## Current objective and dependency

Prepare the current-v1 container-image release convention for #17 in draft
[PR #59](https://github.com/egohygiene/realm/pull/59), branch
`feat/17-container-release`. It targets image-evidence
[PR #58](https://github.com/egohygiene/realm/pull/58), branch
`feat/7-image-evidence`, currently incorporated through
`9eccc1062aa14f8ca06c9d045acf21f4319313e1` from main
`0ebdc4d3562a0af0f806876c5dd81d60e79f9e27`. The PR records the exact pushed
implementation head. The actual #7 verifier is incorporated in this reconciliation; final reviewed-code
receipt validation and independent joined review remain pending.

## Implemented bounded source

The declaration selects an incubating/advisory, unreleased `container-image`
profile with one `git-tag` authority and planned delivery channels. Root
CHANGELOG keeps Unreleased. AGENTS and docs/releasing.md explain the actual
scope, compatibility, immutable tags/digests, partial-publication recovery,
rollback and retention. No version/tag or release history is invented.

`tools/realm_release.py` checks the narrow selected Realm profile and exact
source-locked contract bytes, plans read-only, emits an exclusive review packet
without applying the changelog patch, and maps verified #7 local evidence into
checksum-complete portable Relay records. The root SPDX document indexes the
exact per-platform installed SBOMs; it is not a merged package inventory.
Verification reconstructs all root records from owner-verified receipts rather
than trusting checksum-complete arbitrary JSON. Output creation is exclusive
with cleanup, not atomic visibility; complete-inventory verification is required.

The real manual workflow has only read permissions, checks exact current-main
identity and writes bounded review evidence. The literal Task dispatch names
that exact workflow. It is a review handoff, not a credentialed publisher.
Local-only v1 evidence and all results keep release_ready false; requested
release readiness remains nonzero/unavailable.

## Actual checks and remaining validation

- Original unchanged-main `task check`: all 97 tests and offline gates passed.
- Regression checkpoint `c2579a50579c8bcb50654428cf6163c69f121a4d` is pushed and remote-verified. Its nine methods initially failed as expected (five assertions and ten subcase errors) because the adapter/assets were absent.
- Current focused `python3 -m unittest discover --start-directory tests --pattern test_realm_release.py --verbose`: all 22 methods passed, including actual-owner fixture roundtrips, rewritten-root/owner contradictions, no-tool initialization traps and deterministic captured-copy mutation. Joined `task check` passed 129 tests initially and 136 tests after the first review repair; the final expanded source will be checked again after the predecessor delta. New pure-mapping fixtures test bytes and contradictions only; they are not image-owner or authentication proof.
- Exact Aether Draft 2020-12 validation of the declaration and own report/schema checks pass. Ruff check/format, Python 3.9 grammar and whitespace pass. Initial Ruff import/check flags and missing-yet-unimplemented functions were repaired; no checks were weakened.
- Independent review confirmed pinned contracts and identified working-input provenance and lowercase timestamp seams. Plans now separate HEAD from clean/dirty working input checksums, bind the prepared patch to recorded bytes and normalize valid lowercase RFC3339. Focused controls pass. Independent review reproduced a copy-consistency defect after owner verification; the new regression failed before repair. Captured payload bytes now recheck every receipt hash/size and cached receipt/root metadata is decoded without rereading its path. Shared source-input hashes across platform records must agree.
- Actual large prototype image-owner evidence passed owner verification, portable bundle creation and verification; root SPDX index passed the exact official SPDX 2.3 schema. This prototype is attributed to its original producer bytes; final reviewed-code capture is pending. Required release readiness returns nonzero/unavailable.
- Independent contract inspection confirms vendored bytes and highlights Relay's limited file/checksum boundary. The actual current EgoLint consumer reports advisory rollout with all seven release checks passed and zero release findings. Its aggregate exits 1 with thirteen portability findings, all matching the predecessor baseline; no aggregate clean claim is made. Final reviewed-code #7 bundle qualification, full Task and combined checks remain pending.

## Pins, gates and next action

Current-v1 owner source selections remain Aether
`8a2a3d08f3aa9da3847bd5277843506ab855192e` (draft) and Hygiene
`28f9d6c7519d820644572634ba4476614f418d83` (proposed), with no GitHub Releases
when checked. Published Relay v1.5.0 resolves to
`1eada5142f7fc7da7862f335589e3b8f5884ffaf`; tag signature verification is
unavailable. No successor Hygiene #65 authority is adopted.

Next: finish the ordinary #58 implementation reconciliation, exercise its final
reviewed local receipt through bundle creation and portable verification, reject
spoofed records with clean controls, finish full Task/native/schema checks and
independent joined review, then push the final checkpoint. Parallel #10 owns generated
Dev Containers; shared Task/README/handoff need semantic combined reconciliation.

Full #17 acceptance remains open for accepted compatible producer evidence,
genuine native multiarch qualification, public registry manifest/index identity,
verified signatures/provenance, the owner registry adapter and explicit
publication approval. Hosted Actions are deferred; all new commits include
`[skip ci]`. No merge, tag, release, signing, publication, workflow dispatch,
paid resource or issue closure is performed. Preserve audit/assets/locks/profile
identity; exclude credentials, private paths, environment values and raw logs.
ADR not required: this consumes existing owner protocols and adapter boundaries.
