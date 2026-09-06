ARG GOLANG_BUILDER_IMAGE=mirror.gcr.io/library/golang@sha256:e401dae1bf814e29204a8cb7915682e1780951e609ca0dd8865ee1937f510c48
ARG POSTGRES_BASE_IMAGE=mirror.gcr.io/library/postgres@sha256:051f7b7b3abdd564d5d1bd1e8c4b9c1b6e77087d1dd22020ede611c096a272e0

FROM ${GOLANG_BUILDER_IMAGE} AS gosu-builder
ARG SOURCE_DATE_EPOCH=0

ADD --checksum=sha256:cd9719b775dbfedae53923c9b0dc792b66d42c51e0b36652ed6f747fbadc0164 \
    https://github.com/tianon/gosu/archive/refs/tags/1.19.tar.gz /tmp/gosu.tar.gz
RUN set -eux; \
    test "${SOURCE_DATE_EPOCH}" -ge 0; \
    mkdir -p /src /out; \
    tar -C /src --strip-components=1 -xzf /tmp/gosu.tar.gz; \
    cd /src; \
    CGO_ENABLED=0 go build \
      -trimpath \
      -buildvcs=false \
      -ldflags='-d -w -buildid=' \
      -o /out/gosu .; \
    /out/gosu --version | grep -F '1.19 (go1.25.13 '; \
    touch -d "@${SOURCE_DATE_EPOCH}" /out/gosu

FROM ${POSTGRES_BASE_IMAGE} AS postgres-runtime
ARG SOURCE_COMMIT_SHA=unknown
ARG SOURCE_DATE_EPOCH=0

LABEL org.opencontainers.image.source="https://github.com/appolon1908-hue/klyrow.com" \
      org.opencontainers.image.revision="${SOURCE_COMMIT_SHA}" \
      org.opencontainers.image.title="Klyrow hardened PostgreSQL runtime" \
      org.opencontainers.image.description="Digest-pinned PostgreSQL runtime with a checksum-pinned reproducible gosu build"

COPY --from=gosu-builder --chmod=0755 /out/gosu /usr/local/bin/gosu

RUN set -eux; \
    test "${SOURCE_DATE_EPOCH}" -ge 0; \
    test -x /usr/local/bin/docker-entrypoint.sh; \
    test "$(gosu --version | awk '{print $1}')" = "1.19"; \
    test "$(postgres --version | awk '{print $3}' | cut -d. -f1)" = "17"; \
    test "$(id -u postgres)" -ne 0; \
    test "$(id -g postgres)" -ne 0; \
    gosu postgres sh -ceu 'test "$(id -u)" -ne 0; test "$(id -g)" -ne 0'

# Deliberately inherit the official image ENTRYPOINT, CMD, STOPSIGNAL, and
# volume initialization contract. The immutable POSTGRES_BASE_IMAGE digest is
# the patch-level authority; this image additionally enforces compatibility
# with the supported PostgreSQL 17 major line.
#
# The entrypoint starts with the privileges needed to initialize/chown a new
# data volume and then executes PostgreSQL as the non-root postgres account
# through the checksum-pinned gosu binary.
