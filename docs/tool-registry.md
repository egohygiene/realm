# Curated Tool Evaluation Registry

Realm separates **tool evaluation** from **tool installation**.

The capability catalog answers *how an approved capability can be projected*. The tool evaluation registry answers *whether a tool should be considered for stable Realm inclusion at all*.

## Source of truth

- `catalog/tool-evaluations.json` — review queue and inclusion decisions.
- `schemas/tool-evaluation-registry.v1.schema.json` — portable structural contract.
- `tools/realm_tool_registry.py` — dependency-free policy validation and reporting.

The registry records, for every reviewed tool:

- purpose and category;
- upstream source and license;
- supported platforms;
- security/runtime implications;
- maintenance owner and review cadence;
- overlap with existing tools;
- candidate owning profile;
- stable capability, when the decision has passed admission;
- lifecycle decision and rationale;
- immutable version source and test evidence when stable inclusion is accepted.

## Lifecycle states

### `accepted`

The tool is approved for stable inclusion in the named profile/capability. Accepted tools must have:

- an immutable version source;
- a resolved license;
- an owning Realm profile/capability;
- test evidence;
- explicit security notes;
- a maintenance/review owner.

An `accepted` registry entry does **not** grant runtime credentials or authorization. For example, accepting an IaC CLI means Realm may package the client; it does not give that client permission to apply infrastructure.

An accepted entry must also set `stable_capability` to the catalog capability it
actually supplies. Realm validates that the named `profile_candidate` resolves
that capability for each supported target. Every non-accepted lifecycle state
must set `stable_capability` to `null`; this prevents a candidate from reaching
a stable profile through a metadata-only change.

### `experimental`

The tool is useful enough to evaluate but has not met stable inclusion gates. Common reasons include missing immutable package locks, incomplete architecture support, or insufficient tests.

Experiments must not silently enter stable profiles.

### `deferred`

The tool may be useful, but there is no current need or its cost/risk does not justify adoption yet. A deferred decision should state the trigger for reconsideration.

### `rejected`

The tool should not be included under the current architecture. Rejection records the reason so the organization does not repeatedly rediscover the same decision.

### `superseded`

The tool served a valid historical role but another tool/version/architecture has replaced it. Superseded tools remain visible for migration context.

## Stable-inclusion rule

A tool may only move to `accepted` when its `version_source` is immutable. The
validator accepts pinned semantic versions, full Git commit SHAs, SHA-256 digest
references, or an exact Debian snapshot URL for a snapshot-resolved package.

Do not use these as stable sources:

- `main`
- `master`
- `latest`
- `edge`
- moving release channels
- unversioned installer URLs

Package-manager tools that are not yet locked to an exact snapshot/version should remain `experimental`, even if they are already listed in a capability prototype.

## Security model

The registry records whether a tool:

- needs elevated privileges;
- performs network operations;
- can mutate external systems;
- processes hostile/untrusted inputs;
- creates credential/state implications.

Realm should prefer the least-privileged tool/profile that satisfies the requirement. A tool that requires host/kernel access must not make the default devcontainer privileged.

Credentials, tokens, private keys, cloud login state, and product-specific infrastructure state never belong in the registry or published image.

## Overlap policy

When tools overlap, the registry should explain why both exist or which one wins. Avoid installing several tools merely because they are popular.

Examples from the initial queue:

- OpenTofu and Pulumi are both accepted as optional clients because they represent meaningfully different IaC programming models.
- Terraform is rejected from the generic stable set while OpenTofu already covers the Terraform-compatible capability; a concrete compatibility requirement may reopen that decision.
- Docker Compose v1 is superseded by the v2 plugin architecture.
- Sysdig is deferred because its useful mode may require privilege; lower-risk diagnostics should be preferred first.

## Commands

Validate the registry:

```bash
python3 tools/realm_tool_registry.py validate
```

Render the whole review queue:

```bash
python3 tools/realm_tool_registry.py report
```

Render one state:

```bash
python3 tools/realm_tool_registry.py report --status "experimental"
```

Run all Realm contract tests:

```bash
python3 -m unittest discover --start-directory tests --verbose
```

## Adding a tool

1. Identify a real developer/environment capability rather than starting from a product name.
2. Check whether an existing tool already satisfies the requirement.
3. Verify upstream source, current license, maintenance health, platform support, and security implications.
4. Add the candidate to `catalog/tool-evaluations.json` in sorted order.
5. Choose `experimental`, `deferred`, `rejected`, or `superseded` unless every stable inclusion gate is already met.
6. Before moving to `accepted`, add an immutable version source, owning profile, and test evidence.
7. Run registry validation and the Realm test suite.
8. Only then add or promote the corresponding capability/profile implementation.

## Relationship to later Realm work

Issue #4 owns the decision registry. Later profile/image issues consume it:

```text
candidate tool
    ↓
tool-evaluations.json
    ↓
accepted decision
    ↓
capability catalog
    ↓
profile resolution
    ↓
immutable package/artifact lock
    ↓
build + smoke tests + SBOM
```

This prevents the `full` image from becoming an uncontrolled accumulation of tools and keeps experimental software out of stable profiles by default.
