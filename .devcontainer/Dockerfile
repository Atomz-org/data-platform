# Tag, not digest. A tag is a moving target, which means this image can change
# underneath the harness on a rebuild; pinning the digest would fix that and
# would also have to be bumped deliberately. Left as a tag for now so the
# container does not rot unattended — recorded here rather than implied, so the
# next person knows it was a choice.
FROM python:3.12-slim-bookworm

# git is not optional here — the provenance chain, the gate and `pf` all shell
# out to it. curl and ca-certificates are for the uv installer below; gh is
# what `pf` uses when a loop proposal opens a pull request.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      git curl ca-certificates gnupg make \
 && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
 && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
 && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends gh \
 && rm -rf /var/lib/apt/lists/*

# uv from the official installer, into a path every shell already has.
ENV UV_INSTALL_DIR=/usr/local/bin
RUN curl -fsSL https://astral.sh/uv/install.sh | sh \
 && uv --version

# A non-root user, so a container escape is not automatically a root escape and
# so files the agent writes are not owned by root on a bind mount.
ARG USERNAME=platform
RUN useradd --create-home --shell /bin/bash ${USERNAME}
USER ${USERNAME}
WORKDIR /workspace
