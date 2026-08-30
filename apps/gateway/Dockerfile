FROM node:22-bookworm-slim AS web-build
ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH
WORKDIR /build
RUN corepack enable && corepack prepare pnpm@10.32.1 --activate
COPY apps/web/package.json apps/web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY apps/web/ ./
RUN pnpm build

FROM alpine:3.22
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/opt/python
RUN apk upgrade --no-cache \
    && apk add --no-cache ca-certificates python3 py3-pip
RUN adduser --disabled-password --gecos "" --uid 10001 klyrow
WORKDIR /app
COPY apps/gateway/requirements.txt .
RUN /usr/bin/python3 -m pip install --no-cache-dir --break-system-packages \
    --target=/opt/python -r requirements.txt
COPY apps/gateway/app ./app
# The base gateway serves the same reviewed Vue artifact for /login, /app and
# /admin. The optional dedicated web image remains available for split-edge
# deployments, but the base Compose application can no longer return a 503
# merely because the SPA was absent from the Python image.
COPY --from=web-build /build/dist ./app/auth_web
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=5s --retries=5 CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/v1/health')"
CMD ["python3", "-m", "uvicorn", "app.platform:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
