---
schema: aether.architecture-document/v1
id: realm-decisions
title: Realm Decisions
kind: architecture-document
version: 0.1.0
status: provisional
owners:
  - egohygiene
created: 2026-08-19
updated: 2026-08-19
governed_by:
  - architecture-decisions
depends_on:
  - realm-principles
  - realm-epistemology
  - realm-foundations
  - realm-system
  - realm-architecture
related:
  - realm-purpose
  - realm-vision
  - realm-pillars
  - realm-manifesto
supersedes: []
---

# Realm Decisions

## Purpose

This document preserves significant accepted architectural choices and their rationale. Issues coordinate work, proposals explore alternatives, and this file records decisions that constrain future implementation.

## Governance

Do not rewrite historical context to fit current understanding. Amend a record for corrections that do not change meaning; supersede it with a new record when the decision changes materially.

## Index

- ADR-0001: Keep profiles canonical instead of Dockerfiles
- ADR-0002: Publish a minimal baseline plus composable variants
- ADR-0003: Install Mantle for interactive use without misusing Dockerfile SHELL
- ADR-0004: Project canonical profiles to the Dev Container standard

## ADR-0001: Keep profiles canonical instead of Dockerfiles

- **Status:** Accepted as the current architectural direction
- **Date:** 2026-08-19
- **Context:** Repository evidence and ecosystem ownership require an explicit durable boundary.
- **Decision:** Keep profiles canonical instead of Dockerfiles.
- **Consequences:** The choice improves ownership and predictability while requiring maintained contracts, validation, and migration discipline.
- **Reconsider when:** New evidence shows that the boundary prevents standalone usefulness, safety, portability, or maintainability.

## ADR-0002: Publish a minimal baseline plus composable variants

- **Status:** Accepted as the current architectural direction
- **Date:** 2026-08-19
- **Context:** Repository evidence and ecosystem ownership require an explicit durable boundary.
- **Decision:** Publish a minimal baseline plus composable variants.
- **Consequences:** The choice improves ownership and predictability while requiring maintained contracts, validation, and migration discipline.
- **Reconsider when:** New evidence shows that the boundary prevents standalone usefulness, safety, portability, or maintainability.

## ADR-0003: Install Mantle for interactive use without misusing Dockerfile SHELL

- **Status:** Accepted as the current architectural direction
- **Date:** 2026-08-19
- **Context:** Repository evidence and ecosystem ownership require an explicit durable boundary.
- **Decision:** Install Mantle for interactive use without misusing Dockerfile SHELL.
- **Consequences:** The choice improves ownership and predictability while requiring maintained contracts, validation, and migration discipline.
- **Reconsider when:** New evidence shows that the boundary prevents standalone usefulness, safety, portability, or maintainability.

## ADR-0004: Project canonical profiles to the Dev Container standard

- **Status:** Proposed
- **Date:** 2026-10-30
- **Context:** ADR-0001 keeps profiles canonical. A portable container-development
  interface must not make VS Code, Codespaces or Nix the owner of environment
  intent, and the current resolved manifest has no editor/host overlay fields.
- **Decision:** Proposed for maintainer review: keep Realm profiles and the resolved manifest canonical.
  Project them to the open Dev Container Specification where applicable, with
  explicit consumer overrides and namespaced host adapters. Checked-in generated
  JSON is reviewable output; its generator version, source pins and input digest
  must make regeneration deterministic. Issue #10 implements that emitter; the
  current #39 fixture is authored reference data, not an emitted Realm profile.

| Option | Determinism and inspection | Portability and maintenance | Disposition |
| --- | --- | --- | --- |
| Authored `devcontainer.json` | Directly inspectable; duplication can drift from profiles | Useful explicit consumer input/import, with policy and schema checks | Retain for bounded overlays and the reference fixture; not a second canonical capability model |
| Realm-generated projection | Resolved inputs plus a versioned mapping and immutable artifacts can regenerate exact bytes | Reuses the same capability model across hosts; requires a maintained renderer | Preferred default projection path, preserving ADR-0001; emitter remains #10 work |
| devenv-generated configuration | Nix-selected inputs can generate inspectable JSON but require Nix/devenv and their locks | Useful optional adapter; must not become a universal runtime dependency or competing file generator | Evaluate only where Nix is explicitly selected; runtime qualification remains unavailable here |

- **Source evidence:** At
  [devenv `0d6c556e`](https://github.com/cachix/devenv/blob/0d6c556e5f862c14a75a543e2ee4fdb7acc005ad/src/modules/integrations/devcontainer.nix),
  `devcontainer.enable` generates/copies JSON from freeform settings. Defaults
  include a mutable `latest` image, `updateContentCommand = "devenv test"` and a
  VS Code extension. A Realm adapter must deliberately override mutable inputs,
  review lifecycle behavior, isolate editor settings and avoid two generators
  owning the same file. This is source inspection, not a Nix execution claim.
- **Regeneration rules:** The future emitter takes validated resolved JSON plus
  reviewed overlays and a versioned mapping, orders output deterministically,
  excludes credentials and timestamps from identity, and checks generated bytes
  rather than silently editing them during validation. A source or mapping
  change requires a reviewable regeneration diff. No emitter exists in this
  checkpoint.
- **Consequences:** Official schema validity, Realm reference policy, CLI
  interpretation, runtime behavior and IDE/cloud proof stay separate evidence
  layers. Stable capabilities prefer reusable Features and released images when
  compatible verified artifacts exist. Unsupported or host-specific behavior
  remains explicit in the mapping and conformance matrix.
- **Reconsider when:** An accepted upstream contract or actual cross-host proof
  shows the mapping cannot preserve portable intent without silent loss. A
  host-specific limitation alone does not authorize forking Sanctuary or making
  a cloud/editor/Nix implementation canonical.

## Open decisions

- Release and compatibility policy for the first stable version.
- Exact self-hosted, managed, and organization-integrated deployment boundaries.
- Which target systems must exist before the architecture status may become active.

## Evidence and uncertainty

- **Observed:** The repository README establishes the intended boundary as a reproducible developer-workstation and self-hosted runtime foundation driven by versioned capabilities and profiles; significant implementation remains incomplete.
- **Decided for this draft:** The repository owns the bounded concern described here and participates through versioned contracts.
- **Proposed:** Target systems and later roadmap phases remain proposals until accepted and implemented.
- **Open question:** Which parts of this draft should become active in the first independently versioned release?

## Identifier format migration (2026-10-18)

The maintainer selected four-digit numbering in [Hygiene #73](https://github.com/egohygiene/hygiene/issues/73). This padding-only migration changes current labels and anchors; logical numbers, decision content, dates and disposition remain unchanged. Git retains prior versions. New canonical records use `ADR-NNNN` under Hygiene policy v1.2.0.

| Previous ID | Current ID | Record |
| --- | --- | --- |
| `ADR-001` | `ADR-0001` | [DECISIONS.md](DECISIONS.md#adr-0001-keep-profiles-canonical-instead-of-dockerfiles) |
| `ADR-002` | `ADR-0002` | [DECISIONS.md](DECISIONS.md#adr-0002-publish-a-minimal-baseline-plus-composable-variants) |
| `ADR-003` | `ADR-0003` | [DECISIONS.md](DECISIONS.md#adr-0003-install-mantle-for-interactive-use-without-misusing-dockerfile-shell) |
