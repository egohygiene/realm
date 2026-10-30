# Realm continuity

## Current checkpoint

Observed 2026-10-30. This repository-owned prose handoff records context, not
permission or a new machine-enforced continuity contract. Live repository state,
applicable instructions and canonical sources outrank this snapshot.

- Main includes [PR #55](https://github.com/egohygiene/realm/pull/55) at merge `19dc1faf978a2135fd9b2bc4c89f9c9da89964df`: bounded Mantle source activation preparation for #8.
- [PR #56](https://github.com/egohygiene/realm/pull/56), branch `feat/39-devcontainer-boundary`, is being reconciled onto that main for merge. Reviewed source head: `09f8dd6f571762c1411c9b428000d00e1c72390a`. Its PR records the reconciled pushed head.
- Historical audit [PR #52](https://github.com/egohygiene/realm/pull/52) remains open at `1fdd8dd402fc2f559af8b63cb8bc3290479d5412`, next in the merge sequence. Preserve its report and evidence bytes when refreshing operational pointers.
- Canonical context: [roadmap #25](https://github.com/egohygiene/realm/issues/25), owning issues #8/#39/#10, ARCHITECTURE.md, DECISIONS.md, Taskfile.yml and the guides below.

## Integrated source and ownership

`docs/mantle-shell.md` uses the actual public Bash/Zsh `.shellrc` and native Fish
entrypoints. Mantle is sourced, never substituted for a login-shell executable.
`config/mantle-source-canary.json` pins Mantle source
`0f54fa6e100c5b86af64aa383e41eed8c64e363a`; `tools/realm_mantle.py` verifies its
archive before bounded parsing or isolated activation, publishes acquisition
without replacement and terminates owned process groups on deadlines.
Task check validates the pin offline; acquisition and canary are explicit Tasks.
The source/adapter-bound receipt is `evidence/mantle-source-canary.json`.

The #39 standards checkpoint adds proposed ADR-0004, parallel projection
architecture, thirteen property families and four documented host expectations
in `catalog/devcontainer-boundary.v1.json`. The bounded stdlib checker verifies
Realm's own closed mapping and reference policy, plus exact official base-schema
bytes. It does not implement an emitter or a complete Dev Container schema engine.
Profiles and resolved-profile v1 remain canonical; missing overlay fields are
not invented. Issue #10 owns generation and the first generated Task/Mantle
canary; subsequent host qualification returns to #39.

The authored reference and typed limited receipt under `docs/evidence` bind
fixture SHA-256 `8dfee6fd919c7aad21ebdf31a97e3008b1c6a6110b9f8b84a48c44d8984adc26`,
CLI 0.90.0 and the immutable base schema/image. The offline checker never imports
that external receipt as authentication and reports unperformed layers honestly.

## Verification

- Reviewed #8 source passed 77 tests and all offline gates; a fresh pre-merge replay also passed. Reviewed #39 source passed 85 tests and all offline gates.
- Exact original heads `276467eebe9da3586f1bb2d53ffdbeb0d31aa29d` and `09f8dd6f571762c1411c9b428000d00e1c72390a` passed a combined 97-test qualification. Both source candidates had independent review with no remaining source blocker.
- The real reconciliation retains that qualified source byte-for-byte outside the operational handoff. The Taskfile retains both new checks and all existing tasks; its union is compared to the qualified integration. Fresh merge checks are recorded in PR #56.
- Earlier actual #8 evidence: 24 Linux AMD64 Bash 5.2.37/Zsh 5.9/Fish 4.0.2 process checks, hostile inherited-startup isolation and seven restricted local Docker checks. This is source qualification, not a published Mantle release or Realm image build.
- Earlier actual #39 evidence: official Draft 2019-09 schema validation and CLI interpretation/start/exec/reopen/recreate of the unchanged authored reference, including user/environment/workspace observations and owned-container cleanup. Recreation is not a Dockerfile/Codespaces rebuild.
- Own schema definitions, mapping/report states, limited receipt and source bindings passed independent JSON Schema checks. Review corrected unsafe archive metadata/DEFLATE handling, root aliases, OCI grammar, property paths and host expectations. Unsupported proof requests remain nonzero/unavailable.

## Remaining acceptance and next action

Keep #8 open for a reviewed published Mantle release, independent artifact
verification, accepted release selection and actual image/projection/platform
qualification. Keep #39 open for #10's generated-profile canary, actual IDE/cloud
host proof and sibling adoption. Authored-reference execution establishes no
Task/Mantle/Feature/lifecycle/forwarding/GPU or VS Code/Codespaces/DevPod outcome.
Native macOS/ARM64/Windows, Nix/workstation, signatures/provenance and hosted
qualification remain separate gates. Hosted Actions are deferred; checkpoint and
merge messages include `[skip ci]`. No release, tag or paid resource was created.

Finish PR #56's checked reconciliation, merge it, then reconcile audit PR #52
against the resulting main while preserving historical report/evidence. Refresh
this handoff and the dated roadmap pointer before the next batch. Do not turn
source preparation into issue acceptance or publication claims. Keep credentials,
private paths, environment values and raw logs out of public evidence.
