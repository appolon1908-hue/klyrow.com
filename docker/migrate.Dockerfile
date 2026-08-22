FROM python:3.12.11-alpine3.22
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apk upgrade --no-cache
RUN adduser --disabled-password --gecos "" --uid 10002 klyrow-migrate
WORKDIR /app
COPY apps/gateway/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY scripts/migrate ./scripts/migrate
COPY migrations ./migrations
USER 10002
ENTRYPOINT ["python", "/app/scripts/migrate"]
