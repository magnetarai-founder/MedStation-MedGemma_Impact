"""
Comprehensive tests for api/services/vault/core.py

Tests the VaultService class which handles all vault operations including
documents, files, folders, tags, favorites, versioning, trash, search,
sharing, ACL, and automation.

Coverage targets:
- VaultService initialization and database schema creation
- Inline methods: comments (CRUD), metadata (get/set), thumbnail generation
- Delegated methods to sub-modules (mocked)
- Singleton pattern via get_vault_service()
"""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from datetime import datetime, UTC
from unittest.mock import patch, MagicMock, PropertyMock
import uuid


# ========== Fixtures ==========

@pytest.fixture
def temp_dir():
    """Create temporary directory for test database and files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config_paths(temp_dir):
    """Mock config paths to use temporary directory"""
    mock_paths = MagicMock()
    mock_paths.data_dir = temp_dir

    with patch('api.services.vault.core.get_config_paths', return_value=mock_paths):
        with patch('api.services.vault.core.PATHS', mock_paths):
            with patch('api.services.vault.core.VAULT_DB_PATH', temp_dir / "vault.db"):
                with patch('api.services.vault.core.VAULT_FILES_PATH', temp_dir / "vault_files"):
                    yield mock_paths


@pytest.fixture
def vault_service(mock_config_paths, temp_dir):
    """Create VaultService with temporary database"""
    from api.services.vault.core import VaultService

    # Patch the module-level constants
    with patch('api.services.vault.core.VAULT_DB_PATH', temp_dir / "vault.db"):
        with patch('api.services.vault.core.VAULT_FILES_PATH', temp_dir / "vault_files"):
            service = VaultService()
            service.db_path = temp_dir / "vault.db"
            service.files_path = temp_dir / "vault_files"
            return service


@pytest.fixture
def reset_singleton():
    """Reset singleton between tests"""
    import api.services.vault.core as module
    original = module._vault_service
    module._vault_service = None
    yield module
    module._vault_service = original


@pytest.fixture
def sample_file_id():
    """Generate sample file ID"""
    return str(uuid.uuid4())


@pytest.fixture
def sample_user_id():
    """Generate sample user ID"""
    return str(uuid.uuid4())


# ========== VaultService Initialization Tests ==========

class TestVaultServiceInit:
    """Tests for VaultService initialization"""

    def test_init_creates_database_directory(self, temp_dir, mock_config_paths):
        """Test initialization creates database parent directory"""
        from api.services.vault.core import VaultService

        db_path = temp_dir / "subdir" / "vault.db"

        with patch('api.services.vault.core.VAULT_DB_PATH', db_path):
            with patch('api.services.vault.core.VAULT_FILES_PATH', temp_dir / "vault_files"):
                service = VaultService()
                service.db_path = db_path

                assert db_path.parent.exists()

    def test_init_creates_files_directory(self, temp_dir, mock_config_paths):
        """Test initialization creates files directory"""
        from api.services.vault.core import VaultService

        files_path = temp_dir / "vault_files"

        with patch('api.services.vault.core.VAULT_DB_PATH', temp_dir / "vault.db"):
            with patch('api.services.vault.core.VAULT_FILES_PATH', files_path):
                service = VaultService()
                service.files_path = files_path

                assert files_path.exists()

    def test_init_sets_is_unlocked_false(self, vault_service):
        """Test initialization sets is_unlocked to False"""
        assert vault_service.is_unlocked is False

    def test_init_creates_database_file(self, vault_service):
        """Test initialization creates database file"""
        assert vault_service.db_path.exists()


class TestDatabaseSchema:
    """Tests for database schema creation"""

    def test_vault_documents_table_exists(self, vault_service):
        """Test vault_documents table is created"""
        conn = sqlite3.connect(str(vault_service.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='vault_documents'
        """)

        assert cursor.fetchone() is not None
        conn.close()

    def test_vault_files_table_exists(self, vault_service):
        """Test vault_files table is created"""
        conn = sqlite3.connect(str(vault_service.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='vault_files'
        """)

        assert cursor.fetchone() is not None
        conn.close()

    def test_vault_folders_table_exists(self, vault_service):
        """Test vault_folders table is created"""
        conn = sqlite3.connect(str(vault_service.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='vault_folders'
        """)

        assert cursor.fetchone() is not None
        conn.close()

    def test_vault_file_tags_table_exists(self, vault_service):
        """Test vault_file_tags table is created"""
        conn = sqlite3.connect(str(vault_service.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='vault_file_tags'
        """)

        assert cursor.fetchone() is not None
        conn.close()

    def test_vault_file_favorites_table_exists(self, vault_service):
        """Test vault_file_favorites table is created"""
        conn = sqlite3.connect(str(vault_service.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='vault_file_favorites'
        """)

        assert cursor.fetchone() is not None
        conn.close()

    def test_vault_file_comments_table_exists(self, vault_service):
        """Test vault_file_comments table is created"""
        conn = sqlite3.connect(str(vault_service.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='vault_file_comments'
        """)

        assert cursor.fetchone() is not None
        conn.close()

    def test_vault_file_metadata_table_exists(self, vault_service):
        """Test vault_file_metadata table is created"""
        conn = sqlite3.connect(str(vault_service.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='vault_file_metadata'
        """)

        assert cursor.fetchone() is not None
        conn.close()

    def test_vault_file_versions_table_exists(self, vault_service):
        """Test vault_file_versions table is created"""
        conn = sqlite3.connect(str(vault_service.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='vault_file_versions'
        """)

        assert cursor.fetchone() is not None
        conn.close()

    def test_vault_file_shares_table_exists(self, vault_service):
        """Test vault_file_shares table is created"""
        conn = sqlite3.connect(str(vault_service.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='vault_file_shares'
        """)

        assert cursor.fetchone() is not None
        conn.close()

    def test_vault_audit_logs_table_exists(self, vault_service):
        """Test vault_audit_logs table is created"""
        conn = sqlite3.connect(str(vault_service.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='vault_audit_logs'
        """)

        assert cursor.fetchone() is not None
        conn.close()

    def test_vault_users_table_exists(self, vault_service):
        """Test vault_users table is created"""
        conn = sqlite3.connect(str(vault_service.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='vault_users'
        """)

        assert cursor.fetchone() is not None
        conn.close()

    def test_vault_file_acl_table_exists(self, vault_service):
        """Test vault_file_acl table is created"""
        conn = sqlite3.connect(str(vault_service.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='vault_file_acl'
        """)

        assert cursor.fetchone() is not None
        conn.close()

    def test_vault_organization_rules_table_exists(self, vault_service):
        """Test vault_organization_rules table is created"""
        conn = sqlite3.connect(str(vault_service.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='vault_organization_rules'
        """)

        assert cursor.fetchone() is not None
        conn.close()

    def test_indexes_created(self, vault_service):
        """Test indexes are created"""
        conn = sqlite3.connect(str(vault_service.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND name LIKE 'idx_vault_%'
        """)

        indexes = cursor.fetchall()
        conn.close()

        # Should have many indexes
        assert len(indexes) > 10

    def test_vault_type_constraint_real(self, vault_service):
        """Test vault_type CHECK constraint allows 'real'"""
        conn = sqlite3.connect(str(vault_service.db_path))
        cursor = conn.cursor()

        # Should succeed
        cursor.execute("""
            INSERT INTO vault_documents (
                id, user_id, vault_type, encrypted_blob, encrypted_metadata,
                created_at, updated_at, size_bytes
            ) VALUES (?, ?, 'real', 'blob', 'meta', ?, ?, 100)
        """, ('test-id-1', 'user-1', datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat()))

        conn.commit()
        conn.close()

    def test_vault_type_constraint_decoy(self, vault_service):
        """Test vault_type CHECK constraint allows 'decoy'"""
        conn = sqlite3.connect(str(vault_service.db_path))
        cursor = conn.cursor()

        # Should succeed
        cursor.execute("""
            INSERT INTO vault_documents (
                id, user_id, vault_type, encrypted_blob, encrypted_metadata,
                created_at, updated_at, size_bytes
            ) VALUES (?, ?, 'decoy', 'blob', 'meta', ?, ?, 100)
        """, ('test-id-2', 'user-1', datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat()))

        conn.commit()
        conn.close()

    def test_vault_type_constraint_invalid(self, vault_service):
        """Test vault_type CHECK constraint rejects invalid values"""
        conn = sqlite3.connect(str(vault_service.db_path))
        cursor = conn.cursor()

        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("""
                INSERT INTO vault_documents (
                    id, user_id, vault_type, encrypted_blob, encrypted_metadata,
                    created_at, updated_at, size_bytes
                ) VALUES (?, ?, 'invalid', 'blob', 'meta', ?, ?, 100)
            """, ('test-id-3', 'user-1', datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat()))

        conn.close()


# ========== File Comments Tests ==========

class TestFileComments:
    """Tests for file comment methods"""

    def test_add_file_comment_success(self, vault_service, sample_user_id, sample_file_id):
        """Test adding a comment to a file"""
        result = vault_service.add_file_comment(
            user_id=sample_user_id,
            vault_type="real",
            file_id=sample_file_id,
            comment_text="This is a test comment"
        )

        assert "id" in result
        assert result["file_id"] == sample_file_id
        assert result["comment_text"] == "This is a test comment"
        assert "created_at" in result

    def test_add_file_comment_unicode(self, vault_service, sample_user_id, sample_file_id):
        """Test adding a comment with unicode"""
        result = vault_service.add_file_comment(
            user_id=sample_user_id,
            vault_type="real",
            file_id=sample_file_id,
            comment_text="日本語コメント 🎉"
        )

        assert result["comment_text"] == "日本語コメント 🎉"

    def test_add_file_comment_special_chars(self, vault_service, sample_user_id, sample_file_id):
        """Test adding a comment with special characters"""
        comment = "Test <script>alert('xss')</script> & \"quotes\" 'apostrophe'"
        result = vault_service.add_file_comment(
            user_id=sample_user_id,
            vault_type="real",
            file_id=sample_file_id,
            comment_text=comment
        )

        assert result["comment_text"] == comment

    def test_add_file_comment_long_text(self, vault_service, sample_user_id, sample_file_id):
        """Test adding a very long comment"""
        long_comment = "x" * 10000
        result = vault_service.add_file_comment(
            user_id=sample_user_id,
            vault_type="real",
            file_id=sample_file_id,
            comment_text=long_comment
        )

        assert len(result["comment_text"]) == 10000

    def test_add_multiple_comments(self, vault_service, sample_user_id, sample_file_id):
        """Test adding multiple comments to same file"""
        result1 = vault_service.add_file_comment(
            user_id=sample_user_id,
            vault_type="real",
            file_id=sample_file_id,
            comment_text="First comment"
        )

        result2 = vault_service.add_file_comment(
            user_id=sample_user_id,
            vault_type="real",
            file_id=sample_file_id,
            comment_text="Second comment"
        )

        assert result1["id"] != result2["id"]

    def test_get_file_comments_empty(self, vault_service, sample_user_id, sample_file_id):
        """Test getting comments when none exist"""
        result = vault_service.get_file_comments(
            user_id=sample_user_id,
            vault_type="real",
            file_id=sample_file_id
        )

        assert result == []

    def test_get_file_comments_single(self, vault_service, sample_user_id, sample_file_id):
        """Test getting a single comment"""
        vault_service.add_file_comment(
            user_id=sample_user_id,
            vault_type="real",
            file_id=sample_file_id,
            comment_text="Test comment"
        )

        result = vault_service.get_file_comments(
            user_id=sample_user_id,
            vault_type="real",
            file_id=sample_file_id
        )

        assert len(result) == 1
        assert result[0]["comment_text"] == "Test comment"

    def test_get_file_comments_multiple_ordered(self, vault_service, sample_user_id, sample_file_id):
        """Test getting multiple comments returns them in descending order"""
        vault_service.add_file_comment(
            user_id=sample_user_id,
            vault_type="real",
            file_id=sample_file_id,
            comment_text="First"
        )

        vault_service.add_file_comment(
            user_id=sample_user_id,
            vault_type="real",
            file_id=sample_file_id,
            comment_text="Second"
        )

        result = vault_service.get_file_comments(
            user_id=sample_user_id,
            vault_type="real",
            file_id=sample_file_id
        )

        assert len(result) == 2
        # Most recent first (DESC order)
        assert result[0]["comment_text"] == "Second"
        assert result[1]["comment_text"] == "First"

    def test_get_file_comments_user_isolation(self, vault_service, sample_file_id):
        """Test comments are isolated by user"""
        user1 = str(uuid.uuid4())
        user2 = str(uuid.uuid4())

        vault_service.add_file_comment(
            user_id=user1,
            vault_type="real",
            file_id=sample_file_id,
            comment_text="User 1 comment"
        )

        vault_service.add_file_comment(
            user_id=user2,
            vault_type="real",
            file_id=sample_file_id,
            comment_text="User 2 comment"
        )

        result1 = vault_service.get_file_comments(user1, "real", sample_file_id)
        result2 = vault_service.get_file_comments(user2, "real", sample_file_id)

        assert len(result1) == 1
        assert result1[0]["comment_text"] == "User 1 comment"
        assert len(result2) == 1
        assert result2[0]["comment_text"] == "User 2 comment"

    def test_get_file_comments_vault_isolation(self, vault_service, sample_user_id, sample_file_id):
        """Test comments are isolated by vault type"""
        vault_service.add_file_comment(
            user_id=sample_user_id,
            vault_type="real",
            file_id=sample_file_id,
            comment_text="Real vault comment"
        )

        vault_service.add_file_comment(
            user_id=sample_user_id,
            vault_type="decoy",
            file_id=sample_file_id,
            comment_text="Decoy vault comment"
        )

        real_comments = vault_service.get_file_comments(sample_user_id, "real", sample_file_id)
        decoy_comments = vault_service.get_file_comments(sample_user_id, "decoy", sample_file_id)

        assert len(real_comments) == 1
        assert real_comments[0]["comment_text"] == "Real vault comment"
        assert len(decoy_comments) == 1
        assert decoy_comments[0]["comment_text"] == "Decoy vault comment"

    def test_update_file_comment_success(self, vault_service, sample_user_id, sample_file_id):
        """Test updating a comment"""
        add_result = vault_service.add_file_comment(
            user_id=sample_user_id,
            vault_type="real",
            file_id=sample_file_id,
            comment_text="Original"
        )

        update_result = vault_service.update_file_comment(
            user_id=sample_user_id,
            vault_type="real",
            comment_id=add_result["id"],
            comment_text="Updated"
        )

        assert update_result["comment_text"] == "Updated"
        assert "updated_at" in update_result

    def test_update_file_comment_not_found(self, vault_service, sample_user_id):
        """Test updating nonexistent comment raises error"""
        with pytest.raises(ValueError, match="Comment not found"):
            vault_service.update_file_comment(
                user_id=sample_user_id,
                vault_type="real",
                comment_id="nonexistent-id",
                comment_text="Updated"
            )

    def test_update_file_comment_wrong_user(self, vault_service, sample_file_id):
        """Test updating comment with wrong user fails"""
        user1 = str(uuid.uuid4())
        user2 = str(uuid.uuid4())

        add_result = vault_service.add_file_comment(
            user_id=user1,
            vault_type="real",
            file_id=sample_file_id,
            comment_text="Original"
        )

        with pytest.raises(ValueError, match="Comment not found"):
            vault_service.update_file_comment(
                user_id=user2,  # Wrong user
                vault_type="real",
                comment_id=add_result["id"],
                comment_text="Updated"
            )

    def test_delete_file_comment_success(self, vault_service, sample_user_id, sample_file_id):
        """Test deleting a comment"""
        add_result = vault_service.add_file_comment(
            user_id=sample_user_id,
            vault_type="real",
            file_id=sample_file_id,
            comment_text="To delete"
        )

        delete_result = vault_service.delete_file_comment(
            user_id=sample_user_id,
            vault_type="real",
            comment_id=add_result["id"]
        )

        assert delete_result is True

        # Verify it's gone
        comments = vault_service.get_file_comments(
            sample_user_id, "real", sample_file_id
        )
        assert len(comments) == 0

    def test_delete_file_comment_not_found(self, vault_service, sample_user_id):
        """Test deleting nonexistent comment returns False"""
        result = vault_service.delete_file_comment(
            user_id=sample_user_id,
            vault_type="real",
            comment_id="nonexistent-id"
        )

        assert result is False

    def test_delete_file_comment_wrong_user(self, vault_service, sample_file_id):
        """Test deleting comment with wrong user fails"""
        user1 = str(uuid.uuid4())
        user2 = str(uuid.uuid4())

        add_result = vault_service.add_file_comment(
            user_id=user1,
            vault_type="real",
            file_id=sample_file_id,
            comment_text="Test"
        )

        # Wrong user can't delete
        result = vault_service.delete_file_comment(
            user_id=user2,
            vault_type="real",
            comment_id=add_result["id"]
        )

        assert result is False


# ========== File Metadata Tests ==========

class TestFileMetadata:
    """Tests for file metadata methods"""

    def test_set_file_metadata_new(self, vault_service, sample_user_id, sample_file_id):
        """Test setting new metadata"""
        result = vault_service.set_file_metadata(
            user_id=sample_user_id,
            vault_type="real",
            file_id=sample_file_id,
            key="description",
            value="Test description"
        )

        assert result["key"] == "description"
        assert result["value"] == "Test description"
        assert "updated_at" in result

    def test_set_file_metadata_update_existing(self, vault_service, sample_user_id, sample_file_id):
        """Test updating existing metadata"""
        vault_service.set_file_metadata(
            user_id=sample_user_id,
            vault_type="real",
            file_id=sample_file_id,
            key="description",
            value="Original"
        )

        result = vault_service.set_file_metadata(
            user_id=sample_user_id,
            vault_type="real",
            file_id=sample_file_id,
            key="description",
            value="Updated"
        )

        assert result["value"] == "Updated"

    def test_set_file_metadata_multiple_keys(self, vault_service, sample_user_id, sample_file_id):
        """Test setting multiple metadata keys"""
        vault_service.set_file_metadata(
            sample_user_id, "real", sample_file_id, "key1", "value1"
        )
        vault_service.set_file_metadata(
            sample_user_id, "real", sample_file_id, "key2", "value2"
        )
        vault_service.set_file_metadata(
            sample_user_id, "real", sample_file_id, "key3", "value3"
        )

        metadata = vault_service.get_file_metadata(
            sample_user_id, "real", sample_file_id
        )

        assert len(metadata) == 3
        assert metadata["key1"] == "value1"
        assert metadata["key2"] == "value2"
        assert metadata["key3"] == "value3"

    def test_set_file_metadata_unicode(self, vault_service, sample_user_id, sample_file_id):
        """Test setting metadata with unicode"""
        vault_service.set_file_metadata(
            sample_user_id, "real", sample_file_id,
            "タイトル", "日本語の値 🎌"
        )

        metadata = vault_service.get_file_metadata(
            sample_user_id, "real", sample_file_id
        )

        assert metadata["タイトル"] == "日本語の値 🎌"

    def test_get_file_metadata_empty(self, vault_service, sample_user_id, sample_file_id):
        """Test getting metadata when none exists"""
        result = vault_service.get_file_metadata(
            sample_user_id, "real", sample_file_id
        )

        assert result == {}

    def test_get_file_metadata_user_isolation(self, vault_service, sample_file_id):
        """Test metadata is isolated by user"""
        user1 = str(uuid.uuid4())
        user2 = str(uuid.uuid4())

        vault_service.set_file_metadata(user1, "real", sample_file_id, "key", "user1")
        vault_service.set_file_metadata(user2, "real", sample_file_id, "key", "user2")

        meta1 = vault_service.get_file_metadata(user1, "real", sample_file_id)
        meta2 = vault_service.get_file_metadata(user2, "real", sample_file_id)

        assert meta1["key"] == "user1"
        assert meta2["key"] == "user2"

    def test_get_file_metadata_vault_isolation(self, vault_service, sample_user_id, sample_file_id):
        """Test metadata is isolated by vault type"""
        vault_service.set_file_metadata(sample_user_id, "real", sample_file_id, "key", "real")
        vault_service.set_file_metadata(sample_user_id, "decoy", sample_file_id, "key", "decoy")

        real_meta = vault_service.get_file_metadata(sample_user_id, "real", sample_file_id)
        decoy_meta = vault_service.get_file_metadata(sample_user_id, "decoy", sample_file_id)

        assert real_meta["key"] == "real"
        assert decoy_meta["key"] == "decoy"


# ========== Thumbnail Generation Tests ==========

class TestThumbnailGeneration:
    """Tests for thumbnail generation"""

    @pytest.fixture
    def rgb_image_bytes(self):
        """Create simple RGB image bytes"""
        try:
            from PIL import Image
            import io

            img = Image.new('RGB', (400, 400), color='red')
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            return buffer.getvalue()
        except ImportError:
            pytest.skip("PIL not available")

    @pytest.fixture
    def rgba_image_bytes(self):
        """Create RGBA image with transparency"""
        try:
            from PIL import Image
            import io

            img = Image.new('RGBA', (400, 400), color=(255, 0, 0, 128))
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            return buffer.getvalue()
        except ImportError:
            pytest.skip("PIL not available")

    @pytest.fixture
    def palette_image_bytes(self):
        """Create palette mode image"""
        try:
            from PIL import Image
            import io

            img = Image.new('P', (400, 400))
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            return buffer.getvalue()
        except ImportError:
            pytest.skip("PIL not available")

    def test_generate_thumbnail_rgb(self, vault_service, rgb_image_bytes):
        """Test generating thumbnail from RGB image"""
        result = vault_service.generate_thumbnail(rgb_image_bytes)

        assert result is not None
        assert len(result) > 0

        # Verify it's valid JPEG
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(result))
        assert img.format == 'JPEG'

    def test_generate_thumbnail_rgba(self, vault_service, rgba_image_bytes):
        """Test generating thumbnail from RGBA image (with alpha)"""
        result = vault_service.generate_thumbnail(rgba_image_bytes)

        assert result is not None

        # Verify it's valid JPEG (alpha flattened to white)
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(result))
        assert img.format == 'JPEG'
        assert img.mode == 'RGB'  # RGBA converted to RGB

    def test_generate_thumbnail_palette(self, vault_service, palette_image_bytes):
        """Test generating thumbnail from palette mode image"""
        result = vault_service.generate_thumbnail(palette_image_bytes)

        assert result is not None

    def test_generate_thumbnail_size(self, vault_service, rgb_image_bytes):
        """Test thumbnail respects max_size"""
        result = vault_service.generate_thumbnail(rgb_image_bytes, max_size=(100, 100))

        from PIL import Image
        import io
        img = Image.open(io.BytesIO(result))

        assert img.width <= 100
        assert img.height <= 100

    def test_generate_thumbnail_custom_size(self, vault_service, rgb_image_bytes):
        """Test thumbnail with custom max_size"""
        result = vault_service.generate_thumbnail(rgb_image_bytes, max_size=(50, 50))

        from PIL import Image
        import io
        img = Image.open(io.BytesIO(result))

        assert img.width <= 50
        assert img.height <= 50

    def test_generate_thumbnail_invalid_data(self, vault_service):
        """Test thumbnail generation with invalid data returns None"""
        result = vault_service.generate_thumbnail(b"not an image")

        assert result is None

    def test_generate_thumbnail_empty_data(self, vault_service):
        """Test thumbnail generation with empty data returns None"""
        result = vault_service.generate_thumbnail(b"")

        assert result is None

    def test_generate_thumbnail_preserves_aspect_ratio(self, vault_service):
        """Test thumbnail preserves aspect ratio"""
        try:
            from PIL import Image
            import io

            # Create wide image
            img = Image.new('RGB', (800, 200), color='blue')
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            wide_image = buffer.getvalue()

            result = vault_service.generate_thumbnail(wide_image, max_size=(200, 200))

            thumb = Image.open(io.BytesIO(result))
            # Should be wider than tall, maintaining aspect ratio
            assert thumb.width == 200
            assert thumb.height == 50  # 200 * (200/800)
        except ImportError:
            pytest.skip("PIL not available")


# ========== Delegated Method Tests ==========

class TestDelegatedMethods:
    """Tests for methods delegated to sub-modules"""

    def test_store_document_delegates(self, vault_service, sample_user_id):
        """Test store_document delegates to documents_mod"""
        mock_doc = MagicMock()
        mock_result = MagicMock()

        with patch('api.services.vault.core.documents_mod.store_document', return_value=mock_result) as mock:
            result = vault_service.store_document(sample_user_id, mock_doc)

            mock.assert_called_once_with(vault_service, sample_user_id, mock_doc, None)
            assert result == mock_result

    def test_get_document_delegates(self, vault_service, sample_user_id):
        """Test get_document delegates to documents_mod"""
        mock_result = MagicMock()

        with patch('api.services.vault.core.documents_mod.get_document', return_value=mock_result) as mock:
            result = vault_service.get_document(sample_user_id, "doc-id", "real")

            mock.assert_called_once_with(vault_service, sample_user_id, "doc-id", "real", None)
            assert result == mock_result

    def test_list_documents_delegates(self, vault_service, sample_user_id):
        """Test list_documents delegates to documents_mod"""
        mock_result = MagicMock()

        with patch('api.services.vault.core.documents_mod.list_documents', return_value=mock_result) as mock:
            result = vault_service.list_documents(sample_user_id, "real")

            mock.assert_called_once_with(vault_service, sample_user_id, "real", None)
            assert result == mock_result

    def test_upload_file_delegates(self, vault_service, sample_user_id):
        """Test upload_file delegates to files_mod"""
        mock_result = MagicMock()

        with patch('api.services.vault.core.files_mod.upload_file', return_value=mock_result) as mock:
            result = vault_service.upload_file(
                sample_user_id, b"data", "test.txt", "text/plain", "real", "pass123", "/"
            )

            mock.assert_called_once_with(
                vault_service, sample_user_id, b"data", "test.txt", "text/plain", "real", "pass123", "/"
            )
            assert result == mock_result

    def test_list_files_delegates(self, vault_service, sample_user_id):
        """Test list_files delegates to files_mod"""
        mock_result = []

        with patch('api.services.vault.core.files_mod.list_files', return_value=mock_result) as mock:
            result = vault_service.list_files(sample_user_id, "real", "/folder")

            mock.assert_called_once_with(vault_service, sample_user_id, "real", "/folder")
            assert result == mock_result

    def test_create_folder_delegates(self, vault_service, sample_user_id):
        """Test create_folder delegates to folders_mod"""
        mock_result = MagicMock()

        with patch('api.services.vault.core.folders_mod.create_folder', return_value=mock_result) as mock:
            result = vault_service.create_folder(sample_user_id, "real", "new_folder", "/")

            mock.assert_called_once_with(vault_service, sample_user_id, "real", "new_folder", "/")
            assert result == mock_result

    def test_add_tag_to_file_delegates(self, vault_service, sample_user_id, sample_file_id):
        """Test add_tag_to_file delegates to tags_mod"""
        mock_result = {"id": "tag-id"}

        with patch('api.services.vault.core.tags_mod.add_tag_to_file', return_value=mock_result) as mock:
            result = vault_service.add_tag_to_file(
                sample_user_id, "real", sample_file_id, "important", "#FF0000"
            )

            mock.assert_called_once_with(
                vault_service, sample_user_id, "real", sample_file_id, "important", "#FF0000"
            )
            assert result == mock_result

    def test_add_favorite_delegates(self, vault_service, sample_user_id, sample_file_id):
        """Test add_favorite delegates to favorites_mod"""
        mock_result = {"id": "fav-id"}

        with patch('api.services.vault.core.favorites_mod.add_favorite', return_value=mock_result) as mock:
            result = vault_service.add_favorite(sample_user_id, "real", sample_file_id)

            mock.assert_called_once_with(vault_service, sample_user_id, "real", sample_file_id)
            assert result == mock_result

    def test_search_files_delegates(self, vault_service, sample_user_id):
        """Test search_files delegates to search_mod"""
        mock_result = []

        with patch('api.services.vault.core.search_mod.search_files', return_value=mock_result) as mock:
            result = vault_service.search_files(
                sample_user_id, "real", query="test", mime_type="image/*"
            )

            mock.assert_called_once_with(
                vault_service,
                user_id=sample_user_id,
                vault_type="real",
                query="test",
                mime_type="image/*",
                tags=None,
                date_from=None,
                date_to=None,
                min_size=None,
                max_size=None,
                folder_path=None,
            )
            assert result == mock_result

    def test_create_share_link_delegates(self, vault_service, sample_user_id, sample_file_id):
        """Test create_share_link delegates to sharing_mod"""
        mock_result = {"share_token": "abc123"}

        with patch('api.services.vault.core.sharing_mod.create_share_link', return_value=mock_result) as mock:
            result = vault_service.create_share_link(
                sample_user_id, "real", sample_file_id, password="secret"
            )

            mock.assert_called_once_with(
                vault_service, sample_user_id, "real", sample_file_id, "secret", None, None, "download"
            )
            assert result == mock_result

    def test_log_audit_delegates(self, vault_service, sample_user_id):
        """Test log_audit delegates to audit_mod"""
        mock_result = "audit-id"

        with patch('api.services.vault.core.audit_mod.log_audit', return_value=mock_result) as mock:
            result = vault_service.log_audit(
                sample_user_id, "real", "file_upload", "file", "file-123"
            )

            mock.assert_called_once_with(
                vault_service, sample_user_id, "real", "file_upload", "file", "file-123", None, None, None
            )
            assert result == mock_result

    def test_pin_file_delegates(self, vault_service, sample_user_id, sample_file_id):
        """Test pin_file delegates to automation_mod"""
        mock_result = {"pinned": True}

        with patch('api.services.vault.core.automation_mod.pin_file', return_value=mock_result) as mock:
            result = vault_service.pin_file(sample_user_id, "real", sample_file_id, 1)

            mock.assert_called_once_with(vault_service, sample_user_id, "real", sample_file_id, 1)
            assert result == mock_result

    def test_move_to_trash_delegates(self, vault_service, sample_user_id, sample_file_id):
        """Test move_to_trash delegates to files_mod"""
        mock_result = {"deleted": True}

        with patch('api.services.vault.core.files_mod.move_to_trash', return_value=mock_result) as mock:
            result = vault_service.move_to_trash(sample_user_id, "real", sample_file_id)

            mock.assert_called_once_with(vault_service, sample_user_id, "real", sample_file_id)
            assert result == mock_result

    def test_empty_trash_delegates(self, vault_service, sample_user_id):
        """Test empty_trash delegates to files_mod"""
        mock_result = {"deleted_count": 5}

        with patch('api.services.vault.core.files_mod.empty_trash', return_value=mock_result) as mock:
            result = vault_service.empty_trash(sample_user_id, "real")

            mock.assert_called_once_with(vault_service, sample_user_id, "real")
            assert result == mock_result


# ========== Singleton Tests ==========

class TestSingleton:
    """Tests for singleton pattern"""

    def test_get_vault_service_returns_instance(self, reset_singleton, mock_config_paths, temp_dir):
        """Test get_vault_service returns VaultService instance"""
        from api.services.vault.core import get_vault_service, VaultService

        with patch('api.services.vault.core.VAULT_DB_PATH', temp_dir / "vault.db"):
            with patch('api.services.vault.core.VAULT_FILES_PATH', temp_dir / "vault_files"):
                result = get_vault_service()

                assert isinstance(result, VaultService)

    def test_get_vault_service_returns_same_instance(self, reset_singleton, mock_config_paths, temp_dir):
        """Test get_vault_service returns same instance on multiple calls"""
        from api.services.vault.core import get_vault_service

        with patch('api.services.vault.core.VAULT_DB_PATH', temp_dir / "vault.db"):
            with patch('api.services.vault.core.VAULT_FILES_PATH', temp_dir / "vault_files"):
                service1 = get_vault_service()
                service2 = get_vault_service()

                assert service1 is service2

    def test_singleton_state_persists(self, reset_singleton, mock_config_paths, temp_dir):
        """Test singleton state persists across calls"""
        from api.services.vault.core import get_vault_service

        with patch('api.services.vault.core.VAULT_DB_PATH', temp_dir / "vault.db"):
            with patch('api.services.vault.core.VAULT_FILES_PATH', temp_dir / "vault_files"):
                service1 = get_vault_service()
                service1.is_unlocked = True

                service2 = get_vault_service()

                assert service2.is_unlocked is True


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests"""

    def test_comment_lifecycle(self, vault_service, sample_user_id, sample_file_id):
        """Test full comment lifecycle: create, read, update, delete"""
        # Create
        created = vault_service.add_file_comment(
            sample_user_id, "real", sample_file_id, "Initial comment"
        )
        assert created["comment_text"] == "Initial comment"

        # Read
        comments = vault_service.get_file_comments(sample_user_id, "real", sample_file_id)
        assert len(comments) == 1
        assert comments[0]["id"] == created["id"]

        # Update
        updated = vault_service.update_file_comment(
            sample_user_id, "real", created["id"], "Updated comment"
        )
        assert updated["comment_text"] == "Updated comment"

        # Verify update
        comments = vault_service.get_file_comments(sample_user_id, "real", sample_file_id)
        assert comments[0]["comment_text"] == "Updated comment"

        # Delete
        deleted = vault_service.delete_file_comment(sample_user_id, "real", created["id"])
        assert deleted is True

        # Verify deletion
        comments = vault_service.get_file_comments(sample_user_id, "real", sample_file_id)
        assert len(comments) == 0

    def test_metadata_lifecycle(self, vault_service, sample_user_id, sample_file_id):
        """Test full metadata lifecycle"""
        # Set initial metadata
        vault_service.set_file_metadata(
            sample_user_id, "real", sample_file_id, "author", "John"
        )
        vault_service.set_file_metadata(
            sample_user_id, "real", sample_file_id, "department", "Engineering"
        )

        # Read
        metadata = vault_service.get_file_metadata(sample_user_id, "real", sample_file_id)
        assert metadata["author"] == "John"
        assert metadata["department"] == "Engineering"

        # Update
        vault_service.set_file_metadata(
            sample_user_id, "real", sample_file_id, "author", "Jane"
        )

        # Verify update
        metadata = vault_service.get_file_metadata(sample_user_id, "real", sample_file_id)
        assert metadata["author"] == "Jane"
        assert metadata["department"] == "Engineering"  # Unchanged

    def test_dual_vault_isolation(self, vault_service, sample_user_id, sample_file_id):
        """Test real and decoy vaults are isolated"""
        # Add to both vaults
        vault_service.add_file_comment(
            sample_user_id, "real", sample_file_id, "Real vault comment"
        )
        vault_service.add_file_comment(
            sample_user_id, "decoy", sample_file_id, "Decoy vault comment"
        )

        vault_service.set_file_metadata(
            sample_user_id, "real", sample_file_id, "key", "real_value"
        )
        vault_service.set_file_metadata(
            sample_user_id, "decoy", sample_file_id, "key", "decoy_value"
        )

        # Verify isolation
        real_comments = vault_service.get_file_comments(sample_user_id, "real", sample_file_id)
        decoy_comments = vault_service.get_file_comments(sample_user_id, "decoy", sample_file_id)

        assert len(real_comments) == 1
        assert real_comments[0]["comment_text"] == "Real vault comment"
        assert len(decoy_comments) == 1
        assert decoy_comments[0]["comment_text"] == "Decoy vault comment"

        real_meta = vault_service.get_file_metadata(sample_user_id, "real", sample_file_id)
        decoy_meta = vault_service.get_file_metadata(sample_user_id, "decoy", sample_file_id)

        assert real_meta["key"] == "real_value"
        assert decoy_meta["key"] == "decoy_value"


# ========== Edge Cases ==========

class TestEdgeCases:
    """Tests for edge cases"""

    def test_concurrent_comment_adds(self, vault_service, sample_user_id, sample_file_id):
        """Test concurrent comment additions"""
        import threading

        results = []

        def add_comment(idx):
            result = vault_service.add_file_comment(
                sample_user_id, "real", sample_file_id, f"Comment {idx}"
            )
            results.append(result)

        threads = [threading.Thread(target=add_comment, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should succeed
        assert len(results) == 10

        # All should have unique IDs
        ids = [r["id"] for r in results]
        assert len(set(ids)) == 10

        # Database should have all comments
        comments = vault_service.get_file_comments(sample_user_id, "real", sample_file_id)
        assert len(comments) == 10

    def test_empty_string_metadata_value(self, vault_service, sample_user_id, sample_file_id):
        """Test setting metadata with empty string value"""
        vault_service.set_file_metadata(
            sample_user_id, "real", sample_file_id, "key", ""
        )

        metadata = vault_service.get_file_metadata(sample_user_id, "real", sample_file_id)
        assert metadata["key"] == ""

    def test_empty_string_comment(self, vault_service, sample_user_id, sample_file_id):
        """Test adding empty comment"""
        result = vault_service.add_file_comment(
            sample_user_id, "real", sample_file_id, ""
        )

        assert result["comment_text"] == ""

    def test_very_long_metadata_key(self, vault_service, sample_user_id, sample_file_id):
        """Test setting metadata with very long key"""
        long_key = "k" * 1000

        vault_service.set_file_metadata(
            sample_user_id, "real", sample_file_id, long_key, "value"
        )

        metadata = vault_service.get_file_metadata(sample_user_id, "real", sample_file_id)
        assert metadata[long_key] == "value"

    def test_special_characters_in_file_id(self, vault_service, sample_user_id):
        """Test operations with special characters in file_id"""
        special_file_id = "file-with-special/chars\\and:colons"

        result = vault_service.add_file_comment(
            sample_user_id, "real", special_file_id, "Test comment"
        )

        assert result["file_id"] == special_file_id

        comments = vault_service.get_file_comments(sample_user_id, "real", special_file_id)
        assert len(comments) == 1

    def test_multiline_comment(self, vault_service, sample_user_id, sample_file_id):
        """Test multiline comment"""
        multiline = """Line 1
        Line 2
        Line 3

        With blank line above"""

        result = vault_service.add_file_comment(
            sample_user_id, "real", sample_file_id, multiline
        )

        assert result["comment_text"] == multiline

        comments = vault_service.get_file_comments(sample_user_id, "real", sample_file_id)
        assert comments[0]["comment_text"] == multiline


# ========== Error Handling Tests ==========

class TestErrorHandling:
    """Tests for error handling"""

    def test_add_comment_database_error(self, vault_service, sample_user_id, sample_file_id):
        """Test add_comment handles database errors"""
        # Force an error by using invalid vault_type
        # The CHECK constraint will raise an error
        with pytest.raises(Exception):
            vault_service.add_file_comment(
                sample_user_id, "invalid_vault_type", sample_file_id, "Test"
            )

    def test_set_metadata_database_error(self, vault_service, sample_user_id, sample_file_id):
        """Test set_metadata handles database errors"""
        with pytest.raises(Exception):
            vault_service.set_file_metadata(
                sample_user_id, "invalid_vault_type", sample_file_id, "key", "value"
            )
