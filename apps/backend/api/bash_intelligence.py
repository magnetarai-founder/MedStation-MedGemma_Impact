#!/usr/bin/env python3
"""
Bash Intelligence for ElohimOS Terminal
Powered by Codex patterns + local models

Extracted modules (P2 decomposition):
- bash_patterns.py: Pattern constants, templates, and helper functions

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

try:
    from .config import get_settings
except ImportError:
    from config import get_settings

# Import from extracted module (P2 decomposition)
from api.bash_patterns import (
    DANGEROUS_PATTERNS,
    NL_TEMPLATES,
    NL_INDICATOR_WORDS,
    is_dangerous_command,
    match_nl_template,
    has_nl_indicators,
    get_command_improvements,
    check_root_operation,
    check_sudo_rm,
)

logger = logging.getLogger(__name__)


class BashIntelligence:
    """
    Intelligent bash command generation and validation

    Uses patterns from Codex + local LLM for:
    - NL to bash translation
    - Command safety checking
    - Context-aware suggestions

    Static patterns and templates are defined in bash_patterns.py (P2 decomposition).
    """

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

        # Check for NL indicators (using imported helper)
        nl_indicators = [
            text.endswith('?'),
            has_nl_indicators(text),
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
        """Try to match against template patterns (uses imported match_nl_template)"""
        cmd = match_nl_template(text)
        if cmd:
            logger.debug(f"Template matched: '{text}' -> '{cmd}'")
        return cmd

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
                settings = get_settings()
                response = httpx.post(
                    f'{settings.ollama_base_url}/api/generate',
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
        Check if command is safe to execute (uses imported safety helpers)

        Returns:
            (is_safe: bool, warning_message: str)
        """
        # Check against dangerous patterns (using imported helper)
        is_dangerous, matched_pattern = is_dangerous_command(command)
        if is_dangerous:
            return False, f"⚠️  Dangerous command detected: matches pattern '{matched_pattern}'"

        # Check for sudo without confirmation (using imported helper)
        if check_sudo_rm(command):
            return False, "⚠️  sudo + rm detected - requires confirmation"

        # Check for operations on root (using imported helper)
        if check_root_operation(command):
            return False, "⚠️  Operation on root directory detected"

        return True, ""

    def suggest_improvements(self, command: str) -> List[str]:
        """
        Suggest improvements to a bash command (uses imported get_command_improvements)

        Returns:
            List of suggestions
        """
        return get_command_improvements(command)


# Global instance
_bash_intelligence = None

def get_bash_intelligence(model_manager=None) -> BashIntelligence:
    """Get global bash intelligence instance"""
    global _bash_intelligence
    if _bash_intelligence is None:
        _bash_intelligence = BashIntelligence(model_manager)
    return _bash_intelligence
