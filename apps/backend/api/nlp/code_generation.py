"""
Code generation templates (CODE_GENERATION category).
Moved from core_nlp_templates.py for modular architecture.
"""

from typing import List
from .types import NLPTemplate, IntentCategory


def get_templates() -> List[NLPTemplate]:
    """Return all CODE_GENERATION templates."""
    return [
        NLPTemplate(
            id="CG_001",
            name="Create Function",
            category=IntentCategory.CODE_GENERATION,
            patterns=[
                r"(create|write|implement|build)\s+(?:a\s+)?function\s+(?:to\s+|that\s+|for\s+)?(.+)",
                r"function\s+(?:to\s+|that\s+)(.+)",
                r"(?:can you\s+)?(?:please\s+)?write\s+(?:me\s+)?(?:a\s+)?function"
            ],
            keywords=["function", "create", "write", "implement"],
            entities=["function_name", "purpose", "parameters", "return_type"],
            response_template="Creating function",
            tool_suggestions=["aider", "ollama:qwen2.5-coder"],
            examples=[
                "create a function to sort a list",
                "write function that validates email",
                "implement a function for calculating fibonacci"
            ]
        ),

        NLPTemplate(
            id="CG_002",
            name="Create Class",
            category=IntentCategory.CODE_GENERATION,
            patterns=[
                r"(create|write|implement|build)\s+(?:a\s+)?class\s+(?:for\s+|that\s+)?(.+)",
                r"class\s+(?:to\s+|that\s+|for\s+)(.+)",
                r"(?:i need\s+)?(?:a\s+)?class\s+(?:that\s+)?(.+)"
            ],
            keywords=["class", "create", "object", "implement"],
            entities=["class_name", "purpose", "methods", "attributes"],
            response_template="Creating class for {purpose}",
            tool_suggestions=["aider", "ollama:qwen2.5-coder"],
            examples=[
                "create a class for user management",
                "write class that handles database connections",
                "I need a class to represent a car"
            ]
        ),

        NLPTemplate(
            id="CG_003",
            name="Create API Endpoint",
            category=IntentCategory.CODE_GENERATION,
            patterns=[
                r"(create|add|implement)\s+(?:an?\s+)?(?:api\s+)?endpoint\s+(?:for\s+|to\s+)?(.+)",
                r"(?:rest\s+)?api\s+(?:endpoint\s+)?(?:for\s+|to\s+)(.+)",
                r"add\s+(?:a\s+)?route\s+(?:for\s+|to\s+)?(.+)"
            ],
            keywords=["api", "endpoint", "route", "rest", "http"],
            entities=["endpoint_path", "method", "purpose", "parameters"],
            response_template="Creating API endpoint for {purpose}",
            tool_suggestions=["aider", "workflow:code_gen"],
            examples=[
                "create an API endpoint for user authentication",
                "add endpoint to get user profile",
                "implement REST API for products"
            ]
        ),

        NLPTemplate(
            id="CG_005",
            name="Create Script",
            category=IntentCategory.CODE_GENERATION,
            patterns=[
                r"(create|write|make)\s+(?:a\s+)?script\s+(?:to\s+|that\s+|for\s+)?(.+)",
                r"(?:python\s+)?script\s+(?:to\s+|for\s+)?(.+)",
                r"automation\s+(?:script\s+)?(?:for\s+)?(.+)"
            ],
            keywords=["script", "automation", "automate"],
            entities=["script_purpose", "script_type", "inputs", "outputs"],
            response_template="Creating script to {script_purpose}",
            tool_suggestions=["aider", "bash", "python"],
            examples=[
                "create a script to backup database",
                "write automation script for deployment",
                "make a script that processes CSV files"
            ]
        ),

        NLPTemplate(
            id="CG_006",
            name="Create Database Model",
            category=IntentCategory.CODE_GENERATION,
            patterns=[
                r"(create|write|implement)\s+(?:a\s+)?(?:database\s+)?model\s+(?:for\s+)?(.+)",
                r"(?:define|create)\s+(?:a\s+)?schema\s+(?:for\s+)?(.+)"
            ],
            keywords=["model", "database", "schema", "table"],
            entities=["model_name", "fields", "relationships"],
            response_template="Creating database model for {model_name}",
            tool_suggestions=["aider", "ollama:qwen2.5-coder"],
            examples=["create a model for users", "define schema for products"]
        ),

        NLPTemplate(
            id="CG_007",
            name="Create CLI Tool",
            category=IntentCategory.CODE_GENERATION,
            patterns=[
                r"(create|build|make)\s+(?:a\s+)?(?:cli|command.line)\s+(?:tool|app|application)\s+(?:for\s+)?(.+)",
                r"(?:cli|command)\s+(?:for\s+)?(.+)"
            ],
            keywords=["cli", "command", "tool", "terminal"],
            entities=["tool_name", "commands", "options"],
            response_template="Creating CLI tool for {tool_name}",
            tool_suggestions=["aider", "python"],
            examples=["create a CLI tool for file processing", "build command line app"]
        ),

        NLPTemplate(
            id="CG_008",
            name="Create Configuration",
            category=IntentCategory.CODE_GENERATION,
            patterns=[
                r"(create|generate|write)\s+(?:a\s+)?config(?:uration)?\s+(?:file\s+)?(?:for\s+)?(.+)",
                r"(?:setup|configure)\s+(.+)"
            ],
            keywords=["config", "configuration", "setup", "settings"],
            entities=["config_type", "settings"],
            response_template="Creating configuration for {config_type}",
            tool_suggestions=["aider", "write_file"],
            examples=["create config for docker", "generate configuration file"]
        ),

        NLPTemplate(
            id="CG_009",
            name="Create Interface",
            category=IntentCategory.CODE_GENERATION,
            patterns=[
                r"(create|define|write)\s+(?:an?\s+)?interface\s+(?:for\s+)?(.+)",
                r"interface\s+(.+)"
            ],
            keywords=["interface", "contract", "protocol"],
            entities=["interface_name", "methods"],
            response_template="Creating interface for {interface_name}",
            tool_suggestions=["aider", "ollama:qwen2.5-coder"],
            examples=["create an interface for payment processor", "define interface for storage"]
        ),

        NLPTemplate(
            id="CG_010",
            name="Create Middleware",
            category=IntentCategory.CODE_GENERATION,
            patterns=[
                r"(create|implement|add)\s+(?:a\s+)?middleware\s+(?:for\s+)?(.+)",
                r"middleware\s+(?:for\s+)?(.+)"
            ],
            keywords=["middleware", "interceptor", "handler"],
            entities=["middleware_type", "purpose"],
            response_template="Creating middleware for {middleware_type}",
            tool_suggestions=["aider", "workflow:code_gen"],
            examples=["create authentication middleware", "add middleware for logging"]
        ),
    ]
