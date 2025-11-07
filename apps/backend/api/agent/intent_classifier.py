#!/usr/bin/env python3
"""
Lightweight intent classifier.
Classifies free-text input into one of: 'shell', 'code_edit', 'question'.
Uses Ollama (phi3:mini-instruct) if available; otherwise falls back to
fast heuristics. Returns a plain dict suitable for API responses.
"""

import json
import re
import shutil
import subprocess
from typing import Dict, Optional


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


def _heuristic(command: str) -> Dict[str, object]:
    txt = command.strip()
    c = txt.lower()

    # Shell-like indicators
    shell_markers = [c.startswith(p) for p in ("$", "./", "../")]
    shell_markers += ["|" in c, "&&" in c or "||" in c, c.endswith(";")]
    common_shell_cmds = ["ls ", "cd ", "cat ", "grep ", "find ", "git ", "rm ", "mkdir ", "chmod ", "chown "]
    if any(shell_markers) or any(cmd in c for cmd in common_shell_cmds):
        return {"type": "shell", "confidence": 0.7}

    # Code-edit verbs
    edit_kws = ["fix", "bug", "error", "traceback", "refactor", "rewrite", "modify", "change", "update", "implement", "add", "remove", "rename"]
    if any(kw in c for kw in edit_kws):
        return {"type": "code_edit", "confidence": 0.6}

    # Default to question/explanation
    return {"type": "question", "confidence": 0.5}


class Phi3IntentClassifier:
    def __init__(self, model: str = "phi3:mini-instruct") -> None:
        # Accept either bare name or with provider prefix
        self.model = model.split("/")[-1]

    def classify(self, command: str) -> Dict[str, object]:
        if not command.strip():
            return {"type": "question", "confidence": 0.0}

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
                    task = str(data.get("task_type", "explanation")).lower()
                    mapping = {
                        "system_command": "shell",
                        "git_operation": "shell",
                        "code_edit": "code_edit",
                        "code_write": "code_edit",
                        "bug_fix": "code_edit",
                        "documentation": "question",
                        "test_generation": "code_edit",
                        "research": "question",
                        "explanation": "question",
                    }
                    intent_type = mapping.get(task, "question")
                    conf = float(data.get("confidence", 0.6))
                    return {"type": intent_type, "confidence": conf}
                except Exception:
                    pass

        # Fallback
        return _heuristic(command)

# Backward-compatible alias
IntentClassifier = Phi3IntentClassifier


if __name__ == "__main__":
    import sys
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "create tests for utils.py"
    clf = Phi3IntentClassifier()
    intent = clf.classify(text)
    print(json.dumps(intent, indent=2))
