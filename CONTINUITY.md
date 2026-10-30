# Realm continuity

## Current checkpoint

Observed 2026-10-30. This repository-owned prose handoff records context, not
permission or machine-contract adoption. Live state and canonical sources
outrank it.

- Objective: review the first generated base Dev Container slice for [#10](https://github.com/egohygiene/realm/issues/10).
- Independent base: main `0ebdc4d3562a0af0f806876c5dd81d60e79f9e27`.
- Candidate: `feat/10-devcontainer-projection`, draft [PR #57](https://github.com/egohygiene/realm/pull/57); implementation checkpoint. The PR records its exact pushed head.
- Parallel installed-image evidence is draft [PR #58](https://github.com/egohygiene/realm/pull/58), issue #7; #17 owns the manual release adapter. Reconcile Taskfile/README/continuity semantically.

## Material changes and source ownership

`tools/realm_devcontainer.py` emits faithful base AMD64/ARM64 bundles under
`dist/devcontainers`, using the unchanged resolved-profile v1 and existing
resolver/configuration/lock validation. Each bundle carries exact Realm-owned
recipe/scripts/selected lock/canonical inputs, resolved JSON, relative-path
configuration and a closed source-bundle receipt. It rejects unsupported intent
rather than dropping artifacts, language runtimes, services or privilege.

The source receipt binds actual generator/resolver/validator bytes and input/file
hashes; no time or machine path enters identity. Source modes follow Git's
executable role; output permissions and inventory are checked exactly. Bounded
strict JSON rejects duplicate/non-finite fields. Source/destination parents are
opened without following symlinks, special files reject, and rendering exclusively
creates a new directory. Interrupted new output is detectable, not auto-deleted.
`check` writes nothing, contacts no host and executes no lifecycle/input commands.

Shared optional BuildKit CA transport from #7 commit
`d6f3604d0f787cc8a2b6c97d70bd3122f81a8203` is cherry-picked as
`5130152b6063b1f7affbb485f730307735970333`. The exact same Dockerfile is copied
into both generated bundles; package locks, image/frontend pins and package
intent are unchanged. A local consumer supplies the optional secret explicitly;
it is not copied into layers or silently embedded in generated JSON.

## Actual checks and limits

- Original base `task check`: 97 tests and offline gates passed.
- Stage-one generation regression failed as expected in both architecture subcases because the emitter was absent.
- Implementation focused suite: all nine methods passed, covering same-manifest/recipe/platform binding, relocation identity, no overwrite, symlinks/FIFO, duplicate/non-finite/oversized input, stale locks, malformed source and damaged/missing/extra/permission-drifted output.
- `task check`: all 106 tests and declared offline gates passed. An initial attempt correctly stopped because ShellCheck was absent from that invocation's PATH; rerunning with the existing pinned tool setup passed.
- Ruff check/format, Python 3.9 grammar, exact shared recipe equality, own Draft202012 schema/receipt validation and both generated configurations against the exact official Draft201909 base schema passed.
- An initial implementation incorrectly treated checkout 0600/0700 umasks as source-role errors. The repair uses Git's executable-role semantics and still checks generated permissions exactly; it does not change canonical file modes.

No generated runtime or host proof is claimed yet. Next: independently review the
complete source, then qualify official CLI interpretation and actual native local
start/exec/reopen/recreate using the exact generated bundle. Any private-CA or
build-metadata consumer overlay and disposable Task/Mantle tooling must have
separate identities and limitations, not masquerade as unchanged generated JSON
or installed base capabilities.

## Remaining acceptance and preservation

Full #10 remains open for reviewed Feature/template distribution, Nix/workstation
dry-run/uninstall adapters and broad same-manifest conformance. Full #8 retains
published verified Mantle; #39 retains actual supported-host/sibling proof. No
ARM64 runtime, IDE/cloud, release authentication or hosted proof is inferred from
source generation or schema checks. Hosted Actions are deferred; every checkpoint
uses `[skip ci]`. No merge, tag, release, signing, publication, dispatch, paid
resource or manual issue closure is performed.

Preserve historical audit report/evidence, creative assets and canonical profile
identities. Public records exclude credentials, private paths, environment values
and raw logs. Refresh this snapshot after final validation and review.
