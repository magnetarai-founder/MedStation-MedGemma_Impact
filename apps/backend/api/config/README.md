# Configuration Constants

Centralized configuration for MagnetarCode API to eliminate magic numbers and make values easily configurable.

## Usage

```python
from api.config import OLLAMA_TIMEOUT, MAX_AGENT_ITERATIONS

# Use constants instead of hardcoded values
timeout = OLLAMA_TIMEOUT  # Instead of: timeout = 300
```

## Environment Variables

All constants can be overridden via environment variables:

### Timeouts (seconds)

| Constant | Environment Variable | Default | Description |
|----------|---------------------|---------|-------------|
| `OLLAMA_TIMEOUT` | `OLLAMA_TIMEOUT` | 300 | Ollama API request timeout |
| `OLLAMA_CONNECT_TIMEOUT` | `OLLAMA_CONNECT_TIMEOUT` | 10 | Ollama connection timeout |
| `HTTP_REQUEST_TIMEOUT` | `HTTP_REQUEST_TIMEOUT` | 5 | Default HTTP request timeout |
| `HTTP_RESOURCE_TIMEOUT` | `HTTP_RESOURCE_TIMEOUT` | 300 | HTTP resource download timeout |

### Rate Limits

| Constant | Environment Variable | Default | Description |
|----------|---------------------|---------|-------------|
| `CHAT_STREAM_RATE_LIMIT` | `CHAT_STREAM_RATE_LIMIT` | "10/minute" | Chat endpoint rate limit |
| `AGENT_EXECUTION_RATE_LIMIT` | `AGENT_EXECUTION_RATE_LIMIT` | "5/minute" | Agent endpoint rate limit |
| `FILE_WRITE_RATE_LIMIT` | `FILE_WRITE_RATE_LIMIT` | 30 | File writes per minute |
| `FILE_DELETE_RATE_LIMIT` | `FILE_DELETE_RATE_LIMIT` | 20 | File deletes per minute |
| `AUTH_FAILURE_RATE_LIMIT` | `AUTH_FAILURE_RATE_LIMIT` | 5 | Auth failures per minute |

### Context and Content Limits

| Constant | Environment Variable | Default | Description |
|----------|---------------------|---------|-------------|
| `CHAT_CONTEXT_WINDOW` | `CHAT_CONTEXT_WINDOW` | 50 | Terminal lines in context |
| `MAX_AGENT_ITERATIONS` | `MAX_AGENT_ITERATIONS` | 20 | Max agent execution steps |
| `CONTEXT_BUDGET_DEFAULT` | `CONTEXT_BUDGET_DEFAULT` | 8000 | Default token budget |
| `RAG_TOP_K_DEFAULT` | `RAG_TOP_K_DEFAULT` | 5 | RAG results to include |
| `TERMINAL_BUFFER_MAX_LINES` | `TERMINAL_BUFFER_MAX_LINES` | 100 | Max terminal buffer lines |

### Batch Processing

| Constant | Environment Variable | Default | Description |
|----------|---------------------|---------|-------------|
| `VECTOR_BATCH_SIZE` | `VECTOR_BATCH_SIZE` | 32 | Vector indexing batch size |

### Model Defaults

| Constant | Environment Variable | Default | Description |
|----------|---------------------|---------|-------------|
| `DEFAULT_MODEL` | `DEFAULT_MODEL` | "qwen2.5-coder:3b" | Default LLM model |
| `DEFAULT_TEMPERATURE` | `DEFAULT_TEMPERATURE` | 0.7 | Default sampling temperature |

### JWT Configuration

| Constant | Environment Variable | Default | Description |
|----------|---------------------|---------|-------------|
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | 60 | Access token expiry (minutes) |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | 7 | Refresh token expiry (days) |

### File Size Limits

| Constant | Environment Variable | Default | Description |
|----------|---------------------|---------|-------------|
| `MAX_FILE_SIZE_MB` | `MAX_FILE_SIZE_MB` | 10 | Max upload size (MB) |
| `MAX_FILE_SIZE_BYTES` | - | 10485760 | Max size in bytes (computed) |

### Pagination

| Constant | Environment Variable | Default | Description |
|----------|---------------------|---------|-------------|
| `DEFAULT_PAGE_SIZE` | `DEFAULT_PAGE_SIZE` | 50 | Default pagination size |
| `MAX_PAGE_SIZE` | `MAX_PAGE_SIZE` | 100 | Maximum pagination size |

## Example .env Configuration

```env
# Timeouts
OLLAMA_TIMEOUT=600
OLLAMA_CONNECT_TIMEOUT=15

# Rate Limits
CHAT_STREAM_RATE_LIMIT=20/minute
AGENT_EXECUTION_RATE_LIMIT=10/minute

# Context
CHAT_CONTEXT_WINDOW=100
MAX_AGENT_ITERATIONS=30

# Models
DEFAULT_MODEL=qwen2.5-coder:7b
DEFAULT_TEMPERATURE=0.5

# JWT
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=120
JWT_REFRESH_TOKEN_EXPIRE_DAYS=14
```

## Getting Configuration Summary

```python
from api.config import get_config_summary

# Get all configuration values
config = get_config_summary()
print(config)
```

Output:
```json
{
  "timeouts": {
    "ollama": 300,
    "ollama_connect": 10,
    "http_request": 5,
    "http_resource": 300
  },
  "rate_limits": {
    "chat_stream": "10/minute",
    "agent_execution": "5/minute",
    ...
  },
  ...
}
```

## Migration from Magic Numbers

### Before
```python
# chat_api.py
temperature: Optional[float] = Field(0.7, ...)
terminal_lines: Optional[int] = Field(50, ...)

# ollama_client.py
self.timeout = httpx.Timeout(300.0, connect=10.0)

# agent_api.py
@limiter.limit("5/minute")
```

### After
```python
from api.config import (
    DEFAULT_TEMPERATURE,
    CHAT_CONTEXT_WINDOW,
    OLLAMA_TIMEOUT,
    OLLAMA_CONNECT_TIMEOUT,
    AGENT_EXECUTION_RATE_LIMIT
)

# chat_api.py
temperature: Optional[float] = Field(DEFAULT_TEMPERATURE, ...)
terminal_lines: Optional[int] = Field(CHAT_CONTEXT_WINDOW, ...)

# ollama_client.py
self.timeout = httpx.Timeout(OLLAMA_TIMEOUT, connect=OLLAMA_CONNECT_TIMEOUT)

# agent_api.py
@limiter.limit(AGENT_EXECUTION_RATE_LIMIT)
```

## Benefits

1. **Centralized**: All configuration in one place
2. **Configurable**: Override via environment variables
3. **Documented**: Clear descriptions for each constant
4. **Type-safe**: Proper type conversion (int, float, str)
5. **Maintainable**: Easy to update defaults
6. **Testable**: Easy to mock in tests

## Adding New Constants

1. Add constant to `constants.py`:
```python
NEW_CONSTANT = int(os.getenv("NEW_CONSTANT", "42"))
"""Description of what this constant does"""
```

2. Export in `__init__.py`:
```python
__all__ = [
    ...
    "NEW_CONSTANT",
]
```

3. Document in this README

4. Use in code:
```python
from api.config import NEW_CONSTANT
```
