# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Copy pyproject.toml and uv.lock first to leverage caching
COPY pyproject.toml uv.lock ./

# Install dependencies using UV
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# Copy project files and install
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Reset the entrypoint
ENTRYPOINT []

# Run the FastAPI application
CMD ["uv", "run", "python", "-m", "fastapi", "run", "--host=0.0.0.0"]
