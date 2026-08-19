---
schema: aether.architecture-document/v1
id: realm-ontology
title: Realm Ontology
kind: architecture-document
version: 0.1.0
status: provisional
owners:
  - egohygiene
created: 2026-08-19
updated: 2026-08-19
governed_by:
  - architecture-ontology
depends_on:
  - realm-purpose
  - realm-vision
  - realm-principles
  - realm-epistemology
related:
  - realm-pillars
  - realm-manifesto
  - realm-ai-constitution
  - realm-personal-model
supersedes: []
---

# Realm Ontology

## Domain scope

Realm models the concepts needed for describe development and runtime environments once and project them consistently into containers, Dev Containers, Nix, and workstations. The ontology names conceptual entities and relationships; it is not a source-code class model, API schema, or database design.

## Canonical concepts

| Concept | Meaning |
| --- | --- |
| Capability | A canonical concept in the Realm domain whose exact fields belong to specifications or schemas, not this ontology. |
| Profile | A canonical concept in the Realm domain whose exact fields belong to specifications or schemas, not this ontology. |
| Projection | A canonical concept in the Realm domain whose exact fields belong to specifications or schemas, not this ontology. |
| Resolved profile | A canonical concept in the Realm domain whose exact fields belong to specifications or schemas, not this ontology. |
| Package | A canonical concept in the Realm domain whose exact fields belong to specifications or schemas, not this ontology. |
| Artifact | A canonical concept in the Realm domain whose exact fields belong to specifications or schemas, not this ontology. |
| Platform | A canonical concept in the Realm domain whose exact fields belong to specifications or schemas, not this ontology. |
| Image variant | A canonical concept in the Realm domain whose exact fields belong to specifications or schemas, not this ontology. |
| Runtime service | A canonical concept in the Realm domain whose exact fields belong to specifications or schemas, not this ontology. |

## Core relationships

- A repository or person provides source context to one or more domain artifacts.
- A specification constrains how an artifact is interpreted or produced.
- A plan separates proposed action from execution.
- Evidence supports a claim; a decision authorizes a durable direction.
- Provenance connects derived artifacts to their inputs and processing context.
- A consumer integrates through an explicit interface rather than internal structure.

## Boundaries

- Conceptual identity is distinct from filesystem path, database identifier, or display label.
- Observed state is distinct from desired state.
- Proposed relationships are not accepted facts.
- Neighboring repositories retain ownership of their domain concepts.

## Evidence and uncertainty

- **Observed:** The repository README establishes the intended boundary as a reproducible developer-workstation and self-hosted runtime foundation driven by versioned capabilities and profiles; significant implementation remains incomplete.
- **Decided for this draft:** The repository owns the bounded concern described here and participates through versioned contracts.
- **Proposed:** Target systems and later roadmap phases remain proposals until accepted and implemented.
- **Open question:** Which parts of this draft should become active in the first independently versioned release?
