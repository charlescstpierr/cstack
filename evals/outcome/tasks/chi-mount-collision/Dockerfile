FROM golang:1.24
ENV GOTOOLCHAIN=local GOFLAGS=-mod=mod GOPROXY=off
# Source at base_sha (fetched by the builder), used only to warm the build cache.
# chi has no module dependencies. The graded checkout is mounted at /work.
ADD https://github.com/go-chi/chi.git#bc02284e9db220c644912320fe1db6bc9b4a087c /opt/src
RUN cd /opt/src && go test -count=1 -run '^$' ./... && cd / && rm -rf /opt/src
WORKDIR /work
