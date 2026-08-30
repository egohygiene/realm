# Realm base image

`realm-base` is the smallest supported Debian Trixie foundation inherited by
Realm's language and full development profiles. It is a non-root development
image, not the complete workstation.

## Scope

The canonical package intent is the resolved `base` profile in
[`../../catalog/capabilities.json`](../../catalog/capabilities.json) and
[`../../profiles/base.profile.json`](../../profiles/base.profile.json). The
Dockerfile and package locks consume that intent; they do not define a second
package list.

The profile currently resolves exactly 13 required apt roots on both supported
platforms:

| Capability | Packages |
| --- | --- |
| `realm-base` | `ca-certificates`, `curl`, `gnupg` |
| `common-cli` | `file`, `git-lfs`, `jq`, `openssh-client`, `rsync`, `tree`, `unzip`, `wget`, `xz-utils`, `zip` |

The image preserves these development-container invariants:

- Debian Trixie on `linux/amd64` and `linux/arm64`;
- the upstream non-root `vscode` user with non-interactive `sudo`;
- `C.UTF-8` locale data, UTC, CA certificates, and Bash prerequisites;
- no language runtime, background service, host daemon, or privileged default;
- exact locked versions installed from signed, timestamped Debian snapshots;
- service-start suppression during package installation; and
- cleaned apt indexes and archives in the completed image.

Dockerfile `SHELL` selects the interpreter for build instructions. It does not
change the user's interactive shell or activate Mantle.

## Immutable inputs

[`../../config/debian-trixie.json`](../../config/debian-trixie.json) records:

- the readable Microsoft Dev Containers base tag and immutable OCI index
  digest;
- the matching `amd64` and `arm64` platform-manifest digests;
- independent Debian archive and security snapshot identifiers;
- the expected signed `InRelease` hashes; and
- the resolver keyring artifact and checksum.

The generated locks live in [`packages/locks/`](packages/locks/) and bind those
inputs to the catalog checksum, platform, exact package candidates, capability
owners, and a deterministic lock checksum. See
[`../../docs/apt-package-locks.md`](../../docs/apt-package-locks.md) before
refreshing them.

## Installed evidence

Each completed image exposes offline diagnostics under
`/usr/local/share/realm/packages/`:

| Path | Purpose |
| --- | --- |
| `apt-lock.json` | The exact lock consumed by the build |
| `apt-installed.tsv` | Locked and installed versions with provenance fields |
| `build-metadata.json` | Source revision, snapshots, digests, and lock checksum |

Run `realm-packages`, `realm-packages --json`, or `realm-packages --lock` inside
the image to inspect that evidence without network access.

On a native host or CI runner, replay the lock, build the image, verify its
inventory, and run the non-root smoke test with:

```bash
task packages:verify ARCH="amd64"
task image:size ARCH="amd64"
```

Repeat with `ARCH="arm64"` on an Arm64 runner. Size output is informational in
the base-image issue; the explicit full-image budget belongs to issue #6.

## Explicit boundaries

- [Issue #5](https://github.com/egohygiene/realm/issues/5) owns language,
  media, cloud, Git, and other curated workstation profiles.
- [Issue #6](https://github.com/egohygiene/realm/issues/6) owns the complete
  stable-profile union, image-size budgets, and the delta from this base.
- The explicit `services` profile or consuming orchestration owns privileged
  host and service capabilities; neither the base nor `full` inherits them.

Adding a convenient tool directly to this Dockerfile would bypass those
boundaries. Change package intent through the capability/profile contract and
regenerate the affected locks instead.
