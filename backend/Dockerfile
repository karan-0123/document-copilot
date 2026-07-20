FROM python:3.12-slim

# Install uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# Copy application files
COPY alembic.ini alembic.ini
COPY alembic alembic
COPY app app

# Expose FastAPI port
EXPOSE 8000

# Set environment path to the virtualenv binaries
ENV PATH="/app/.venv/bin:$PATH"

# Run FastAPI app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
