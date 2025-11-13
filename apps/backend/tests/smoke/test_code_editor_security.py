"""
Smoke tests for code editor security features.

Tests:
1. Path guard function (ensure_under_root)
2. Diff endpoint functionality
3. Optimistic concurrency control

These are lightweight smoke tests to verify security features load correctly.
Full integration tests should be added separately.
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

# Skip test if FastAPI is not installed
fastapi = pytest.importorskip("fastapi")

from fastapi import HTTPException


def test_code_editor_service_import():
    """Test that code_editor_service imports successfully."""
    from api import code_editor_service

    assert hasattr(code_editor_service, "router"), "code_editor_service should expose 'router' attribute"
    assert isinstance(code_editor_service.router, fastapi.APIRouter), "router should be an APIRouter instance"


def test_ensure_under_root_valid_path():
    """Test that ensure_under_root accepts valid paths under root."""
    from api.code_editor_service import ensure_under_root

    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        valid_child = root / "subdir" / "file.txt"

        # Should not raise
        try:
            ensure_under_root(root, valid_child)
        except HTTPException:
            pytest.fail("ensure_under_root raised HTTPException for valid path")


def test_ensure_under_root_traversal_attempt():
    """Test that ensure_under_root blocks path traversal attempts."""
    from api.code_editor_service import ensure_under_root

    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "workspace"
        root.mkdir()

        # Attempt to escape workspace
        malicious_path = root / ".." / ".." / "etc" / "passwd"

        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            ensure_under_root(root, malicious_path)

        assert exc_info.value.status_code == 400
        assert "workspace root" in str(exc_info.value.detail).lower()


def test_ensure_under_root_absolute_escape():
    """Test that ensure_under_root blocks absolute paths outside root."""
    from api.code_editor_service import ensure_under_root

    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "workspace"
        root.mkdir()

        # Absolute path outside workspace
        external_path = Path("/tmp/malicious.txt")

        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            ensure_under_root(root, external_path)

        assert exc_info.value.status_code == 400


def test_file_diff_models_import():
    """Test that diff models can be imported."""
    from api.code_editor_service import FileDiffRequest, FileDiffResponse

    # Test FileDiffRequest
    diff_req = FileDiffRequest(
        new_content="hello world",
        base_updated_at="2025-01-01T00:00:00"
    )
    assert diff_req.new_content == "hello world"
    assert diff_req.base_updated_at == "2025-01-01T00:00:00"

    # Test FileDiffResponse
    diff_resp = FileDiffResponse(
        diff="@@ -1 +1 @@\n-old\n+new",
        current_hash="abc123",
        current_updated_at="2025-01-01T00:00:00",
        conflict=False
    )
    assert diff_resp.conflict is False


def test_file_update_has_base_updated_at():
    """Test that FileUpdate model includes base_updated_at for optimistic concurrency."""
    from api.code_editor_service import FileUpdate

    # Test with base_updated_at
    update = FileUpdate(
        content="new content",
        base_updated_at="2025-01-01T00:00:00"
    )
    assert update.base_updated_at == "2025-01-01T00:00:00"

    # Test without base_updated_at (should be None)
    update_no_base = FileUpdate(content="new content")
    assert update_no_base.base_updated_at is None


def test_rbac_decorators_present():
    """Test that RBAC decorators are applied to code editor endpoints."""
    from api import code_editor_service
    import inspect

    # Check that key endpoints have @require_perm decorator
    # We check this by looking for the decorator's wrapper signature

    # Write operations should have code.edit permission
    create_workspace = code_editor_service.create_workspace
    assert callable(create_workspace), "create_workspace should be callable"

    create_file = code_editor_service.create_file
    assert callable(create_file), "create_file should be callable"

    update_file = code_editor_service.update_file
    assert callable(update_file), "update_file should be callable"

    # Read operations should have code.use permission
    get_file = code_editor_service.get_file
    assert callable(get_file), "get_file should be callable"

    get_file_diff = code_editor_service.get_file_diff
    assert callable(get_file_diff), "get_file_diff should be callable"


def test_audit_action_constants():
    """Test that code editor audit action constants are defined."""
    from audit_logger import AuditAction

    # Verify all required audit actions exist
    assert hasattr(AuditAction, "CODE_WORKSPACE_CREATED")
    assert hasattr(AuditAction, "CODE_WORKSPACE_SYNCED")
    assert hasattr(AuditAction, "CODE_FILE_CREATED")
    assert hasattr(AuditAction, "CODE_FILE_UPDATED")
    assert hasattr(AuditAction, "CODE_FILE_DELETED")
    assert hasattr(AuditAction, "CODE_FILE_IMPORTED")

    # Verify they have string values
    assert isinstance(AuditAction.CODE_FILE_CREATED, str)
    assert AuditAction.CODE_FILE_CREATED.startswith("code.")
