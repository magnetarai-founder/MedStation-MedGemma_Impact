#!/bin/bash
# Start MagnetarStudio Backend Server
# Called by Xcode scheme pre-action

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/apps/backend"
PID_FILE="$PROJECT_ROOT/.backend.pid"
LOG_FILE="$PROJECT_ROOT/.backend.log"

# Check if already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "Backend already running (PID: $OLD_PID)"
        exit 0
    else
        rm -f "$PID_FILE"
    fi
fi

# Check if port 8000 is in use
if lsof -i :8000 > /dev/null 2>&1; then
    echo "Port 8000 already in use, assuming backend is running"
    exit 0
fi

echo "Starting MagnetarStudio backend..."

# Start backend in background
cd "$BACKEND_DIR"
export PATH="/opt/homebrew/bin:$PATH"
nohup /opt/homebrew/bin/python3 -m uvicorn api.app_factory:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    > "$LOG_FILE" 2>&1 &

BACKEND_PID=$!
echo $BACKEND_PID > "$PID_FILE"

echo "Backend started (PID: $BACKEND_PID)"
echo "Logs: $LOG_FILE"

# Wait for backend to be ready (max 30 seconds)
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "Backend is ready!"
        exit 0
    fi
    sleep 1
done

echo "Warning: Backend may not be fully ready yet"
exit 0
