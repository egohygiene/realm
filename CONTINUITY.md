# Realm continuity

## Current checkpoint

Observed 2026-10-30. This concise repository-owned handoff is context rather than
permission or a new machine-enforced continuity contract. Live state and
canonical sources outrank it.

- Objective: prepare the first generated base Dev Container slice for [#10](https://github.com/egohygiene/realm/issues/10).
- Independent base: main `0ebdc4d3562a0af0f806876c5dd81d60e79f9e27`, including merged #8/#39 preparation and historical audit #52.
- Candidate branch: `feat/10-devcontainer-projection`; diagnosis/regression checkpoint. The draft PR records its pushed head and later stages.
- Canonical sources: catalog/profiles, resolved-profile v1, the exact base Dockerfile/scripts/locks, proposed ADR-0004, Dev Container boundary mapping and [roadmap #25](https://github.com/egohygiene/realm/issues/25).

## Diagnosis and intended boundary

The resolver declares Dev Container intent, but no emitter turns it into a
buildable local template. The authored #39 reference is not emitted Realm intent
or installed-profile proof. The regression checks demand a relocatable generated
bundle for base AMD64/ARM64, exact resolved-manifest and recipe binding, read-only
drift detection, controlled unsupported input, and no overwrite or symlink escape.

The implementation will support only a faithful minimal base, preserving the
canonical profile and resolved v1 contract. Unsupported language, service and
artifact profiles must fail instead of silently dropping capabilities. Local
source generation is not registry publication. Features, Nix/workstation,
released Mantle, and IDE/cloud qualification remain broader acceptance criteria.

## Validation and next action

The unchanged base passed `task check`: all 97 tests and declared offline gates.
The new focused regression
`python3 -m unittest discover --start-directory tests --pattern test_realm_devcontainer.py -k generated_bundle_matches_same_resolved_manifest --verbose`
failed as expected for both architecture subcases because the emitter is absent.
Ruff check/format and whitespace checks passed after correcting import order and
an unnecessary suppression. The full new suite is not presented as passing.

Next: implement deterministic generation and exact source/lock checks, run all
focused tests and `task check`, then independently review and qualify the actual
generated bundle using the official schema/CLI and available local runtime.
Parallel #7 owns installed-image evidence and #17 owns the manual release adapter;
coordinate immutable image/source receipts without copying sibling code.

## Gates, preservation and privacy

Full #10 includes Features publication, Nix/workstation adapters and broader
conformance; keep it open. Full #8/#39 retain published Mantle, generated canary,
and actual supported-host proof. Hosted Actions are deferred and all new commits
use `[skip ci]`. No merge, tag, release, signing, publication, workflow dispatch,
paid resource or manual issue closure is performed.

Preserve historical audit report/evidence, artwork, package locks and canonical
catalog/profile identities. Public artifacts exclude credentials, private paths,
environment values and raw logs. Refresh this operational snapshot from actual
results before the next PR handoff.
