#!/bin/bash
# cloudrun/run_dev_docker.sh - Local development with Docker and hot reloading

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

echo "Building development Docker image..."
docker build -f Dockerfile.dev -t model-checker-dev .

echo "Starting development container with hot reloading..."
docker run -p 8080:8080 \
    -e SPECKLE_APP_ID="$SPECKLE_APP_ID" \
    -e SPECKLE_APP_SECRET="$SPECKLE_APP_SECRET" \
    -e SPECKLE_CHALLENGE_ID="$SPECKLE_CHALLENGE_ID" \
    -e SPECKLE_SERVER_URL="$SPECKLE_SERVER_URL" \
    -e GOOGLE_APPLICATION_CREDENTIALS="/app/key.json" \
    -v "$GOOGLE_APPLICATION_CREDENTIALS:/app/key.json:ro" \
    -v "$(pwd):/app" \
    model-checker-dev

# This mounts your current directory as a volume for hot reloading
# Any changes to your code will be reflected immediately