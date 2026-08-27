FROM node:22-bookworm-slim AS build
ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH
WORKDIR /build
RUN corepack enable && corepack prepare pnpm@10.32.1 --activate
COPY apps/web/package.json apps/web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY apps/web/ ./
RUN pnpm build

FROM nginxinc/nginx-unprivileged:1.28.3-alpine3.23
# Pin the patched stable Nginx release rather than the moving 1.28-alpine tag.
# Apply any remaining Alpine security updates while building the immutable
# image, assert the expected Nginx patch level, then return to non-root UID 101.
USER root
RUN apk upgrade --no-cache \
    && nginx -v 2>&1 | grep -q 'nginx/1.28.3'
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /build/dist /usr/share/nginx/html
USER 101
EXPOSE 8080
HEALTHCHECK --interval=20s --timeout=5s --retries=5 CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
