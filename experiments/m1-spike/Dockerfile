# PAIEP M1 integration spike — thin RAG slice runner.
# Uses the cached python:3.11-slim base (offline-friendly after first build).
FROM python:3.11-slim

WORKDIR /app

# Install deps first for layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "spike.py"]
