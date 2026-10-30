# Realm release guidance

Before changing release behavior, read [.egohygiene/release.json](.egohygiene/release.json),
[CHANGELOG.md](CHANGELOG.md) and [docs/releasing.md](docs/releasing.md). The selected
container-image convention is incubating/advisory; current-v1 Aether and Hygiene
inputs are immutable source references, not published owner conformance.

Use `release:plan`, `release:prepare` and `release:verify` for local preparation.
`release:publish` dispatches the real manual review workflow; that workflow has
read-only permissions and creates no release or registry artifact. Publication,
signing, attestation and registry credentials require a separately reviewed
repository-owned producer/adapter and explicit publication approval.

Preserve exact version tags, image digests, historical audit bytes and creative
assets. A local Docker config ID is not a registry manifest/index digest. Read
the current prose [CONTINUITY.md](CONTINUITY.md), verify mutable state, and refresh
the handoff after validation. This file adopts no machine continuity contract.
