---
schema: aether.architecture-document/v1
id: realm-roadmap
title: Realm Roadmap
kind: architecture-document
version: 0.1.0
status: provisional
owners:
  - egohygiene
created: 2026-08-19
updated: 2026-10-30
governed_by:
  - architecture-roadmap
depends_on:
  - realm-vision
  - realm-pillars
  - realm-architecture
  - realm-decisions
related:
  - realm-purpose
  - realm-principles
  - realm-manifesto
  - realm-epistemology
supersedes: []
---

# Realm Roadmap

## Current engineering handoff — 2026-10-30

Use [roadmap #25](https://github.com/egohygiene/realm/issues/25), the owning issues
and [current continuity](CONTINUITY.md) for live execution status. The preserved
[source-revision audit](audits/realm-engineering-readiness-20261028T064323Z.md)
and [evidence](audits/evidence/realm-engineering-readiness-20261028T064323Z.json)
describe source `d66a0e4d5a100d287a9745f4c45f055e0a78948b` on 2026-10-28.
Its 39-item inventory, 9-ready/30-gated classification, negative probes and
delivery state are historical observations, not refreshed acceptance claims.

The #50 resolver repair and #51 structural validation repair are merged in
[PR #53](https://github.com/egohygiene/realm/pull/53) and
[PR #54](https://github.com/egohygiene/realm/pull/54). Bounded #8 Mantle source
activation preparation and #39 Dev Container standards/mapping are merged in
[PR #55](https://github.com/egohygiene/realm/pull/55) and
[PR #56](https://github.com/egohygiene/realm/pull/56). Their combined source passed
97 local tests. Full #8/#39 acceptance remains open: published verified Mantle,
#10's generated projection/Task/Mantle canary and actual supported-host proof
are separate gates. The next implementation batch has not been selected.

The August execution snapshot below is historical: CI, immutable action pins and the minimal base Dockerfile now exist. Profile declarations still do not prove emitted Nix/workstation/Dev Container adapters or a published image.

The recommended first-version scope is the existing minimal runtime/environment
with credible checks, pinned Mantle activation and one local Dev Container
canary where applicable. Distributed-release approval remains separate.
Optional full images, services, models, knowledge/confidential environments,
new dashboards and ADR-history migration do not block comic content. Original
issue scopes and the longer-horizon strategy below are preserved.


<!-- BEGIN ROADMAP EXECUTION SNAPSHOT -->
<!-- roadmap-manifest
schema: hygiene.roadmap/v1alpha1
repository: egohygiene/realm
visibility: public
publication: central
route: /roadmap/realm/
updated: 2026-08-24
-->
## 2026-08-24 execution snapshot

> This evidence-reconciled snapshot is the issue-generation and visual-roadmap handoff. The longer-horizon strategy below remains canonical context; generated HTML, JSON, progress, issue plans, and commit lists are projections.

**Lifecycle:** contract prototype  
**Current gate:** Pin workflow dependencies, add CI, and prove the contract through a real base-image projection.  
**North-star outcome:** One capability model projected consistently to Docker, devcontainer, Nix, and workstation environments.

### Visual roadmap publication

**Mode:** `central`  
**Route:** `/roadmap/realm/`  
**Current publication evidence:** Source-only prototype; container and projection publication are planned but absent.

Publish the public-safe projection through egohygiene.io at /roadmap/realm/. This repository owns intent and acceptance evidence; it does not add a second site deployment.

### Quest line

<!-- roadmap-step
id: REA-Q01
status: complete
depends_on: []
issues: []
-->
#### REA-Q01 — Define the capability contract

**State:** `complete`  
**Depends on:** None

**Outcome:** Schemas, profiles, a resolver, and tests describe the initial environment model.

**Exit criteria:**

- [x] Representative profiles resolve deterministically.
- [x] Contract fixtures are covered by tests.

**Current evidence:**

- Schemas, profiles, resolver code, and tests were observed.

<!-- roadmap-step
id: REA-Q02
status: blocked
depends_on: [REA-Q01]
issues: []
-->
#### REA-Q02 — Secure and activate CI

**State:** `blocked`  
**Depends on:** `REA-Q01`

**Outcome:** Every change is tested using immutable workflow dependencies.

**Exit criteria:**

- [ ] All third-party actions are pinned to full SHAs.
- [ ] Contract and resolver tests run green on the default branch.

**Current evidence:**

- The audit found zero full-SHA action pins and no active CI proof.

<!-- roadmap-step
id: REA-Q03
status: planned
depends_on: [REA-Q02]
issues: [1]
-->
#### REA-Q03 — Build the base image projection

**State:** `planned`  
**Depends on:** `REA-Q02`

**Outcome:** Issue #1 produces a deterministic base container from the capability model.

**Exit criteria:**

- [ ] A Dockerfile or generated equivalent exists.
- [ ] The built image is tested against the resolved contract.

**Current evidence:**

- Issue #1 tracks the base image.
- No Dockerfile was observed.

<!-- roadmap-step
id: REA-Q04
status: planned
depends_on: [REA-Q03]
issues: [5, 6, 8]
-->
#### REA-Q04 — Add language and Mantle profiles

**State:** `planned`  
**Depends on:** `REA-Q03`

**Outcome:** Language, full-environment, and Mantle capabilities compose without divergent definitions.

**Exit criteria:**

- [ ] Issues #5, #6, and #8 have tested projections.
- [ ] Profile composition and override rules are documented.

**Current evidence:**

- Issues #5, #6, and #8 define this backlog.

<!-- roadmap-step
id: REA-Q05
status: planned
depends_on: [REA-Q04]
issues: [7, 10]
-->
#### REA-Q05 — Publish provenance-rich projections

**State:** `planned`  
**Depends on:** `REA-Q04`

**Outcome:** Container, devcontainer, Nix, or workstation outputs carry SBOM and source provenance.

**Exit criteria:**

- [ ] Issues #7 and #10 close with verified SBOM and projection artifacts.
- [ ] At least one consumer pins a published immutable artifact.

**Current evidence:**

- Issues #7 and #10 cover SBOM and projections.
- No projection release was observed.

### Roadmap-to-issue handoff

- A step is complete only when its exit criteria and required evidence are satisfied; commit count never determines progress.
- Ready steps without an issue are candidates for the private, duplicate-aware roadmap.issue-plan.json dry run. Planned steps remain preview-only unless a reviewer explicitly opts them in with issue_policy: propose.
- Issue creation or reconciliation requires human approval or an explicitly authorized Pace operation and returns issue references through a reviewable roadmap pull request.
- Pull requests and commits should include Roadmap-Step: <ID>; historical evidence may be linked through existing issue and pull-request relationships.
- Public rendering uses only allowlisted build-time evidence and never places a GitHub token or private issue plan in the browser artifact.

<!-- END ROADMAP EXECUTION SNAPSHOT -->

## Strategic context

This roadmap describes capability evolution, not promised dates or an issue queue. Sequence follows architecture dependencies and may change when evidence or risk changes.

## Phase 1: Stabilize capability and profile contracts

**Outcome:** A bounded capability advances from documented intent to validated, independently usable behavior.

**Exit signals:**

- The owning contract and acceptance criteria are versioned.
- Implementation and documentation agree.
- Relevant tests and safety checks pass.
- Downstream consumers and migration impact are understood.
- Remaining uncertainty is visible.

## Phase 2: Publish baseline and language images

**Outcome:** A bounded capability advances from documented intent to validated, independently usable behavior.

**Exit signals:**

- The owning contract and acceptance criteria are versioned.
- Implementation and documentation agree.
- Relevant tests and safety checks pass.
- Downstream consumers and migration impact are understood.
- Remaining uncertainty is visible.

## Phase 3: Complete full and services boundaries

**Outcome:** A bounded capability advances from documented intent to validated, independently usable behavior.

**Exit signals:**

- The owning contract and acceptance criteria are versioned.
- Implementation and documentation agree.
- Relevant tests and safety checks pass.
- Downstream consumers and migration impact are understood.
- Remaining uncertainty is visible.

## Phase 4: Add Nix and workstation projections

**Outcome:** A bounded capability advances from documented intent to validated, independently usable behavior.

**Exit signals:**

- The owning contract and acceptance criteria are versioned.
- Implementation and documentation agree.
- Relevant tests and safety checks pass.
- Downstream consumers and migration impact are understood.
- Remaining uncertainty is visible.

## Phase 5: Integrate infrastructure deployment

**Outcome:** A bounded capability advances from documented intent to validated, independently usable behavior.

**Exit signals:**

- The owning contract and acceptance criteria are versioned.
- Implementation and documentation agree.
- Relevant tests and safety checks pass.
- Downstream consumers and migration impact are understood.
- Remaining uncertainty is visible.

## Cross-cutting tracks

- Security, privacy, accessibility, licensing, and provenance.
- Documentation, architecture portals, examples, and onboarding.
- Packaging, release, compatibility, and self-hosting.
- Organization integration through explicit contracts.
- Observatory evidence and Pace conformance when those systems exist.

## Deferred direction

Optional managed services, enterprise controls, marketplaces, and the conversational organization compiler remain later architecture work. Current choices should preserve portability and avoid foreclosing them.

## Evidence and uncertainty

- **Observed:** The repository README establishes the intended boundary as a reproducible developer-workstation and self-hosted runtime foundation driven by versioned capabilities and profiles; significant implementation remains incomplete.
- **Decided for this draft:** The repository owns the bounded concern described here and participates through versioned contracts.
- **Proposed:** Target systems and later roadmap phases remain proposals until accepted and implemented.
- **Open question:** Which parts of this draft should become active in the first independently versioned release?
