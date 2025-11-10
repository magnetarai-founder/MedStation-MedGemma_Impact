#!/usr/bin/env python3
"""
Standardized Error Codes for ElohimOS
Provides consistent error codes and user-friendly messages across the platform
"""

from enum import Enum
from typing import Dict, Any


class ErrorCode(str, Enum):
    """Standardized error codes for ElohimOS API"""

    # Authentication (1000-1099)
    AUTH_INVALID_CREDENTIALS = "ERR-1001"
    AUTH_TOKEN_EXPIRED = "ERR-1002"
    AUTH_INSUFFICIENT_PERMISSIONS = "ERR-1003"
    AUTH_RATE_LIMIT_EXCEEDED = "ERR-1004"
    AUTH_USER_NOT_FOUND = "ERR-1005"
    AUTH_USER_ALREADY_EXISTS = "ERR-1006"
    AUTH_INVALID_TOKEN = "ERR-1007"
    AUTH_ACCOUNT_DISABLED = "ERR-1008"
    AUTH_SESSION_EXPIRED = "ERR-1009"

    # Model Operations (2000-2099)
    MODEL_NOT_FOUND = "ERR-2001"
    MODEL_LOAD_FAILED = "ERR-2002"
    MODEL_INFERENCE_TIMEOUT = "ERR-2003"
    MODEL_CONTEXT_EXCEEDED = "ERR-2004"
    MODEL_ALREADY_LOADED = "ERR-2005"
    MODEL_INVALID_NAME = "ERR-2006"
    MODEL_DOWNLOAD_FAILED = "ERR-2007"
    MODEL_SLOT_OCCUPIED = "ERR-2008"
    MODEL_NOT_LOADED = "ERR-2009"

    # File Operations (3000-3099)
    FILE_TOO_LARGE = "ERR-3001"
    FILE_INVALID_FORMAT = "ERR-3002"
    FILE_UPLOAD_FAILED = "ERR-3003"
    FILE_NOT_FOUND = "ERR-3004"
    FILE_ALREADY_EXISTS = "ERR-3005"
    FILE_PERMISSION_DENIED = "ERR-3006"
    FILE_CORRUPTED = "ERR-3007"
    FILE_SCAN_FAILED = "ERR-3008"

    # Database (4000-4099)
    DB_CONNECTION_FAILED = "ERR-4001"
    DB_QUERY_FAILED = "ERR-4002"
    DB_CONSTRAINT_VIOLATION = "ERR-4003"
    DB_RECORD_NOT_FOUND = "ERR-4004"
    DB_DUPLICATE_ENTRY = "ERR-4005"
    DB_TRANSACTION_FAILED = "ERR-4006"
    DB_MIGRATION_FAILED = "ERR-4007"

    # Configuration (5000-5099)
    CONFIG_INVALID = "ERR-5001"
    CONFIG_MISSING_REQUIRED = "ERR-5002"
    CONFIG_VALIDATION_FAILED = "ERR-5003"
    CONFIG_FILE_NOT_FOUND = "ERR-5004"
    CONFIG_PARSE_ERROR = "ERR-5005"

    # Network/P2P (6000-6099)
    NETWORK_UNREACHABLE = "ERR-6001"
    PEER_CONNECTION_FAILED = "ERR-6002"
    PEER_NOT_FOUND = "ERR-6003"
    PEER_HANDSHAKE_FAILED = "ERR-6004"
    PEER_TIMEOUT = "ERR-6005"
    PEER_AUTHENTICATION_FAILED = "ERR-6006"

    # Workflow/Agent (7000-7099)
    WORKFLOW_NOT_FOUND = "ERR-7001"
    WORKFLOW_VALIDATION_FAILED = "ERR-7002"
    WORKFLOW_EXECUTION_FAILED = "ERR-7003"
    WORKFLOW_TIMEOUT = "ERR-7004"
    AGENT_NOT_AVAILABLE = "ERR-7005"
    AGENT_EXECUTION_FAILED = "ERR-7006"
    TOOL_NOT_FOUND = "ERR-7007"
    TOOL_EXECUTION_FAILED = "ERR-7008"

    # Vault/Security (8000-8099)
    VAULT_LOCKED = "ERR-8001"
    VAULT_UNLOCK_FAILED = "ERR-8002"
    VAULT_ENCRYPTION_FAILED = "ERR-8003"
    VAULT_DECRYPTION_FAILED = "ERR-8004"
    VAULT_ITEM_NOT_FOUND = "ERR-8005"
    BIOMETRIC_AUTH_FAILED = "ERR-8006"
    PANIC_MODE_ACTIVE = "ERR-8007"

    # System (9000-9099)
    SYSTEM_RESOURCE_EXHAUSTED = "ERR-9001"
    SYSTEM_INTERNAL_ERROR = "ERR-9002"
    SYSTEM_NOT_IMPLEMENTED = "ERR-9003"
    SYSTEM_MAINTENANCE_MODE = "ERR-9004"
    SYSTEM_DEPENDENCY_FAILED = "ERR-9005"
    SYSTEM_INVALID_REQUEST = "ERR-9006"
    SYSTEM_VALIDATION_FAILED = "ERR-9007"


# Error message templates with user-friendly messages and actionable suggestions
ERROR_MESSAGES: Dict[ErrorCode, Dict[str, str]] = {
    # Authentication Errors
    ErrorCode.AUTH_INVALID_CREDENTIALS: {
        "user_message": "Invalid username or password",
        "suggestion": "Please check your credentials and try again. If you've forgotten your password, contact your administrator.",
        "technical": "Authentication failed - invalid credentials provided"
    },
    ErrorCode.AUTH_TOKEN_EXPIRED: {
        "user_message": "Your session has expired",
        "suggestion": "Please log in again to continue.",
        "technical": "JWT token has expired"
    },
    ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS: {
        "user_message": "You don't have permission to perform this action",
        "suggestion": "Contact your administrator to request the necessary permissions.",
        "technical": "User lacks required role or permission for this operation"
    },
    ErrorCode.AUTH_RATE_LIMIT_EXCEEDED: {
        "user_message": "Too many requests",
        "suggestion": "Please wait {retry_after} seconds before trying again.",
        "technical": "Rate limit exceeded for this endpoint"
    },
    ErrorCode.AUTH_USER_NOT_FOUND: {
        "user_message": "User not found",
        "suggestion": "The specified user does not exist. Please check the username.",
        "technical": "User ID or username not found in database"
    },
    ErrorCode.AUTH_USER_ALREADY_EXISTS: {
        "user_message": "User already exists",
        "suggestion": "A user with this username or email already exists. Please choose a different one.",
        "technical": "Duplicate user creation attempted"
    },
    ErrorCode.AUTH_INVALID_TOKEN: {
        "user_message": "Invalid authentication token",
        "suggestion": "Your session token is invalid. Please log in again.",
        "technical": "JWT token signature validation failed"
    },
    ErrorCode.AUTH_ACCOUNT_DISABLED: {
        "user_message": "Account disabled",
        "suggestion": "Your account has been disabled. Contact your administrator for assistance.",
        "technical": "User account is marked as disabled"
    },
    ErrorCode.AUTH_SESSION_EXPIRED: {
        "user_message": "Session expired",
        "suggestion": "Your session has timed out. Please log in again.",
        "technical": "Session timeout exceeded"
    },

    # Model Errors
    ErrorCode.MODEL_NOT_FOUND: {
        "user_message": "Model not available",
        "suggestion": "Download the model using 'ollama pull {model}' or select a different model from the list.",
        "technical": "Requested model not found in Ollama"
    },
    ErrorCode.MODEL_LOAD_FAILED: {
        "user_message": "Failed to load model",
        "suggestion": "The model could not be loaded. Try unloading other models first to free up resources.",
        "technical": "Model loading failed - possible memory or configuration issue"
    },
    ErrorCode.MODEL_INFERENCE_TIMEOUT: {
        "user_message": "Model response timed out",
        "suggestion": "The model took too long to respond. Try a smaller model or reduce the context size.",
        "technical": "Model inference exceeded timeout threshold"
    },
    ErrorCode.MODEL_CONTEXT_EXCEEDED: {
        "user_message": "Context too large",
        "suggestion": "Your input exceeds the model's context window ({max_tokens} tokens). Try shortening your message or starting a new conversation.",
        "technical": "Input token count exceeds model's maximum context length"
    },
    ErrorCode.MODEL_ALREADY_LOADED: {
        "user_message": "Model already loaded",
        "suggestion": "This model is already loaded in slot {slot}. Unload it first if you want to reload.",
        "technical": "Attempted to load model that's already in a hot slot"
    },
    ErrorCode.MODEL_INVALID_NAME: {
        "user_message": "Invalid model name",
        "suggestion": "The model name '{model}' is not valid. Check available models with 'ollama list'.",
        "technical": "Model name validation failed"
    },
    ErrorCode.MODEL_DOWNLOAD_FAILED: {
        "user_message": "Model download failed",
        "suggestion": "Could not download the model. Check your internet connection and disk space.",
        "technical": "Ollama pull command failed"
    },
    ErrorCode.MODEL_SLOT_OCCUPIED: {
        "user_message": "Model slot occupied",
        "suggestion": "Slot {slot} is already in use by {current_model}. Unload it first or choose a different slot.",
        "technical": "Hot slot already contains a model"
    },
    ErrorCode.MODEL_NOT_LOADED: {
        "user_message": "Model not loaded",
        "suggestion": "Load the model first before using it.",
        "technical": "Attempted to use model that's not in any hot slot"
    },

    # File Errors
    ErrorCode.FILE_TOO_LARGE: {
        "user_message": "File is too large",
        "suggestion": "Maximum file size is {max_size}MB. Try compressing or splitting the file.",
        "technical": "File size exceeds configured maximum"
    },
    ErrorCode.FILE_INVALID_FORMAT: {
        "user_message": "Invalid file format",
        "suggestion": "Supported formats: {supported_formats}. Please convert your file to one of these formats.",
        "technical": "File format not in allowed list"
    },
    ErrorCode.FILE_UPLOAD_FAILED: {
        "user_message": "File upload failed",
        "suggestion": "The file could not be uploaded. Check your connection and try again.",
        "technical": "File upload operation failed"
    },
    ErrorCode.FILE_NOT_FOUND: {
        "user_message": "File not found",
        "suggestion": "The requested file does not exist or has been deleted.",
        "technical": "File path does not exist"
    },
    ErrorCode.FILE_ALREADY_EXISTS: {
        "user_message": "File already exists",
        "suggestion": "A file with this name already exists. Choose a different name or delete the existing file.",
        "technical": "File creation failed - path already exists"
    },
    ErrorCode.FILE_PERMISSION_DENIED: {
        "user_message": "Permission denied",
        "suggestion": "You don't have permission to access this file.",
        "technical": "File operation rejected due to insufficient permissions"
    },
    ErrorCode.FILE_CORRUPTED: {
        "user_message": "File corrupted",
        "suggestion": "The file appears to be corrupted. Try uploading it again.",
        "technical": "File integrity check failed"
    },
    ErrorCode.FILE_SCAN_FAILED: {
        "user_message": "File scan failed",
        "suggestion": "Could not scan the file for security issues. Contact your administrator.",
        "technical": "Virus/malware scan failed or timed out"
    },

    # Database Errors
    ErrorCode.DB_CONNECTION_FAILED: {
        "user_message": "Database connection failed",
        "suggestion": "Could not connect to the database. Please try again later.",
        "technical": "Database connection pool exhausted or server unreachable"
    },
    ErrorCode.DB_QUERY_FAILED: {
        "user_message": "Database operation failed",
        "suggestion": "An error occurred while accessing the database. Please try again.",
        "technical": "SQL query execution failed"
    },
    ErrorCode.DB_CONSTRAINT_VIOLATION: {
        "user_message": "Data validation failed",
        "suggestion": "The data you entered violates database constraints. Check for duplicates or invalid references.",
        "technical": "Database constraint violation (unique, foreign key, etc.)"
    },
    ErrorCode.DB_RECORD_NOT_FOUND: {
        "user_message": "Record not found",
        "suggestion": "The requested record does not exist in the database.",
        "technical": "Query returned no rows"
    },
    ErrorCode.DB_DUPLICATE_ENTRY: {
        "user_message": "Duplicate entry",
        "suggestion": "A record with this identifier already exists.",
        "technical": "Unique constraint violation on insert"
    },
    ErrorCode.DB_TRANSACTION_FAILED: {
        "user_message": "Transaction failed",
        "suggestion": "The operation could not be completed. No changes were made.",
        "technical": "Database transaction rolled back"
    },
    ErrorCode.DB_MIGRATION_FAILED: {
        "user_message": "Database update failed",
        "suggestion": "Could not update the database schema. Contact your administrator.",
        "technical": "Database migration script failed"
    },

    # Configuration Errors
    ErrorCode.CONFIG_INVALID: {
        "user_message": "Invalid configuration",
        "suggestion": "Check your .env file or environment variables for errors.",
        "technical": "Configuration validation failed"
    },
    ErrorCode.CONFIG_MISSING_REQUIRED: {
        "user_message": "Missing required configuration",
        "suggestion": "Required setting '{setting}' is not configured. Add it to your .env file.",
        "technical": "Required configuration parameter not provided"
    },
    ErrorCode.CONFIG_VALIDATION_FAILED: {
        "user_message": "Configuration validation failed",
        "suggestion": "One or more configuration values are invalid: {errors}",
        "technical": "Pydantic validation failed for settings"
    },
    ErrorCode.CONFIG_FILE_NOT_FOUND: {
        "user_message": "Configuration file not found",
        "suggestion": "Create a .env file based on .env.example",
        "technical": "Expected configuration file does not exist"
    },
    ErrorCode.CONFIG_PARSE_ERROR: {
        "user_message": "Configuration parse error",
        "suggestion": "Check your .env file for syntax errors.",
        "technical": "Failed to parse configuration file"
    },

    # Network/P2P Errors
    ErrorCode.NETWORK_UNREACHABLE: {
        "user_message": "Network unreachable",
        "suggestion": "Check your internet connection and try again.",
        "technical": "Network socket operation failed"
    },
    ErrorCode.PEER_CONNECTION_FAILED: {
        "user_message": "Could not connect to peer",
        "suggestion": "The peer device is offline or unreachable. Make sure both devices are on the same network.",
        "technical": "P2P connection handshake failed"
    },
    ErrorCode.PEER_NOT_FOUND: {
        "user_message": "Peer not found",
        "suggestion": "The requested peer is not available. Refresh the peer list and try again.",
        "technical": "Peer ID not in discovery registry"
    },
    ErrorCode.PEER_HANDSHAKE_FAILED: {
        "user_message": "Peer handshake failed",
        "suggestion": "Could not establish secure connection with peer. Check that both devices are running compatible versions.",
        "technical": "P2P protocol handshake failed"
    },
    ErrorCode.PEER_TIMEOUT: {
        "user_message": "Peer connection timed out",
        "suggestion": "The peer took too long to respond. Check network connectivity.",
        "technical": "P2P connection timeout exceeded"
    },
    ErrorCode.PEER_AUTHENTICATION_FAILED: {
        "user_message": "Peer authentication failed",
        "suggestion": "Could not verify peer identity. Make sure the peer is authorized.",
        "technical": "Peer signature verification failed"
    },

    # Workflow/Agent Errors
    ErrorCode.WORKFLOW_NOT_FOUND: {
        "user_message": "Workflow not found",
        "suggestion": "The requested workflow does not exist or has been deleted.",
        "technical": "Workflow ID not found in database"
    },
    ErrorCode.WORKFLOW_VALIDATION_FAILED: {
        "user_message": "Workflow validation failed",
        "suggestion": "The workflow contains errors: {errors}. Fix them and try again.",
        "technical": "Workflow schema validation failed"
    },
    ErrorCode.WORKFLOW_EXECUTION_FAILED: {
        "user_message": "Workflow execution failed",
        "suggestion": "An error occurred during workflow execution: {error}",
        "technical": "Workflow execution raised an exception"
    },
    ErrorCode.WORKFLOW_TIMEOUT: {
        "user_message": "Workflow timed out",
        "suggestion": "The workflow took too long to complete. Optimize it or increase the timeout.",
        "technical": "Workflow execution exceeded timeout limit"
    },
    ErrorCode.AGENT_NOT_AVAILABLE: {
        "user_message": "Agent not available",
        "suggestion": "The requested agent '{agent}' is not available. Check agent configuration.",
        "technical": "Agent type not registered or disabled"
    },
    ErrorCode.AGENT_EXECUTION_FAILED: {
        "user_message": "Agent execution failed",
        "suggestion": "The agent encountered an error: {error}",
        "technical": "Agent execution raised an exception"
    },
    ErrorCode.TOOL_NOT_FOUND: {
        "user_message": "Tool not found",
        "suggestion": "The tool '{tool}' is not available. Check tool configuration.",
        "technical": "Tool name not in registry"
    },
    ErrorCode.TOOL_EXECUTION_FAILED: {
        "user_message": "Tool execution failed",
        "suggestion": "The tool '{tool}' failed to execute: {error}",
        "technical": "Tool raised an exception during execution"
    },

    # Vault/Security Errors
    ErrorCode.VAULT_LOCKED: {
        "user_message": "Vault is locked",
        "suggestion": "Unlock the vault with your password or biometric authentication.",
        "technical": "Vault access attempted while in locked state"
    },
    ErrorCode.VAULT_UNLOCK_FAILED: {
        "user_message": "Failed to unlock vault",
        "suggestion": "Incorrect password or authentication method. Try again.",
        "technical": "Vault unlock credentials invalid"
    },
    ErrorCode.VAULT_ENCRYPTION_FAILED: {
        "user_message": "Encryption failed",
        "suggestion": "Could not encrypt vault data. Contact support.",
        "technical": "Vault encryption operation failed"
    },
    ErrorCode.VAULT_DECRYPTION_FAILED: {
        "user_message": "Decryption failed",
        "suggestion": "Could not decrypt vault data. Vault may be corrupted.",
        "technical": "Vault decryption operation failed"
    },
    ErrorCode.VAULT_ITEM_NOT_FOUND: {
        "user_message": "Vault item not found",
        "suggestion": "The requested item does not exist in the vault.",
        "technical": "Vault item ID not found"
    },
    ErrorCode.BIOMETRIC_AUTH_FAILED: {
        "user_message": "Biometric authentication failed",
        "suggestion": "Touch ID / Face ID authentication failed. Use password instead.",
        "technical": "Biometric authentication rejected or unavailable"
    },
    ErrorCode.PANIC_MODE_ACTIVE: {
        "user_message": "System in panic mode",
        "suggestion": "The system is in panic mode. Contact your administrator to restore access.",
        "technical": "Panic mode triggered - sensitive data wiped"
    },

    # System Errors
    ErrorCode.SYSTEM_RESOURCE_EXHAUSTED: {
        "user_message": "System resources exhausted",
        "suggestion": "The system is overloaded. Try again later or contact your administrator.",
        "technical": "CPU, memory, or disk space exhausted"
    },
    ErrorCode.SYSTEM_INTERNAL_ERROR: {
        "user_message": "An unexpected error occurred",
        "suggestion": "Please try again. If the problem persists, contact support with error ID {error_id}.",
        "technical": "Unhandled exception in application code"
    },
    ErrorCode.SYSTEM_NOT_IMPLEMENTED: {
        "user_message": "Feature not implemented",
        "suggestion": "This feature is not yet available. Check for updates.",
        "technical": "NotImplementedError raised"
    },
    ErrorCode.SYSTEM_MAINTENANCE_MODE: {
        "user_message": "System under maintenance",
        "suggestion": "The system is temporarily unavailable for maintenance. Please try again later.",
        "technical": "Maintenance mode active - most operations disabled"
    },
    ErrorCode.SYSTEM_DEPENDENCY_FAILED: {
        "user_message": "System dependency failed",
        "suggestion": "A required system component is not available. Contact your administrator.",
        "technical": "External service or dependency failed (Ollama, database, etc.)"
    },
    ErrorCode.SYSTEM_INVALID_REQUEST: {
        "user_message": "Invalid request",
        "suggestion": "The request contains invalid data. Check the documentation and try again.",
        "technical": "Request validation failed"
    },
    ErrorCode.SYSTEM_VALIDATION_FAILED: {
        "user_message": "Validation failed",
        "suggestion": "The provided data is invalid: {errors}",
        "technical": "Pydantic validation failed on request model"
    },
}


def get_error_message(error_code: ErrorCode, **context) -> Dict[str, str]:
    """
    Get formatted error message for an error code with context substitution

    Args:
        error_code: The error code enum
        **context: Context variables for message formatting (e.g., max_size=10, model="llama2")

    Returns:
        Dict with user_message, suggestion, and technical fields
    """
    if error_code not in ERROR_MESSAGES:
        return {
            "user_message": "An error occurred",
            "suggestion": "Please try again or contact support.",
            "technical": f"Unknown error code: {error_code}"
        }

    error_info = ERROR_MESSAGES[error_code].copy()

    # Format messages with context variables
    if context:
        for key in ["user_message", "suggestion", "technical"]:
            try:
                error_info[key] = error_info[key].format(**context)
            except KeyError:
                # Context variable not in template - leave as is
                pass

    return error_info
