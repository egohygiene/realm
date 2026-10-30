# Installed-image evidence checkpoint

Realm #7 needs evidence from an actual installed image. The existing
`dist/profiles/*/sbom.spdx.json` files describe declared intent and cannot prove
that an image contains those packages or passed a vulnerability scan.

The planned producer accepts an exact local image configuration digest, records
native platform and source identity, runs the pinned scanners and image checks,
and publishes a new evidence directory without replacing earlier records. Its
receipt is limited local evidence. A Docker configuration digest is not a
registry manifest or multi-platform index digest. Registry publication,
signatures and provenance authentication remain separate #17/manual gates.

The first regression checkpoint exposes the absent producer/schema and rejects
mutable image tags and declared-intent substitution. Actual validation commands,
tool pins, report semantics and recovery instructions follow with implementation.

The unmodified base Dockerfile's initial local build reached apt but failed TLS
certificate verification in the managed proxy environment. A narrowly scoped
optional BuildKit CA secret will preserve TLS verification without persisting
session trust material or changing package locks, source pins or base policy.
The unchanged-source failure is not an image-build success.
