# Realm continuity

## Current checkpoint

Observed 2026-10-30. This repository-owned prose snapshot records context, not
permission or a machine-enforced continuity contract. Live source, instructions
and owning issues outrank it.

- Objective: prepare bounded installed-image evidence for [#7](https://github.com/egohygiene/realm/issues/7).
- Base: main `0ebdc4d3562a0af0f806876c5dd81d60e79f9e27`; prior audit and #8/#39 preparation are merged.
- Candidate: `feat/7-image-evidence`; regression checkpoint, draft PR to be recorded after creation.
- Canonical inputs: catalog/profiles, immutable base configuration and apt locks, images/base, Taskfile.yml, docs/image-evidence.md and [roadmap #25](https://github.com/egohygiene/realm/issues/25).

## Diagnosis and actual checks

Current profile SPDX files declare requested intent, not an installed image.
No image-evidence producer or typed local receipt exists at the base. The four
new regression controls expose this gap: one expected failure and three expected
missing-file errors. They cover a read-only plan, refusal of mutable tags,
declared-intent substitution and distinct image identities. The unchanged base
passed 97 tests and every offline gate before these intentional regressions.

The first actual unchanged-image build reached apt but failed HTTPS certificate
verification under the managed proxy. No successful image build is claimed.
The next narrow repair supplies optional BuildKit CA trust for that RUN only,
without disabling TLS, persisting session certificates or altering source pins.

## Next action, parallel work and limits

Implement and independently review the producer and its closed contract, then
run actual pinned scanners and image verification on an exact reviewed native
image if supported. Publish no registry/tag/release or signing claims. Preserve
reported vulnerability findings; tool exit zero is not a clean-image verdict.

Parallel #10 owns generated Dev Container projection. #17 owns the manual
release adapter and consumes #7 evidence without confusing local configuration
IDs with registry manifests/indexes or authentication. Separate branches may
update Taskfile and this handoff; reconcile by live evidence at integration.
Full #7 remains open for native ARM64, signatures/provenance, reviewed policy
and actual accepted distribution. Hosted Actions are deferred; every checkpoint
uses `[skip ci]`. No workflow dispatch, paid resource, issue closure or merge.

Keep historical audit/creative bytes unchanged. Exclude private paths,
credentials, environment values and unrestricted logs from public evidence.
Refresh this handoff after validation and before each PR checkpoint.
