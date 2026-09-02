FROM node:22-bookworm-slim@sha256:83f487e0a63425e5b4d146fb5e5be574bcbe1b7b843d3ebafdd95eaf7767a7e5 AS build
ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH
WORKDIR /build
RUN corepack enable && corepack prepare pnpm@10.32.1 --activate
COPY apps/web/package.json apps/web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY apps/web/ ./
RUN pnpm build

FROM nginxinc/nginx-unprivileged:1.30.4-alpine3.24@sha256:45ce1e2e699234253d1def7baa96218a5d00b498d1ba0cbb1a17b6bdf73d1351
ARG SOURCE_COMMIT_SHA
RUN test "$(printf '%s' "$SOURCE_COMMIT_SHA" | wc -c)" -eq 40 \
    && case "$SOURCE_COMMIT_SHA" in *[!0-9a-f]*) exit 1 ;; *) : ;; esac
LABEL org.opencontainers.image.source="https://github.com/appolon1908-hue/klyrow.com" \
      org.opencontainers.image.revision="$SOURCE_COMMIT_SHA"
# Pin an exact published patched Nginx runtime rather than a moving minor tag.
# Assert the exact pinned runtime patch level, then return to non-root UID 101.
USER root
RUN nginx -v 2>&1 | grep -q 'nginx/1.30.4' \
    && apk add --no-cache --upgrade 'libexpat=2.8.4-r0' \
    && rm -f /var/log/apk.log
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /build/dist /usr/share/nginx/html
RUN printf '{"source_sha":"%s"}\n' "$SOURCE_COMMIT_SHA" > /usr/share/nginx/html/version.json \
    && chmod 0444 /usr/share/nginx/html/version.json
USER 101
EXPOSE 8080
HEALTHCHECK --interval=20s --timeout=5s --retries=5 CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
