#!/usr/bin/env python3
"""
Aider Library Integration for ElohimOS
Uses Aider as a Python library instead of subprocess for tighter integration
"""

import logging
import sys
import os
from pathlib import Path
from typing import List, Dict, Optional, Any
import io
from contextlib import redirect_stdout, redirect_stderr

# Add external Aider to Python path
AIDER_PATH = Path(__file__).parent.parent / "external" / "aider"
if AIDER_PATH.exists():
    sys.path.insert(0, str(AIDER_PATH.parent))

logger = logging.getLogger(__name__)


class AiderLibrary:
    """
    Aider integration using library mode

    Provides direct Python API access to Aider's capabilities:
    - Multi-file editing
    - Diff generation
    - Code refactoring
    - Context-aware changes
    """

    def __init__(
        self,
        repo_root: str,
        model: str = "ollama/qwen2.5-coder:32b",
        files: Optional[List[str]] = None
    ):
        self.repo_root = Path(repo_root)
        self.model = model
        self.files = files or []

        # Import Aider components
        try:
            from aider.coders import Coder
            from aider.models import Model
            from aider.io import InputOutput
            from aider.repo import GitRepo

            self.Coder = Coder
            self.Model = Model
            self.InputOutput = InputOutput
            self.GitRepo = GitRepo

        except ImportError as e:
            logger.error(f"Failed to import Aider: {e}")
            logger.error(f"Make sure Aider is in: {AIDER_PATH}")
            raise

    def generate_edit(
        self,
        prompt: str,
        files: Optional[List[str]] = None,
        read_only_files: Optional[List[str]] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Generate code edit using Aider

        Args:
            prompt: Natural language description of changes
            files: Files to edit
            read_only_files: Files for context only
            dry_run: If True, don't actually write changes

        Returns:
            {
                'success': bool,
                'diffs': [{'file': str, 'diff': str, 'summary': str}],
                'message': str,
                'tokens_used': int
            }
        """
        files = files or self.files
        read_only_files = read_only_files or []

        try:
            # Create IO handler (capture stdout/stderr)
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()

            # Setup Aider coder
            io_handler = self.InputOutput(
                yes=True,  # Auto-confirm changes
                chat_history_file=None,  # Don't save history
                input_history_file=None,
                dry_run=dry_run
            )

            # Create model
            model = self.Model(self.model)

            # Initialize git repo
            repo = self.GitRepo(self.InputOutput(yes=True), str(self.repo_root))

            # Create coder
            coder = self.Coder.create(
                main_model=model,
                fnames=[str(self.repo_root / f) for f in files],
                read_only_fnames=[str(self.repo_root / f) for f in read_only_files],
                io=io_handler,
                repo=repo,
                auto_commits=False,  # We'll handle commits via PatchBus
                dirty_commits=True,
                dry_run=dry_run
            )

            # Run the edit with captured output
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                result = coder.run(prompt)

            # Get captured output
            stdout_text = stdout_capture.getvalue()
            stderr_text = stderr_capture.getvalue()

            # Parse diffs from result
            diffs = self._parse_diffs(coder, files)

            return {
                'success': True,
                'diffs': diffs,
                'message': f"Generated {len(diffs)} change(s)",
                'tokens_used': getattr(coder, 'total_cost', 0),
                'stdout': stdout_text,
                'stderr': stderr_text
            }

        except Exception as e:
            logger.error(f"Aider edit failed: {e}")
            return {
                'success': False,
                'diffs': [],
                'message': str(e),
                'tokens_used': 0
            }

    def _parse_diffs(self, coder, files: List[str]) -> List[Dict[str, str]]:
        """Parse diffs from Aider coder instance"""
        diffs = []

        # Get diffs for each file
        for file in files:
            file_path = self.repo_root / file

            if not file_path.exists():
                continue

            try:
                # Get git diff for this file
                import subprocess
                result = subprocess.run(
                    ['git', 'diff', '--', str(file_path)],
                    capture_output=True,
                    text=True,
                    cwd=str(self.repo_root)
                )

                if result.returncode == 0 and result.stdout.strip():
                    diffs.append({
                        'file': file,
                        'diff': result.stdout,
                        'summary': f"Modified {file}"
                    })

            except Exception as e:
                logger.warning(f"Failed to get diff for {file}: {e}")

        return diffs

    def ask_question(self, question: str, files: Optional[List[str]] = None) -> str:
        """
        Ask Aider a question about the codebase

        Args:
            question: Question to ask
            files: Files for context

        Returns:
            Answer as string
        """
        files = files or self.files

        try:
            # Create IO handler
            io_handler = self.InputOutput(
                yes=True,
                chat_history_file=None,
                input_history_file=None
            )

            # Create model
            model = self.Model(self.model)

            # Initialize git repo
            repo = self.GitRepo(self.InputOutput(yes=True), str(self.repo_root))

            # Create coder
            coder = self.Coder.create(
                main_model=model,
                fnames=[str(self.repo_root / f) for f in files],
                io=io_handler,
                repo=repo,
                auto_commits=False,
                dirty_commits=True
            )

            # Capture output
            stdout_capture = io.StringIO()
            with redirect_stdout(stdout_capture):
                coder.run(question)

            answer = stdout_capture.getvalue()
            return answer.strip()

        except Exception as e:
            logger.error(f"Aider question failed: {e}")
            return f"Error: {e}"


def test_aider_integration() -> bool:
    """Test Aider library integration"""
    try:
        aider = AiderLibrary(
            repo_root="/tmp/test_repo",
            model="ollama/qwen2.5-coder:7b"
        )

        # Test import
        print("✓ Aider library imported successfully")
        print(f"✓ Coder class: {aider.Coder}")
        print(f"✓ Model class: {aider.Model}")

        return True

    except Exception as e:
        print(f"✗ Aider integration test failed: {e}")
        return False


if __name__ == '__main__':
    test_aider_integration()
