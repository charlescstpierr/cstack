# syntax=docker/dockerfile:1
FROM node:24-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
# Source at base_sha, used only to install the locked dependencies. The graded checkout is mounted at /work.
# Optional build secret "ca": an extra CA bundle for TLS-intercepting proxies; unused otherwise.
RUN --mount=type=secret,id=ca \
    if [ -s /run/secrets/ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/ca GIT_SSL_CAINFO=/run/secrets/ca; fi \
    && git init -q /opt/src && cd /opt/src \
    && git fetch -q --depth 1 https://github.com/honojs/hono 1096d66e03a3fd16a5cc5f912c2d5e8fd6d990b0 \
    && git checkout -q FETCH_HEAD \
    && npm install -g bun@1.2.19 \
    && bun install --frozen-lockfile --ignore-scripts \
    && mkdir /deps && mv node_modules /deps/node_modules \
    && cd / && rm -rf /opt/src
ENV CI=1
WORKDIR /work
