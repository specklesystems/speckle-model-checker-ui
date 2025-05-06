#!/bin/bash
# cloudrun/run_docker_local.sh - Test with Docker locally (exactly like Cloud Run)

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found"
    echo "Please copy .env.example to .env and configure it"
    exit 1
fi

# Load environment variables from .env
set -a
source .env
set +a

echo "Building Docker image..."
docker build -t model-checker-local .

echo "Starting container..."
docker run -p 8080:8080 \
    -e SPECKLE_APP_ID="$SPECKLE_APP_ID" \
    -e SPECKLE_APP_SECRET="$SPECKLE_APP_SECRET" \
    -e SPECKLE_CHALLENGE_ID="$SPECKLE_CHALLENGE_ID" \
    -e SPECKLE_SERVER_URL="$SPECKLE_SERVER_URL" \
    -e GOOGLE_APPLICATION_CREDENTIALS="/app/key.json" \
    -v "$GOOGLE_APPLICATION_CREDENTIALS:/app/key.json:ro" \
    model-checker-local

# Note: This mounts your local Firebase service account key into the container