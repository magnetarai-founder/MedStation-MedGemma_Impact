"""
Shared models and enums for agent system
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Optional


class TaskType(str, Enum):
    """Task type classification for intent classifier"""
    CODE_WRITE = "code_write"
    CODE_EDIT = "code_edit"
    BUG_FIX = "bug_fix"
    CODE_REVIEW = "code_review"
    TEST_GENERATION = "test_generation"
    DOCUMENTATION = "documentation"
    RESEARCH = "research"
    EXPLANATION = "explanation"
    SYSTEM_COMMAND = "system_command"
    GIT_OPERATION = "git_operation"


class ModelSelector:
    """Model selection helper (stub for future implementation)"""

    @staticmethod
    def select_for_task(task_type: TaskType) -> str:
        """Select appropriate model for task type"""
        model_map = {
            TaskType.CODE_WRITE: "qwen2.5-coder:32b",
            TaskType.CODE_EDIT: "qwen2.5-coder:32b",
            TaskType.BUG_FIX: "qwen2.5-coder:32b",
            TaskType.CODE_REVIEW: "codestral:22b",
            TaskType.TEST_GENERATION: "qwen2.5-coder:14b",
            TaskType.DOCUMENTATION: "llama3.1:8b",
            TaskType.RESEARCH: "deepseek-r1:32b",
            TaskType.EXPLANATION: "deepseek-r1:32b",
            TaskType.SYSTEM_COMMAND: "llama3.1:8b",
            TaskType.GIT_OPERATION: "llama3.1:8b",
        }
        return model_map.get(task_type, "qwen2.5-coder:32b")
