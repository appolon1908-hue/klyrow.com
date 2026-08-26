FROM node:22-alpine AS auth-web
WORKDIR /web
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
COPY --from=auth-web /web/dist ./app/auth_web
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=5s --retries=5 CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/v1/health')"
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
