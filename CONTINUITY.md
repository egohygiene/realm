# Realm checkpoint

This is a concise operational handoff, not a new machine-enforced continuity
contract. Repository instructions, live state and canonical sources outrank it.

The candidate `feat/39-devcontainer-boundary` starts from verified main
`ef018932ac6c5096295aeee11beeb45ea0299184`. It defines the #39 standards/mapping
checkpoint. Issue #10 still owns generated projections and the first generated
Task/Mantle canary; later host proof returns to #39 without a circular gate.

Implementation checkpoint `76f2794`: the bounded stdlib checker, ADR-0004, parallel
projection architecture and offline Task integration are implemented. The
regression checkpoint `272a3a2` first reproduced the expected missing-checker
failure. Final focused tests pass all 20 methods; `task check` passes 85 tests,
catalog/profile/package checks, Bash syntax, ShellCheck, byte compilation and
diff whitespace checks. Ruff check and format pass on the new Python files.
Independent JSON Schema checks pass for all three own schema definitions, the
mapping, three report states, the limited reference receipt with three prohibited
claim controls, and the reference against the pinned official Draft 2019-09 base
schema. The public receipt is source-bound by an offline test and is never
imported as authentication by the checker. No complete Dev Container schema
engine, Realm emitter or publication is claimed.

Review corrected CLI forwarding/resource expectations, nonexistent resolved
field paths, root user aliases, overly broad OCI names and the distinction
between ignored Codespaces bind mounts and allowed volume mounts. The unmodified
authored reference remains SHA-256
`8dfee6fd919c7aad21ebdf31a97e3008b1c6a6110b9f8b84a48c44d8984adc26`.
Separate official CLI interpretation and local Linux AMD64 start/exec/reopen/
recreate evidence passed for that authored reference. These do not establish
generated-profile, Task, Mantle or host IDE/cloud conformance; the read-only
checker continues to report those external layers as not performed.

Parallel Mantle activation work is draft [PR #55](https://github.com/egohygiene/realm/pull/55).
Its reported final head is `276467eebe9da3586f1bb2d53ffdbeb0d31aa29d`;
preserve its source and catalog selections. This candidate is draft
[PR #56](https://github.com/egohygiene/realm/pull/56). Audit draft
[PR #52](https://github.com/egohygiene/realm/pull/52) remains separate; preserve its
historical audit bytes. Shared documentation, Taskfile and this handoff may need
semantic reconciliation at merge.

Independent implementation review is clear: focused tests and additional deep
JSON, nonfinite, malformed environment/Feature and unavailable-proof probes
passed. The limited receipt validates and matches the fixture/mapping pins;
root review also confirmed its facts, sanitized commands, hashes and scope.

Next: maintainer review of draft PR #56, followed by semantic reconciliation with
PR #55 if accepted. The standards/mapping checkpoint is complete as a candidate.
VS Code, Codespaces, DevPod, generated-profile conformance, sibling adoption,
Nix/workstation adapters and paid/remote resource authorization remain separate
gates. No merge, tag, release, hosted dispatch or paid resource is performed here.
