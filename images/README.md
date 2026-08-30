# Realm images

Realm images are projections of the versioned capability/profile contract, not
independent package lists.

Initial intended image family:

| Image | Profile | Purpose |
|---|---|---|
| `realm-base` | `base` | Small language-neutral foundation |
| `realm-rust` | `rust` | Baseline plus Rust and build tooling |
| `realm-node` | `node` | Baseline plus Node.js and build tooling |
| `realm-python` | `python` | Baseline plus Python and build tooling |
| `realm-full` | `full` | Union of supported non-service development tools |

Host daemons and privileged service capabilities stay outside `full`; they are
selected through the explicit `services` profile or consuming orchestration.
This preserves a useful full workstation toolset without silently granting a
container extra privilege.

`images/base/Dockerfile` consumes the resolved `base` package intent through
snapshot-pinned, per-architecture locks. It contains no independent package
list. See [`base/README.md`](base/README.md) for the image boundary, installed
evidence, and refresh workflow.
