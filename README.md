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
- [`config/debian-trixie.json`](config/debian-trixie.json) pins the Debian
  archive snapshots, signed metadata, resolver keyring, and multi-architecture
  base image.
- [`profiles/`](profiles/) defines `base`, language variants, `full`, and an
  explicit `services` boundary.
- [`schemas/`](schemas/) publishes the v1 catalog, profile, resolved-profile,
  tool-evaluation, apt snapshot, and apt lock contracts.
- [`images/base/packages/locks/`](images/base/packages/locks/) contains the
  committed `amd64` and `arm64` package locks for the base image.
- [`tools/realm_profiles.py`](tools/realm_profiles.py) validates and resolves the
  environment model without third-party dependencies.
- [`tools/realm_apt_packages.py`](tools/realm_apt_packages.py) checks, resolves,
  replays, and previews refreshes of the snapshot-pinned apt locks.
- [`tools/realm_tool_registry.py`](tools/realm_tool_registry.py) validates tool
  inclusion decisions and renders the review queue.
- [`docs/profiles.md`](docs/profiles.md) records profile semantics and release
  boundaries.
- [`docs/tool-registry.md`](docs/tool-registry.md) documents tool evaluation,
  stable-inclusion gates, overlap decisions, and maintenance policy.
- [`docs/mantle-shell.md`](docs/mantle-shell.md) explains build-time `SHELL`
  versus an installed interactive Mantle shell.
- [`docs/apt-package-locks.md`](docs/apt-package-locks.md) documents the apt
  lock design, maintenance workflow, review gates, and limitations.
- [`images/base/README.md`](images/base/README.md) defines the minimal base image
  boundary and its runtime evidence.

## Reproducible base image

Realm's first image projection is a deliberately small Debian Trixie base for
`linux/amd64` and `linux/arm64`. Its 13 direct package roots come only from the
resolved `base` profile (`realm-base` plus `common-cli`):

```text
ca-certificates  curl  file  git-lfs  gnupg  jq  openssh-client
rsync  tree  unzip  wget  xz-utils  zip
```

The readable base-image tag is paired with an immutable OCI index digest and
per-platform manifest digests. Debian archive and security repositories use
explicit snapshots, signed `InRelease` metadata, and exact per-architecture
package versions. A build fails closed when those inputs disagree; it never
falls back to a live mirror.

Language toolchains and curated workstation tools remain in the profile work
tracked by [issue #5](https://github.com/egohygiene/realm/issues/5). The tested
union and its size budget remain in
[issue #6](https://github.com/egohygiene/realm/issues/6). Privileged or
service-backed capabilities are never inherited by the base or `full` profile.

Validate every offline contract, committed lock, script, and unit test through
the repository's stable task interface:

```bash
task check
```

The underlying dependency-free commands remain available for focused checks:

```bash
python3 tools/realm_profiles.py validate-catalog
python3 tools/realm_profiles.py validate-profiles
python3 tools/realm_tool_registry.py validate
python3 tools/realm_apt_packages.py check
python3 -m unittest discover --start-directory "tests" --verbose
```

Resolve the full Docker profile contract without building an image:

```bash
python3 tools/realm_profiles.py resolve \
  --profile "full" \
  --platform "linux/amd64" \
  --projection "docker" \
  --output "/tmp/realm-full.json"
```

Render the current tool review queue:

```bash
python3 tools/realm_tool_registry.py report
```

A tool must pass the curated inclusion gates before stable profile admission.
Published images must be rendered from a resolved profile, built and tested for
every supported platform, and then referenced by immutable digest.
