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
