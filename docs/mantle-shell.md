# Mantle activation in Realm

Mantle is a portable environment sourced into a real shell. Its public
Bash/Zsh entrypoint is `.shellrc`; Fish uses
`runtime/shells/fish/runtime.fish` after setting an absolute `MANTLE_ROOT`.
`bin/mantle` is a command dispatcher, not a login shell or a Docker interpreter.
Realm consumes these public surfaces without copying Mantle's implementation.

## Current source boundary

[Issue #8](https://github.com/egohygiene/realm/issues/8) still requires a published,
verified Mantle release. Mantle release preparation is merged, but no release is
published. The bounded canary below uses reviewed source commit
`0f54fa6e100c5b86af64aa383e41eed8c64e363a`, not a released distribution.
[Its pin](../config/mantle-source-canary.json) binds the immutable codeload URL
and SHA-256 `9461d47e66e274e6bdaeb04b77eb069a82d5e5a528139e765211c01c477449ca`.
The archive contains Mantle's MIT license and retained asset notices; source is
acquired outside version control, never vendored into Realm. A reviewed checksum
binds bytes; it is not a signature or publication/provenance verification.

```sh
task check           # Offline; validates the pin without downloading anything.
task mantle:fetch    # Explicit network acquisition; refuses existing output.
task mantle:canary   # Offline after acquisition; requires Bash, Zsh and Fish.
```

Equivalent commands accept an explicit archive location:

```sh
python3 tools/realm_mantle.py fetch --output .cache/realm/mantle-source.tar.gz
python3 tools/realm_mantle.py canary --archive .cache/realm/mantle-source.tar.gz
```

Every canary rechecks the checksum before extracting or executing source. It
rejects traversal, links, duplicate/special members and oversized archives;
temporary files and homes are removed after success or failure. Acquisition
publishes with an exclusive filesystem link, preserving a competing destination.
It never falls back to another commit, release, local sibling checkout or shell.

The canary uses the real pinned installer to copy into a temporary user prefix
and create temporary hooks. Actual shell processes test Bash/Zsh/Fish interactive
startup (without a TTY), explicit noninteractive activation, `ci` profiles,
command status, invalid-profile rejection, missing-runtime Bash recovery and
disabled-hook recovery. Inherited HOME/XDG/startup variables are not forwarded.
Results describe a synthetic filesystem with actual local processes; they do
not prove a native macOS/ARM64/Windows host, TTY behavior, Docker build, VS Code,
Codespaces, or a published release. Missing required shells fail the canary;
offline unit fixtures are not reported as product activation.

## Docker RUN and process activation

Dockerfile `SHELL` selects the interpreter for subsequent shell-form `RUN`
instructions. It does not select a user's login shell, activate a terminal,
or persist environment changes across build layers. Keep Realm's existing
command-compatible Bash interpreter:

```dockerfile
SHELL ["/bin/bash", "-o", "errexit", "-o", "nounset", "-o", "pipefail", "-c"]
# After a separately verified Mantle distribution is installed at this prefix:
RUN export MANTLE_PROFILE=ci && source /opt/mantle/.shellrc && mantle version --short
```

Activation and the dependent command run in the same shell. Each later `RUN`
needs explicit activation again. Realm's base Dockerfile, root shell and user
login shell remain unchanged by this preparation. The catalog's existing Mantle
artifact remains a declaration of intent, not this source canary or an installed
image; released artifact selection and projection belong to #8/#10.

For a CI step or an exec-form entrypoint, use a real interpreter and propagate
activation failure. Pass untrusted arguments as arguments, not interpolated code:

```sh
/bin/bash --noprofile --norc -c '
  export MANTLE_PROFILE=ci
  source "$MANTLE_ROOT/.shellrc" || exit "$?"
  exec "$@"
' realm-ci your-command argument
```

Set `MANTLE_ROOT` to the independently verified installed prefix before running
this command. Keep entrypoint activation opt-in: it affects only that process and
its children. Native Fish must source its own runtime, never Bash `.shellrc`:

```fish
set -gx MANTLE_ROOT /opt/mantle
set -gx MANTLE_PROFILE ci
source "$MANTLE_ROOT/runtime/shells/fish/runtime.fish"; or exit $status
your-command argument
```

## Interactive terminals and login shells

A future released installation should use Mantle's supported installer with
an exact release `--pin`, a user-owned prefix and `--shell bash`, `zsh`, `fish`
or `all`. It manages bounded Bash/Zsh startup blocks and a native Fish `conf.d`
fragment. Bash/Zsh may instead source `"$MANTLE_ROOT/.shellrc"` explicitly;
Fish needs the native entrypoint above. Select `MANTLE_PROFILE=container` before
startup. Login Bash reads its login startup files; the login file must source
the managed `.bashrc` if login sessions should activate it. Do not assume
noninteractive shells read interactive hooks.

Dev Container terminals should select a real installed shell (for example
`terminal.integrated.defaultProfile.linux: "bash"` in VS Code settings) whose
user-owned startup file is configured by the installer. `remoteEnv.SHELL` alone
does not activate Mantle or change `/etc/passwd`; terminal settings do not affect
Docker RUN or CI processes. The portable mapping and future emitted projection
are owned by [#39](https://github.com/egohygiene/realm/issues/39) and
[#10](https://github.com/egohygiene/realm/issues/10).

Do not register `bin/mantle` in `/etc/shells` or use it with `chsh`.
Changing a user's preferred Bash/Zsh/Fish login shell is optional and belongs to
an explicit user-authorized setup after that interpreter, the verified Mantle
release, activation, noninteractive commands and recovery have been validated.
Never change root's login shell. This canary makes no account changes.

## Recovery and release gates

Open `/bin/bash --noprofile --norc` with `BASH_ENV`/`ENV` unset to bypass user
startup hooks. The Mantle installer can disable its own hooks with
`install.sh --disable --prefix /verified/prefix --shell all`; do not delete an
unmanaged dotfile. Missing Mantle payloads must leave a plain shell usable.
Retain the prior verified distribution and use Mantle's documented pinned
update/rollback contract instead of replacing immutable release assets.

Full #8 acceptance still requires a separately approved published Mantle release,
independent checksum/signature/provenance verification, a reviewed release pin,
real image/projection integration and supported-platform/host evidence. Local
source canaries and current source checks do not remove those gates. No hosted
workflow, release, signing, publication, default-shell change or paid resource is
invoked by the offline gate or the source canary.
