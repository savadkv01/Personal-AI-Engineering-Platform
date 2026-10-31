# PAIEP ingestion runner (M3) — load -> chunk -> embed -> upsert.
# Built from the repo root (context: ..) so it can COPY the rag package,
# the ingest CLI, and config. The knowledge corpus is mounted at runtime.
# Cached python:3.11-slim base -> offline-friendly after first build.
FROM python:3.11-slim

WORKDIR /app

# eMudhra/emSign CA incident: hash-pinned pip >= 26.2.2 and certifi >= 2026.10.19
RUN pip install --no-cache-dir "pip @ https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl#sha256=fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70" \
    && pip install --no-cache-dir --upgrade "certifi>=2026.10.19"

# Install deps first for layer caching.
COPY rag/ingest/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# App code + config (corpus is mounted read-only at /app/knowledge).
COPY rag /app/rag
COPY memory /app/memory
COPY scripts/ingest.py /app/scripts/ingest.py
COPY scripts/rag-query.py /app/scripts/rag-query.py
COPY scripts/memory-cli.py /app/scripts/memory-cli.py
COPY config /app/config

ENV PYTHONPATH=/app \
    INGEST_PATHS=knowledge \
    INGEST_SOURCE_ROOT=/app

ENTRYPOINT ["python", "/app/scripts/ingest.py"]
CMD ["knowledge"]
