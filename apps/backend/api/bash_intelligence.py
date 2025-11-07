#!/usr/bin/env python3
"""
Bash Intelligence for ElohimOS Terminal
Powered by Codex patterns + local models

Features:
- Natural language → bash command translation
- Context-aware command suggestions
- Safe command validation
- Shell history integration
"""

import logging
import re
import subprocess
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class BashIntelligence:
    """
    Intelligent bash command generation and validation

    Uses patterns from Codex + local LLM for:
    - NL to bash translation
    - Command safety checking
    - Context-aware suggestions
    """

    # Dangerous commands that require confirmation
    DANGEROUS_PATTERNS = [
        r'\brm\s+-rf\s+/',
        r'\bdd\s+if=',
        r'\b(sudo\s+)?mkfs',
        r'\b:>',  # Truncate file
        r'\bchmod\s+-R\s+777',
        r'\bshred',
        r'\bwipefs',
        r'\bformat\b',
    ]

    # Common NL patterns → bash templates
    NL_TEMPLATES = {
        # File operations
        r'(list|show|display)\s+(all\s+)?files': 'ls -lah',
        r'find\s+(.+?)\s+files?': r'find . -name "\1"',
        r'search\s+for\s+"?(.+?)"?\s+in\s+files?': r'grep -r "\1" .',
        r'count\s+lines\s+in\s+(.+)': r'wc -l "\1"',
        r'show\s+disk\s+usage': 'df -h',
        r'show\s+directory\s+size': 'du -sh',

        # Git operations
        r'commit\s+(.+)': r'git add -A && git commit -m "\1"',
        r'push\s+to\s+(.+)': r'git push \1',
        r'create\s+branch\s+(.+)': r'git checkout -b "\1"',
        r'git\s+status': 'git status',
        r'show\s+git\s+log': 'git log --oneline -10',
        r'undo\s+last\s+commit': 'git reset --soft HEAD~1',

        # Process management
        r'kill\s+process\s+(.+)': r'pkill -f "\1"',
        r'show\s+running\s+processes': 'ps aux',
        r'find\s+process\s+(.+)': r'ps aux | grep "\1"',

        # Network
        r'check\s+port\s+(\d+)': r'lsof -i :\1',
        r'test\s+connection\s+to\s+(.+)': r'ping -c 4 \1',
        r'download\s+(.+)': r'curl -O "\1"',

        # System
        r'show\s+environment': 'env',
        r'which\s+(.+)': r'which "\1"',
        r'create\s+directory\s+(.+)': r'mkdir -p "\1"',
        r'go\s+to\s+(.+)': r'cd "\1"',
    }

    def __init__(self, model_manager=None):
        """
        Initialize bash intelligence

        Args:
            model_manager: AdaptiveRouter for LLM-based translation
        """
        self.model_manager = model_manager

    def classify_input(self, input_text: str) -> Dict[str, any]:
        """
        Classify if input is:
        - Natural language (needs translation)
        - Already a bash command
        - Ambiguous

        Returns:
            {
                'type': 'nl' | 'bash' | 'ambiguous',
                'confidence': float,
                'suggestion': Optional[str]
            }
        """
        # Clean input
        text = input_text.strip()

        # Empty check
        if not text:
            return {'type': 'bash', 'confidence': 1.0, 'suggestion': None}

        # Check for bash indicators
        bash_indicators = [
            text.startswith('$'),
            text.startswith('./'),
            text.startswith('../'),
            re.match(r'^[a-z_][\w-]*\s+', text),  # command pattern
            '|' in text,  # pipe
            '&&' in text or '||' in text,  # logical operators
            text.endswith(';'),
        ]

        # Check for NL indicators
        nl_indicators = [
            text.endswith('?'),
            any(word in text.lower() for word in ['please', 'can you', 'could you', 'how do i', 'show me']),
            len(text.split()) > 6 and not any(bash_indicators),  # Long phrases
        ]

        bash_score = sum(bash_indicators) / len(bash_indicators)
        nl_score = sum(nl_indicators) / len(nl_indicators)

        if bash_score > 0.5:
            return {'type': 'bash', 'confidence': bash_score, 'suggestion': None}
        elif nl_score > 0.3:
            suggestion = self.translate_to_bash(text)
            return {'type': 'nl', 'confidence': nl_score, 'suggestion': suggestion}
        else:
            # Ambiguous - try template match first
            suggestion = self._try_template_match(text)
            if suggestion:
                return {'type': 'nl', 'confidence': 0.6, 'suggestion': suggestion}
            else:
                return {'type': 'ambiguous', 'confidence': 0.5, 'suggestion': None}

    def translate_to_bash(self, nl_text: str) -> str:
        """
        Translate natural language to bash command

        Uses:
        1. Template matching (fast)
        2. LLM translation (fallback)

        Args:
            nl_text: Natural language description

        Returns:
            Bash command string
        """
        # Try template match first
        template_cmd = self._try_template_match(nl_text)
        if template_cmd:
            return template_cmd

        # Fall back to LLM
        if self.model_manager:
            return self._llm_translate(nl_text)
        else:
            # No LLM available, return error
            return f"# Could not translate: {nl_text}"

    def _try_template_match(self, text: str) -> Optional[str]:
        """Try to match against template patterns"""
        text_lower = text.lower().strip()

        for pattern, template in self.NL_TEMPLATES.items():
            match = re.search(pattern, text_lower)
            if match:
                # Replace capture groups
                if '\\1' in template:
                    cmd = re.sub(pattern, template, text_lower)
                else:
                    cmd = template

                logger.debug(f"Template matched: '{text}' -> '{cmd}'")
                return cmd

        return None

    def _llm_translate(self, nl_text: str) -> str:
        """Use LLM to translate NL to bash"""
        try:
            # Use lightweight model for quick translation
            model = "llama3.1:8b-instruct"

            prompt = f"""Convert this natural language request to a bash command:

Request: {nl_text}

Return ONLY the bash command, no explanation. If multiple commands are needed, separate with &&.

Bash command:"""

            # Call model manager
            if hasattr(self.model_manager, 'route_task'):
                result = self.model_manager.route_task(prompt, task_type='bash_translation')
                cmd = result.get('response', '').strip()
            else:
                # Direct ollama call
                import httpx
                response = httpx.post(
                    'http://localhost:11434/api/generate',
                    json={'model': model, 'prompt': prompt, 'stream': False},
                    timeout=30.0
                )
                cmd = response.json().get('response', '').strip()

            # Clean up response
            cmd = cmd.replace('```bash', '').replace('```', '').strip()
            cmd = cmd.split('\n')[0]  # Take first line only

            logger.debug(f"LLM translated: '{nl_text}' -> '{cmd}'")
            return cmd

        except Exception as e:
            logger.error(f"LLM translation failed: {e}")
            return f"# Translation failed: {nl_text}"

    def check_safety(self, command: str) -> Tuple[bool, str]:
        """
        Check if command is safe to execute

        Returns:
            (is_safe: bool, warning_message: str)
        """
        # Check against dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"⚠️  Dangerous command detected: matches pattern '{pattern}'"

        # Check for sudo without confirmation
        if command.strip().startswith('sudo') and 'rm' in command:
            return False, "⚠️  sudo + rm detected - requires confirmation"

        # Check for operations on root
        if re.search(r'[/\s](/+|~)\s*$', command):
            return False, "⚠️  Operation on root directory detected"

        return True, ""

    def suggest_improvements(self, command: str) -> List[str]:
        """
        Suggest improvements to a bash command

        Returns:
            List of suggestions
        """
        suggestions = []

        # Check for common improvements
        if re.search(r'\bfind\b.*\|\s*grep', command):
            suggestions.append("💡 Consider using 'find -name' instead of piping to grep")

        if 'cat' in command and '|' in command and 'grep' in command:
            suggestions.append("💡 Consider using 'grep' directly instead of 'cat | grep'")

        if re.search(r'\bls\s+\|', command):
            suggestions.append("💡 Consider using ls options instead of piping")

        if 'rm' in command and '-r' in command:
            suggestions.append("⚠️  Use 'rm -r' carefully - specify explicit paths to avoid accidents")

        return suggestions


# Global instance
_bash_intelligence = None

def get_bash_intelligence(model_manager=None) -> BashIntelligence:
    """Get global bash intelligence instance"""
    global _bash_intelligence
    if _bash_intelligence is None:
        _bash_intelligence = BashIntelligence(model_manager)
    return _bash_intelligence
