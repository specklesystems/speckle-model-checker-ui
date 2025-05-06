#!/bin/bash
# cloudrun/scripts/deploy.sh - Deploy to Google Cloud Run

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if project ID is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Please provide Google Cloud project ID${NC}"
    echo "Usage: ./deploy.sh PROJECT_ID [REGION]"
    exit 1
fi

PROJECT_ID=$1
REGION=${2:-us-central1}  # Default to us-central1 if not provided
SERVICE_NAME="speckle-model-checker"

echo -e "${GREEN}Deploying to Google Cloud Run...${NC}\n"

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | xargs)
else
    echo -e "${YELLOW}Warning: .env file not found${NC}"
fi

# Check required environment variables
if [ -z "$SPECKLE_APP_ID" ] || [ -z "$SPECKLE_APP_SECRET" ]; then
    echo -e "${RED}Error: Missing required environment variables${NC}"
    echo "Please set SPECKLE_APP_ID and SPECKLE_APP_SECRET in .env file"
    exit 1
fi

# Authenticate with Google Cloud (if not already authenticated)
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q ""; then
    echo -e "${YELLOW}Not authenticated with Google Cloud. Please run:${NC}"
    echo "gcloud auth login"
    echo "gcloud auth application-default login"
    exit 1
fi

# Set the project
echo -e "${YELLOW}Setting project to $PROJECT_ID...${NC}"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${YELLOW}Enabling required APIs...${NC}"
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable container.googleapis.com

# Build and deploy to Cloud Run
echo -e "${YELLOW}Building and deploying to Cloud Run...${NC}"
gcloud run deploy $SERVICE_NAME \
    --source . \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --set-env-vars "SPECKLE_APP_ID=$SPECKLE_APP_ID,SPECKLE_APP_SECRET=$SPECKLE_APP_SECRET,SPECKLE_SERVER_URL=$SPECKLE_SERVER_URL,SESSION_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')" \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --timeout 300 \
    --execution-environment gen2

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)')

echo -e "\n${GREEN}Deployment successful!${NC}"
echo -e "Service URL: ${YELLOW}$SERVICE_URL${NC}"
echo -e "\n${GREEN}Next steps:${NC}"
echo "1. Update your Speckle app redirect URL to: $SERVICE_URL/api/auth/token"
echo "2. Test your deployment at: $SERVICE_URL"

# Optionally open in browser
if command -v xdg-open &> /dev/null; then
    xdg-open $SERVICE_URL
elif command -v open &> /dev/null; then
    open $SERVICE_URL
fi