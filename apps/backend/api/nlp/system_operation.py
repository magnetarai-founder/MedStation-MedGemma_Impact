"""
System operation templates (SYSTEM_OPERATION category).
Moved from core_nlp_templates.py for modular architecture.
"""

from typing import List
from .types import NLPTemplate, IntentCategory


def get_templates() -> List[NLPTemplate]:
    """Return all SYSTEM_OPERATION templates."""
    return [
        NLPTemplate(
            id="SO_001",
            name="Run Command",
            category=IntentCategory.SYSTEM_OPERATION,
            patterns=[
                r"run\s+(.+)",
                r"execute\s+(.+)",
                r"(?:can you\s+)?(?:please\s+)?run\s+(?:the\s+)?command:?\s*(.+)"
            ],
            keywords=["run", "execute", "command"],
            entities=["command", "arguments", "working_directory"],
            response_template="Running: {command}",
            tool_suggestions=["bash", "system"],
            examples=[
                "run npm install",
                "execute the build script",
                "run python main.py"
            ]
        ),

        NLPTemplate(
            id="SO_002",
            name="Git Operations",
            category=IntentCategory.SYSTEM_OPERATION,
            patterns=[
                r"(?:git\s+)?commit\s+(.+)",
                r"(?:git\s+)?(?:push|pull|merge|branch)",
                r"(?:create|make)\s+(?:a\s+)?(?:git\s+)?commit"
            ],
            keywords=["git", "commit", "push", "pull", "branch"],
            entities=["git_command", "message", "branch"],
            response_template="Executing git {git_command}",
            tool_suggestions=["git", "workflow:git_ops"],
            examples=[
                "commit the changes",
                "git push to main",
                "create a new branch"
            ]
        ),

        NLPTemplate(
            id="SO_003",
            name="File Operations",
            category=IntentCategory.SYSTEM_OPERATION,
            patterns=[
                r"(?:create|make|touch)\s+(?:a\s+)?(?:new\s+)?file\s+(.+)",
                r"(?:delete|remove|rm)\s+(?:the\s+)?file\s+(.+)",
                r"(?:move|rename|mv)\s+(.+)\s+to\s+(.+)"
            ],
            keywords=["file", "create", "delete", "move", "rename"],
            entities=["file_path", "operation", "destination"],
            response_template="Performing file operation: {operation}",
            tool_suggestions=["bash", "file_system"],
            examples=[
                "create a new file config.json",
                "delete the temp file",
                "rename old.txt to new.txt"
            ]
        ),

        NLPTemplate(
            id="SO_004",
            name="Install Package",
            category=IntentCategory.SYSTEM_OPERATION,
            patterns=[
                r"install\s+(.+)",
                r"(?:pip|npm|cargo|gem)\s+install\s+(.+)",
                r"add\s+(?:package|dependency)\s+(.+)"
            ],
            keywords=["install", "package", "dependency"],
            entities=["package_name", "package_manager"],
            response_template="Installing {package_name}",
            tool_suggestions=["pip", "npm", "bash"],
            examples=["install numpy", "pip install requests", "add package flask"]
        ),

        NLPTemplate(
            id="SO_005",
            name="Environment Setup",
            category=IntentCategory.SYSTEM_OPERATION,
            patterns=[
                r"(?:setup|create|init)\s+(?:virtual\s+)?env(?:ironment)?",
                r"(?:activate|deactivate)\s+(?:virtual\s+)?env(?:ironment)?"
            ],
            keywords=["environment", "venv", "virtualenv", "setup"],
            entities=["env_name", "python_version"],
            response_template="Setting up environment",
            tool_suggestions=["venv", "virtualenv", "conda"],
            examples=["setup virtual environment", "create venv", "activate environment"]
        ),

        NLPTemplate(
            id="SO_006",
            name="Process Management",
            category=IntentCategory.SYSTEM_OPERATION,
            patterns=[
                r"(?:kill|stop|terminate)\s+(?:process|pid)\s+(.+)",
                r"(?:list|show)\s+(?:running\s+)?processes",
                r"(?:restart|start)\s+(?:service\s+)?(.+)"
            ],
            keywords=["process", "kill", "stop", "restart", "service"],
            entities=["process_name", "pid"],
            response_template="Managing process {process_name}",
            tool_suggestions=["ps", "kill", "systemctl"],
            examples=["kill process 1234", "restart nginx", "list processes"]
        ),

        NLPTemplate(
            id="SYS_CMD_001",
            name="Direct System Command",
            category=IntentCategory.SYSTEM_OPERATION,
            patterns=[
                r"^(echo|cat|ls|pwd|cd|mkdir|rm|cp|mv|touch|grep|find|ps|kill|df|du|chmod|chown)\b"
            ],
            keywords=["echo", "cat", "ls", "pwd", "system", "command"],
            entities=["command", "arguments"],
            response_template="Executing system command",
            tool_suggestions=["system", "bash"],
            examples=["echo hello", "ls -la", "pwd", "cat file.txt"]
        ),

        NLPTemplate(
            id="SYS_CMD_002",
            name="Command with Redirection",
            category=IntentCategory.SYSTEM_OPERATION,
            patterns=[
                r".*(>|\|).*"
            ],
            keywords=["pipe", "redirect", "output"],
            entities=["command", "target"],
            response_template="Executing command with redirection",
            tool_suggestions=["system", "bash"],
            examples=["echo test > file.txt", "ls | grep py", "cat file | head"]
        ),
    ]
