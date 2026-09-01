ARG SOURCE_DATE_EPOCH
FROM mirror.gcr.io/library/golang@sha256:e401dae1bf814e29204a8cb7915682e1780951e609ca0dd8865ee1937f510c48 AS gosu-builder

ADD --checksum=sha256:cd9719b775dbfedae53923c9b0dc792b66d42c51e0b36652ed6f747fbadc0164 \
    https://github.com/tianon/gosu/archive/refs/tags/1.19.tar.gz /tmp/gosu.tar.gz
RUN mkdir -p /src /out \
    && tar -C /src --strip-components=1 -xzf /tmp/gosu.tar.gz \
    && cd /src \
    && CGO_ENABLED=0 go build \
        -trimpath \
        -buildvcs=false \
        -ldflags='-d -w -buildid=' \
        -o /out/gosu . \
    && /out/gosu --version | grep -F '1.19 (go1.25.13 '

FROM mirror.gcr.io/library/postgres@sha256:051f7b7b3abdd564d5d1bd1e8c4b9c1b6e77087d1dd22020ede611c096a272e0 AS postgres
COPY --from=gosu-builder /out/gosu /usr/local/bin/gosu
RUN test "$(gosu --version | awk '{print $1}')" = 1.19 \
    && gosu nobody true

FROM mirror.gcr.io/library/mariadb@sha256:611a2fcc5fa7c6ceb8644c6f74b25ede004ff6c3a6b38c8f8c23d3bbf6c26430 AS mariadb
COPY --from=gosu-builder /out/gosu /usr/local/bin/gosu
RUN test "$(gosu --version | awk '{print $1}')" = 1.19 \
    && gosu nobody true
