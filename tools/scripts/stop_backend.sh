#!/bin/bash
# Stop MagnetarStudio Backend Server
# Called by Xcode scheme post-action

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PID_FILE="$PROJECT_ROOT/.backend.pid"

# Stop by PID file
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Stopping backend (PID: $PID)..."
        kill "$PID" 2>/dev/null || true

        # Wait for graceful shutdown
        for i in {1..5}; do
            if ! ps -p "$PID" > /dev/null 2>&1; then
                break
            fi
            sleep 1
        done

        # Force kill if still running
        if ps -p "$PID" > /dev/null 2>&1; then
            kill -9 "$PID" 2>/dev/null || true
        fi
    fi
    rm -f "$PID_FILE"
    echo "Backend stopped"
else
    # Fallback: kill any process on port 8000
    PID=$(lsof -ti :8000 2>/dev/null || true)
    if [ -n "$PID" ]; then
        echo "Stopping backend on port 8000 (PID: $PID)..."
        kill "$PID" 2>/dev/null || true
        sleep 1
        kill -9 "$PID" 2>/dev/null || true
        echo "Backend stopped"
    else
        echo "No backend running"
    fi
fi

exit 0
