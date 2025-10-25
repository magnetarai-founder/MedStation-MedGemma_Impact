#!/bin/bash
# ElohimOS Python Environment Setup
# Creates virtual environment and installs all dependencies

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}ElohimOS Python Environment Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Navigate to project root
cd "$(dirname "$0")/../.."
PROJECT_ROOT=$(pwd)

echo -e "${YELLOW}Project root:${NC} $PROJECT_ROOT"
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

echo -e "${YELLOW}Checking Python version...${NC}"
echo "  Found: Python $PYTHON_VERSION"

if [ "$PYTHON_MAJOR" -lt 3 ] || [ "$PYTHON_MINOR" -lt 11 ]; then
    echo -e "${RED}✗ Error: Python 3.11+ required${NC}"
    echo "  Current: Python $PYTHON_VERSION"
    echo "  Install with: brew install python@3.11"
    exit 1
fi

echo -e "${GREEN}  ✓ Python version OK${NC}"
echo ""

# Create virtual environment
if [ -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment already exists${NC}"
    echo "  Location: $PROJECT_ROOT/venv"
else
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}  ✓ Virtual environment created${NC}"
fi
echo ""

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Verify activation
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${RED}✗ Failed to activate virtual environment${NC}"
    exit 1
fi

echo -e "${GREEN}  ✓ Virtual environment activated${NC}"
echo "  Path: $VIRTUAL_ENV"
echo ""

# Upgrade pip
echo -e "${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip --quiet
echo -e "${GREEN}  ✓ pip upgraded${NC}"
echo ""

# Install production dependencies
echo -e "${YELLOW}Installing production dependencies...${NC}"
if [ -f "apps/backend/requirements.txt" ]; then
    pip install -r apps/backend/requirements.txt
    echo -e "${GREEN}  ✓ Production dependencies installed${NC}"
else
    echo -e "${RED}  ✗ Warning: apps/backend/requirements.txt not found${NC}"
fi
echo ""

# Install development dependencies
echo -e "${YELLOW}Installing development dependencies...${NC}"
if [ -f "requirements-dev.txt" ]; then
    pip install -r requirements-dev.txt
    echo -e "${GREEN}  ✓ Development dependencies installed${NC}"
else
    echo -e "${RED}  ✗ Warning: requirements-dev.txt not found${NC}"
fi
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}To activate the environment:${NC}"
echo "  source venv/bin/activate"
echo ""
echo -e "${YELLOW}To deactivate:${NC}"
echo "  deactivate"
echo ""
echo -e "${YELLOW}Development tools available:${NC}"
echo "  ruff check apps/backend/api/     # Lint Python code"
echo "  black apps/backend/api/          # Format Python code"
echo "  pytest apps/backend/tests/       # Run tests"
echo "  mypy apps/backend/api/           # Type check"
echo ""
echo -e "${YELLOW}To start ElohimOS:${NC}"
echo "  omni    # (if alias configured)"
echo "  ./elohim"
echo ""
