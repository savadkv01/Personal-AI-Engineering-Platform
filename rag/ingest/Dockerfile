# PAIEP ingestion runner (M3) — load -> chunk -> embed -> upsert.
# Built from the repo root (context: ..) so it can COPY the rag package,
# the ingest CLI, and config. The knowledge corpus is mounted at runtime.
# Cached python:3.11-slim base -> offline-friendly after first build.
FROM python:3.11-slim

WORKDIR /app

# Install deps first for layer caching.
COPY rag/ingest/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# App code + config (corpus is mounted read-only at /app/knowledge).
COPY rag /app/rag
COPY scripts/ingest.py /app/scripts/ingest.py
COPY scripts/rag-query.py /app/scripts/rag-query.py
COPY config /app/config

ENV PYTHONPATH=/app \
    INGEST_PATHS=knowledge \
    INGEST_SOURCE_ROOT=/app

ENTRYPOINT ["python", "/app/scripts/ingest.py"]
CMD ["knowledge"]
