FROM python:3.12-slim AS builder
WORKDIR /build
COPY app/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-alpine
RUN apk update && apk upgrade && rm -rf /var/cache/apk/*
RUN adduser --disabled-password --uid 1000 appuser
WORKDIR /home/appuser
COPY --from=builder /install /usr/local
COPY app/ ./app/
USER appuser
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "app.main:app"]