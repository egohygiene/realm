# syntax=docker/dockerfile:1
# check=error=true

# Realm base development image
#
# This image is intentionally a small, language-neutral foundation for Ego
# Hygiene development containers. Language runtimes, repository-specific
# dependencies, and the Mantle shell experience should be layered on through
# Dev Container Features or consuming repository configuration.

ARG DEVCONTAINERS_BASE_VERSION="2"
ARG DEBIAN_VARIANT="trixie"

FROM mcr.microsoft.com/devcontainers/base:${DEVCONTAINERS_BASE_VERSION}-${DEBIAN_VARIANT} AS realm-base

# Re-declare global build arguments so they are available in this stage.
ARG DEVCONTAINERS_BASE_VERSION
ARG DEBIAN_VARIANT

# Release metadata should be supplied by the publishing workflow.
ARG IMAGE_CREATED="unknown"
ARG IMAGE_REVISION="unknown"
ARG IMAGE_VERSION="0.0.0-dev"

# The upstream Dev Containers base image provides this interactive, non-root
# user with sudo access. Do not replace it with an application-style user whose
# shell is disabled; this image is intended for development work.
ARG REMOTE_USER="vscode"

LABEL org.opencontainers.image.authors="Alan Szmyt" \
      org.opencontainers.image.base.name="mcr.microsoft.com/devcontainers/base:${DEVCONTAINERS_BASE_VERSION}-${DEBIAN_VARIANT}" \
      org.opencontainers.image.created="${IMAGE_CREATED}" \
      org.opencontainers.image.description="Language-neutral base development image for Ego Hygiene repositories." \
      org.opencontainers.image.documentation="https://github.com/egohygiene/realm/tree/main/docs/images/base" \
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

# Initial cross-repository baseline. Add a package here only when most Realm
# consumers require it. Language runtimes belong in Dev Container Features;
# product-specific libraries belong in the consuming repository.
RUN apt-get update \
    && DEBIAN_FRONTEND="noninteractive" apt-get install --yes --no-install-recommends \
        build-essential \
        ca-certificates \
        ccache \
        clang \
        clang-format \
        clang-tidy \
        cmake \
        curl \
        dnsutils \
        file \
        gettext \
        git-lfs \
        gnupg \
        htop \
        iputils-ping \
        jq \
        lsof \
        make \
        moreutils \
        net-tools \
        ninja-build \
        openssh-client \
        pkg-config \
        python3 \
        python3-pip \
        python3-venv \
        rsync \
        strace \
        sysstat \
        tcpdump \
        tree \
        unzip \
        uuid-runtime \
        wget \
        xz-utils \
        zip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Restore the non-root interactive development user supplied by the upstream
# image. Dev Container tooling can update this user's UID/GID for the host.
USER ${REMOTE_USER}

WORKDIR /workspaces

# Preserve the upstream image entrypoint and command. The consuming
# devcontainer.json or Compose service owns workspace mounts, lifecycle hooks,
# service orchestration, and any long-running override command.
