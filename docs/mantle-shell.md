# Mantle shell integration

Mantle is an interactive shell capability owned by `egohygiene/mantle`. Realm
can install and configure it, but must not absorb Mantle's source or redefine its
behavior.

## What Dockerfile `SHELL` actually changes

This is legitimate:

```dockerfile
SHELL ["/usr/local/bin/mantle", "--execute"]
RUN mantle-specific-build-command
```

However, Dockerfile `SHELL` only selects the interpreter used by subsequent
shell-form build instructions such as `RUN`. It does **not** select the login or
interactive shell when a user opens the container. It also creates a bootstrap
problem: every following build instruction now depends on Mantle being present
and stable.

Realm should therefore keep Bash as the build interpreter unless a build step
specifically requires Mantle. The current strict Bash `SHELL` is appropriate for
reliable `RUN` failure behavior.

## Complete interactive setup

The Mantle capability projection should:

1. Fetch a pinned release or commit and verify its checksum/provenance.
2. Install the executable to a stable system path.
3. Register it in `/etc/shells` only if it implements login-shell semantics.
4. Configure the non-root development user through `chsh` only after standalone
   compatibility tests pass.
5. Set `SHELL` in Dev Container remote/container environment configuration for
   tools that consult the variable.
6. Preserve an explicit Bash recovery path and never change root's login shell.
7. Run interactive, login, command-string, signal, terminal, and non-TTY smoke
   tests on Linux amd64/arm64 and supported workstations.

Until Mantle passes that contract, Realm may install it as an opt-in command but
should not make it the default login shell. This avoids turning every image
build or rescue session into an implicit integration test.
