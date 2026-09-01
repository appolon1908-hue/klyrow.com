FROM python:3.12.11-alpine3.22@sha256:efcdfa6a6b2fd2afb9c7dfa9a5b288a6f68338b5cfdebe6b637d986067d85757
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN adduser --disabled-password --gecos "" --uid 10002 klyrow-migrate
WORKDIR /app
COPY apps/gateway/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --no-compile --no-deps -r requirements.txt \
    && pip check
COPY scripts/migrate ./scripts/migrate
COPY migrations ./migrations
USER 10002
ENTRYPOINT ["python", "/app/scripts/migrate"]
