# syntax=docker/dockerfile:1
FROM node:24-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
# Source at base_sha, used only to install dependencies. ky has no lockfile, so npm resolves
# versions as of the base commit date (--before). The graded checkout is mounted at /work.
# Optional build secret "ca": an extra CA bundle for TLS-intercepting proxies; unused otherwise.
RUN --mount=type=secret,id=ca \
    if [ -s /run/secrets/ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/ca GIT_SSL_CAINFO=/run/secrets/ca; fi \
    && git init -q /opt/src && cd /opt/src \
    && git fetch -q --depth 1 https://github.com/sindresorhus/ky f87efe6f5d8d6067756a80c5120e7782f4ed847e \
    && git checkout -q FETCH_HEAD \
    && npm install --no-audit --no-fund --ignore-scripts --before=2026-09-12T09:24:32Z \
    && mkdir /deps && mv node_modules /deps/node_modules \
    && cd / && rm -rf /opt/src
ENV CI=1
WORKDIR /work
