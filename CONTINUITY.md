# Realm continuity

## Current checkpoint

- Objective: prepare the bounded Mantle source activation canary for [#8](https://github.com/egohygiene/realm/issues/8); released integration remains gated.
- Verified base: main `ef018932ac6c5096295aeee11beeb45ea0299184`, observed 2026-10-30.
- Candidate: `fix/8-mantle-activation`, [draft PR #55](https://github.com/egohygiene/realm/pull/55), implementation checkpoint; open and unmerged when checked.
- Canonical context: issue #8 audit note, `ARCHITECTURE.md`, accepted ADR-0003 in `DECISIONS.md`, `Taskfile.yml` and `docs/mantle-shell.md`.

No root AGENTS.md or CONTINUITY.md was present at this base. This concise
repository-owned handoff does not adopt an organization machine contract or
grant authority. Historical audit [draft PR #52](https://github.com/egohygiene/realm/pull/52)
and its evidence are untouched. Parallel #39 prepares the Dev Container mapping;
reconcile overlapping README, Taskfile and continuity semantically before merge.

## Material changes

`config/mantle-source-canary.json` pins Mantle source commit
`0f54fa6e100c5b86af64aa383e41eed8c64e363a` and its archive checksum.
`tools/realm_mantle.py` owns explicit no-overwrite acquisition and isolated
actual-shell checks. It verifies bytes before parsing or execution, bounds
extraction and creates temporary user homes/prefixes. Nothing is vendored.

The guide now uses public Bash/Zsh `.shellrc` and native Fish activation.
Mantle is a sourced environment and CLI, never a replacement login executable.
Docker SHELL, account shells, base image, catalog declaration and startup remain
unchanged. Task check only validates the pin offline; fetch/canary are explicit.
Mantle has release preparation but no published release; checksums do not prove
signatures, provenance or released acceptance.

## Checks and limits

- Unchanged-base `task check`: all offline checks and 65 tests passed.
- Regression checkpoint: four expected focused failures reproduced the incorrect guide and absent adapter/pin.
- `python3 -m unittest discover --start-directory tests --pattern test_realm_mantle.py --verbose`: nine tests passed, including corrupt acquisition, preexisting/racing output, unsafe archive members, mutable pins and missing Fish. Synthetic controls do not prove Mantle activation or real concurrency.
- Actual explicit fetch verified the exact codeload bytes; actual canary passed 22 process checks using Bash 5.2, Zsh 5.9 and Fish 4.0.2 on Linux AMD64.
- The canary covers temporary copy installation, native interactive hooks without TTY, explicit noninteractive/container and CI activation, status 23, invalid-profile status 64, missing-runtime recovery, disable and hook-free recovery.
- `git diff --check` passed. Exact configured base image was pulled locally; no Docker activation result is claimed yet.

## Next action and boundaries

Obtain independent review, run the complete offline gate and a bounded actual
local Docker process canary, then refresh this handoff. Full #8 remains gated on
a published verified Mantle release, accepted release selection and real image/
projection/supported-platform evidence. This source canary proves no native
macOS/ARM64/Windows, TTY, VS Code, Codespaces or hosted behavior.

No default shell, account, host startup file, system package, audit/creative
bytes, release, tag, publication, workflow dispatch, paid resource, issue closure
or merge was changed/performed. Keep source, local process evidence and released
acceptance separate. Exclude credentials, private paths, environment values and
raw logs from public evidence; refresh after checks and before PR updates.
