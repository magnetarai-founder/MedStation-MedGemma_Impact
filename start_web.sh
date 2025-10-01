#!/bin/bash

# Start script for Neutron Star web version

echo "🚀 Starting Neutron Star Web..."

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
    pip install -q -r requirements.txt
    pip install -q -r backend_requirements.txt
else
    echo "✓ Python dependencies already installed"
fi

# Start backend in background
echo "Starting backend API server..."
cd api
uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level warning &
BACKEND_PID=$!
cd ..

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
cd frontend
if [ ! -d "node_modules" ] || [ ! -f "node_modules/.package-lock.json" ]; then
    echo "Installing frontend dependencies..."
    npm install --silent
else
    echo "✓ Frontend dependencies already installed"
fi

# Start frontend
echo "Starting frontend development server..."
echo ""
echo "🌟 Neutron Star Web is starting up..."
echo "📡 Backend API: http://localhost:8000"
echo "🖥️  Frontend UI: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait a bit for servers to start
sleep 3

# Open browser
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open http://localhost:5173
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    xdg-open http://localhost:5173 2>/dev/null || sensible-browser http://localhost:5173
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    # Windows
    start http://localhost:5173
fi

# Start frontend (this will block)
npm run dev

# Cleanup on exit
trap "echo 'Stopping services...'; kill $BACKEND_PID 2>/dev/null" EXIT
