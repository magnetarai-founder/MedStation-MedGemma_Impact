"""
Code Editor Diff Service
Generate unified diffs with truncation support
"""

import logging
import difflib
import hashlib
from .models import FileDiffResponse

logger = logging.getLogger(__name__)


# ============================================================================
# DIFF CONFIGURATION
# ============================================================================

# Diff size limits (configurable)
MAX_DIFF_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_DIFF_LINES = 10_000  # Max lines in diff
TRUNCATE_HEAD_LINES = 200  # Head lines to show when truncated
TRUNCATE_TAIL_LINES = 200  # Tail lines to show when truncated


# ============================================================================
# DIFF GENERATION
# ============================================================================

def generate_file_diff(
    file_id: str,
    current_content: str,
    current_updated_at: str,
    new_content: str,
    base_updated_at: str = None
) -> FileDiffResponse:
    """
    Generate unified diff between current file content and proposed new content.
    Optionally detects conflicts if base_updated_at is provided.
    Truncates large diffs with flags.
    """
    # Check for conflict if base timestamp provided
    conflict = False
    if base_updated_at and base_updated_at != current_updated_at:
        conflict = True
        logger.warning(f"File {file_id} has been modified since base timestamp")

    # Check file size limits
    if len(current_content) > MAX_DIFF_FILE_SIZE or len(new_content) > MAX_DIFF_FILE_SIZE:
        logger.warning(
            f"File {file_id} exceeds size limit: current={len(current_content)} bytes, new={len(new_content)} bytes"
        )
        # Generate hash of current content
        current_hash = hashlib.sha256(current_content.encode('utf-8')).hexdigest()

        return FileDiffResponse(
            diff=f"""[Diff unavailable - file exceeds {MAX_DIFF_FILE_SIZE / 1024 / 1024:.1f}MB limit]

Current: {len(current_content):,} bytes
Proposed: {len(new_content):,} bytes""",
            current_hash=current_hash,
            current_updated_at=current_updated_at,
            conflict=conflict,
            truncated=True,
            max_lines=0,
            shown_head=0,
            shown_tail=0,
            message="Diff unavailable for files exceeding size limit"
        )

    # Generate unified diff
    current_lines = current_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff = difflib.unified_diff(
        current_lines,
        new_lines,
        fromfile='current',
        tofile='proposed',
        lineterm=''
    )

    diff_lines = list(diff)

    # Check if diff exceeds line limit
    if len(diff_lines) > MAX_DIFF_LINES:
        logger.warning(f"Diff for file {file_id} exceeds {MAX_DIFF_LINES} lines, truncating")

        # Take head and tail
        head = diff_lines[:TRUNCATE_HEAD_LINES]
        tail = diff_lines[-TRUNCATE_TAIL_LINES:]

        truncated_diff = '\n'.join(head) + f"\n\n... [Truncated: {len(diff_lines) - TRUNCATE_HEAD_LINES - TRUNCATE_TAIL_LINES:,} lines omitted] ...\n\n" + '\n'.join(tail)

        # Generate hash of current content
        current_hash = hashlib.sha256(current_content.encode('utf-8')).hexdigest()

        return FileDiffResponse(
            diff=truncated_diff,
            current_hash=current_hash,
            current_updated_at=current_updated_at,
            conflict=conflict,
            truncated=True,
            max_lines=MAX_DIFF_LINES,
            shown_head=TRUNCATE_HEAD_LINES,
            shown_tail=TRUNCATE_TAIL_LINES,
            message=f"Diff truncated: showing first {TRUNCATE_HEAD_LINES} and last {TRUNCATE_TAIL_LINES} lines of {len(diff_lines):,} total"
        )

    diff_str = '\n'.join(diff_lines)

    # Generate hash of current content
    current_hash = hashlib.sha256(current_content.encode('utf-8')).hexdigest()

    return FileDiffResponse(
        diff=diff_str,
        current_hash=current_hash,
        current_updated_at=current_updated_at,
        conflict=conflict
    )
