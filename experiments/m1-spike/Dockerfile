# PAIEP M1 integration spike — thin RAG slice runner.
# Uses the cached python:3.11-slim base (offline-friendly after first build).
FROM python:3.11-slim

WORKDIR /app

# eMudhra/emSign CA incident: hash-pinned pip >= 26.2.2 and certifi >= 2026.10.19
RUN pip install --no-cache-dir "pip @ https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl#sha256=fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70" \
    && pip install --no-cache-dir --upgrade "certifi>=2026.10.19"

# Install deps first for layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "spike.py"]
