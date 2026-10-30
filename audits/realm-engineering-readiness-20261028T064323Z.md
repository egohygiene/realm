# Realm engineering-readiness audit — 2026-10-28

**Outcome:** keep the first version small. Realm already has a working capability/profile model and a tested minimal Debian image. Repair two input-validation defects, finish the existing Mantle/Dev Container integration and release boundaries, and leave the large optional workstation program open without making it a comic-content prerequisite.

- Source: [main at `d66a0e4d5a100d287a9745f4c45f055e0a78948b`](https://github.com/egohygiene/realm/tree/d66a0e4d5a100d287a9745f4c45f055e0a78948b).
- Candidate branch: `docs/engineering-readiness-audit-2026-10-28`; review reference is recorded in [CONTINUITY.md](../CONTINUITY.md).
- Current execution roadmap: [existing parent #25](https://github.com/egohygiene/realm/issues/25). Companion: [Mantle #45](https://github.com/egohygiene/mantle/issues/45).
- Report status: **complete audit workflow; partial runtime/platform validation**. This is a bounded engineering/organization audit, not security certification.
- Before audit: **38 open issues, including the roadmap; 0 open PRs**. Added **2 focused follow-ups**. Current work: **39 issues = 9 ready + 30 gated**, excluding the parent and PRs.
- Inspectable evidence: [validation, coverage, preservation, and native hierarchy JSON](evidence/realm-engineering-readiness-20261028T064323Z.json).

## Scope and authority

The request authorizes inspection, proportionate validation, issue reconciliation, a complete execution roadmap, and audit/continuity artifacts in a draft PR. It excludes product fixes, CI repair, dependency upgrades, merges, releases, deployment, history rewriting, and changes to authored content or assets.

The inspected tree has **88 tracked files**, four Python tools, five Python test modules, seven schemas, ten profile declarations, one base-image Dockerfile, package locks/scripts, generated profile declarations, and one validation workflow. No applicable repository-local AGENTS.md, root CONTINUITY.md, or SECURITY.md existed. Organization AGENTS.md explicitly does not auto-inherit into other repositories.

Canonical guidance was read at immutable sources:

| Source | Revision / disposition |
| --- | --- |
| Aether auditor specification | `dc8a16851f452763ef4f7fbe4bf057d4500b1921`, approved v2.0.0 |
| Aether audit / issue-authoring / continuity skills | Same revision; draft 1.1.0 / experimental 1.2.0 / draft 1.1.0 |
| Hygiene continuity applicability policy | `aa6a5e25ea3ef80e4dcc15570a1ea166b9f4af3d`, proposed 1.0.0-alpha.1, observe |
| Organization title/label guidance | `ac2e4035173ed252d71d6655e723964ef93684df`, title contract 1.0.1, explicit adoption |

The portable guidance informs this authorized workflow; draft standards are not silently promoted to adopted release requirements. Both repositories lack provider `type:*` labels. New issues use the canonical title style and verified existing labels; full title/label-policy conformance is not claimed. TRUST_POLICY.md keeps unclassified legacy consumers nonblocking until explicit adoption.

Discovery covered entry/product and architecture/system documents, decision records, contracts, instructions, Taskfile, dependencies, workflows, implementation, tests, guides, prior audits, all open issue bodies and relevant discussion. Realm #9's service umbrella comment and closed #1's captured smallest-base clarification were read; completed #2/#4/#5 were checked to avoid reopening their implementation history.

## Implemented, declared, proposed, and released

| State | Evidence and practical meaning |
| --- | --- |
| Implemented source | Deterministic profile resolution; curated admission registry; profile declaration generation/checking; snapshot-pinned apt lock maintenance; base Docker projection and verification scripts. |
| Executed locally | `task check` passed, including **55 Python tests**, locks, deterministic generated output, Bash syntax and ShellCheck. |
| Observed native hosted proof | [Run 39167134555](https://github.com/egohygiene/realm/actions/runs/39167134555) at the exact source passed offline contracts and native AMD64/ARM64 base-image replay/build/verify/smoke jobs. This audit did not re-execute them. |
| Declared intent | Ten profile manifests, support matrix, cache identities, and SPDX declarations under dist/profiles. They explicitly describe intent; they are not installed-image SBOMs, container digests, or measured full-image sizes. |
| Proposed / working draft | Root architecture is provisional; executable profile v1 documentation is draft. Most service, Nix/workstation, local-agent, garden, confidential, and media/document integrations remain issue-scoped designs. |
| Released capability | **No GitHub Release exists.** No verified first distributed Realm release is inferred from builds or committed declarations. Other registry state was not exhaustively inventoried. |

The base deliberately contains 13 direct package roots and excludes language toolchains/long-running services. Closed #1's discussion records the smallest supported base; its original comprehensive package list is not a reason to expand that base during this audit. The full image remains #6.

## Findings and issue coverage

Severity is consequence, confidence is evidence strength, and effort describes the bounded follow-up. All observations below are source-revision-specific.

| Finding | Classification | Severity / confidence | Coverage |
| --- | --- | --- | --- |
| AUDIT-001 — invalid inheritance is traversed after validation | Confirmed defect | Medium / high | Gap → new [#50](https://github.com/egohygiene/realm/issues/50) |
| AUDIT-002 — published structural schema rules are not fully enforced | Confirmed defect | Medium / high | Gap → new [#51](https://github.com/egohygiene/realm/issues/51) |
| AUDIT-003 — Mantle activation guidance assumes a shell executable | Documentation gap / architectural concern | Medium / high | Partial → additive evidence in #8; ownership decision in #45 |
| AUDIT-004 — projection/publication outcomes remain unfinished | Maintainability risk | Medium / high | Existing #6/#7/#10/#17/#19/#39/#47; no duplicate tickets |
| AUDIT-005 — execution snapshot/handoff are stale or absent | Documentation gap | Low / high | Addressed only as audit artifacts in this candidate; #25 remains the tracker |
| AUDIT-006 — private reporting guidance is not established locally/default | Documentation gap | Low / high | Existing organization [#24](https://github.com/egohygiene/.github/issues/24), no duplicate local policy |

### AUDIT-001 — early validation does not stop invalid traversal

**Status:** confirmed. **Area:** resolver. **Effort:** small. **Impact:** medium. **Evidence:** observed synthetic negative probe against `tools/realm_profiles.py:289` and the existing cycle test.

An in-memory `base.extends = ["base"]` fixture produces a cycle diagnostic from validate_profiles, but resolve_profile traverses inheritance and raises RecursionError before returning those errors. The committed graph is valid. Existing tests cover validator rejection, not resolver/CLI rejection of that graph.

**Recommendation:** #50 returns bounded contract errors before traversal and proves no output/traceback on invalid fixtures. **Validation:** direct resolver plus temporary CLI self/multi-cycle cases, then `task check`. **Dependencies/risks:** none beyond current source; preserve deterministic valid outputs.

### AUDIT-002 — runtime validator and structural schemas disagree

**Status:** confirmed. **Area:** contracts. **Effort:** medium. **Impact:** high for trustworthy future input handling. **Evidence:** observed synthetic copies, `tools/realm_profiles.py:159`, capability/profile schemas.

An unsupported capability kind and a string in allow_privileged each return an empty validation-error list, although the published schemas require an enum and a boolean. Required/nested fields and exact nested field sets also need coherent validation. No malformed production profile or deployed compromise is asserted.

**Recommendation:** #51 enforces the advertised v1 structural contract without silently abandoning the dependency-free interface. **Validation:** meaningful malformed-type/required-field fixtures, CLI rejection, existing valid declarations, and `task check`. A development JSON Schema comparison is useful but is distinct from the runtime implementation. **Dependencies:** coordinate with #50 without merging their scopes.

### AUDIT-003 — sourceable Mantle and the recovered UBI design need reconciliation

**Status:** confirmed documentation discrepancy; owner choice needs clarification. **Area:** shell integration. **Effort:** small for guidance, unknown for any selected adapter. **Impact:** medium.

`docs/mantle-shell.md` illustrates a Mantle `--execute` shell and discusses login-shell registration/chsh. Current Mantle is a public dispatcher plus sourceable Bash/Zsh and native Fish entrypoints; its installation guide explicitly avoids replacing system shells. Realm's Mantle pin is a source declaration, not a verified current release integration. #8 already owns activation, fallback, and shell tests.

#45 separately proposes another sourceable shell/bootstrap tree. That overlaps Mantle's implemented owner boundary. **Recommendation:** reuse Mantle runtime behavior and keep Realm environment/system/home controls thin. Preserve #45's captured requirements until the maintainer chooses ownership. Do not implement a second framework or change login shells from this audit. **Validation:** source/dispatcher contract comparison now; real interactive/noninteractive recovery canary after integration. **Full-outcome gate:** verified published Mantle plus the explicit #45 owner decision for overlapping work.

### AUDIT-004 — source readiness is ahead of distributed readiness

**Status:** confirmed. **Area:** projections and distribution. **Effort:** large across existing issues. **Impact:** high for reusable consumption.

Only the minimal Docker projection is implemented. Full image budgets, emitted Dev Container/Nix/workstation adapters, installed-image SBOM/vulnerability evidence, signed published digests, and downstream release consumption remain unfinished. No GitHub Releases were found for Mantle, Renderflow, or Mindgarden either; the named released-consumer outcomes are genuinely gated, not merely waiting on an old issue checkbox.

#7/#17 own trusted image/release evidence; #6 owns full-image measurements; #10/#39 own actual portable projections; #19 needs released Renderflow plus another tool; #47 retains Hygiene #65's successor-tool gate. Aether #61, Hygiene #27, and Relay #47 are closed source foundations, while Egolint #29's fixture/dogfood closeout remains open. Closure alone establishes neither compatible publication nor approval.

**Recommendation/validation:** follow those original issues in bounded producer/consumer checkpoints. Current-v1 preparation can start without inventing a dependency on every successor policy feature. Publish nothing during this audit.

### AUDIT-005 — the current execution handoff is misleading

**Status:** confirmed; candidate proposes the handoff repair. **Area:** organization/documentation. **Effort:** small. **Impact:** medium.

ROADMAP.md's August snapshot still says no pinned actions, active CI, or Dockerfile. All three are now present, with exact native run evidence. There was no root continuity file. This candidate adds a dated current-roadmap pointer and a concise operational checkpoint, preserving historical text rather than overwriting it or silently adopting a draft fleet contract. **Validation:** source/tracker comparisons, local links, diff scope, and live hierarchy/coverage checks. No product work is represented as completed.

### AUDIT-006 — reporting defaults are unfinished organization work

**Status:** confirmed absence in inspected recognized locations. **Area:** contributor/security intake. **Effort:** small at the shared owner. **Impact:** medium for discoverability, not an asserted exploit.

No SECURITY.md was found in either repository or the inspected organization default root/.github/docs locations. Organization #24 already explicitly owns adopt/defer/repository-specific decisions for security/support defaults and forbids promising unestablished channels. **Recommendation:** consume that decision when available; do not invent a contact or disclosure promise here. No sensitive vulnerability finding was confirmed or published. This default-policy work does not block drawing/writing.

## Positive observations and historical reconciliation

- Canonical catalogs/profiles remain separate from generated declarations, and candidate tools cannot silently claim stable admission. The distinction between declared and installed SBOMs is documented well.
- Base packages bind catalog intent to architecture-specific locks, signed snapshot metadata, and immutable image digests; image verification checks installed state and cleanup. Services/privilege stay outside base/full defaults.
- CI uses SHA-pinned actions, checksum-verified Task, native architecture assertions, and read-only PR validation. Local tasks remain directly callable.
- The August organization audit's zero pins/no workflow/no Dockerfile and placeholder-pin concerns are **apparently resolved** for the inspected base path. Missing actual projection releases is **recurring**. The two negative-input defects are **new**.
- No artwork or comic manuscript is managed here in the inspected tree; no authored architecture, original asset, or creative material was rewritten.

## Validation and limits

Exact command records and evidence labels are in the JSON companion. `task check` ran with Task 3.53.1, Python 3.12.14, Bash 5.2.21, and ShellCheck 0.10.0 on Linux x86_64. Task's download matched the workflow-pinned SHA-256. Temporary external validation tools are not project dependency changes.

The additional probe was:

```python
import copy
from pathlib import Path
from realm_profiles import load_json, load_profiles, validate_catalog, validate_profiles, resolve_profile
catalog = load_json(Path("catalog/capabilities.json"))
profiles = load_profiles(Path("profiles"))
bad_catalog = copy.deepcopy(catalog)
bad_catalog["capabilities"]["common-cli"]["kind"] = "nonsense"
print(validate_catalog(bad_catalog))  # observed: []
bad_profiles = copy.deepcopy(profiles)
bad_profiles["base"]["constraints"]["allow_privileged"] = "false"
print(validate_profiles(catalog, bad_profiles))  # observed: []
cyclic_profiles = copy.deepcopy(profiles)
cyclic_profiles["base"]["extends"] = ["base"]
resolve_profile(catalog, cyclic_profiles, "base", "linux/amd64", "docker")
# observed: RecursionError
```

Run with `PYTHONPATH=tools python3` from the source checkout. These are synthetic observations, not new repository tests or product fixes. The dependency-free tests do not establish full external JSON Schema-engine validation; that engine was unavailable.

Docker, native ARM64/macOS/Windows, online lock replay, image rebuilds, registry inventories outside GitHub Releases, vulnerability scans, and signing/publication were not executed locally. Hosted October 18 proof is retained with its date/revision, not presented as a fresh local build. No broad upstream-tool/model evaluation or real confidential-data journey was attempted.

## Complete ordered execution ledger

“Ready” means no identified full-outcome dependency/approval gate; it does not mean a feature is implemented or selected for v1. “Gated *” still permits the bounded preparation described in the owning issue. The ledger has **39 distinct local work issues**; root #25, PRs, and external producers are excluded.

| Order | Work | Full outcome | Lane |
| --- | --- | --- | --- |
| 1 | [#50](https://github.com/egohygiene/realm/issues/50) — Fix invalid-inheritance resolution | Ready | core |
| 2 | [#51](https://github.com/egohygiene/realm/issues/51) — Enforce catalog/profile schema parity | Ready | core |
| 3 | [#8](https://github.com/egohygiene/realm/issues/8) — Integrate the verified Mantle runtime | Gated * | core |
| 4 | [#39](https://github.com/egohygiene/realm/issues/39) — Prove the portable Dev Container boundary | Gated * | core-slice |
| 5 | [#10](https://github.com/egohygiene/realm/issues/10) — Deliver the first Dev Container projection | Gated * | core-slice |
| 6 | [#7](https://github.com/egohygiene/realm/issues/7) — Produce image SBOM, provenance, and signing evidence | Gated * | distribution |
| 7 | [#17](https://github.com/egohygiene/realm/issues/17) — Adopt the reviewed container release path | Gated * | distribution |
| 8 | [#6](https://github.com/egohygiene/realm/issues/6) — Build the measured full development image | Gated * | optional |
| 9 | [#48](https://github.com/egohygiene/realm/issues/48) — Package act and the bounded local validation sweep | Ready | optional |
| 10 | [#47](https://github.com/egohygiene/realm/issues/47) — Package release-authoring tools | Gated * | optional |
| 11 | [#19](https://github.com/egohygiene/realm/issues/19) — Consume released Ego Hygiene tools | Gated * | optional |
| 12 | [#40](https://github.com/egohygiene/realm/issues/40) — Add the pinned cheat CLI and completions | Ready | optional |
| 13 | [#44](https://github.com/egohygiene/realm/issues/44) — Add the document-authoring capability | Gated * | optional |
| 14 | [#46](https://github.com/egohygiene/realm/issues/46) — Add the reproducible Nix media capability | Gated * | optional |
| 15 | [#9](https://github.com/egohygiene/realm/issues/9) — Establish the optional service-profile foundation | Gated * | optional |
| 16 | [#13](https://github.com/egohygiene/realm/issues/13) — Evaluate optional orchestration and review services | Gated * | optional |
| 17 | [#15](https://github.com/egohygiene/realm/issues/15) — Evaluate AgentPrism ownership and value | Ready | optional |
| 18 | [#21](https://github.com/egohygiene/realm/issues/21) — Evaluate CodeGraph with measured local fixtures | Ready | optional |
| 19 | [#22](https://github.com/egohygiene/realm/issues/22) — Evaluate whether Cog has a current workload | Ready | optional |
| 20 | [#23](https://github.com/egohygiene/realm/issues/23) — Evaluate Langfuse with synthetic traces | Ready | optional |
| 21 | [#24](https://github.com/egohygiene/realm/issues/24) — Evaluate/package optional Context7 documentation access | Ready | optional |
| 22 | [#26](https://github.com/egohygiene/realm/issues/26) — Generate the organization workspace | Gated * | optional |
| 23 | [#36](https://github.com/egohygiene/realm/issues/36) — Generalize organization workspaces | Gated * | optional |
| 24 | [#27](https://github.com/egohygiene/realm/issues/27) — Provide the local model gateway | Gated * | optional |
| 25 | [#20](https://github.com/egohygiene/realm/issues/20) — Compose the knowledge workspace | Gated * | optional |
| 26 | [#28](https://github.com/egohygiene/realm/issues/28) — Select and define the encrypted vault contract | Gated * | optional |
| 27 | [#29](https://github.com/egohygiene/realm/issues/29) — Implement the selected vault adapter | Gated * | optional |
| 28 | [#30](https://github.com/egohygiene/realm/issues/30) — Prove the confidential workspace | Gated * | optional |
| 29 | [#31](https://github.com/egohygiene/realm/issues/31) — Implement the one-way context import | Gated * | optional |
| 30 | [#32](https://github.com/egohygiene/realm/issues/32) — Evaluate the local chat surface | Gated * | optional |
| 31 | [#33](https://github.com/egohygiene/realm/issues/33) — Package the optional ComfyUI profile | Gated * | optional |
| 32 | [#37](https://github.com/egohygiene/realm/issues/37) — Evaluate the local agent runtime | Gated * | optional |
| 33 | [#38](https://github.com/egohygiene/realm/issues/38) — Evaluate the VS Code agent/chat surface | Gated * | optional |
| 34 | [#34](https://github.com/egohygiene/realm/issues/34) — Prove the complete agent workstation lifecycle | Gated * | optional |
| 35 | [#43](https://github.com/egohygiene/realm/issues/43) — Evaluate a local service-control dashboard | Gated * | optional |
| 36 | [#41](https://github.com/egohygiene/realm/issues/41) — Run the isolated Papra evaluation | Gated * | optional |
| 37 | [#45](https://github.com/egohygiene/realm/issues/45) — Resolve UBI versus Mantle ownership before a new shell | Gated * | decision |
| 38 | [#35](https://github.com/egohygiene/realm/issues/35) — Publish the accepted-architecture infographic pair | Gated * | optional |
| 39 | [#42](https://github.com/egohygiene/realm/issues/42) — Backfill ADR history after shared adoption is ready | Gated * | optional |

The verified native tree contains **38 local descendants**. The remaining local work issue has native parent [organization release program #20](https://github.com/egohygiene/.github/issues/20), preserving its original program relationship. The ledger includes it once. API collection reads verified every saved edge; initial parent reads found no pre-existing native relationships, and explicit meaningful textual groupings were retained when attaching them.

## Next checkpoint, stopping rule, and decisions

Start with **#50**, one reviewable repair PR, then #51. Mantle's first checkpoint is its native macOS cleanup regression. The roadmap's finite boundary is the minimal profile/base + verified Mantle activation + one local Dev Container path, with trusted distribution completed separately when publishing is selected. Larger issue acceptance remains open; a bounded first slice does not falsely close #10/#39 or the broader #25 program.

Only the UBI-versus-Mantle owner choice genuinely needs a maintainer design decision now. Release candidate and publication approval occur at their existing gates; no new permission process is introduced. Size budgets and optional feature selection can be proposed within their owning issues when scheduled.

The audit candidate changes only this report/evidence, ROADMAP.md's current pointer, and CONTINUITY.md. No issue was closed, retitled, relabeled, reassigned, or stripped of original body/acceptance text. Final publication receipts and PR scope are recorded in the handoff/evidence. ADR not required: this is an evidence and execution recommendation, not an accepted architecture change.
