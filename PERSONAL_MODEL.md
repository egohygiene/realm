---
schema: aether.architecture-document/v1
id: realm-personal-model
title: Realm Personal Model
kind: architecture-document
version: 0.1.0
status: provisional
owners:
  - egohygiene
created: 2026-08-19
updated: 2026-08-19
governed_by:
  - architecture-personal-model
depends_on:
  - realm-purpose
  - realm-vision
  - realm-principles
  - realm-epistemology
  - realm-ontology
related:
  - realm-pillars
  - realm-manifesto
  - realm-ai-constitution
  - realm-foundations
supersedes: []
---

# Realm Personal Model

## Purpose

Realm is designed for and operated by people even when it is primarily a library or automation surface. This document makes its limited human assumptions explicit; it is not a persona catalog, diagnosis, identity model, or prediction engine.

## People in scope

- developers
- CI systems
- self-hosters
- Holon-generated repositories
- infrastructure automation

Maintainers, contributors, reviewers, and people indirectly affected by generated or published outputs are also in scope.

## Human assumptions

- Attention, time, technical knowledge, sensory tolerance, and risk tolerance vary.
- People may arrive under stress, with incomplete context, or using assistive technology.
- A person's files, history, choices, or metrics do not fully represent them.
- Consent to inspect is not automatically consent to mutate, publish, infer, or retain.
- People need meaningful recovery paths when systems fail.

## Agency and consent boundaries

Consequential operations require understandable scope, current authorization, and an appropriate preview or confirmation. Personal inference must be optional, purpose-limited, labeled, correctable, and removable.

## Accessibility and dignity

Primary journeys should remain keyboard-accessible, screen-reader legible, reduced-motion compatible, and understandable without expert vocabulary. Error messages describe recovery without blame.

## Evidence and uncertainty

- **Observed:** The repository README establishes the intended boundary as a reproducible developer-workstation and self-hosted runtime foundation driven by versioned capabilities and profiles; significant implementation remains incomplete.
- **Decided for this draft:** The repository owns the bounded concern described here and participates through versioned contracts.
- **Proposed:** Target systems and later roadmap phases remain proposals until accepted and implemented.
- **Open question:** Which parts of this draft should become active in the first independently versioned release?
