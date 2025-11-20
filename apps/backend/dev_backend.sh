#!/bin/bash
# Development backend launcher for ElohimOS
# Ensures consistent environment and easy startup

set -e

# Navigate to backend directory
cd "$(dirname "$0")"

# Load .env from repo root (two levels up)
if [ -f "../../.env" ]; then
    echo "Loading environment from ../../.env"
    export $(cat ../../.env | grep -v '^#' | xargs)
else
    echo "⚠️  Warning: No .env file found in repo root"
    echo "   Creating one with ELOHIM_ENV=development..."
    echo "ELOHIM_ENV=development" > ../../.env
fi

# Ensure ELOHIM_ENV is set
if [ -z "$ELOHIM_ENV" ]; then
    export ELOHIM_ENV=development
fi

echo ""
echo "================================================"
echo "  ElohimOS Development Backend"
echo "================================================"
echo "  Environment: $ELOHIM_ENV"
echo "  Backend URL: http://localhost:8000"
echo "  Frontend URL: http://localhost:4200"
echo ""
echo "  Founder Login:"
echo "    Username: ${ELOHIM_FOUNDER_USERNAME:-elohim_founder}"
echo "    Password: ${ELOHIM_FOUNDER_PASSWORD:-ElohimOS_2024_Founder}"
echo "================================================"
echo ""

# Start uvicorn with reload
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
