#!/usr/bin/env python3
"""
Context-aware engine wrappers that inject RAG context
Ensures Continue and Aider get the same context information
"""

import subprocess
from pathlib import Path
from typing import List, Optional
import logging

from patchbus import ChangeProposal

logger = logging.getLogger(__name__)


class ContextAwareContinueEngine:
    """Continue engine that properly uses context snippets"""
    
    def __init__(self, binary: str = None):
        from engines.continue_engine import ContinueEngine
        self.base_engine = ContinueEngine(binary)
        
    def propose(self, description: str, files: List[str], context_snippets: List[str]) -> ChangeProposal:
        if not self.base_engine.cn:
            return ChangeProposal(description=description, diff="", affected_files=[], confidence=0.0)
            
        # Build context-aware prompt
        prompt_parts = [
            "Propose a unified diff for the following change. Output ONLY the diff, no prose.",
            "Paths should be relative to repo root.",
            ""
        ]
        
        # Add context if available
        if context_snippets:
            prompt_parts.extend([
                "[CONTEXT]",
                "The following code snippets provide relevant context for this change:",
                ""
            ])
            for i, snippet in enumerate(context_snippets[:4]):  # Limit to 4 snippets
                prompt_parts.append(f"=== Context {i+1} ===")
                prompt_parts.append(snippet)
                prompt_parts.append("")
                
        # Add the change description
        prompt_parts.extend([
            "[CHANGE REQUEST]",
            description,
            ""
        ])
        
        # Add file list if provided
        if files:
            prompt_parts.extend([
                "[FILES TO MODIFY]",
                "\n".join(f"- {f}" for f in files),
                ""
            ])
            
        prompt = "\n".join(prompt_parts)
        
        try:
            # Use stdin to pass the full prompt to avoid shell escaping issues
            p = subprocess.run(
                [self.base_engine.cn, "-p", "-", *files], 
                input=prompt,
                capture_output=True, 
                text=True, 
                timeout=600
            )
            out = p.stdout
        except Exception as e:
            logger.error(f"Continue engine failed: {e}")
            out = str(e)
            
        diff = self.base_engine._extract_diff(out)
        return ChangeProposal(
            description=description, 
            diff=diff or "", 
            affected_files=files, 
            confidence=0.7 if context_snippets else 0.6
        )


class ContextAwareAiderEngine:
    """Aider engine that properly uses context snippets"""
    
    def __init__(self, model: str, venv_path: Path):
        from engines.aider_engine import AiderEngine
        self.base_engine = AiderEngine(model, venv_path)
        
    def propose(self, description: str, files: List[str], context_snippets: List[str]) -> ChangeProposal:
        # Build context-aware message
        message_parts = [
            "[Instructions]",
            "Propose a unified diff for the requested change.",
            "Output ONLY the diff. Do NOT explain. Do NOT apply changes.",
            "Use paths relative to repo root.",
            ""
        ]
        
        # Add context if available
        if context_snippets:
            message_parts.extend([
                "[CONTEXT]",
                "The following code snippets provide relevant context for this change:",
                ""
            ])
            for i, snippet in enumerate(context_snippets[:4]):  # Limit to 4 snippets
                message_parts.append(f"=== Context {i+1} ===")
                message_parts.append(snippet)
                message_parts.append("")
                
        # Add the change description
        message_parts.extend([
            "[CHANGE REQUEST]",
            description,
            ""
        ])
        
        full_msg = "\n".join(message_parts)
        escaped = full_msg.replace("'", "'\"'\"'")
        
        cmd = [
            "bash",
            "-c",
            f"source {self.base_engine.venv_path}/bin/activate && "
            f"export AIDER_NO_BROWSER=1 && export NO_COLOR=1 && "
            f"aider --yes --no-auto-commits --no-git --model ollama/{self.base_engine.model} "
            f"--message '{escaped}'"
            + (" " + " ".join(files) if files else "")
        ]
        
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            out = p.stdout + p.stderr
        except Exception as e:
            logger.error(f"Aider engine failed: {e}")
            out = str(e)
            
        diff = self.base_engine._extract_diff(out)
        return ChangeProposal(
            description=description, 
            diff=diff or "", 
            affected_files=files, 
            confidence=0.7 if context_snippets else 0.6
        )


def get_context_from_rag(description: str, files: List[str], 
                        current_file: Optional[str] = None) -> List[str]:
    """Get context snippets from RAG for a change request"""
    try:
        from rag_pipeline_enhanced import get_enhanced_pipeline
        
        pipeline = get_enhanced_pipeline()
        
        # Build query combining description and files
        query = description
        if files:
            query += "\nFiles: " + ", ".join(files)
            
        # Get context with biased retrieval
        chunks = pipeline.retrieve_context(
            query, 
            max_snippets=4,
            current_file=current_file or (files[0] if files else None)
        )
        
        # Format chunks as context snippets
        snippets = []
        for chunk in chunks:
            bias_info = f" [{', '.join(chunk['bias_reasons'])}]" if chunk.get('bias_reasons') else ""
            header = f"File: {chunk['path']} [{chunk['start_line']}-{chunk['end_line']}]{bias_info}"
            snippet = f"{header}\n{chunk['chunk']}"
            snippets.append(snippet)
            
        return snippets
        
    except Exception as e:
        logger.warning(f"Failed to get RAG context: {e}")
        return []