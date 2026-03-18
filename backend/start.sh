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

# Start uvicorn
exec uvicorn main:app --host 0.0.0.0 --port "$PORT" --workers 1
