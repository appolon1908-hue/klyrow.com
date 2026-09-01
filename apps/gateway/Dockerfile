FROM node:22-bookworm-slim@sha256:83f487e0a63425e5b4d146fb5e5be574bcbe1b7b843d3ebafdd95eaf7767a7e5 AS web-build
ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH
WORKDIR /build
RUN corepack enable && corepack prepare pnpm@10.32.1 --activate
COPY apps/web/package.json apps/web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY apps/web/ ./
RUN pnpm build

FROM python:3.12.11-alpine3.22@sha256:efcdfa6a6b2fd2afb9c7dfa9a5b288a6f68338b5cfdebe6b637d986067d85757
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN adduser --disabled-password --gecos "" --uid 10001 klyrow
WORKDIR /app
COPY apps/gateway/requirements.txt .
RUN /usr/local/bin/python3 -m pip install --no-cache-dir --no-compile --no-deps \
    -r requirements.txt \
    && /usr/local/bin/python3 -m pip check
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
