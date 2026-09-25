# Test runtime for pallets/click@8c1a0a7abbc1 (base_sha). The graded checkout is mounted at /work and
# imported from source through PYTHONPATH; the project itself is not installed.
# Dependencies come from Debian packages so the image builds without PyPI access.
FROM debian:trixie-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pytest \
    && rm -rf /var/lib/apt/lists/*
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/work/src
WORKDIR /work
