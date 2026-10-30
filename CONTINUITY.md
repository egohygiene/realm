# Realm checkpoint

This is a concise operational handoff, not a new machine-enforced continuity
contract. Repository instructions, live state and canonical sources outrank it.

The candidate `feat/39-devcontainer-boundary` starts from verified main
`ef018932ac6c5096295aeee11beeb45ea0299184`. It defines the #39 standards/mapping
checkpoint. Issue #10 still owns generated projections and the first generated
Task/Mantle canary; later host proof returns to #39 without a circular gate.

Implementation checkpoint: the bounded stdlib checker, ADR-0004, parallel
projection architecture and offline Task integration are implemented. The
regression checkpoint `272a3a2` first reproduced the expected missing-checker
failure. Current focused tests pass all 19 methods; `task check` passes 84 tests,
catalog/profile/package checks, Bash syntax, ShellCheck, byte compilation and
diff whitespace checks. Ruff check and format pass on the new Python files.
Independent JSON Schema checks pass for both own schema definitions, the mapping,
three report states and the reference against the pinned official Draft 2019-09
base schema. No complete Dev Container schema engine, Realm emitter or
publication is claimed.

Review corrected CLI forwarding/resource expectations, nonexistent resolved
field paths, root user aliases and overly broad OCI names. The unmodified
authored reference remains SHA-256
`8dfee6fd919c7aad21ebdf31a97e3008b1c6a6110b9f8b84a48c44d8984adc26`.
Separate official CLI interpretation and local Linux AMD64 start/exec/reopen/
recreate evidence passed for that authored reference. These do not establish
generated-profile, Task, Mantle or host IDE/cloud conformance; the read-only
checker continues to report those external layers as not performed.

Parallel Mantle activation work is draft [PR #55](https://github.com/egohygiene/realm/pull/55).
Preserve its source and catalog selections. Audit draft
[PR #52](https://github.com/egohygiene/realm/pull/52) remains separate; preserve its
historical audit bytes. Shared documentation, Taskfile and this handoff may need
semantic reconciliation at merge.

Next: independent implementation review, record the bounded public reference
receipt and final checks, then hand off the draft candidate for maintainer review.
VS Code, Codespaces, DevPod, generated-profile conformance, sibling adoption,
Nix/workstation adapters and paid/remote resource authorization remain separate
gates. No merge, tag, release, hosted dispatch or paid resource is performed here.
