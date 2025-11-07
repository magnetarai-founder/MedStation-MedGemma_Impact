#!/bin/bash

# Start script for ElohimOS

# macOS-only check
if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "❌ Error: ElohimOS is macOS-only. Detected OS: $(uname -s)"
    echo "This system requires macOS (Darwin) to run."
    exit 1
fi

# Set development environment
export ELOHIM_ENV=development
export ELOHIM_JWT_SECRET="dev_secret_do_not_use_in_production_12345678"

echo "🚀 Starting ElohimOS..."

# Find a compatible Python version (3.12 or 3.11)
PYTHON_CMD=""
if command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
elif command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo "❌ Error: Python 3.11 or 3.12 is required but not found"
    exit 1
fi

echo "Using $PYTHON_CMD"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies only if needed
if ! venv/bin/python3 -c "import fastapi, uvicorn, duckdb, pandas, httpx, jwt" 2>/dev/null; then
    echo "Installing Python dependencies..."
    venv/bin/python3 -m pip install -q -r apps/backend/requirements.txt
else
    echo "✓ Python dependencies already installed"
fi

# Start Ollama if not already running
if ! pgrep -x "ollama" > /dev/null; then
    if command -v ollama &> /dev/null; then
        echo "Starting Ollama..."
        nohup ollama serve > /tmp/ollama.log 2>&1 &
        OLLAMA_PID=$!
        sleep 3
        # Verify Ollama is actually running
        if pgrep -x "ollama" > /dev/null; then
            echo "✓ Ollama started (PID: $OLLAMA_PID)"
        else
            echo "⚠️  Warning: Ollama failed to start (check /tmp/ollama.log)"
        fi
    else
        echo "⚠️  Warning: Ollama not installed - AI features will be unavailable"
    fi
else
    echo "✓ Ollama already running"
fi

# Validate Metal 4 before starting
venv/bin/python3 apps/backend/validate_metal4.py

# Check if backend port 8000 is in use
BACKEND_PORT=8000
if lsof -Pi :$BACKEND_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port $BACKEND_PORT is already in use"
    echo "Attempting to free port $BACKEND_PORT..."

    if lsof -ti:$BACKEND_PORT | xargs kill -9 2>/dev/null; then
        echo "✓ Port $BACKEND_PORT freed successfully"
        sleep 1
    else
        echo "⚠️  Could not free port $BACKEND_PORT"
        # Try fallback ports
        for port in 8001 8002 8003 8004 8005; do
            if ! lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
                BACKEND_PORT=$port
                echo "ℹ️  Using fallback port $BACKEND_PORT for backend"
                break
            fi
        done
    fi
fi

# Start backend in background
echo "Starting backend API server on port $BACKEND_PORT..."
cd apps/backend/api
../../../venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port $BACKEND_PORT --log-level warning &
BACKEND_PID=$!
cd ../../..

# Wait for backend to start
echo "Waiting for backend to initialize..."
for i in {1..30}; do
    if curl -s http://localhost:$BACKEND_PORT/ > /dev/null; then
        echo "✓ Backend is ready on port $BACKEND_PORT!"
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

# Export backend port for frontend (WebSocket + API proxy)
export VITE_WS_PORT=$BACKEND_PORT
export VITE_BACKEND_PORT=$BACKEND_PORT
echo "📡 Frontend will connect to backend on port: $BACKEND_PORT"

# Install frontend dependencies only if needed
cd apps/frontend
if [ ! -d "node_modules" ] || [ ! -f "node_modules/.package-lock.json" ]; then
    echo "Installing frontend dependencies..."
    npm install --silent
else
    echo "✓ Frontend dependencies already installed"
fi

# Check if port 4200 is in use and attempt cleanup
FRONTEND_PORT=4200
if lsof -Pi :$FRONTEND_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port $FRONTEND_PORT is already in use"
    echo "Attempting to free port $FRONTEND_PORT..."

    # Try to kill the process using the port
    if lsof -ti:$FRONTEND_PORT | xargs kill -9 2>/dev/null; then
        echo "✓ Port $FRONTEND_PORT freed successfully"
        sleep 1
    else
        echo "ℹ️  Could not free port $FRONTEND_PORT - Vite will use next available port"
        FRONTEND_PORT="auto"
    fi
fi

# Start frontend
echo "Starting frontend development server..."
echo ""
echo "🌟 ElohimOS is starting up..."
echo "📡 Backend API: http://127.0.0.1:$BACKEND_PORT"
if [ "$FRONTEND_PORT" = "auto" ]; then
    echo "🖥️  Frontend UI: Will open on next available port (likely 4201-4210)"
else
    echo "🖥️  Frontend UI: http://127.0.0.1:$FRONTEND_PORT"
fi
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Start frontend in background to capture the actual port
npm run dev > /tmp/vite-output.log 2>&1 &
FRONTEND_PID=$!

# Wait for frontend to start and detect the actual port
echo "Waiting for frontend to start..."
for i in {1..15}; do
    # Try to extract port from Vite output
    if [ -f /tmp/vite-output.log ]; then
        ACTUAL_PORT=$(grep -o "localhost:[0-9]*" /tmp/vite-output.log | head -1 | cut -d: -f2)
        if [ ! -z "$ACTUAL_PORT" ]; then
            echo "✓ Frontend started on port $ACTUAL_PORT"
            FRONTEND_PORT=$ACTUAL_PORT
            break
        fi
    fi
    echo -n "."
    sleep 1
done
echo ""

# Open browser with actual port
if [ ! -z "$ACTUAL_PORT" ]; then
    sleep 2
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        open http://127.0.0.1:$ACTUAL_PORT
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        xdg-open http://127.0.0.1:$ACTUAL_PORT 2>/dev/null || sensible-browser http://127.0.0.1:$ACTUAL_PORT
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        # Windows
        start http://127.0.0.1:$ACTUAL_PORT
    fi
fi

# Update cleanup trap to include frontend
trap "echo 'Stopping services...'; kill $FRONTEND_PID 2>/dev/null; kill $BACKEND_PID 2>/dev/null; echo 'Shutting down...'" EXIT

# Tail the Vite output (this will block)
tail -f /tmp/vite-output.log
