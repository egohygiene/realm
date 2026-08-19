---
schema: aether.architecture-document/v1
id: realm-system
title: Realm System
kind: architecture-document
version: 0.1.0
status: provisional
owners:
  - egohygiene
created: 2026-08-19
updated: 2026-08-19
governed_by:
  - architecture-system
depends_on:
  - realm-foundations
  - realm-ontology
related:
  - realm-purpose
  - realm-vision
  - realm-principles
  - realm-pillars
supersedes: []
---

# Realm System

## Purpose and scope

This document identifies Realm's logical systems and responsibilities. It answers what the major systems do; [ARCHITECTURE.md](ARCHITECTURE.md) owns their structural organization and dependency rules.

## System inventory

| System | State | Responsibility |
| --- | --- | --- |
| Capability catalog | Target | Owns its bounded portion of a reproducible developer-workstation and self-hosted runtime foundation driven by versioned capabilities and profiles; exposes explicit inputs, outputs, failure states, and evidence. |
| Profile resolver | Target | Owns its bounded portion of a reproducible developer-workstation and self-hosted runtime foundation driven by versioned capabilities and profiles; exposes explicit inputs, outputs, failure states, and evidence. |
| Docker image renderer | Target | Owns its bounded portion of a reproducible developer-workstation and self-hosted runtime foundation driven by versioned capabilities and profiles; exposes explicit inputs, outputs, failure states, and evidence. |
| Dev Container projection | Target | Owns its bounded portion of a reproducible developer-workstation and self-hosted runtime foundation driven by versioned capabilities and profiles; exposes explicit inputs, outputs, failure states, and evidence. |
| Nix projection | Target | Owns its bounded portion of a reproducible developer-workstation and self-hosted runtime foundation driven by versioned capabilities and profiles; exposes explicit inputs, outputs, failure states, and evidence. |
| Workstation projection | Target | Owns its bounded portion of a reproducible developer-workstation and self-hosted runtime foundation driven by versioned capabilities and profiles; exposes explicit inputs, outputs, failure states, and evidence. |
| Artifact test and publication | Target | Owns its bounded portion of a reproducible developer-workstation and self-hosted runtime foundation driven by versioned capabilities and profiles; exposes explicit inputs, outputs, failure states, and evidence. |

## External systems

- Mantle shell
- Empathy Dev Container baseline
- Holon manifests
- Relay image publication
- future Firmament infrastructure

External systems are integrations, not hidden implementation units. Each requires version, authentication, availability, data, error, and replacement boundaries appropriate to its risk.

## System interactions

Inputs enter through an adapter or validated contract, move through domain systems, produce artifacts and diagnostics, and leave through a stable interface. Evidence flows back to validation, review, and future decisions.

## Failure model

Systems fail closed at destructive, publication, privacy, and security boundaries. Partial results identify coverage and remain distinguishable from complete success.

## Evidence and uncertainty

- **Observed:** The repository README establishes the intended boundary as a reproducible developer-workstation and self-hosted runtime foundation driven by versioned capabilities and profiles; significant implementation remains incomplete.
- **Decided for this draft:** The repository owns the bounded concern described here and participates through versioned contracts.
- **Proposed:** Target systems and later roadmap phases remain proposals until accepted and implemented.
- **Open question:** Which parts of this draft should become active in the first independently versioned release?
