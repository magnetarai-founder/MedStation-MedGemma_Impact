#!/bin/bash

# Start script for OmniStudio

echo "🚀 Starting OmniStudio..."

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
if ! python -c "import fastapi, uvicorn, duckdb, pandas" 2>/dev/null; then
    echo "Installing Python dependencies..."
    pip install -q -r apps/backend/backend_requirements.txt
else
    echo "✓ Python dependencies already installed"
fi

# Start Ollama if not already running
if ! pgrep -x "ollama" > /dev/null; then
    echo "Starting Ollama..."
    ollama serve > /dev/null 2>&1 &
    OLLAMA_PID=$!
    sleep 2
    echo "✓ Ollama started"
else
    echo "✓ Ollama already running"
fi

# Validate Metal 4 before starting
python apps/backend/validate_metal4.py

# Start backend in background
echo "Starting backend API server..."
cd apps/backend/api
uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level warning &
BACKEND_PID=$!
cd ../../..

# Wait for backend to start
echo "Waiting for backend to initialize..."
for i in {1..30}; do
    if curl -s http://localhost:8000/ > /dev/null; then
        echo "Backend is ready!"
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

# Install frontend dependencies only if needed
cd apps/frontend
if [ ! -d "node_modules" ] || [ ! -f "node_modules/.package-lock.json" ]; then
    echo "Installing frontend dependencies..."
    npm install --silent
else
    echo "✓ Frontend dependencies already installed"
fi

# Start frontend
echo "Starting frontend development server..."
echo ""
echo "🌟 OmniStudio is starting up..."
echo "📡 Backend API: http://127.0.0.1:8000"
echo "🖥️  Frontend UI: http://127.0.0.1:4200"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait a bit for servers to start
sleep 3

# Open browser
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open http://127.0.0.1:4200
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    xdg-open http://127.0.0.1:4200 2>/dev/null || sensible-browser http://127.0.0.1:4200
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    # Windows
    start http://127.0.0.1:4200
fi

# Start frontend (this will block)
npm run dev

# Cleanup on exit
trap "echo 'Stopping services...'; kill $BACKEND_PID 2>/dev/null; pkill -x ollama 2>/dev/null" EXIT
