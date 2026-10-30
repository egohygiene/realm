# Realm checkpoint

This is a concise operational handoff, not a new machine-enforced continuity
contract. Repository instructions, live state and canonical sources outrank it.

The candidate `feat/39-devcontainer-boundary` starts from verified main
`ef018932ac6c5096295aeee11beeb45ea0299184`. It defines the #39 standards/mapping
checkpoint. Issue #10 still owns generated projections and the first generated
Task/Mantle canary; later host proof returns to #39 without a circular gate.

Current work adds an immutable official schema with attribution, thirteen mapping
families, four documented host expectations and an authored reference. The
adversarial regression suite exists; its default-check case deliberately fails
because the bounded checker has not been implemented. No complete
Dev Container schema engine, Realm emitter, host qualification or publication is
claimed. `python3 -m unittest discover --start-directory tests --pattern
test_realm_devcontainer_boundary.py -k default_check -v` failed as expected
with the missing checker. The independent pinned official schema and CLI
configuration interpretation passed on the unchanged reference; these do not
establish generated-profile, Task or host IDE/cloud conformance.

Parallel Mantle activation work is draft [PR #55](https://github.com/egohygiene/realm/pull/55).
Preserve its source and catalog selections. Audit draft
[PR #52](https://github.com/egohygiene/realm/pull/52) remains separate; preserve its
historical audit bytes. Shared documentation, Taskfile and this handoff may need
semantic reconciliation at merge.

Next: finish the bounded checker, run offline checks and independent official
schema validation, then record exact review and reference-CLI proof limits.
VS Code, Codespaces, DevPod, generated-profile conformance, sibling adoption,
Nix/workstation adapters and paid/remote resource authorization remain separate
gates. No merge, tag, release, hosted dispatch or paid resource is performed here.
