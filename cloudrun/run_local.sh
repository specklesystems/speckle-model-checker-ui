#!/bin/bash
# cloudrun/run_local.sh - Local development script

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Starting local development server...${NC}\n"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | xargs)
else
    echo -e "${YELLOW}Warning: .env file not found. Create one from .env.example${NC}"
fi

# Check required environment variables
if [ -z "$SPECKLE_APP_ID" ] || [ -z "$SPECKLE_APP_SECRET" ] || [ -z "$SPECKLE_CHALLENGE_ID" ]; then
    echo -e "${YELLOW}Warning: Some required environment variables are missing${NC}"
    echo "Please check: SPECKLE_APP_ID, SPECKLE_APP_SECRET, SPECKLE_CHALLENGE_ID"
fi

# Set development-specific environment variables
export FLASK_ENV=development
export FLASK_DEBUG=1
export PORT=8080

# Start the Flask development server
echo -e "\n${GREEN}Starting Flask development server...${NC}"
echo -e "Server running at: ${YELLOW}http://localhost:8080${NC}"
echo -e "Press CTRL+C to stop\n"

python main.py