FROM python:3.12-slim-bookworm

# Install system dependencies (including ffmpeg and git for LFS)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    git-lfs \
    curl \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv globally using the official ghcr image layer
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./

# Synchronize python environment
RUN uv sync --frozen --no-dev

# Copy app code
COPY app ./app
COPY main.py ./

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 5000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]
