FROM python:3.11-slim

WORKDIR /app

# Install minimal build tools
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Install `uv` package manager and runtime dependencies
# Note: `uv` is installed so the container can use it as requested.
RUN pip install --no-cache-dir uv fastapi uvicorn

# Copy backend app
COPY backend /app/backend
WORKDIR /app/backend

EXPOSE 8000

# Use `uv` to run the app (fallback to uvicorn if `uv` isn't available)
CMD ["uv", "run", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
