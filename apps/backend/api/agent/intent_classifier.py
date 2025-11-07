#!/usr/bin/env python3
"""
Phi-3 based intent classifier (stub).
Uses Ollama (phi3:mini-instruct) to classify a free-text command into a
structured intent Jarvis can use. Falls back to a heuristic classifier when
Ollama or the model are unavailable.
"""

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional

try:
    from agent_simple import TaskType  # type: ignore
except Exception:
    # Local fallback to avoid tight coupling during early wiring
    from models import TaskType  # reuse enum stub


@dataclass
class Intent:
    task_type: TaskType
    files: List[str]
    heavy: bool
    confidence: float


PROMPT = (
    "You are an intent classifier. Read the user's command and return ONLY a JSON object with keys: "
    "task_type (one of: code_write, code_edit, bug_fix, code_review, test_generation, documentation, research, explanation, system_command, git_operation), "
    "files (array of filenames if referenced), heavy (true/false if the task seems complex or large), confidence (0..1).\n\n"
    "Command: {command}\n\nJSON:"
)


def _ollama_available() -> bool:
    return shutil.which("ollama") is not None


def _run_ollama(model: str, prompt: str, timeout: int = 20) -> Optional[str]:
    try:
        p = subprocess.run(["ollama", "run", model, prompt], capture_output=True, text=True, timeout=timeout)
        if p.returncode == 0 and p.stdout:
            return p.stdout.strip()
    except Exception:
        pass
    return None


def _heuristic(command: str) -> Intent:
    c = command.lower()
    files = re.findall(r"\b[\w/\\.-]+\.(py|js|ts|java|c|cpp|go|rs)\b", command)
    def any_kw(words):
        return any(w in c for w in words)

    if any_kw(["fix", "bug", "error", "traceback", "stack trace"]):
        return Intent(TaskType.BUG_FIX, files, heavy=len(files) > 2, confidence=0.55)
    if any_kw(["refactor", "rewrite", "modify", "change", "update"]):
        return Intent(TaskType.CODE_EDIT, files, heavy=len(files) > 3, confidence=0.5)
    if any_kw(["create", "implement", "build", "write"]) and files:
        return Intent(TaskType.CODE_WRITE, files, heavy=len(files) > 2, confidence=0.55)
    if any_kw(["test", "unit test", "pytest"]):
        return Intent(TaskType.TEST_GENERATION, files, heavy=False, confidence=0.5)
    if any_kw(["document", "readme", "docs"]):
        return Intent(TaskType.DOCUMENTATION, files, heavy=False, confidence=0.5)
    if any_kw(["git ", "commit", "push", "pull", "status", "branch"]):
        return Intent(TaskType.GIT_OPERATION, files, heavy=False, confidence=0.5)
    if any_kw(["ls", "pwd", "mkdir", "rm ", "chmod", "chown"]):
        return Intent(TaskType.SYSTEM_COMMAND, files, heavy=False, confidence=0.5)
    if any_kw(["what", "why", "how", "explain", "describe"]):
        return Intent(TaskType.EXPLANATION, files, heavy=False, confidence=0.45)
    if any_kw(["research", "investigate", "look up", "find information"]):
        return Intent(TaskType.RESEARCH, files, heavy=False, confidence=0.45)
    return Intent(TaskType.EXPLANATION, files, heavy=False, confidence=0.4)


class Phi3IntentClassifier:
    def __init__(self, model: str = "phi3:mini-instruct") -> None:
        # Accept either bare name or with provider prefix
        self.model = model.split("/")[-1]

    def classify(self, command: str) -> Intent:
        if not command.strip():
            return Intent(TaskType.EXPLANATION, [], False, 0.0)

        if _ollama_available():
            prompt = PROMPT.format(command=command.strip())
            out = _run_ollama(self.model, prompt)
            if out:
                # Try to extract JSON (be forgiving)
                json_text = out
                start = json_text.find("{")
                end = json_text.rfind("}")
                if start != -1 and end != -1 and end > start:
                    json_text = json_text[start : end + 1]
                try:
                    data = json.loads(json_text)
                    task = TaskType(data.get("task_type", "explanation"))
                    files = data.get("files", []) or []
                    heavy = bool(data.get("heavy", False))
                    conf = float(data.get("confidence", 0.5))
                    return Intent(task, files, heavy, conf)
                except Exception:
                    pass

        # Fallback
        return _heuristic(command)


if __name__ == "__main__":
    import sys
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "create tests for utils.py"
    clf = Phi3IntentClassifier()
    intent = clf.classify(text)
    print(json.dumps({
        "task_type": intent.task_type.value,
        "files": intent.files,
        "heavy": intent.heavy,
        "confidence": intent.confidence,
    }, indent=2))

