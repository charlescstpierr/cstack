# Test runtime for jd/tenacity@c650fb45204635 (base_sha). The graded checkout is mounted at /work and
# imported from source through PYTHONPATH; the project itself is not installed.
# Dependencies come from Debian packages so the image builds without PyPI access.
FROM debian:trixie-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pytest python3-tornado python3-typeguard python3-trio \
    && rm -rf /var/lib/apt/lists/*
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/work
WORKDIR /work
