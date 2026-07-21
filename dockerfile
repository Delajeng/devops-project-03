FROM python:3.12-slim-bookworm AS builder
WORKDIR /build
COPY app/requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get upgrade -y && apt-get clean && rm -rf /var/lib/apt/lists/*
# Upgrade pip in the runtime image too — this fixes the HIGH CVE
RUN pip install --upgrade pip
RUN useradd --create-home --uid 1000 appuser
WORKDIR /home/appuser
COPY --from=builder /install /usr/local
COPY app/ ./app/
USER appuser
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "app.main:app"]