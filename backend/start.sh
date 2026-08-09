#!/bin/bash
# Railway start script for Budezivo.cz Backend
# This script ensures proper startup with environment variable expansion

set -e

# Default port if not set by Railway
PORT=${PORT:-8000}

echo "Starting Budezivo.cz Backend..."
echo "Port: $PORT"
echo "Python version: $(python --version)"
echo "Uvicorn version: $(python -c 'import uvicorn; print(uvicorn.__version__)')"

if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERROR: DATABASE_URL is not set; refusing to start backend without database migrations."
  exit 1
fi

echo "Running Alembic migrations..."
alembic upgrade head
echo "Alembic migrations complete."

# Start uvicorn
exec uvicorn main:app --host 0.0.0.0 --port "$PORT" --workers 1
