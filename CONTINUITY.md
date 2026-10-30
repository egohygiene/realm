# Realm continuity

## Current checkpoint

Observed 2026-10-30. This repository-owned prose handoff records context, not
permission or a new machine-enforced continuity contract. Live repository state,
applicable instructions and canonical sources outrank this snapshot.

- Verified main before audit integration: `b0d53ffda312ef82b0c3af16540b898a9ea3df82`.
- #50 and #51 repairs are integrated through [PR #53](https://github.com/egohygiene/realm/pull/53) and [PR #54](https://github.com/egohygiene/realm/pull/54).
- #8 source activation preparation merged through [PR #55](https://github.com/egohygiene/realm/pull/55) at `19dc1faf978a2135fd9b2bc4c89f9c9da89964df`.
- #39 standards/mapping merged through [PR #56](https://github.com/egohygiene/realm/pull/56) at `b0d53ffda312ef82b0c3af16540b898a9ea3df82`; reconciled candidate `e9dc8d3f09e999d8ec6b7d92382b7bc150469ddc`.
- [Audit PR #52](https://github.com/egohygiene/realm/pull/52) integrates its historical report/evidence and refreshes only the operational roadmap pointer and this handoff. The PR records its final head and merge state.
- Next implementation batch: not selected. Read the requested issue and live [roadmap #25](https://github.com/egohygiene/realm/issues/25) before starting a new issue-sized branch from updated main.

## Source ownership and acceptance

`docs/mantle-shell.md` uses public Bash/Zsh `.shellrc` and native Fish activation.
Mantle is sourced, never substituted for a login-shell executable.
`config/mantle-source-canary.json` pins source
`0f54fa6e100c5b86af64aa383e41eed8c64e363a`; `tools/realm_mantle.py` verifies
archive bytes, bounds complete gzip expansion before tar metadata parsing,
rejects unsafe inventory, publishes acquisition without replacement and runs
isolated real-shell canaries with owned process-group deadlines. Offline Task
check validates the pin; acquisition/canary are explicit separate Tasks.
The source/adapter-bound receipt is `evidence/mantle-source-canary.json`.

#39's standards checkpoint adds proposed ADR-0004, parallel projections and a
thirteen-family/four-host mapping. `tools/realm_devcontainer_boundary.py` checks
the closed mapping, bounded reference policy and exact official base-schema
bytes. It is neither an emitter nor a full Dev Container schema engine. Profiles
and resolved-profile v1 remain canonical. The authored reference is not generated
by Realm #10; the separate typed limited receipt under `docs/evidence` records
actual CLI/local-container observations and explicitly unproved layers. The
read-only checker does not import external receipts as authentication.

Keep #8 open for a reviewed published Mantle release, independent artifact
verification, accepted release selection and actual image/projection/platform
qualification. Keep #39 open for #10's generated-profile Task/Mantle canary,
actual IDE/cloud host proof and sibling adoption. Later host proof returns to
#39 without a circular prerequisite. Optional Nix/workstation and broader
services remain separate; they do not block the minimal project boundary.

## Verification and preserved evidence

- The original #8/#39 heads `276467eebe9da3586f1bb2d53ffdbeb0d31aa29d` and `09f8dd6f571762c1411c9b428000d00e1c72390a` had independent review and passed a combined 97-test qualification.
- Fresh pre-merge checks passed all 77 tests for #55 and all 97 tests plus declared offline gates for #56. Its real reconciliation preserved every one of the twenty qualified non-handoff files byte-for-byte, including the combined Taskfile. Merged main matches the reconciled candidate tree.
- Earlier #8 evidence passed 24 actual Linux AMD64 Bash/Zsh/Fish process cases, inherited-startup isolation and seven restricted local Docker cases. Earlier #39 evidence passed official Draft 2019-09 schema validation and CLI 0.90.0 interpretation/start/exec/reopen/recreate of the unchanged authored reference. Own schemas, mapping/report/limited-receipt instances and source bindings passed independent JSON Schema checks.
- Audit report `audits/realm-engineering-readiness-20261028T064323Z.md` and its evidence JSON retain exact bytes and modes from original PR #52 head `1fdd8dd402fc2f559af8b63cb8bc3290479d5412`.
- That audit describes source `d66a0e4d5a100d287a9745f4c45f055e0a78948b` and its 2026-10-28 tracker state. Its 55-test result, 39-item ledger, negative probes and then-draft delivery record are historical. They are not rerun or rewritten to describe repaired source.
- The audit reconciliation changes only CONTINUITY.md, ROADMAP.md and the two preserved artifacts relative to current main. Artifact identity, JSON/ledger consistency, local links, documentation scope, historical roadmap preservation and whitespace are checked before merge; the PR records the results.

## Limits and recovery

Source checksum proof is not release authentication. Authored-reference execution
proves no generated profile, installed Realm capability, Task/Mantle/Feature,
lifecycle, forwarding, GPU or VS Code/Codespaces/DevPod outcome. Recreation is
not a Dockerfile/Codespaces rebuild. Native macOS/ARM64/Windows, signature and
provenance verification, hosted qualification and publication remain unproved.
Hosted Actions remain deferred; all new checkpoint and merge messages include
`[skip ci]`. No release, tag, deployment or paid resource was created.

Verify the linked PR states and current remote main before resuming. Preserve
historical audit evidence and the truthful external gates. Select no additional
implementation from this handoff alone; the next batch is pending. Keep private
paths, credentials, environment values and raw logs out of public evidence.
