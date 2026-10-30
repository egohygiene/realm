# Realm continuity

## Current checkpoint

- Objective: prepare the bounded Mantle source activation canary for [#8](https://github.com/egohygiene/realm/issues/8); released integration remains gated.
- Verified base: main `ef018932ac6c5096295aeee11beeb45ea0299184`, observed 2026-10-30.
- Candidate branch: `fix/8-mantle-activation`; regression checkpoint, not merged.
- Read issue #8's audit note, `ARCHITECTURE.md`, `DECISIONS.md`, `Taskfile.yml` and `docs/mantle-shell.md` before resuming.

No root AGENTS.md or CONTINUITY.md was present at this base. This concise
repository-owned handoff does not adopt an organization machine contract or
grant authority. The independent historical audit draft [PR #52](https://github.com/egohygiene/realm/pull/52)+and its evidence are untouched. Parallel #39 prepares the Dev Container mapping;
reconcile overlapping documentation and continuity by current evidence.

## Diagnosis and checks

The existing guide describes a nonexistent Mantle executable shell mode. Mantle
is sourced into Bash/Zsh through `.shellrc`, or Fish through its native runtime.
Mantle main `0f54fa6e100c5b86af64aa383e41eed8c64e363a` includes release
preparation, but no published release is available. A source checksum canary
does not satisfy released-artifact acceptance.

`task check` on the unchanged base passed all offline checks and 65 Python tests.
`python3 -m unittest discover --start-directory tests --pattern test_realm_mantle.py --verbose`
currently fails four expected regressions: wrong documented public entrypoints,
missing source pin, missing checksum rejection and missing no-overwrite fetch.
The latter two fail because the bounded adapter does not exist yet.

## Next action and boundaries

Implement explicit immutable acquisition and temporary-home activation checks,
then fix the guide and rerun the offline gate. Test actual available Bash/Zsh/
Fish; label synthetic observations and unverified container/platform behavior.
Do not change Docker SHELL, login shells, catalog release claims, host startup
files, audit bytes, or sibling source. No publication, tagging, dispatch, paid
resources, issue closure or merge is part of this candidate.

Keep source revision, checksum, local/platform evidence and released acceptance
separate. Exclude credentials, private paths, environment values and raw logs
from committed/public evidence. Refresh after checks and before each PR update.
