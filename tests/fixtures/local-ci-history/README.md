# Historical qualification inputs

These files preserve original reviewed bytes for the immutable 2026-10-30
receipts in `docs/evidence/devcontainer-generated-base.v1.json` and
`docs/evidence/image-local-capture.v1.json`. They are regression fixtures,
not current runtime evidence or new package-resolution results.

- `generated-base/` files came from the exact recorded qualified revision
  `03d9e436a5b4c8c73560e10d6d82476d3533f346`, under
  `dist/devcontainers/base-linux-amd64/`.
- `catalog/capabilities.json` and the selected package lock came from the
  image receipt's exact source revision
  `d6f3604d0f787cc8a2b6c97d70bd3122f81a8203`. The lock also matches the generated
  receipt's recorded lock checksum.

Each file was read from its Git blob and its SHA-256 verified against the
unchanged owning receipt before capture. Only inputs changed by the local-CI
catalog addition are duplicated here; unchanged recipe, generator, schema and
other source files remain checked against their existing source locations.

Tests verify these original bytes and separately prove that the old runtime
receipts do not qualify the current catalog/projection. Current generated
projections still pass the existing generator's exact check. New runtime
qualification requires its own real run and evidence; these fixtures cannot
upgrade historical observations or establish current ARM64/host support.
