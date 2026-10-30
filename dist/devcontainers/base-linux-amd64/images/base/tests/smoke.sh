#!/usr/bin/env bash

set -Eeuo pipefail


# @description Fail with a focused image-smoke diagnostic.
# @arg $1 string Failure reason.
# @exitcode 1 Always.
die() {
    printf "Realm base smoke test failed: %s\n" "$1" >&2
    exit 1
}


# @description Assert one command is available to the normal development user.
# @arg $1 string Command name.
require_command() {
    command -v "$1" >/dev/null 2>&1 || die "missing command: $1"
}


# @description Exercise the minimal base as its default non-root user.
main() {
    [[ "$(id --user --name)" == "vscode" ]] || die "default user must remain vscode"
    [[ "$(id --user)" -ne 0 ]] || die "default user must be non-root"
    sudo --non-interactive true || die "vscode must retain non-interactive sudo"
    [[ "${LANG:-}" == "C.UTF-8" ]] || die "LANG must be C.UTF-8"
    [[ "${LC_ALL:-}" == "C.UTF-8" ]] || die "LC_ALL must be C.UTF-8"
    [[ -s /etc/ssl/certs/ca-certificates.crt ]] || die "CA certificate bundle is missing"
    [[ -x /bin/bash ]] || die "Bash shell prerequisite is missing"

    for command_name in curl file gpg jq rsync ssh tree unzip wget xz zip realm-packages; do
        require_command "${command_name}"
    done
    git lfs version >/dev/null
    realm-packages --json >/dev/null
    printf "Realm base smoke test passed for %s\n" "$(dpkg --print-architecture)"
}


main "$@"
