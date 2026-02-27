FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Railway provides PORT env variable
ENV PORT=8000

# Expose port
EXPOSE $PORT

# Start command - uses shell to expand $PORT
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
