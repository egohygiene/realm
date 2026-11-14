# Local command-reference capability

The optional `reference` profile selects **cheat 5.1.0** and its upstream Bash
completion dependency. Base/full profiles and their package selection are
unchanged. The current Dev Container emitter remains base-only; profile
resolution is artifact intent, not a claim that optional Docker/Nix adapters or
a published image exist.

## One explicit bootstrap

Use the repository's Python 3.10+ tooling and Bash 4.2+ in a native Linux AMD64 or
ARM64 workspace. Bootstrap installs into your XDG data directory, creates default
configuration only when absent, and adds one guarded block to `~/.bashrc`:

```sh
task cheat:bootstrap
# Without Task:
python3 tools/realm_cheat.py bootstrap
```

Open a new interactive Bash shell, then inspect the tool and the bundled example:

```sh
cheat --version
type cheat
cheat --list
cheat realm
complete -p cheat
```

Typing `cheat --v` followed by Tab completes `--version`. Sheet, tag and path
completion comes from the exact upstream `cheat --completion bash` output. The
activation loads it only when no completion is already registered, uses existing
Bash completion helpers when available and supplies a pinned fallback otherwise.
Repeated activation does not duplicate PATH or registrations. Noninteractive
shells do not activate it. Missing optional activation/completion files stay
quiet; no network, package installation or personal-sheet creation occurs during
shell startup.

An existing `CHEAT_CONFIG_PATH` is preserved. Existing configuration and personal
sheets are not replaced or parsed by bootstrap. An unavailable config path,
conflicting managed file, malformed hook or relative XDG path produces a useful
failure. Managed dotfile symlinks are preserved: use `--no-shell-hook` and source
the reported `activate.bash` through your existing dotfile manager.

## Paths and persistence

| Content | Default path | Ownership |
| --- | --- | --- |
| Versioned installation | `$XDG_DATA_HOME/realm/cheat/5.1.0` | Managed binary, upstream completion/helpers, licenses, activation and read-only Realm example |
| Configuration | `$XDG_CONFIG_HOME/cheat/conf.yml` | User-owned after initial creation; mode 0600 |
| Personal sheets | `$XDG_DATA_HOME/cheat/personal` | User-owned, never overwritten or committed; initial directory mode 0700 |
| Bash integration | One `BEGIN/END REALM CHEAT` block in `~/.bashrc` | Explicit bootstrap updates only its own block and preserves local prose |

Unset XDG variables default to `~/.local/share` and `~/.config`. Use absolute
paths. The binary is under the installation's `bin/`, which activation prepends
once. For an explicit dedicated location or a pre-downloaded archive:

```sh
python3 tools/realm_cheat.py bootstrap \
  --prefix "$HOME/.local/share/realm/cheat/5.1.0" \
  --archive "/absolute/path/cheat-linux-amd64.gz"
```

The gzip SHA-256 is checked before bounded decompression; the resulting executable
must match the selected Linux ELF architecture. Existing managed bytes or modes
must match exactly. Each managed file is created exclusively; the whole bootstrap
is not a multi-file transaction. A late filesystem/concurrency failure may leave
verified owned files for an idempotent retry. No existing different executable,
configuration or personal sheet is overwritten. A `.bashrc` edit detected before
replacement fails instead of discarding that edit.

The default contains one small first-party `realm` example and an empty personal
path. **Community cheatsheets are opt-in**, not fetched during bootstrap or
startup. Follow [upstream cheatpath guidance](https://github.com/cheat/cheat/blob/e2aa2d3611a02593a71cbf645050424228c0e8b0/README.md#cheatpaths)
to add a separately reviewed local community checkout as a read-only path. Keep
that checkout, personal sheets and generated state outside Git/image source.
Editors, pagers, custom helper libraries and local completion configurations are
trusted user settings rather than an isolation boundary.

## Immutable inputs and licenses

[`config/cheat.v1.json`](../config/cheat.v1.json) pins the official Linux AMD64
and ARM64 gzip assets from [cheat 5.1.0](https://github.com/cheat/cheat/releases/tag/5.1.0),
source `e2aa2d3611a02593a71cbf645050424228c0e8b0`. Both release asset digests were
compared with downloaded bytes. Checksums establish byte identity, not an
independent publisher-signature verification.

The small upstream shell resources are retained without modifications under
[`config/cheat/`](../config/cheat/). Their origins and original licenses are:

| Resource | Immutable origin | License |
| --- | --- | --- |
| `completion.bash` | Output of the checksum-verified native cheat 5.1.0 binary's `--completion bash`; SHA-256 is in the pin | Cheat MIT and its vendored Cobra Apache-2.0 completion implementation; original licenses retained as `LICENSE.cheat` and `LICENSE.cobra` |
| `bash_completion` and `bash_completion_compat.bash` | `scop/bash-completion` 2.17.0 at `47cc2eb87af2f95bc3a6b13ccebe6bd39b1b107a`, original `bash_completion` and `bash_completion.d/000_bash_completion_compat.bash` | GPL-2.0-or-later; original `COPYING` retained as `LICENSE.bash-completion` |

The helper fallback is 131,789 bytes plus its compatibility definitions, rather
than a copy of the complete upstream completion catalog. These third-party files
retain their own licenses; Realm's first-party MIT code does not relabel them.
Bootstrap validates their pinned hashes before installation and does not fork the
upstream completion behavior.

## Upgrade, recovery and removal

Maintainers upgrade the release/source/checksums, regenerate the upstream
completion from the verified native binary, review the helper/license sources,
update catalog/registry versions and regenerate profile/Dev Container metadata.
Then rerun the focused and native proofs. Architecture archives must be verified
independently; do not infer ARM64 execution from its ELF header.

Users bootstrap the reviewed successor into a new versioned directory; the
managed Bash block moves to that activation path. Keep previous directories until
configuration references, including the read-only Realm example, have been
reviewed. Existing personal sheets and configuration survive. Changing an already
managed activation's paths deliberately requires a new prefix rather than an
overwrite. To roll back, restore the prior reviewed source/pin and bootstrap its
retained prefix. Start a new shell after either change.

For removal, first remove only the marked Realm cheat block through your dotfile
manager and start a new shell. Review the dedicated installation path before
deleting its managed payload. Retain personal sheets/configuration unless you
explicitly choose to remove them. No automatic uninstall deletes user data.

## Local evidence and limitations

```sh
python3 -m unittest discover --start-directory tests --pattern test_realm_cheat.py --verbose
task check
python3 tools/realm_cheat.py verify --platform linux/arm64 \
  --archive "/absolute/path/cheat-linux-arm64.gz"
```

Synthetic controls cover checksums, architecture, pin shapes, symlinks/modes,
existing content, hook conflicts, explicit paths, repeat runs and guarded
activation. A separate native AMD64 proof bootstraps the actual binary in a
temporary HOME and uses a real interactive PTY to test version, listing, the
example, Tab completion and repeated sourcing without startup errors. Its
sanitized transcript is recorded in the PR evidence. ARM64 archive/ELF checks
are distinct from unrun native ARM64 behavior. No new image build, Dev Container
runtime, Nix/workstation renderer, hosted workflow or publication is qualified.
