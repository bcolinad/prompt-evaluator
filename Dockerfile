# ── Stage 1: Base ────────────────────────────────────────
FROM python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies required by asyncpg, psycopg2, and document processing
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# ── Stage 2: Development ────────────────────────────────
FROM base AS dev

# Install all dependencies including dev extras
RUN uv sync --extra dev --no-install-project

# Copy the rest of the application
COPY . .

# Install the project itself
RUN uv sync --extra dev

EXPOSE 8000

# Development: Chainlit with watch mode for hot reload
CMD ["uv", "run", "python", "run.py", "run", "src/app.py", "-w", "--host", "0.0.0.0", "--port", "8000"]

# ── Stage 3: Production ─────────────────────────────────
FROM base AS production

# Install only production dependencies
RUN uv sync --no-install-project

# Copy the rest of the application
COPY . .

# Install the project itself
RUN uv sync

EXPOSE 8000

# Production: Chainlit without watch mode
CMD ["uv", "run", "python", "run.py", "run", "src/app.py", "--host", "0.0.0.0", "--port", "8000"]
