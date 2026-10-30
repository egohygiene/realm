# Realm release checkpoint

Observed 2026-10-30. This concise prose handoff records context, not authority or
an adopted machine-enforced continuity contract. Verify live source and work
tracker state before resuming.

## Current objective and base

Prepare the current-v1 container-image release convention for #17 as one bounded
draft. The branch `feat/17-container-release` is stacked on image-evidence
[PR #58](https://github.com/egohygiene/realm/pull/58), branch
`feat/7-image-evidence`, at `d6f3604d0f787cc8a2b6c97d70bd3122f81a8203`.
Original main is `0ebdc4d3562a0af0f806876c5dd81d60e79f9e27`.
No merge or publication is claimed. The PR will record this checkpoint's exact
remotely pushed head and live draft reference after creation.

## Diagnosis and checks

Main has no repository release declaration, changelog, release Task handoffs or
manual release workflow. Nine new focused regression methods cover the missing
adapter and owned assets, exact tag grammar, read-only plans, exclusive review
patches, date/output rejection, duplicate local tags, malformed declarations,
source pin drift and the literal manual workflow handoff. The expected initial
run failed with five assertions and ten subcase errors because those product
surfaces do not exist. The full unchanged-main baseline passed all 97 tests and
declared offline checks. These expected failures are not passing qualification.

Read the complete #17/#25 descriptions and dependency issues/comments. Aether
#61, Hygiene #27 and Relay #47 are closed; EgoLint #29 remains open although its
source checkpoint PRs are merged. Current-v1 source pins remain Aether
`8a2a3d08f3aa9da3847bd5277843506ab855192e` (draft) and Hygiene
`28f9d6c7519d820644572634ba4476614f418d83` (proposed); no owner GitHub Releases
exist when checked. Relay v1.5.0 is published and its annotated tag resolves to
`1eada5142f7fc7da7862f335589e3b8f5884ffaf`; tag signature verification is not
established. No successor Hygiene #65 authority is adopted.

## Implementation and recovery

Implement the actual local plan/prepare/verify adapter, source-locked declaration
and contracts, reviewable changelog patch, and bounded no-overwrite Relay
container-image evidence bundle. Consume #7's real `verify_evidence` interface;
local config identity must never be relabelled as a registry manifest/index
digest. Root bundle SBOM indexing must distinguish actual platform inventories
from declared intent. Missing signatures, registry and native-platform evidence
remain unavailable; local receipts cannot become release-ready by flags.

The manual workflow will review exact-source evidence with read-only permissions.
Its literal Task dispatch will point to that real workflow. It will not silently
add credentialed registry publication, tags or release writes. Complete #7's
implementation dependency through an ordinary merge before qualification, then
run focused/full checks and independent review and push the next checkpoint.
Parallel #10 owns the generated Dev Container slice; reconcile shared Taskfile,
README and handoff semantically for combined validation.

## Gates and preservation

Full #17 acceptance needs compatible accepted producer evidence, genuine native
AMD64/ARM64 qualification, verified signatures/provenance, public immutable image
identity, registry adapter and explicit publication approval. Source preparation
remains incubating/advisory. Hosted Actions are deferred; all new commits include
`[skip ci]`. No workflow dispatch, bot review request, release, tag, signing,
publication, paid resource or manual issue closure is performed.

Preserve historical audit report/evidence, package locks, source pins, profile
identity and creative assets. Keep credentials, private paths, environment values
and raw machine logs out of public content. ADR not required: this consumes the
existing owner release protocol and repository-owned adapter boundary without
ratifying a new architecture or rewriting historical decisions.
