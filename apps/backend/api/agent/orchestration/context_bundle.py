"""
Agent Orchestration - Context Bundle Construction

Context bundle building for code tasks:
- File tree slice generation
- Git history and diff statistics
- Chat snippet integration
- Security: repo_root validation against workspace/home dirs

Extracted from orchestrator.py during Phase 6.3d modularization.
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Any

try:
    from .models import ContextRequest, ContextResponse
except ImportError:
    from models import ContextRequest, ContextResponse

logger = logging.getLogger(__name__)


def build_context_bundle(
    body: ContextRequest,
    current_user: Dict,
    paths
) -> ContextResponse:
    """
    Get contextual information bundle for code tasks.

    Security: Validates repo_root is within user's code_workspaces or home directory.
    This matches the pattern used in code_operations.py for consistent security.

    Args:
        body: ContextRequest with repo_root, session_id, open_files
        current_user: User dict with user_id
        paths: Config paths object with data_dir

    Returns:
        ContextResponse with:
        - file_tree_slice: List of file paths (max 50)
        - recent_diffs: List of recent git commits with diffs
        - embeddings_hits: List of embedding matches (placeholder)
        - chat_snippets: Recent chat context
        - active_models: List of active models

    Raises:
        HTTPException if repo_root access denied or context building fails
    """
    file_tree_slice = []
    if body.repo_root:
        repo_path = Path(body.repo_root).resolve()

        # Security: Validate repo_root is within user's code_workspaces
        # This matches the pattern used in code_operations.py for consistent security
        user_id = current_user['user_id']
        user_workspace_root = paths.data_dir / "code_workspaces" / user_id

        # Allow user's home directory for convenience (can be disabled via env var)
        # Set ELOHIM_STRICT_WORKSPACE=1 to restrict to code_workspaces only
        allowed_roots = [user_workspace_root]
        if not os.getenv("ELOHIM_STRICT_WORKSPACE", "").lower() in ("1", "true", "yes"):
            user_home = Path.home()
            allowed_roots.append(user_home)

        is_allowed = False
        for allowed_root in allowed_roots:
            try:
                repo_path.relative_to(allowed_root)
                is_allowed = True
                break
            except ValueError:
                continue

        if not is_allowed:
            raise PermissionError(
                f"Access denied: repo_root must be within your workspace ({user_workspace_root}) or home directory"
            )

        if repo_path.exists():
            # Get top-level structure
            file_tree_slice = [
                str(p.relative_to(repo_path))
                for p in repo_path.rglob('*')
                if p.is_file() and not any(part.startswith('.') for part in p.parts)
            ][:50]  # Limit to 50 files

    # Get recent git diffs if repo has git
    recent_diffs = []
    if body.repo_root and Path(body.repo_root).exists():
        repo_path = Path(body.repo_root).resolve()
        git_dir = repo_path / ".git"

        if git_dir.exists():
            try:
                # Get recent commits (last 5)
                result = subprocess.run(
                    ["git", "-C", str(repo_path), "log", "--oneline", "-5"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    commits = result.stdout.strip().split('\n')
                    for commit in commits[:3]:  # Limit to 3 most recent
                        if commit:
                            commit_hash = commit.split()[0]
                            # Get diff for this commit
                            try:
                                diff_result = subprocess.run(
                                    ["git", "-C", str(repo_path), "show", "--stat", commit_hash],
                                    capture_output=True,
                                    text=True,
                                    timeout=5
                                )
                                if diff_result.returncode == 0:
                                    recent_diffs.append({
                                        "commit": commit,
                                        "diff_stat": diff_result.stdout[:500]  # Truncate
                                    })
                            except subprocess.TimeoutExpired:
                                # On timeout, skip this commit but continue with others
                                logger.warning(f"Git show timeout for {commit_hash}, skipping")
                                continue
            except subprocess.TimeoutExpired:
                # On timeout getting commits, return empty list but don't fail the whole request
                logger.warning(f"Git log timeout for {repo_path}, proceeding without git context")
            except Exception as e:
                logger.warning(f"Failed to get git diffs: {e}")

    # Get embeddings hits via semantic search against unified context
    embeddings_hits = []
    if body.open_files or body.repo_root:
        try:
            # Build search query from context
            search_terms = []

            # Add open file names as search context
            for filepath in body.open_files[:5]:  # Limit to 5 files
                filename = Path(filepath).name
                search_terms.append(filename)

            # Add repo name if available
            if body.repo_root:
                repo_name = Path(body.repo_root).name
                search_terms.append(repo_name)

            if search_terms:
                search_query = " ".join(search_terms)

                # Get recent context entries and rank by semantic similarity
                try:
                    from api.unified_context import get_unified_context
                except ImportError:
                    from unified_context import get_unified_context

                try:
                    from api.unified_embedder import get_unified_embedder
                except ImportError:
                    from unified_embedder import get_unified_embedder

                context_mgr = get_unified_context()
                embedder = get_unified_embedder()

                # Get recent context entries
                recent_entries = context_mgr.get_recent_context(
                    user_id=current_user['user_id'],
                    max_entries=50,
                    sources=['code', 'file', 'chat']
                )

                if recent_entries and embedder and embedder.is_available():
                    # Compute query embedding
                    query_embedding = embedder.embed(search_query)

                    # Score each entry by similarity
                    scored_entries = []
                    for entry in recent_entries:
                        if hasattr(entry, 'content') and entry.content and len(entry.content) > 20:
                            entry_embedding = embedder.embed(entry.content[:500])

                            # Cosine similarity
                            dot_product = sum(a * b for a, b in zip(query_embedding, entry_embedding))
                            norm_q = sum(x * x for x in query_embedding) ** 0.5
                            norm_e = sum(x * x for x in entry_embedding) ** 0.5

                            if norm_q > 0 and norm_e > 0:
                                similarity = dot_product / (norm_q * norm_e)
                                if similarity > 0.3:  # Threshold
                                    scored_entries.append((similarity, entry))

                    # Sort by similarity and take top 5
                    scored_entries.sort(key=lambda x: x[0], reverse=True)
                    for _, entry in scored_entries[:5]:
                        summary = entry.content[:150].replace('\n', ' ').strip()
                        if len(entry.content) > 150:
                            summary += "..."
                        embeddings_hits.append(summary)

        except Exception as e:
            # Non-fatal: log but continue without embeddings
            logger.debug(f"Embeddings search unavailable: {e}")

    # Get recent chat snippets from unified context
    chat_snippets = []
    if body.session_id:
        try:
            # Import from parent api directory (two levels up from orchestration/)
            try:
                from api.unified_context import get_unified_context
            except ImportError:
                from unified_context import get_unified_context

            context_mgr = get_unified_context()
            recent_entries = context_mgr.get_recent_context(
                user_id=current_user['user_id'],
                max_entries=10,
                sources=['chat']
            )
            chat_snippets = [
                f"{entry.content[:100]}..." for entry in recent_entries
            ]
        except Exception as e:
            logger.warning(f"Failed to get chat snippets: {e}")

    # Get active models
    active_models = ['qwen2.5-coder:32b', 'deepseek-r1:32b', 'codestral:22b']

    return ContextResponse(
        file_tree_slice=file_tree_slice,
        recent_diffs=recent_diffs,
        embeddings_hits=embeddings_hits,
        chat_snippets=chat_snippets,
        active_models=active_models
    )
