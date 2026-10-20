# Sovereign AI Workbench — Backend Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for OCR, PDF rendering, and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml README.md ./

# Install dependencies using uv
RUN uv sync --no-dev

# Copy application code
COPY app/ ./app/
COPY skills/ ../skills/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
