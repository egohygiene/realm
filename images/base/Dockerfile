# syntax=docker/dockerfile:1.10@sha256:865e5dd094beca432e8c0a1d5e1c465db5f998dca4e439981029b3b81fb39ed5
# check=error=true

# Realm base development image
#
# This image is intentionally a small, language-neutral foundation for Ego
# Hygiene development containers. Language runtimes, repository-specific
# dependencies, and the Mantle shell experience should be layered on through
# Dev Container Features or consuming repository configuration.

FROM mcr.microsoft.com/devcontainers/base:2.1.15-trixie@sha256:b8c3669fb4cc652621b3386517c40ab3e151e827de958d6fe75528798ffb5727 AS realm-base

# BuildKit supplies the native target architecture. It selects a committed lock
# whose base-platform digest and Debian package versions are architecture bound.
ARG TARGETARCH

# Release metadata should be supplied by the publishing workflow.
ARG IMAGE_CREATED="unknown"
ARG IMAGE_REVISION="unknown"
ARG IMAGE_VERSION="0.0.0-dev"

# The upstream Dev Containers base image provides this interactive, non-root
# user with sudo access. Do not replace it with an application-style user whose
# shell is disabled; this image is intended for development work.
ARG REMOTE_USER="vscode"

LABEL org.opencontainers.image.authors="Alan Szmyt" \
      org.opencontainers.image.base.name="mcr.microsoft.com/devcontainers/base:2.1.15-trixie@sha256:b8c3669fb4cc652621b3386517c40ab3e151e827de958d6fe75528798ffb5727" \
      org.opencontainers.image.created="${IMAGE_CREATED}" \
      org.opencontainers.image.description="Language-neutral base development image for Ego Hygiene repositories." \
      org.opencontainers.image.documentation="https://github.com/egohygiene/realm/tree/main/images/base" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.revision="${IMAGE_REVISION}" \
      org.opencontainers.image.source="https://github.com/egohygiene/realm" \
      org.opencontainers.image.title="Ego Hygiene Realm Base" \
      org.opencontainers.image.url="https://github.com/egohygiene/realm/pkgs/container/realm-base" \
      org.opencontainers.image.vendor="Ego Hygiene" \
      org.opencontainers.image.version="${IMAGE_VERSION}"

# Keep runtime defaults narrow and unsurprising. Build-only configuration such
# as DEBIAN_FRONTEND belongs on the relevant RUN instruction and must not leak
# into interactive containers.
ENV LANG="C.UTF-8" \
    LC_ALL="C.UTF-8" \
    TZ="Etc/UTC"

USER root

SHELL ["/bin/bash", "-o", "errexit", "-o", "nounset", "-o", "pipefail", "-c"]

# Package intent comes from the canonical base profile. The architecture locks
# bind that intent to signed Debian snapshots and exact versions; the installer
# fails closed on any checksum, platform, source, or package mismatch.
COPY --chmod=0755 images/base/scripts/install-apt-packages /usr/local/libexec/realm/install-apt-packages
COPY --chmod=0755 images/base/scripts/verify-apt-packages /usr/local/libexec/realm/verify-apt-packages
COPY --chmod=0755 images/base/scripts/realm-packages /usr/local/bin/realm-packages
COPY --chmod=0755 images/base/tests/smoke.sh /usr/local/libexec/realm/smoke
COPY images/base/packages/locks/debian-trixie-${TARGETARCH}.lock.json /tmp/realm-apt-lock.json
COPY catalog/capabilities.json /tmp/realm-inputs/catalog.json
COPY config/debian-trixie.json /tmp/realm-inputs/config.json
COPY images/base/Dockerfile /tmp/realm-inputs/Dockerfile
COPY profiles/base.profile.json /tmp/realm-inputs/base.profile.json

RUN [[ -n "${TARGETARCH}" ]] \
    && /usr/local/libexec/realm/install-apt-packages \
        --catalog "/tmp/realm-inputs/catalog.json" \
        --config "/tmp/realm-inputs/config.json" \
        --dockerfile "/tmp/realm-inputs/Dockerfile" \
        --lock "/tmp/realm-apt-lock.json" \
        --profile "/tmp/realm-inputs/base.profile.json" \
        --build-revision "${IMAGE_REVISION}" \
    && rm --force "/tmp/realm-apt-lock.json" \
    && rm --recursive --force "/tmp/realm-inputs"

# Restore the non-root interactive development user supplied by the upstream
# image. Dev Container tooling can update this user's UID/GID for the host.
USER ${REMOTE_USER}

WORKDIR /workspaces

# Preserve the upstream image entrypoint and command. The consuming
# devcontainer.json or Compose service owns workspace mounts, lifecycle hooks,
# service orchestration, and any long-running override command.
