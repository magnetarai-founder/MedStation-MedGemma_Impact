"""
Built-in JSON Schema presets for optional validation.
"""

BUILTIN_SCHEMAS = {
    # Minimal schema for the documented feed-like structure
    "feed": {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "messages": {"type": "array"},
            "header": {"type": "object"}
        },
        "required": ["messages"],
        "additionalProperties": True
    }
}

