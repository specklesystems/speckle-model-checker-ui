# cloudrun/Dockerfile
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
  PORT=8080 \
  APP_HOME=/app \
  # Disable Python bytecode files for smaller image
  PYTHONDONTWRITEBYTECODE=1 \
  # Use production-grade defaults
  FLASK_ENV=production

# Set work directory
WORKDIR $APP_HOME

# Install only necessary system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir --no-compile -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -s /bin/bash appuser && \
  chown -R appuser:appuser $APP_HOME && \
  # Create session directory with proper permissions
  mkdir -p /tmp/flask_session && \
  chown -R appuser:appuser /tmp/flask_session

USER appuser

# Expose port
EXPOSE 8080

# Run with optimized gunicorn settings for Cloud Run
CMD exec gunicorn \
  --bind :$PORT \
  --workers 4 \
  --threads 2 \
  --timeout 120 \
  --worker-class gthread \
  --worker-connections 1000 \
  --max-requests 1000 \
  --max-requests-jitter 50 \
  main:app