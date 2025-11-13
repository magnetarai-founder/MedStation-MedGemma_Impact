#!/bin/bash
set -e

echo "=================================="
echo "ElohimOS Backend Development Setup"
echo "=================================="
echo ""

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ Error: ElohimOS requires macOS for Metal framework support"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $PYTHON_VERSION"

# Navigate to backend directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "Step 1: Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

echo ""
echo "Step 2: Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"

echo ""
echo "Step 3: Upgrading pip..."
pip install --upgrade pip --quiet
echo "✓ pip upgraded"

echo ""
echo "Step 4: Installing dependencies..."
pip install -r requirements.txt --quiet
echo "✓ Dependencies installed"

echo ""
echo "Step 5: Installing development dependencies..."
pip install pytest pytest-asyncio --quiet
echo "✓ Development dependencies installed"

echo ""
echo "Step 6: Setting environment variables..."
if [ ! -f ".env" ]; then
    cat > .env << EOF
# ElohimOS Development Environment Variables
ELOHIM_ENV=development
ELOHIM_CORS_ORIGINS=http://localhost:4200,http://localhost:5173,http://localhost:5174

# Founder password (default for development)
# Set ELOHIM_FOUNDER_PASSWORD for production deployments
EOF
    echo "✓ Created .env file with development defaults"
else
    echo "✓ .env file already exists"
fi

echo ""
echo "Step 7: Running smoke tests..."
export ELOHIM_ENV=development
if python3 -m pytest tests/smoke/ -v --tb=short 2>&1 | grep -E "passed|failed|skipped" | tail -1; then
    echo "✓ Smoke tests completed"
else
    echo "⚠️  Some smoke tests may have failed - check output above"
fi

echo ""
echo "=================================="
echo "✨ Setup Complete!"
echo "=================================="
echo ""
echo "To start the development server:"
echo "  1. source venv/bin/activate"
echo "  2. export ELOHIM_ENV=development"
echo "  3. uvicorn api.main:app --reload --port 8000"
echo ""
echo "API documentation will be available at:"
echo "  - Swagger UI: http://localhost:8000/api/docs"
echo "  - ReDoc: http://localhost:8000/api/redoc"
echo ""
