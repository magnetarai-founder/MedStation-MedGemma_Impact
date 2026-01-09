"""
Comprehensive tests for api/code_operations.py

Tests Code Operations API endpoints for file browsing, reading, writing.

Coverage targets:
- Pydantic models: ProjectLibraryDocument, UpdateDocumentRequest, WorkspaceRootRequest
- Helper functions: get_library_db_path, init_library_db
- API endpoints: health, files, read, write, delete, library, git
- Security: Path validation, permission checking, rate limiting
"""

import pytest
import tempfile
import os
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
from fastapi import HTTPException

from api.code_operations import (
    ProjectLibraryDocument,
    UpdateDocumentRequest,
    WorkspaceRootRequest,
    get_library_db_path,
    init_library_db,
    router,
)


# ========== Fixtures ==========

@pytest.fixture
def mock_current_user():
    """Mock authenticated user"""
    return {"user_id": "test-user-123", "role": "user"}


@pytest.fixture
def temp_workspace():
    """Create temporary workspace directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir) / "code_workspaces" / "test-user-123"
        workspace.mkdir(parents=True, exist_ok=True)

        # Create some test files
        (workspace / "test.py").write_text("print('hello')")
        (workspace / "readme.md").write_text("# Test Project")

        # Create a subdirectory with files
        subdir = workspace / "src"
        subdir.mkdir()
        (subdir / "main.py").write_text("def main(): pass")

        yield workspace


@pytest.fixture
def temp_db():
    """Create temporary library database"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "project_library.db"
        yield db_path


@pytest.fixture
def mock_code_service():
    """Mock code service"""
    with patch('api.code_operations.file_routes.code_service') as mock:
        mock.get_user_workspace.return_value = Path("/tmp/workspace")
        mock.get_code_workspace_base.return_value = Path("/tmp/code_workspaces")
        mock.is_safe_path.return_value = True
        mock.should_ignore.return_value = False
        mock.walk_directory.return_value = []
        mock.generate_unified_diff.return_value = ""
        yield mock


@pytest.fixture
def mock_permission_layer():
    """Mock permission layer"""
    from api.permission_layer import RiskLevel
    with patch('api.code_operations.file_routes.permission_layer') as mock:
        mock.assess_risk.return_value = (RiskLevel.LOW, "Safe operation")
        yield mock


@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter"""
    with patch('api.code_operations.file_routes.rate_limiter') as mock:
        mock.check_rate_limit.return_value = True
        yield mock


# ========== Pydantic Model Tests ==========

class TestProjectLibraryDocument:
    """Tests for ProjectLibraryDocument model"""

    def test_create_minimal(self):
        """Test creation with minimal fields"""
        doc = ProjectLibraryDocument(
            name="test.md",
            content="# Hello"
        )

        assert doc.name == "test.md"
        assert doc.content == "# Hello"
        assert doc.tags == []
        assert doc.file_type == "markdown"

    def test_create_full(self):
        """Test creation with all fields"""
        doc = ProjectLibraryDocument(
            name="notes.md",
            content="Some notes",
            tags=["work", "important"],
            file_type="text"
        )

        assert doc.name == "notes.md"
        assert doc.tags == ["work", "important"]
        assert doc.file_type == "text"

    def test_empty_content(self):
        """Test with empty content"""
        doc = ProjectLibraryDocument(
            name="empty.md",
            content=""
        )

        assert doc.content == ""

    def test_unicode_content(self):
        """Test with unicode content"""
        doc = ProjectLibraryDocument(
            name="unicode.md",
            content="日本語テスト 🚀"
        )

        assert "日本語" in doc.content


class TestUpdateDocumentRequest:
    """Tests for UpdateDocumentRequest model"""

    def test_create_empty(self):
        """Test creation with no fields"""
        update = UpdateDocumentRequest()

        assert update.name is None
        assert update.content is None
        assert update.tags is None

    def test_create_name_only(self):
        """Test creation with only name"""
        update = UpdateDocumentRequest(name="new_name.md")

        assert update.name == "new_name.md"
        assert update.content is None

    def test_create_full(self):
        """Test creation with all fields"""
        update = UpdateDocumentRequest(
            name="updated.md",
            content="Updated content",
            tags=["new-tag"]
        )

        assert update.name == "updated.md"
        assert update.content == "Updated content"
        assert update.tags == ["new-tag"]


class TestWorkspaceRootRequest:
    """Tests for WorkspaceRootRequest model"""

    def test_create(self):
        """Test creation"""
        req = WorkspaceRootRequest(workspace_root="/Users/test/project")

        assert req.workspace_root == "/Users/test/project"

    def test_unicode_path(self):
        """Test with unicode path"""
        req = WorkspaceRootRequest(workspace_root="/Users/test/项目")

        assert "项目" in req.workspace_root


# ========== Helper Function Tests ==========

class TestGetLibraryDbPath:
    """Tests for get_library_db_path function"""

    def test_returns_path(self):
        """Test returns Path object"""
        result = get_library_db_path()

        assert isinstance(result, Path)
        assert "project_library.db" in str(result)


class TestInitLibraryDb:
    """Tests for init_library_db function"""

    def test_creates_database(self, temp_db):
        """Test creates database file"""
        with patch('api.code_operations.library_db.get_library_db_path', return_value=temp_db):
            init_library_db()

            # Database should be created
            assert temp_db.exists()

    def test_creates_documents_table(self, temp_db):
        """Test creates documents table"""
        with patch('api.code_operations.library_db.get_library_db_path', return_value=temp_db):
            init_library_db()

            # Check table exists
            conn = sqlite3.connect(str(temp_db))
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='documents'
            """)
            result = cursor.fetchone()
            conn.close()

            assert result is not None
            assert result[0] == 'documents'

    def test_idempotent(self, temp_db):
        """Test can be called multiple times safely"""
        with patch('api.code_operations.library_db.get_library_db_path', return_value=temp_db):
            init_library_db()
            init_library_db()
            init_library_db()

            # Should not raise


# ========== Health Check Tests ==========

class TestHealthCheck:
    """Tests for health check endpoint"""

    @pytest.mark.asyncio
    async def test_health_returns_ok(self, mock_code_service):
        """Test health check returns ok"""
        from api.code_operations import health_check

        result = await health_check()

        assert result['status'] == 'ok'
        assert result['service'] == 'code_operations'
        assert 'workspace_base' in result


# ========== File Tree Tests ==========

class TestGetFileTree:
    """Tests for get_file_tree endpoint"""

    @pytest.mark.asyncio
    async def test_list_files_basic(self, mock_code_service, mock_current_user, temp_workspace):
        """Test listing files in workspace"""
        mock_code_service.get_user_workspace.return_value = temp_workspace
        mock_code_service.walk_directory.return_value = [
            {'name': 'test.py', 'is_dir': False},
            {'name': 'src', 'is_dir': True}
        ]

        with patch('api.code_operations.file_routes.log_action', new_callable=AsyncMock):
            from api.code_operations import get_file_tree

            result = await get_file_tree(
                path=".",
                recursive=True,
                absolute_path=None,
                current_user=mock_current_user
            )

            assert 'items' in result
            assert 'path' in result

    @pytest.mark.asyncio
    async def test_list_files_nonexistent_path(self, mock_code_service, mock_current_user):
        """Test listing files for nonexistent path"""
        mock_code_service.get_user_workspace.return_value = Path("/nonexistent")

        from api.code_operations import get_file_tree

        with pytest.raises(HTTPException) as exc:
            await get_file_tree(
                path=".",
                recursive=True,
                absolute_path=None,
                current_user=mock_current_user
            )

        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_absolute_path_outside_workspace(self, mock_code_service, mock_current_user):
        """Test absolute path outside workspace is denied"""
        mock_code_service.get_user_workspace.return_value = Path("/tmp/workspace")

        # Create mock PATHS
        mock_paths = MagicMock()
        mock_paths.data_dir = Path("/tmp")

        # get_config_paths is lazy imported inside function, patch at source module
        with patch('api.config_paths.get_config_paths', return_value=mock_paths):
            from api.code_operations import get_file_tree

            with pytest.raises(HTTPException) as exc:
                await get_file_tree(
                    path=".",
                    recursive=True,
                    absolute_path="/etc/passwd",
                    current_user=mock_current_user
                )

            assert exc.value.status_code == 403


# ========== File Read Tests ==========

class TestReadFile:
    """Tests for read_file endpoint"""

    @pytest.mark.asyncio
    async def test_read_file_success(self, mock_code_service, mock_permission_layer, mock_current_user, temp_workspace):
        """Test reading file successfully"""
        mock_code_service.get_user_workspace.return_value = temp_workspace

        with patch('api.code_operations.file_routes.log_action', new_callable=AsyncMock):
            from api.code_operations import read_file

            result = await read_file(
                path="test.py",
                offset=1,
                limit=100,
                absolute_path=False,
                current_user=mock_current_user
            )

            assert 'content' in result
            assert 'lines' in result
            assert result['path'] == "test.py"

    @pytest.mark.asyncio
    async def test_read_file_not_found(self, mock_code_service, mock_current_user, temp_workspace):
        """Test reading nonexistent file"""
        mock_code_service.get_user_workspace.return_value = temp_workspace

        from api.code_operations import read_file

        with pytest.raises(HTTPException) as exc:
            await read_file(
                path="nonexistent.py",
                offset=1,
                limit=100,
                absolute_path=False,
                current_user=mock_current_user
            )

        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_read_file_is_directory(self, mock_code_service, mock_current_user, temp_workspace):
        """Test reading directory raises error"""
        mock_code_service.get_user_workspace.return_value = temp_workspace

        from api.code_operations import read_file

        with pytest.raises(HTTPException) as exc:
            await read_file(
                path="src",
                offset=1,
                limit=100,
                absolute_path=False,
                current_user=mock_current_user
            )

        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_read_file_invalid_path(self, mock_code_service, mock_current_user, temp_workspace):
        """Test reading file with path traversal"""
        mock_code_service.get_user_workspace.return_value = temp_workspace
        mock_code_service.is_safe_path.return_value = False

        from api.code_operations import read_file

        with pytest.raises(HTTPException) as exc:
            await read_file(
                path="../../../etc/passwd",
                offset=1,
                limit=100,
                absolute_path=False,
                current_user=mock_current_user
            )

        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_read_file_critical_risk(self, mock_code_service, mock_current_user, temp_workspace):
        """Test reading file blocked by permission layer"""
        mock_code_service.get_user_workspace.return_value = temp_workspace

        from api.permission_layer import RiskLevel
        with patch('api.code_operations.file_routes.permission_layer') as mock_perm:
            mock_perm.assess_risk.return_value = (RiskLevel.CRITICAL, "Access denied")

            from api.code_operations import read_file

            with pytest.raises(HTTPException) as exc:
                await read_file(
                    path="test.py",
                    offset=1,
                    limit=100,
                    absolute_path=False,
                    current_user=mock_current_user
                )

            assert exc.value.status_code == 403


# ========== Workspace Info Tests ==========

class TestGetWorkspaceInfo:
    """Tests for get_workspace_info endpoint"""

    @pytest.mark.asyncio
    async def test_get_workspace_info_success(self, mock_code_service, mock_current_user, temp_workspace):
        """Test getting workspace info"""
        mock_code_service.get_user_workspace.return_value = temp_workspace

        from api.code_operations import get_workspace_info

        result = await get_workspace_info(current_user=mock_current_user)

        assert 'workspace_path' in result
        assert 'file_count' in result
        assert 'directory_count' in result
        assert 'total_size' in result
        assert 'total_size_mb' in result


# ========== Diff Preview Tests ==========

class TestPreviewDiff:
    """Tests for preview_diff endpoint"""

    @pytest.mark.asyncio
    async def test_preview_diff_new_file(self, mock_code_service, mock_current_user, temp_workspace):
        """Test preview diff for new file"""
        mock_code_service.get_user_workspace.return_value = temp_workspace
        mock_code_service.generate_unified_diff.return_value = "+new content"

        # Create mock request
        mock_request = MagicMock()
        mock_request.path = "new_file.py"
        mock_request.new_content = "new content"

        from api.code_operations import preview_diff

        result = await preview_diff(
            request=mock_request,
            current_user=mock_current_user
        )

        assert 'diff' in result
        assert 'stats' in result
        assert result['exists'] is False

    @pytest.mark.asyncio
    async def test_preview_diff_existing_file(self, mock_code_service, mock_current_user, temp_workspace):
        """Test preview diff for existing file"""
        mock_code_service.get_user_workspace.return_value = temp_workspace
        mock_code_service.generate_unified_diff.return_value = "-old\n+new"

        mock_request = MagicMock()
        mock_request.path = "test.py"
        mock_request.new_content = "new content"

        from api.code_operations import preview_diff

        result = await preview_diff(
            request=mock_request,
            current_user=mock_current_user
        )

        assert result['exists'] is True
        assert result['stats']['additions'] >= 0
        assert result['stats']['deletions'] >= 0


# ========== Write File Tests ==========

class TestWriteFile:
    """Tests for write_file endpoint"""

    @pytest.mark.asyncio
    async def test_write_file_success(self, mock_code_service, mock_permission_layer, mock_rate_limiter, mock_current_user, temp_workspace):
        """Test writing file successfully"""
        mock_code_service.get_user_workspace.return_value = temp_workspace

        mock_request = MagicMock()
        mock_request.path = "new_file.py"
        mock_request.content = "print('hello')"
        mock_request.create_if_missing = True

        with patch('api.code_operations.file_routes.log_action', new_callable=AsyncMock):
            from api.code_operations import write_file

            result = await write_file(
                request=mock_request,
                current_user=mock_current_user
            )

            assert result['success'] is True
            assert result['path'] == "new_file.py"

    @pytest.mark.asyncio
    async def test_write_file_rate_limited(self, mock_code_service, mock_current_user):
        """Test write file rate limiting"""
        with patch('api.code_operations.file_routes.rate_limiter') as mock_limiter:
            mock_limiter.check_rate_limit.return_value = False

            mock_request = MagicMock()
            mock_request.path = "test.py"
            mock_request.content = "content"

            from api.code_operations import write_file

            with pytest.raises(HTTPException) as exc:
                await write_file(
                    request=mock_request,
                    current_user=mock_current_user
                )

            assert exc.value.status_code == 429

    @pytest.mark.asyncio
    async def test_write_file_invalid_path(self, mock_code_service, mock_rate_limiter, mock_current_user, temp_workspace):
        """Test write file with invalid path"""
        mock_code_service.get_user_workspace.return_value = temp_workspace
        mock_code_service.is_safe_path.return_value = False

        mock_request = MagicMock()
        mock_request.path = "../../../etc/passwd"
        mock_request.content = "malicious"

        from api.code_operations import write_file

        with pytest.raises(HTTPException) as exc:
            await write_file(
                request=mock_request,
                current_user=mock_current_user
            )

        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_write_file_critical_risk(self, mock_code_service, mock_rate_limiter, mock_current_user, temp_workspace):
        """Test write file blocked by permission layer"""
        mock_code_service.get_user_workspace.return_value = temp_workspace

        from api.permission_layer import RiskLevel
        with patch('api.code_operations.file_routes.permission_layer') as mock_perm:
            mock_perm.assess_risk.return_value = (RiskLevel.CRITICAL, "Dangerous operation")

            mock_request = MagicMock()
            mock_request.path = "dangerous.py"
            mock_request.content = "rm -rf /"
            mock_request.create_if_missing = True

            from api.code_operations import write_file

            with pytest.raises(HTTPException) as exc:
                await write_file(
                    request=mock_request,
                    current_user=mock_current_user
                )

            assert exc.value.status_code == 403


# ========== Delete File Tests ==========

class TestDeleteFile:
    """Tests for delete_file endpoint"""

    @pytest.mark.asyncio
    async def test_delete_file_success(self, mock_code_service, mock_permission_layer, mock_rate_limiter, mock_current_user, temp_workspace):
        """Test deleting file successfully"""
        mock_code_service.get_user_workspace.return_value = temp_workspace

        with patch('api.code_operations.file_routes.log_action', new_callable=AsyncMock):
            from api.code_operations import delete_file

            result = await delete_file(
                path="test.py",
                current_user=mock_current_user
            )

            assert result['success'] is True
            assert result['operation'] == 'delete'

    @pytest.mark.asyncio
    async def test_delete_file_not_found(self, mock_code_service, mock_rate_limiter, mock_current_user, temp_workspace):
        """Test deleting nonexistent file"""
        mock_code_service.get_user_workspace.return_value = temp_workspace

        from api.code_operations import delete_file

        with pytest.raises(HTTPException) as exc:
            await delete_file(
                path="nonexistent.py",
                current_user=mock_current_user
            )

        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_file_rate_limited(self, mock_code_service, mock_current_user):
        """Test delete file rate limiting"""
        with patch('api.code_operations.file_routes.rate_limiter') as mock_limiter:
            mock_limiter.check_rate_limit.return_value = False

            from api.code_operations import delete_file

            with pytest.raises(HTTPException) as exc:
                await delete_file(
                    path="test.py",
                    current_user=mock_current_user
                )

            assert exc.value.status_code == 429

    @pytest.mark.asyncio
    async def test_delete_directory_fails(self, mock_code_service, mock_rate_limiter, mock_permission_layer, mock_current_user, temp_workspace):
        """Test deleting directory fails"""
        mock_code_service.get_user_workspace.return_value = temp_workspace

        from api.code_operations import delete_file

        with pytest.raises(HTTPException) as exc:
            await delete_file(
                path="src",
                current_user=mock_current_user
            )

        assert exc.value.status_code == 400


# ========== Library Tests ==========

class TestLibraryEndpoints:
    """Tests for project library endpoints"""

    @pytest.mark.asyncio
    async def test_get_library_documents_empty(self, mock_current_user, temp_db):
        """Test getting empty library"""
        with patch('api.code_operations.library_db.get_library_db_path', return_value=temp_db):
            # Initialize database
            conn = sqlite3.connect(str(temp_db))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()

            from api.code_operations import get_library_documents

            result = await get_library_documents(current_user=mock_current_user)

            assert result == []

    @pytest.mark.asyncio
    async def test_create_library_document(self, mock_current_user, temp_db):
        """Test creating library document"""
        with patch('api.code_operations.library_db.get_library_db_path', return_value=temp_db):
            # Initialize database
            conn = sqlite3.connect(str(temp_db))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()

            doc = ProjectLibraryDocument(
                name="test.md",
                content="# Test",
                tags=["test"]
            )

            with patch('api.code_operations.library_routes.log_action', new_callable=AsyncMock):
                from api.code_operations import create_library_document

                result = await create_library_document(doc=doc, current_user=mock_current_user)

                assert result['success'] is True
                assert 'id' in result

    @pytest.mark.asyncio
    async def test_update_library_document(self, mock_current_user, temp_db):
        """Test updating library document"""
        with patch('api.code_operations.library_db.get_library_db_path', return_value=temp_db):
            # Initialize and insert test document
            import json
            conn = sqlite3.connect(str(temp_db))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
            """)
            conn.execute(
                "INSERT INTO documents (user_id, name, content, tags, file_type) VALUES (?, ?, ?, ?, ?)",
                ("test-user-123", "old.md", "old content", json.dumps([]), "markdown")
            )
            conn.commit()
            conn.close()

            update = UpdateDocumentRequest(name="new.md", content="new content")

            with patch('api.code_operations.library_routes.log_action', new_callable=AsyncMock):
                from api.code_operations import update_library_document

                result = await update_library_document(doc_id=1, update=update, current_user=mock_current_user)

                assert result['success'] is True

    @pytest.mark.asyncio
    async def test_delete_library_document(self, mock_current_user, temp_db):
        """Test deleting library document"""
        with patch('api.code_operations.library_db.get_library_db_path', return_value=temp_db):
            # Initialize and insert test document
            import json
            conn = sqlite3.connect(str(temp_db))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
            """)
            conn.execute(
                "INSERT INTO documents (user_id, name, content, tags, file_type) VALUES (?, ?, ?, ?, ?)",
                ("test-user-123", "test.md", "content", json.dumps([]), "markdown")
            )
            conn.commit()
            conn.close()

            with patch('api.code_operations.library_routes.log_action', new_callable=AsyncMock):
                from api.code_operations import delete_library_document

                result = await delete_library_document(doc_id=1, current_user=mock_current_user)

                assert result['success'] is True


# ========== Workspace Set Tests ==========

class TestSetWorkspaceRoot:
    """Tests for set_workspace_root endpoint"""

    @pytest.mark.asyncio
    async def test_set_workspace_success(self, temp_workspace):
        """Test setting workspace root successfully"""
        with patch.object(Path, 'write_text') as mock_write:
            from api.code_operations import set_workspace_root

            req = WorkspaceRootRequest(workspace_root=str(temp_workspace))

            result = await set_workspace_root(request=req)

            assert result['success'] is True

    @pytest.mark.asyncio
    async def test_set_workspace_nonexistent_path(self):
        """Test setting nonexistent workspace path"""
        from api.code_operations import set_workspace_root

        req = WorkspaceRootRequest(workspace_root="/nonexistent/path")

        with pytest.raises(HTTPException) as exc:
            await set_workspace_root(request=req)

        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_set_workspace_not_directory(self, temp_workspace):
        """Test setting file as workspace"""
        from api.code_operations import set_workspace_root

        file_path = temp_workspace / "test.py"
        req = WorkspaceRootRequest(workspace_root=str(file_path))

        with pytest.raises(HTTPException) as exc:
            await set_workspace_root(request=req)

        assert exc.value.status_code == 400


# ========== Git Log Tests ==========

class TestGetGitLog:
    """Tests for get_git_log endpoint"""

    @pytest.mark.asyncio
    async def test_git_log_no_workspace(self, mock_current_user):
        """Test git log when no workspace set"""
        # Create a temp directory for the marker file without content
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_paths = MagicMock()
            mock_paths.data_dir = Path(tmpdir)

            with patch('api.code_operations.git_routes.PATHS', mock_paths):
                from api.code_operations import get_git_log

                result = await get_git_log(current_user=mock_current_user)

                assert result['commits'] == []
                assert result['error'] == 'No workspace opened'

    @pytest.mark.asyncio
    async def test_git_log_not_git_repo(self, mock_current_user, temp_workspace):
        """Test git log when workspace is not a git repo"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_paths = MagicMock()
            mock_paths.data_dir = Path(tmpdir)

            # Write marker file pointing to temp_workspace (no .git)
            marker_file = Path(tmpdir) / "current_workspace.txt"
            marker_file.write_text(str(temp_workspace))

            with patch('api.code_operations.git_routes.PATHS', mock_paths):
                from api.code_operations import get_git_log

                result = await get_git_log(current_user=mock_current_user)

                assert result['commits'] == []
                assert result['error'] == 'Not a git repository'

    @pytest.mark.asyncio
    async def test_git_log_timeout(self, mock_current_user, temp_workspace):
        """Test git log handles timeout"""
        import subprocess

        # Create .git directory
        (temp_workspace / ".git").mkdir()

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_paths = MagicMock()
            mock_paths.data_dir = Path(tmpdir)

            marker_file = Path(tmpdir) / "current_workspace.txt"
            marker_file.write_text(str(temp_workspace))

            with patch('api.code_operations.git_routes.PATHS', mock_paths), \
                 patch('api.code_operations.git_routes.subprocess.run', side_effect=subprocess.TimeoutExpired("git", 5)):
                from api.code_operations import get_git_log

                with pytest.raises(HTTPException) as exc:
                    await get_git_log(current_user=mock_current_user)

                assert exc.value.status_code == 500


# ========== Router Tests ==========

class TestRouter:
    """Tests for router configuration"""

    def test_router_prefix(self):
        """Test router has correct prefix"""
        assert router.prefix == "/api/v1/code"

    def test_router_tags(self):
        """Test router has correct tags"""
        assert "code" in router.tags


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests"""

    @pytest.mark.asyncio
    async def test_full_library_lifecycle(self, mock_current_user, temp_db):
        """Test full library document lifecycle"""
        with patch('api.code_operations.library_db.get_library_db_path', return_value=temp_db), \
             patch('api.code_operations.library_routes.log_action', new_callable=AsyncMock):

            # Initialize database
            conn = sqlite3.connect(str(temp_db))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()

            from api.code_operations import (
                create_library_document,
                get_library_documents,
                update_library_document,
                delete_library_document
            )

            # Create
            doc = ProjectLibraryDocument(name="test.md", content="initial")
            create_result = await create_library_document(doc=doc, current_user=mock_current_user)
            doc_id = create_result['id']

            # Read
            docs = await get_library_documents(current_user=mock_current_user)
            assert len(docs) == 1

            # Update
            update = UpdateDocumentRequest(content="updated")
            await update_library_document(doc_id=doc_id, update=update, current_user=mock_current_user)

            # Verify update
            docs = await get_library_documents(current_user=mock_current_user)
            assert docs[0]['content'] == "updated"

            # Delete
            await delete_library_document(doc_id=doc_id, current_user=mock_current_user)

            # Verify deletion
            docs = await get_library_documents(current_user=mock_current_user)
            assert len(docs) == 0

