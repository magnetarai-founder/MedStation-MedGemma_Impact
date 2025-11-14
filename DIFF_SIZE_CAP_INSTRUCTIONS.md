# Diff Size Cap Implementation Instructions

Due to macOS Full Disk Access restrictions, these changes need to be applied manually to `apps/backend/api/code_editor_service.py`.

## Step 1: Update FileDiffResponse Model

Find the `FileDiffResponse` class (around line 90-95) and add optional fields:

```python
class FileDiffResponse(BaseModel):
    diff: str
    current_hash: str
    current_updated_at: str
    conflict: bool = False
    # New optional fields for truncation
    truncated: bool = False
    max_lines: Optional[int] = None
    shown_head: Optional[int] = None
    shown_tail: Optional[int] = None
    message: Optional[str] = None
```

**Make sure to import Optional from typing at the top of the file if not already present:**

```python
from typing import Optional  # Add if not already in imports
```

## Step 2: Add Constants

Add these constants right before the `@router.post("/files/{file_id}/diff")` endpoint (around line 532):

```python
# Diff size limits (configurable)
MAX_DIFF_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_DIFF_LINES = 10_000  # Max lines in diff
TRUNCATE_HEAD_LINES = 200  # Head lines to show when truncated
TRUNCATE_TAIL_LINES = 200  # Tail lines to show when truncated
```

## Step 3: Replace get_file_diff Function

Replace the entire `get_file_diff` function (lines 533-590) with:

```python
@router.post("/files/{file_id}/diff", response_model=FileDiffResponse)
@require_perm("code.use")
async def get_file_diff(file_id: str, diff_request: FileDiffRequest, current_user: dict = Depends(get_current_user)):
    """
    Generate unified diff between current file content and proposed new content.
    Optionally detects conflicts if base_updated_at is provided.
    Truncates large diffs with flags.
    """
    try:
        conn = memory.memory.conn

        # Get current file
        file = conn.execute("""
            SELECT content, updated_at
            FROM code_editor_files
            WHERE id = ?
        """, (file_id,)).fetchone()

        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        current_content = file[0] or ""
        current_updated_at = file[1]

        # Check for conflict if base timestamp provided
        conflict = False
        if diff_request.base_updated_at and diff_request.base_updated_at != current_updated_at:
            conflict = True
            logger.warning(f"File {file_id} has been modified since base timestamp")

        # Check file size limits
        if len(current_content) > MAX_DIFF_FILE_SIZE or len(diff_request.new_content) > MAX_DIFF_FILE_SIZE:
            logger.warning(
                f"File {file_id} exceeds size limit: current={len(current_content)} bytes, new={len(diff_request.new_content)} bytes"
            )
            # Generate hash of current content
            current_hash = hashlib.sha256(current_content.encode('utf-8')).hexdigest()

            return FileDiffResponse(
                diff=f"[Diff unavailable - file exceeds {MAX_DIFF_FILE_SIZE / 1024 / 1024:.1f}MB limit]\n\nCurrent: {len(current_content):,} bytes\nProposed: {len(diff_request.new_content):,} bytes",
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
        new_lines = diff_request.new_content.splitlines(keepends=True)

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

            truncated_diff = (
                '\n'.join(head) +
                f"\n\n... [Truncated: {len(diff_lines) - TRUNCATE_HEAD_LINES - TRUNCATE_TAIL_LINES:,} lines omitted] ...\n\n" +
                '\n'.join(tail)
            )

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate diff: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

## Verification

After applying changes, verify:

```bash
cd apps/backend
rg -n "MAX_DIFF_FILE_SIZE" api/code_editor_service.py
rg -n "truncated:" api/code_editor_service.py
```

Expected output:
- Line showing `MAX_DIFF_FILE_SIZE = 10 * 1024 * 1024`
- Lines showing `truncated=True` in return statements
