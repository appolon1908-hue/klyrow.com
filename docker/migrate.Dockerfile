FROM python:3.12.13-alpine3.22@sha256:a190708a2dec1bd18b1decb539f8e8f5407abaa9bf39cacda583f7f8c11db322
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apk add --no-cache --upgrade \
    libcrypto3=3.5.8-r0 \
    libssl3=3.5.8-r0 \
    && rm -f /var/log/apk.log
RUN adduser --disabled-password --gecos "" --uid 10002 klyrow-migrate
WORKDIR /app
COPY apps/gateway/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --no-compile --no-deps -r requirements.txt \
    && pip check
COPY scripts/migrate ./scripts/migrate
COPY migrations ./migrations
USER 10002
ENTRYPOINT ["python", "/app/scripts/migrate"]
