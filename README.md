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
- [`profiles/`](profiles/) defines `base`, language variants, `full`, and an
  explicit `services` boundary.
- [`schemas/`](schemas/) publishes the v1 catalog, profile, and resolved-profile
  contracts.
- [`tools/realm_profiles.py`](tools/realm_profiles.py) validates and resolves the
  model without third-party dependencies.
- [`docs/profiles.md`](docs/profiles.md) records profile semantics and release
  boundaries.
- [`docs/mantle-shell.md`](docs/mantle-shell.md) explains build-time `SHELL`
  versus an installed interactive Mantle shell.

Validate and resolve the full Docker projection:

```bash
python3 tools/realm_profiles.py validate-catalog
python3 tools/realm_profiles.py validate-profiles
python3 tools/realm_profiles.py resolve \
  --profile "full" \
  --platform "linux/amd64" \
  --projection "docker" \
  --output "/tmp/realm-full.json"
python3 -m unittest discover --start-directory tests --verbose
```

This contract intentionally precedes image generation. Published images must be
rendered from a resolved profile, built for supported platforms, tested, and
then referenced by immutable digest.
