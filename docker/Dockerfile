FROM python:3.11-slim

WORKDIR /app

# System deps for PyMuPDF and psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Install CPU-only torch explicitly, BEFORE the rest of requirements.txt.
# sentence-transformers pulls in torch as a dependency, and without this,
# pip resolves the default PyPI build — which includes the full CUDA/GPU
# stack (triton, nvidia-cublas, nvidia-cudnn, etc: several GB) even though
# this project runs CPU-only embedding/reranking locally alongside Ollama.
# Installing the CPU wheel first satisfies the torch dependency before
# sentence-transformers gets a chance to pull the GPU one in.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Run as a non-root user — the default is root, which is unnecessary
# privilege for a process that only needs to read its own app code and
# talk to the network. Files were copied as root above (fine, they only
# need to be readable), then ownership handed to appuser before switching.
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Lets `docker compose ps` / orchestrators report actual readiness, and is
# what docker-compose.yml's depends_on: condition: service_healthy below
# waits on — matters because the API needs Qdrant/Postgres/Ollama up
# before /health can report "ok", not just before the process has started.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
