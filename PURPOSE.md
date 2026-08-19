---
schema: aether.architecture-document/v1
id: realm-purpose
title: Realm Purpose
kind: architecture-document
version: 0.1.0
status: provisional
owners:
  - egohygiene
created: 2026-08-19
updated: 2026-08-19
governed_by:
  - architecture-purpose
depends_on:
  []
related:
  - realm-vision
  - realm-principles
  - realm-pillars
  - realm-manifesto
supersedes: []
---

# Realm Purpose

## Purpose statement

Realm exists to describe development and runtime environments once and project them consistently into containers, Dev Containers, Nix, and workstations.

## Need

environment intent is often trapped in Dockerfiles and machine-specific scripts that cannot be reused, compared, or verified across projections.

## Beneficiaries

- developers
- CI systems
- self-hosters
- Holon-generated repositories
- infrastructure automation

## Enduring value

The enduring value is a trustworthy, portable capability that remains useful when its implementation, delivery channel, or surrounding platform changes.

## Scope boundaries

Realm owns a reproducible developer-workstation and self-hosted runtime foundation driven by versioned capabilities and profiles. It does not absorb neighboring repositories, treat temporary implementation choices as purpose, or claim authority beyond its explicit contracts.

## Evidence and uncertainty

- **Observed:** The repository README establishes the intended boundary as a reproducible developer-workstation and self-hosted runtime foundation driven by versioned capabilities and profiles; significant implementation remains incomplete.
- **Decided for this draft:** The repository owns the bounded concern described here and participates through versioned contracts.
- **Proposed:** Target systems and later roadmap phases remain proposals until accepted and implemented.
- **Open question:** Which parts of this draft should become active in the first independently versioned release?

## Open questions

- Which beneficiary needs require direct research before this document can become active?
- Which current features are incidental and should remain outside the enduring purpose?
