---
schema: aether.architecture-document/v1
id: realm-meta
title: Realm Meta
kind: architecture-document
version: 0.1.0
status: provisional
owners:
  - egohygiene
created: 2026-08-19
updated: 2026-08-19
governed_by:
  - architecture-meta
depends_on:
  - realm-epistemology
  - realm-ai-constitution
related:
  - realm-purpose
  - realm-vision
  - realm-principles
  - realm-pillars
supersedes: []
---

# Realm Meta Architecture

## Architecture-system overview

Realm's architecture is an 18-document graph materialized from the Aether architecture specifications. Each document owns one bounded concern. This index maps ownership and relationships without replacing the documents themselves.

## Document inventory

| Artifact | Path | Category | Status | Governing specification | Upstream dependencies |
| --- | --- | --- | --- | --- | --- |
| realm-purpose | [PURPOSE.md](PURPOSE.md) | Identity | provisional | architecture-purpose | — |
| realm-vision | [VISION.md](VISION.md) | Identity | provisional | architecture-vision | realm-purpose |
| realm-principles | [PRINCIPLES.md](PRINCIPLES.md) | Identity | provisional | architecture-principles | realm-purpose, realm-vision |
| realm-pillars | [PILLARS.md](PILLARS.md) | Identity | provisional | architecture-pillars | realm-purpose, realm-vision, realm-principles |
| realm-manifesto | [MANIFESTO.md](MANIFESTO.md) | Identity | provisional | architecture-manifesto | realm-purpose, realm-vision, realm-principles, realm-pillars |
| realm-epistemology | [EPISTEMOLOGY.md](EPISTEMOLOGY.md) | Meta | provisional | architecture-epistemology | realm-purpose, realm-principles |
| realm-ai-constitution | [AI_CONSTITUTION.md](AI_CONSTITUTION.md) | Meta | provisional | architecture-ai-constitution | realm-purpose, realm-vision, realm-principles, realm-epistemology |
| realm-ontology | [ONTOLOGY.md](ONTOLOGY.md) | Domain | provisional | architecture-ontology | realm-purpose, realm-vision, realm-principles, realm-epistemology |
| realm-personal-model | [PERSONAL_MODEL.md](PERSONAL_MODEL.md) | Domain | provisional | architecture-personal-model | realm-purpose, realm-vision, realm-principles, realm-epistemology, realm-ontology |
| realm-foundations | [FOUNDATIONS.md](FOUNDATIONS.md) | Foundation | provisional | architecture-foundations | realm-purpose, realm-principles, realm-epistemology |
| realm-system | [SYSTEM.md](SYSTEM.md) | Foundation | provisional | architecture-system | realm-foundations, realm-ontology |
| realm-architecture | [ARCHITECTURE.md](ARCHITECTURE.md) | Foundation | provisional | architecture-architecture | realm-foundations, realm-system |
| realm-methodology | [METHODOLOGY.md](METHODOLOGY.md) | Foundation | provisional | architecture-methodology | realm-principles, realm-epistemology, realm-ai-constitution, realm-foundations, realm-architecture |
| realm-design | [DESIGN.md](DESIGN.md) | Experience | provisional | architecture-design | realm-purpose, realm-vision, realm-principles, realm-personal-model |
| realm-design-system | [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md) | Experience | provisional | architecture-design-system | realm-personal-model, realm-design |
| realm-decisions | [DECISIONS.md](DECISIONS.md) | Governance | provisional | architecture-decisions | realm-principles, realm-epistemology, realm-foundations, realm-system, realm-architecture |
| realm-roadmap | [ROADMAP.md](ROADMAP.md) | Foundation | provisional | architecture-roadmap | realm-vision, realm-pillars, realm-architecture, realm-decisions |
| realm-meta | [META.md](META.md) | Meta | provisional | architecture-meta | realm-epistemology, realm-ai-constitution |

## Relationship graph

```mermaid
flowchart TD
  PURPOSE --> VISION --> PRINCIPLES --> PILLARS --> MANIFESTO
  PURPOSE --> EPISTEMOLOGY --> AI[AI Constitution]
  PRINCIPLES --> EPISTEMOLOGY
  EPISTEMOLOGY --> ONTOLOGY --> PERSONAL[Personal Model]
  PRINCIPLES --> FOUNDATIONS
  EPISTEMOLOGY --> FOUNDATIONS
  FOUNDATIONS --> SYSTEM --> ARCHITECTURE --> METHODOLOGY
  PERSONAL --> DESIGN --> DS[Design System]
  ARCHITECTURE --> DECISIONS --> ROADMAP
  PILLARS --> ROADMAP
  AI --> META
  EPISTEMOLOGY --> META
```

## Ownership map

- Identity documents own why the repository exists, its desired future, decision heuristics, strategic capabilities, and public commitments.
- Meta documents own knowledge integrity, AI authority, and navigation of this document system.
- Domain documents own canonical concepts and bounded human assumptions.
- Foundation documents own invariants, logical systems, structure, working method, and strategic evolution.
- Experience documents own intended experience and reusable semantic design language.
- Governance owns accepted architectural decisions and historical lineage.

## Reading order

1. PURPOSE, VISION, and PRINCIPLES.
2. EPISTEMOLOGY and ONTOLOGY.
3. FOUNDATIONS, SYSTEM, and ARCHITECTURE.
4. PERSONAL_MODEL, DESIGN, and DESIGN_SYSTEM when evaluating human-facing surfaces.
5. AI_CONSTITUTION before delegating consequential work.
6. DECISIONS and ROADMAP for accepted constraints and evolution.

## Authoring order

Follow the dependency graph from purpose through identity and evidence, then domain and foundations, experience, governance, roadmap, and finally this META index.

## Lifecycle and validation

All documents begin as provisional and require human review before becoming active. Validation covers frontmatter, stable identifiers, links, graph acyclicity, ownership boundaries, evidence labels, Markdown structure, and agreement with repository reality.

## Change propagation

A material upstream change triggers review of every downstream node. Implementation changes first update the owning specification or decision when they alter durable behavior; META changes whenever inventory or relationships change.

## Gaps and omissions

- No document in this set is intentionally omitted because Realm has repository, automation, human, AI, and public or documentation surfaces that justify the complete reference set.
- Target systems remain provisional where implementation evidence is absent.
- Repository-local schemas and automated graph validation should be added or connected to Aether in a later conformance pass.

## Evidence and uncertainty

- **Observed:** The repository README establishes the intended boundary as a reproducible developer-workstation and self-hosted runtime foundation driven by versioned capabilities and profiles; significant implementation remains incomplete.
- **Decided for this draft:** The repository owns the bounded concern described here and participates through versioned contracts.
- **Proposed:** Target systems and later roadmap phases remain proposals until accepted and implemented.
- **Open question:** Which parts of this draft should become active in the first independently versioned release?
