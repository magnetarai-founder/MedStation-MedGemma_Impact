"""
Configuration Constants for MagnetarCode API

Centralized configuration to eliminate magic numbers and make
values configurable via environment variables.

Usage:
    from api.config import OLLAMA_TIMEOUT, MAX_AGENT_ITERATIONS
"""

import os

# ===== HTTP Timeouts (seconds) =====

OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))  # 5 minutes
"""Timeout for Ollama API requests (default: 300 seconds)"""

OLLAMA_CONNECT_TIMEOUT = int(os.getenv("OLLAMA_CONNECT_TIMEOUT", "10"))  # 10 seconds
"""Connection timeout for Ollama API (default: 10 seconds)"""

HTTP_REQUEST_TIMEOUT = int(os.getenv("HTTP_REQUEST_TIMEOUT", "5"))  # 5 seconds
"""Default HTTP request timeout (default: 5 seconds)"""

HTTP_RESOURCE_TIMEOUT = int(os.getenv("HTTP_RESOURCE_TIMEOUT", "300"))  # 5 minutes
"""HTTP resource download timeout (default: 300 seconds)"""


# ===== Rate Limits (requests per minute) =====

CHAT_STREAM_RATE_LIMIT = os.getenv("CHAT_STREAM_RATE_LIMIT", "10/minute")
"""Chat streaming endpoint rate limit (default: 10 requests/minute)"""

AGENT_EXECUTION_RATE_LIMIT = os.getenv("AGENT_EXECUTION_RATE_LIMIT", "5/minute")
"""Agent execution endpoint rate limit (default: 5 requests/minute)"""

FILE_WRITE_RATE_LIMIT = int(os.getenv("FILE_WRITE_RATE_LIMIT", "30"))
"""File write operations per minute (default: 30)"""

FILE_DELETE_RATE_LIMIT = int(os.getenv("FILE_DELETE_RATE_LIMIT", "20"))
"""File delete operations per minute (default: 20)"""

AUTH_FAILURE_RATE_LIMIT = int(os.getenv("AUTH_FAILURE_RATE_LIMIT", "5"))
"""Authentication failure attempts per minute (default: 5)"""


# ===== Context and Content Limits =====

CHAT_CONTEXT_WINDOW = int(os.getenv("CHAT_CONTEXT_WINDOW", "50"))
"""Number of terminal output lines to include in context (default: 50)"""

MAX_AGENT_ITERATIONS = int(os.getenv("MAX_AGENT_ITERATIONS", "20"))
"""Maximum iterations for agent execution (default: 20)"""

CONTEXT_BUDGET_DEFAULT = int(os.getenv("CONTEXT_BUDGET_DEFAULT", "8000"))
"""Default token budget for context (default: 8000 tokens)"""

RAG_TOP_K_DEFAULT = int(os.getenv("RAG_TOP_K_DEFAULT", "5"))
"""Default number of RAG results to include (default: 5)"""

TERMINAL_BUFFER_MAX_LINES = int(os.getenv("TERMINAL_BUFFER_MAX_LINES", "100"))
"""Maximum lines per terminal command buffer (default: 100)"""


# ===== Vector Processing and Batch Sizes =====

VECTOR_BATCH_SIZE = int(os.getenv("VECTOR_BATCH_SIZE", "32"))
"""Batch size for vector indexing operations (default: 32)"""


# ===== Model Defaults =====

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen2.5-coder:3b")
"""Default LLM model to use (default: qwen2.5-coder:3b)"""

DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))
"""Default sampling temperature for LLM (default: 0.7)"""


# ===== JWT Configuration =====

JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
"""JWT access token expiration in minutes (default: 60)"""

JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
"""JWT refresh token expiration in days (default: 7)"""


# ===== Health Check Settings =====

HEALTH_CHECK_MAX_RETRIES = int(os.getenv("HEALTH_CHECK_MAX_RETRIES", "3"))
"""Maximum retries for health checks (default: 3)"""

HEALTH_CHECK_BACKOFF_INITIAL = float(os.getenv("HEALTH_CHECK_BACKOFF_INITIAL", "0.5"))
"""Initial backoff delay for health check retries in seconds (default: 0.5)"""


# ===== File Size Limits =====

MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
"""Maximum file size for uploads in MB (default: 10)"""

MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
"""Maximum file size in bytes"""


# ===== Pagination Defaults =====

DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", "50"))
"""Default page size for paginated results (default: 50)"""

MAX_PAGE_SIZE = int(os.getenv("MAX_PAGE_SIZE", "100"))
"""Maximum page size for paginated results (default: 100)"""


# ===== Context Engine / RAG Configuration =====

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "512"))
"""Text chunk size for context engine (default: 512)"""

CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
"""Overlap between chunks (default: 50)"""

SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))
"""Minimum similarity score for RAG results (default: 0.7)"""

EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "384"))
"""Dimension of sentence-transformers embeddings (default: 384)"""

MAX_CONTEXT_FILES = int(os.getenv("MAX_CONTEXT_FILES", "10"))
"""Maximum files to include in context (default: 10)"""


# ===== Cache Configuration =====

CACHE_TTL_DEFAULT = int(os.getenv("CACHE_TTL_DEFAULT", "3600"))
"""Default cache TTL in seconds (default: 3600 = 1 hour)"""

CACHE_TTL_SHORT = int(os.getenv("CACHE_TTL_SHORT", "300"))
"""Short cache TTL in seconds (default: 300 = 5 minutes)"""

CACHE_TTL_LONG = int(os.getenv("CACHE_TTL_LONG", "86400"))
"""Long cache TTL in seconds (default: 86400 = 24 hours)"""


# ===== Circuit Breaker Configuration =====

CIRCUIT_BREAKER_FAILURE_THRESHOLD = int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5"))
"""Failures before circuit breaker opens (default: 5)"""

CIRCUIT_BREAKER_TIMEOUT = int(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "60"))
"""Circuit breaker timeout in seconds (default: 60)"""


# ===== Retry Configuration =====

RETRY_MAX_ATTEMPTS = int(os.getenv("RETRY_MAX_ATTEMPTS", "3"))
"""Maximum retry attempts (default: 3)"""

RETRY_BACKOFF_BASE = float(os.getenv("RETRY_BACKOFF_BASE", "2.0"))
"""Base for exponential backoff (default: 2.0)"""

RETRY_MAX_DELAY = int(os.getenv("RETRY_MAX_DELAY", "60"))
"""Maximum retry delay in seconds (default: 60)"""


# ===== Performance Configuration =====

MAX_MESSAGE_LENGTH = int(os.getenv("MAX_MESSAGE_LENGTH", "10000"))
"""Maximum message content length (default: 10000)"""

MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))
"""Maximum tokens for LLM generation (default: 4096)"""

RATE_LIMIT_BURST = int(os.getenv("RATE_LIMIT_BURST", "10"))
"""Rate limit burst allowance (default: 10)"""


# ===== Agent Configuration =====

AGENT_MAX_TOOLS = int(os.getenv("AGENT_MAX_TOOLS", "50"))
"""Maximum custom tools per agent (default: 50)"""

AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "300"))
"""Agent execution timeout in seconds (default: 300)"""

AGENT_PLANNING_TIMEOUT = int(os.getenv("AGENT_PLANNING_TIMEOUT", "60"))
"""Agent planning phase timeout in seconds (default: 60)"""


# ===== Configuration Summary =====


def get_config_summary() -> dict:
    """
    Get a summary of all configuration values.

    Returns:
        Dictionary with all configuration constants
    """
    return {
        "timeouts": {
            "ollama": OLLAMA_TIMEOUT,
            "ollama_connect": OLLAMA_CONNECT_TIMEOUT,
            "http_request": HTTP_REQUEST_TIMEOUT,
            "http_resource": HTTP_RESOURCE_TIMEOUT,
        },
        "rate_limits": {
            "chat_stream": CHAT_STREAM_RATE_LIMIT,
            "agent_execution": AGENT_EXECUTION_RATE_LIMIT,
            "file_write": FILE_WRITE_RATE_LIMIT,
            "file_delete": FILE_DELETE_RATE_LIMIT,
            "auth_failure": AUTH_FAILURE_RATE_LIMIT,
        },
        "context": {
            "chat_window": CHAT_CONTEXT_WINDOW,
            "max_iterations": MAX_AGENT_ITERATIONS,
            "budget_default": CONTEXT_BUDGET_DEFAULT,
            "rag_top_k": RAG_TOP_K_DEFAULT,
            "terminal_buffer": TERMINAL_BUFFER_MAX_LINES,
        },
        "batch_sizes": {
            "vector_indexing": VECTOR_BATCH_SIZE,
        },
        "models": {
            "default_model": DEFAULT_MODEL,
            "default_temperature": DEFAULT_TEMPERATURE,
        },
        "jwt": {
            "access_token_expire_minutes": JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
            "refresh_token_expire_days": JWT_REFRESH_TOKEN_EXPIRE_DAYS,
        },
        "files": {
            "max_size_mb": MAX_FILE_SIZE_MB,
            "max_size_bytes": MAX_FILE_SIZE_BYTES,
        },
        "pagination": {
            "default_page_size": DEFAULT_PAGE_SIZE,
            "max_page_size": MAX_PAGE_SIZE,
        },
        "context_engine": {
            "chunk_size": CHUNK_SIZE,
            "chunk_overlap": CHUNK_OVERLAP,
            "similarity_threshold": SIMILARITY_THRESHOLD,
            "embedding_dimension": EMBEDDING_DIMENSION,
            "max_context_files": MAX_CONTEXT_FILES,
        },
        "cache": {
            "ttl_default": CACHE_TTL_DEFAULT,
            "ttl_short": CACHE_TTL_SHORT,
            "ttl_long": CACHE_TTL_LONG,
        },
        "circuit_breaker": {
            "failure_threshold": CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            "timeout": CIRCUIT_BREAKER_TIMEOUT,
        },
        "retry": {
            "max_attempts": RETRY_MAX_ATTEMPTS,
            "backoff_base": RETRY_BACKOFF_BASE,
            "max_delay": RETRY_MAX_DELAY,
        },
        "performance": {
            "max_message_length": MAX_MESSAGE_LENGTH,
            "max_tokens": MAX_TOKENS,
            "rate_limit_burst": RATE_LIMIT_BURST,
        },
        "agent": {
            "max_tools": AGENT_MAX_TOOLS,
            "timeout": AGENT_TIMEOUT,
            "planning_timeout": AGENT_PLANNING_TIMEOUT,
        },
    }
