# Test runtime for python-poetry/tomlkit@e23a25438c6c (base_sha). The graded checkout is mounted at /work and
# imported from source through PYTHONPATH; the project itself is not installed.
# Dependencies come from Debian packages so the image builds without PyPI access.
FROM debian:trixie-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pytest python3-yaml \
    && rm -rf /var/lib/apt/lists/*
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/work
WORKDIR /work
