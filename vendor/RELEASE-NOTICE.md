# Release contract sources

These files are unmodified public contract data, not sibling implementations.
All three source repositories use the MIT license. Their source revisions,
paths, SHA-256 digests and authority status are recorded in
[`config/release-inputs.v1.json`](../config/release-inputs.v1.json).

- Aether release declaration schema: `8a2a3d08f3aa9da3847bd5277843506ab855192e`, draft contract 1.0.0.
- Hygiene release applicability policy: `28f9d6c7519d820644572634ba4476614f418d83`, proposed policy 1.0.0-alpha.1.
- Relay release profile catalog: `1eada5142f7fc7da7862f335589e3b8f5884ffaf`, published v1.5.0.

Source licensing notices remain in the respective repositories:
[Aether](https://github.com/egohygiene/aether/blob/8a2a3d08f3aa9da3847bd5277843506ab855192e/LICENSE),
[Hygiene](https://github.com/egohygiene/hygiene/blob/28f9d6c7519d820644572634ba4476614f418d83/LICENSE),
[Relay](https://github.com/egohygiene/relay/blob/1eada5142f7fc7da7862f335589e3b8f5884ffaf/LICENSE).

No Aether or Hygiene GitHub Release existed when checked on 2026-10-30.
Immutable source compatibility and owner release/adoption authority remain
separate. Relay's profile validation proves bundle mechanics; it does not
authenticate image signatures, attestations or registry publication.
