#!/bin/bash
# MagnetarStudio Startup Script
# Clean, minimal, production-grade

set -e  # Exit on error

# macOS-only check
if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "❌ MagnetarStudio requires macOS"
    exit 1
fi

# Set development environment (MagnetarStudio with Elohim compatibility)
export MAGNETAR_ENV="${MAGNETAR_ENV:-${ELOHIM_ENV:-development}}"
export MAGNETAR_JWT_SECRET="${MAGNETAR_JWT_SECRET:-${ELOHIM_JWT_SECRET:-dev_secret_do_not_use_in_production_12345678}}"
# Keep legacy names for compatibility
export ELOHIM_ENV="${ELOHIM_ENV:-$MAGNETAR_ENV}"
export ELOHIM_JWT_SECRET="${ELOHIM_JWT_SECRET:-$MAGNETAR_JWT_SECRET}"

echo "🚀 Starting MagnetarStudio..."

# Find Python
PYTHON_CMD=""
for cmd in python3.12 python3.11 python3; do
    if command -v $cmd &> /dev/null; then
        PYTHON_CMD=$cmd
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "❌ Python 3.11+ required"
    exit 1
fi

# Setup venv
if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
fi

source venv/bin/activate

# Install dependencies (silent)
if ! venv/bin/python3 -c "import fastapi" 2>/dev/null; then
    venv/bin/python3 -m pip install -q -r apps/backend/requirements.txt
fi

# Start Ollama if needed
if ! pgrep -x "ollama" > /dev/null && command -v ollama &> /dev/null; then
    nohup ollama serve > /dev/null 2>&1 &
    sleep 2
fi

# Validate Metal 4
venv/bin/python3 apps/backend/validate_metal4.py 2>&1 | grep -E "METAL 4|Device:|Services:"

# Clean ports
for port in 8000 4200; do
    lsof -ti:$port 2>/dev/null | xargs kill -9 2>/dev/null || true
done

# Start backend
cd apps/backend/api
../../../venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level error &
BACKEND_PID=$!
cd ../../..

# Wait for backend
for i in {1..30}; do
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        break
    fi
    sleep 0.5
done

# Install frontend deps (silent)
cd apps/frontend
[ ! -d "node_modules" ] && npm install --silent > /dev/null 2>&1
cd ../..

# Start frontend
cd apps/frontend
npm run dev > /dev/null 2>&1 &
FRONTEND_PID=$!
cd ../..

# Wait for frontend
sleep 2

echo "✓ MagnetarStudio running"
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:4200"
echo ""

# Open browser (use localhost for WebAuthn compatibility)
open http://localhost:4200 2>/dev/null || true

echo "Press Ctrl+C to stop"

# Cleanup on exit
trap "kill $FRONTEND_PID $BACKEND_PID 2>/dev/null; exit" INT TERM

# Keep running
wait
