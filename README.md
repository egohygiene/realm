# Realm

🌌 A reproducible developer workstation and self-hosted runtime foundation
for projects and organizations.

Realm describes environments as versioned capabilities and composable profiles.
One resolved profile can feed several projections—Docker images, Dev Containers,
Nix, or Linux workstation setup—without turning a Dockerfile into the source of
truth.

## Contract preview

- [`catalog/capabilities.json`](catalog/capabilities.json) defines packages,
  artifacts, dependencies, platforms, projections, and safety constraints.
- [`catalog/tool-evaluations.json`](catalog/tool-evaluations.json) is the curated
  admission queue for tools before they become stable profile capabilities.
- [`profiles/`](profiles/) defines `base`, language variants, `full`, and an
  explicit `services` boundary.
- [`schemas/`](schemas/) publishes the v1 catalog, profile, resolved-profile,
  and tool-evaluation contracts.
- [`tools/realm_profiles.py`](tools/realm_profiles.py) validates and resolves the
  environment model without third-party dependencies.
- [`tools/realm_tool_registry.py`](tools/realm_tool_registry.py) validates tool
  inclusion decisions and renders the review queue.
- [`docs/profiles.md`](docs/profiles.md) records profile semantics and release
  boundaries.
- [`docs/tool-registry.md`](docs/tool-registry.md) documents tool evaluation,
  stable-inclusion gates, overlap decisions, and maintenance policy.
- [`docs/mantle-shell.md`](docs/mantle-shell.md) explains build-time `SHELL`
  versus an installed interactive Mantle shell.

Validate the contracts and resolve the full Docker projection:

```bash
python3 tools/realm_profiles.py validate-catalog
python3 tools/realm_profiles.py validate-profiles
python3 tools/realm_tool_registry.py validate
python3 tools/realm_profiles.py resolve \
  --profile "full" \
  --platform "linux/amd64" \
  --projection "docker" \
  --output "/tmp/realm-full.json"
python3 -m unittest discover --start-directory tests --verbose
```

Render the current tool review queue:

```bash
python3 tools/realm_tool_registry.py report
```

This contract intentionally precedes image generation. A tool must pass the
curated inclusion gates before stable profile admission. Published images must
be rendered from a resolved profile, built for supported platforms, tested, and
then referenced by immutable digest.
