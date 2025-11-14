# ElohimOS Backend Setup

## Prerequisites

- **Python 3.12 or 3.13** (required - Python 3.14 not supported due to `openai-whisper` build failures)
- macOS (ElohimOS is macOS-only for Metal framework support)

### Python Version

ElohimOS backend requires Python 3.12 or 3.13. Python 3.14 is not currently supported due to compatibility issues with the `openai-whisper` dependency.

**Recommended setup:**
```bash
# Using pyenv (recommended)
pyenv install 3.13.0
pyenv local 3.13.0

# Or using system Python
python3.13 -m venv venv
```

The `.python-version` file in this directory specifies Python 3.13.0 for automatic version selection with pyenv.

## Installation

### 1. Create Virtual Environment

```bash
cd /Users/indiedevhipps/Documents/ElohimOS/apps/backend
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Environment Variables

For development, create a `.env` file or export these variables:

```bash
# Development mode (allows default founder password)
export ELOHIM_ENV=development

# Optional: Set custom founder password (required in production)
# export ELOHIM_FOUNDER_PASSWORD=your_secure_password_here

# Optional: Set CORS origins (defaults to localhost:4200, 5173, etc.)
# export ELOHIM_CORS_ORIGINS=http://localhost:4200,http://localhost:5173
```

### 4. Python Path Setup

ElohimOS uses custom packages in `/packages` directory. These are automatically added to sys.path by main.py:
- `neutron_core` - SQL engine
- `neutron_utils` - Utilities
- `pulsar_core` - JSON to Excel engine

No additional setup needed - main.py handles this automatically.

## Running the Backend

### Development Server

```bash
# From apps/backend directory
source venv/bin/activate
export ELOHIM_ENV=development
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Server

```bash
source venv/bin/activate
export ELOHIM_FOUNDER_PASSWORD=your_secure_password
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Testing

### Run Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Install pytest if not already installed
pip install pytest

# Run all tests
pytest apps/backend/tests -v

# Run specific test suites
pytest apps/backend/tests/smoke/ -v           # Smoke tests
pytest apps/backend/tests/vault/ -v           # Vault tests
pytest apps/backend/tests/auth/ -v            # Auth tests
pytest apps/backend/tests/analytics/ -v       # Analytics tests
```

### Verify Installation

Run smoke tests to verify setup:

```bash
pytest tests/smoke/ -v
```

Expected results:
- Some tests may skip if FastAPI not fully configured
- With `ELOHIM_ENV=development` set, most routers should load successfully
- Some optional features (libp2p, MLX) may show warnings - this is expected

## Troubleshooting

### Missing Dependencies

If you see `ModuleNotFoundError`, ensure all dependencies are installed:

```bash
pip install -r requirements.txt
```

### Founder Password Error

If you see `ELOHIM_FOUNDER_PASSWORD environment variable is required`:

```bash
export ELOHIM_ENV=development  # Use dev mode with default password
```

### Metal Framework Errors (macOS only)

Install Metal frameworks:

```bash
pip install pyobjc-framework-Metal pyobjc-framework-MetalPerformanceShaders
```

### MLX Installation (Apple Silicon, Python ≤3.13)

MLX is optional but provides better performance:

```bash
pip install mlx mlx-lm
```

## Router Registry

ElohimOS uses a centralized router registry (`api/router_registry.py`) that loads all API routers on startup. You can verify which routers loaded successfully by checking the startup logs:

```
✓ Services: Chat API, Users API, Team API, Vault API, ...
✗ Failed: <any failed services>
```

Failed services are expected if optional dependencies (like libp2p) are not installed.

## Code Tab

For Code Tab setup and usage (Monaco editor, terminal, workspace management), see [docs/development/CodeTab.md](../../docs/development/CodeTab.md).
