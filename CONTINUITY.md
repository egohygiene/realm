# Realm continuity

## Current checkpoint

- Objective: review the bounded Mantle source activation candidate for [#8](https://github.com/egohygiene/realm/issues/8); released integration remains gated.
- Verified base: main `ef018932ac6c5096295aeee11beeb45ea0299184`, observed 2026-10-30.
- Candidate: `fix/8-mantle-activation`, [draft PR #55](https://github.com/egohygiene/realm/pull/55); open, draft and unmerged when checked. The PR records the final pushed head.
- Canonical context: issue #8 audit note, [roadmap #25](https://github.com/egohygiene/realm/issues/25), `ARCHITECTURE.md`, accepted ADR-0003 in `DECISIONS.md`, `Taskfile.yml` and `docs/mantle-shell.md`.

No root AGENTS.md or CONTINUITY.md was present at this base. This concise
repository-owned handoff does not adopt an organization machine contract or
grant authority. Historical audit [draft PR #52](https://github.com/egohygiene/realm/pull/52)
and head `1fdd8dd402fc2f559af8b63cb8bc3290479d5412` remain untouched.
Parallel [#39](https://github.com/egohygiene/realm/issues/39) prepares the Dev
Container mapping independently; reconcile README, Taskfile and continuity
semantically before any later merge. No historical audit evidence is rewritten.

## Material changes and ownership

`config/mantle-source-canary.json` binds Mantle commit
`0f54fa6e100c5b86af64aa383e41eed8c64e363a` to its immutable source archive
and SHA-256. `tools/realm_mantle.py` owns explicit no-overwrite acquisition and
isolated real-shell checks. Bytes are verified before parsing or execution;
complete gzip expansion is bounded before tar metadata parsing. Traversal,
links, special/duplicate members and inventory excess reject. Owned process
groups are terminated on deadlines. No sibling implementation is vendored.

The guide uses public Bash/Zsh `.shellrc` and native Fish activation. Mantle
is a sourced environment and CLI, never a replacement login executable.
Docker SHELL, account shells, base image, catalog declaration and host startup
remain unchanged. Task check validates the pin offline; fetch/canary are explicit.
The safe local [receipt](evidence/mantle-source-canary.json) binds the reviewed
adapter checksum and actual results, without raw logs or machine paths.

## Actual checks and independent review

- Unchanged-base `task check`: all offline checks and 65 tests passed.
- Regression checkpoint: four expected failures demonstrated the incorrect guide and absent adapter/pin; all now pass.
- Final `task check`: all offline gates and 77 Python tests passed, including 12 focused Mantle tests. Byte-compilation, shell syntax/ShellCheck, catalogs/profiles/publications, apt locks and whitespace passed.
- Review repaired hidden PAX/GNU metadata expansion and malformed DEFLATE handling. Metadata-heavy, truncated, malformed-deflate and oversized-header controls reject cleanly before writes. The actual checksum-matching archive still unpacks.
- Acquisition guards cover corrupt bytes, preexisting/racing output, unsafe members, mutable pins and missing Fish. Synthetic inputs and deterministic collision injection do not claim product activation or real concurrency. An actual harmless owned-child timeout control passes.
- Actual explicit fetch verified the exact source bytes. Actual Linux AMD64 canary passed 24 process checks with Bash 5.2.37, Zsh 5.9 and Fish 4.0.2: copy install, native interactive hooks without TTY, explicit noninteractive/container and CI activation, status 23, invalid-profile status 64, all-shell missing-runtime/disabled-hook recovery and plain Bash recovery.
- Actual inherited startup/config/home/profile pollution control passed; its supplied synthetic hook was not executed. An independent replay also passed all 12 focused tests and 24 native cases at the receipt's adapter hash.
- Actual local Docker process canary passed seven checks against the existing exact Realm base-image pin, with network disabled, read-only root/source, non-root UID 1000 and restricted capabilities: Bash/Zsh positives, status 23 and invalid-profile status 64, plus plain Bash recovery. This image lacks Fish/Python; it was not a Realm image build or Feature/projection test.
- Python 3.9 grammar, receipt checksum binding, JSON and whitespace checks passed. Independent review found no remaining source blocker after the bounded repairs.

## Gates and limitations

Mantle releases API returned no releases when checked on 2026-10-30. A reviewed
source checksum proves bytes, not release signatures, provenance or published
acceptance. Full #8 still needs a separately approved published verified Mantle
release, accepted release selection and actual image/projection/supported-platform
evidence. The catalog's existing artifact remains declared intent.

No native macOS/ARM64/Windows, real TTY/signal behavior, VS Code, Codespaces,
remote/paid host or hosted qualification is claimed. No release, signing,
publication, tag, dispatch, account/default-shell change, host startup edit,
system package install, audit/creative change, issue closure or merge occurred.

## Next action and privacy

Review PR #55 alongside #39's mapping and retain the release gate before #10
projection work consumes Mantle. Reconcile continuity by live evidence at merge;
keep #8 open for its unreleased-artifact and external acceptance criteria.
Exclude credentials, private paths, environment values and raw logs from public
evidence. Refresh after checks and before the next PR handoff. This file records
context, not permission or proof of later mutable state.
