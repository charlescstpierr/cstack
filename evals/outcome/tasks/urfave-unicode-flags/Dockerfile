FROM golang:1.22
ENV GOTOOLCHAIN=local GOFLAGS=-mod=mod GOSUMDB=off
# Source at base_sha and the modules listed in its go.sum, fetched by the builder
# into a file-based module proxy, then loaded into the module cache.
# The graded checkout is mounted at /work.
ADD https://github.com/urfave/cli.git#277cbea35016fe8e389643ffe9f659ea2e9efe8b /opt/src
ADD https://proxy.golang.org/github.com/stretchr/testify/@v/v1.12.1.info /opt/goproxy/github.com/stretchr/testify/@v/v1.12.1.info
ADD https://proxy.golang.org/github.com/stretchr/testify/@v/v1.12.1.mod /opt/goproxy/github.com/stretchr/testify/@v/v1.12.1.mod
ADD https://proxy.golang.org/github.com/stretchr/testify/@v/v1.12.1.zip /opt/goproxy/github.com/stretchr/testify/@v/v1.12.1.zip
ADD https://proxy.golang.org/go.yaml.in/yaml/v3/@v/v3.0.5.info /opt/goproxy/go.yaml.in/yaml/v3/@v/v3.0.5.info
ADD https://proxy.golang.org/go.yaml.in/yaml/v3/@v/v3.0.5.mod /opt/goproxy/go.yaml.in/yaml/v3/@v/v3.0.5.mod
ADD https://proxy.golang.org/go.yaml.in/yaml/v3/@v/v3.0.5.zip /opt/goproxy/go.yaml.in/yaml/v3/@v/v3.0.5.zip
RUN cd /opt/src && GOPROXY=file:///opt/goproxy go mod download \
    && GOPROXY=off go test -count=1 -run '^$' . \
    && cd / && rm -rf /opt/src /opt/goproxy
ENV GOPROXY=off
WORKDIR /work
