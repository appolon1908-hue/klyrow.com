FROM alpine:3.22
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/opt/python
RUN apk upgrade --no-cache \
    && apk add --no-cache ca-certificates python3 py3-pip
RUN adduser --disabled-password --gecos "" --uid 10001 klyrow
WORKDIR /app
COPY requirements.txt .
RUN /usr/bin/python3 -m pip install --no-cache-dir --break-system-packages \
    --target=/opt/python -r requirements.txt
COPY app ./app
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=5s --retries=5 CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/v1/health')"
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
