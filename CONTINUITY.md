# Realm continuity

## Current checkpoint

Observed 2026-10-30. This repository-owned prose handoff is context, not permission
or machine-contract adoption. Live state and canonical sources outrank it.

- Objective: review the bounded generated base Dev Container candidate for [#10](https://github.com/egohygiene/realm/issues/10).
- Independent base: main `0ebdc4d3562a0af0f806876c5dd81d60e79f9e27`.
- Candidate: `feat/10-devcontainer-projection`, draft [PR #57](https://github.com/egohygiene/realm/pull/57); its description records the final pushed head/checkpoints.
- Runtime/source qualification pin: `03d9e436a5b4c8c73560e10d6d82476d3533f346`; generator SHA-256 `d074299f13b5a66737c147f79521c85fdf2b764e450306f6c3c8d77c60830748` remains unchanged by receipt/handoff additions.
- Parallel #7/[PR #58](https://github.com/egohygiene/realm/pull/58) owns installed-image evidence; #17 owns the manual release adapter. Reconcile shared Taskfile/README/continuity by live evidence.

## Material changes and ownership

`tools/realm_devcontainer.py` emits relocatable base AMD64/ARM64 source bundles
from the existing resolver, configuration and lock contracts. Each carries the
exact Realm-owned recipe/scripts/selected lock/canonical inputs/license, unchanged
resolved-profile v1 JSON, relative-path configuration and a closed source receipt.
Unsupported artifact/language/service intent fails rather than disappearing.

Bounded strict JSON rejects duplicates/non-finite data; source reads cap individual
files at one MiB, all canonical inputs at eight MiB and profile-directory entries
at 128. Output traversal/errors cap at 64 members. Non-following handles reject
symlinks/special files; rendering exclusively creates new output. Read-only checks
compare exact inventory/bytes and Git owner-executable roles, rejecting special
mode bits. Host read/write/group permissions remain separate runtime concerns.

The shared optional CA transport patch from #7 source
`d6f3604d0f787cc8a2b6c97d70bd3122f81a8203` is cherry-picked as
`5130152b6063b1f7affbb485f730307735970333`; both bundles copy the exact recipe.
Existing package locks, package intent and frontend/base-image pins are preserved.
The source identity and local image configuration ID are not a Git commit or an
authenticated published OCI digest.

## Actual validation and independent review

- The original base passed 97 tests; the generation regression initially failed as expected in both architecture subcases because no emitter existed.
- Independent review reproduced and repaired two P2 defects: a 12,299,076-byte non-emitted graph bypassed the output-only cap, and clean restrictive-umask checkout modes falsely failed literal permission comparison. Aggregate/enumeration caps and Git owner-executable semantics now reject real drift while retaining clean controls.
- Reviewed source passed all twelve focused methods and all 109 Task tests/offline gates. A fresh restrictive-umask independent checkout passed the same suite plus 22 additional schema/grammar/IO controls. The exact over-budget reproduction now rejects before output. No source blocker remained.
- Final local `task check` passed all 110 tests, including the added receipt/source-binding guard, and every offline gate. Ruff check/format, Python 3.9 grammar, whitespace, own closed schemas and pinned official Draft201909 configuration validation passed. Initial Ruff/import and ShellCheck PATH setup failures were corrected and recorded in PR #57.
- The typed limited receipt `docs/evidence/devcontainer-generated-base.v1.json` binds the source/configuration/bundle/overlay hashes, official CLI 0.90.0 and Docker 28.4.0. Both generated architecture configurations and the consumer overlay passed official schema validation.
- Actual generated Linux AMD64 build/start, original emitted CLI interpretation, non-root workspace/runtime smoke, installed-lock verification, same-container reopen and different-container recreation passed. Original generated JSON and clone stayed unchanged; uniquely owned containers were cleaned.
- Actual canonical Task workflow passed all 109 tests inside the reviewed container snapshot. The checksum-pinned unreleased Mantle source passed 24 actual Bash/Zsh/Fish install/activation/status/recovery cases in temporary homes. The later receipt-only guard is a separate local check, not an invented 110-test container result.

## Qualification overlays and limits

Execution used a separately hashed local consumer configuration: equivalent
absolute recipe/context paths, optional BuildKit CA transport and a read-only
qualification-input bind, retaining emitted build arguments. Explicit Task 3.53.1
and exact signed-snapshot Python/Fish/ShellCheck packages were disposable test
inputs, not capabilities of the thirteen-root built base. Direct tool roots are
not a complete dependency inventory. CLI package signatures/provenance remain
unverified; Mantle is unreleased source, not authenticated release integration.

Three harness environment failures preceded success: sudo proxy stripping,
restrictive staging permissions blocking apt's CA read, and password-requiring
direct sudo to the apt user. Scoped proxy preservation, readable owned public
inputs and root-runuser preflight fixed these without generator/lock/image input
changes or disabled TLS. Raw logs and machine paths remain private.

## Next action, preservation and acceptance

Review PR #57's source and limited metadata, then validate the combined batch
with #7/#17 and reconcile operational handoffs. Keep full #10 open for reviewed
Feature/template distribution, Nix/workstation dry-run/uninstall adapters and
broader same-manifest conformance. #8 retains published verified Mantle and #39
actual supported-host/sibling proof. No native ARM64, IDE/cloud, lifecycle,
forwarding/GPU, no-cache rebuild, signatures or registry publication is inferred.
Hosted Actions remain deferred and all new commits include `[skip ci]`.

No merge, release, tag, signing, registry write, workflow dispatch, bot review,
paid resource or manual issue closure is performed. Preserve historical audit
bytes, creative assets and canonical profile identities. Public evidence excludes
credentials, private paths, environment values and raw logs.
