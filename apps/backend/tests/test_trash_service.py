"""
Tests for Trash Service

Tests the 30-day soft delete system for vault items.
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, UTC
from unittest.mock import patch

from api.trash_service import TrashService, TrashItem, TrashStats


@pytest.fixture
def temp_db():
    """Create a temporary database for testing with required tables"""
    import sqlite3

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    # Create the vault tables that TrashService expects
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vault_documents (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                vault_type TEXT NOT NULL,
                title TEXT,
                content TEXT,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vault_files (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                vault_type TEXT NOT NULL,
                filename TEXT,
                size INTEGER,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vault_folders (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                vault_type TEXT NOT NULL,
                name TEXT,
                parent_id TEXT,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT
            )
        """)
        conn.commit()

    yield db_path
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def trash_service(temp_db):
    """Create a TrashService with temporary database"""
    return TrashService(db_path=temp_db)


class TestTrashItem:
    """Tests for TrashItem model"""

    def test_trash_item_creation(self):
        """Test creating a TrashItem"""
        item = TrashItem(
            id="trash_doc_001",
            user_id="user_001",
            vault_type="real",
            item_type="document",
            item_id="doc_001",
            item_name="Test Document",
            deleted_at="2025-01-01T00:00:00+00:00",
            permanent_delete_at="2025-01-31T00:00:00+00:00",
            original_data='{"content": "test"}'
        )

        assert item.id == "trash_doc_001"
        assert item.user_id == "user_001"
        assert item.vault_type == "real"
        assert item.item_type == "document"

    def test_trash_item_validation(self):
        """Test TrashItem validates required fields"""
        with pytest.raises(Exception):
            TrashItem(
                id="trash_001",
                # Missing required fields
            )


class TestTrashStats:
    """Tests for TrashStats model"""

    def test_trash_stats_creation(self):
        """Test creating TrashStats"""
        stats = TrashStats(
            total_items=10,
            document_count=5,
            file_count=3,
            folder_count=2,
            total_size_bytes=1024,
            oldest_item_date="2025-01-01T00:00:00"
        )

        assert stats.total_items == 10
        assert stats.document_count == 5
        assert stats.total_size_bytes == 1024

    def test_trash_stats_optional_oldest(self):
        """Test TrashStats with no oldest item"""
        stats = TrashStats(
            total_items=0,
            document_count=0,
            file_count=0,
            folder_count=0,
            total_size_bytes=0,
            oldest_item_date=None
        )

        assert stats.oldest_item_date is None


class TestTrashServiceInit:
    """Tests for TrashService initialization"""

    def test_service_initialization(self, temp_db):
        """Test service initializes correctly"""
        service = TrashService(db_path=temp_db)

        assert service.db_path == temp_db
        assert service.RETENTION_DAYS == 30

    def test_service_creates_table(self, temp_db):
        """Test service creates trash table"""
        import sqlite3

        service = TrashService(db_path=temp_db)

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='vault_trash'"
            )
            result = cursor.fetchone()

        assert result is not None
        assert result[0] == "vault_trash"


class TestMoveToTrash:
    """Tests for move_to_trash functionality"""

    def test_move_document_to_trash(self, trash_service):
        """Test moving a document to trash"""
        original_data = json.dumps({"title": "Test", "content": "Hello"})

        item = trash_service.move_to_trash(
            user_id="user_001",
            vault_type="real",
            item_type="document",
            item_id="doc_001",
            item_name="Test Document",
            original_data=original_data
        )

        assert item.id == "trash_doc_001"
        assert item.user_id == "user_001"
        assert item.item_type == "document"
        assert item.original_data == original_data

    def test_move_file_to_trash(self, trash_service):
        """Test moving a file to trash"""
        original_data = json.dumps({"filename": "test.pdf", "size": 1024})

        item = trash_service.move_to_trash(
            user_id="user_001",
            vault_type="real",
            item_type="file",
            item_id="file_001",
            item_name="test.pdf",
            original_data=original_data
        )

        assert item.item_type == "file"
        assert item.item_id == "file_001"

    def test_move_folder_to_trash(self, trash_service):
        """Test moving a folder to trash"""
        original_data = json.dumps({"name": "My Folder", "parent_id": None})

        item = trash_service.move_to_trash(
            user_id="user_001",
            vault_type="real",
            item_type="folder",
            item_id="folder_001",
            item_name="My Folder",
            original_data=original_data
        )

        assert item.item_type == "folder"

    def test_trash_item_has_correct_expiry(self, trash_service):
        """Test trash item has 30-day expiry"""
        item = trash_service.move_to_trash(
            user_id="user_001",
            vault_type="real",
            item_type="document",
            item_id="doc_001",
            item_name="Test",
            original_data="{}"
        )

        deleted = datetime.fromisoformat(item.deleted_at)
        permanent = datetime.fromisoformat(item.permanent_delete_at)

        # Should be approximately 30 days apart
        delta = permanent - deleted
        assert delta.days == 30

    def test_move_to_decoy_vault_trash(self, trash_service):
        """Test moving item to decoy vault trash"""
        item = trash_service.move_to_trash(
            user_id="user_001",
            vault_type="decoy",
            item_type="document",
            item_id="doc_001",
            item_name="Decoy Doc",
            original_data="{}"
        )

        assert item.vault_type == "decoy"


class TestGetTrashItems:
    """Tests for get_trash_items functionality"""

    def test_get_empty_trash(self, trash_service):
        """Test getting items from empty trash"""
        items = trash_service.get_trash_items(
            user_id="user_001",
            vault_type="real"
        )

        assert items == []

    def test_get_trash_items(self, trash_service):
        """Test getting trash items"""
        # Add items
        trash_service.move_to_trash("user_001", "real", "document", "doc_001", "Doc 1", "{}")
        trash_service.move_to_trash("user_001", "real", "file", "file_001", "File 1", "{}")

        items = trash_service.get_trash_items(
            user_id="user_001",
            vault_type="real"
        )

        assert len(items) == 2

    def test_get_trash_items_filtered_by_type(self, trash_service):
        """Test getting trash items filtered by type"""
        trash_service.move_to_trash("user_001", "real", "document", "doc_001", "Doc 1", "{}")
        trash_service.move_to_trash("user_001", "real", "file", "file_001", "File 1", "{}")

        items = trash_service.get_trash_items(
            user_id="user_001",
            vault_type="real",
            item_type="document"
        )

        assert len(items) == 1
        assert items[0].item_type == "document"

    def test_get_trash_items_separate_vaults(self, trash_service):
        """Test trash items are separate between real and decoy vaults"""
        trash_service.move_to_trash("user_001", "real", "document", "doc_001", "Real Doc", "{}")
        trash_service.move_to_trash("user_001", "decoy", "document", "doc_002", "Decoy Doc", "{}")

        real_items = trash_service.get_trash_items("user_001", "real")
        decoy_items = trash_service.get_trash_items("user_001", "decoy")

        assert len(real_items) == 1
        assert len(decoy_items) == 1
        assert real_items[0].vault_type == "real"
        assert decoy_items[0].vault_type == "decoy"


class TestPermanentDelete:
    """Tests for permanently_delete functionality"""

    def test_permanently_delete_existing(self, trash_service):
        """Test permanently deleting an existing trash item"""
        trash_service.move_to_trash("user_001", "real", "document", "doc_001", "Doc", "{}")

        result = trash_service.permanently_delete(
            trash_id="trash_doc_001",
            user_id="user_001",
            vault_type="real"
        )

        assert result is True

        # Verify item is gone
        items = trash_service.get_trash_items("user_001", "real")
        assert len(items) == 0

    def test_permanently_delete_nonexistent(self, trash_service):
        """Test permanently deleting a nonexistent item"""
        result = trash_service.permanently_delete(
            trash_id="trash_nonexistent",
            user_id="user_001",
            vault_type="real"
        )

        assert result is False


class TestEmptyTrash:
    """Tests for empty_trash functionality"""

    def test_empty_trash(self, trash_service):
        """Test emptying all trash"""
        trash_service.move_to_trash("user_001", "real", "document", "doc_001", "Doc 1", "{}")
        trash_service.move_to_trash("user_001", "real", "file", "file_001", "File 1", "{}")

        count = trash_service.empty_trash(user_id="user_001", vault_type="real")

        assert count == 2

        items = trash_service.get_trash_items("user_001", "real")
        assert len(items) == 0

    def test_empty_trash_empty(self, trash_service):
        """Test emptying already empty trash"""
        count = trash_service.empty_trash(user_id="user_001", vault_type="real")

        assert count == 0


class TestCleanupExpired:
    """Tests for cleanup_expired functionality"""

    def test_cleanup_expired_removes_old_items(self, trash_service):
        """Test cleanup removes expired items"""
        import sqlite3

        # Manually insert an expired item
        expired_date = (datetime.now(UTC) - timedelta(days=31)).isoformat()

        with sqlite3.connect(trash_service.db_path) as conn:
            conn.execute("""
                INSERT INTO vault_trash
                (id, user_id, vault_type, item_type, item_id, item_name,
                 deleted_at, permanent_delete_at, original_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "trash_expired",
                "user_001",
                "real",
                "document",
                "doc_expired",
                "Expired Doc",
                expired_date,
                expired_date,  # Already past
                "{}"
            ))
            conn.commit()

        count = trash_service.cleanup_expired()

        assert count >= 1

    def test_cleanup_expired_keeps_valid_items(self, trash_service):
        """Test cleanup keeps non-expired items"""
        trash_service.move_to_trash("user_001", "real", "document", "doc_001", "Doc", "{}")

        count = trash_service.cleanup_expired()

        # New item shouldn't be expired
        items = trash_service.get_trash_items("user_001", "real")
        assert len(items) == 1


class TestGetStats:
    """Tests for get_stats functionality"""

    def test_get_stats_empty(self, trash_service):
        """Test getting stats from empty trash"""
        stats = trash_service.get_stats(user_id="user_001", vault_type="real")

        assert stats.total_items == 0
        assert stats.document_count == 0
        assert stats.file_count == 0
        assert stats.folder_count == 0

    def test_get_stats_with_items(self, trash_service):
        """Test getting stats with items"""
        trash_service.move_to_trash("user_001", "real", "document", "doc_001", "Doc 1", "{}")
        trash_service.move_to_trash("user_001", "real", "document", "doc_002", "Doc 2", "{}")
        trash_service.move_to_trash("user_001", "real", "file", "file_001", "File 1", "{}")

        stats = trash_service.get_stats(user_id="user_001", vault_type="real")

        assert stats.total_items == 3
        assert stats.document_count == 2
        assert stats.file_count == 1
        assert stats.folder_count == 0


class TestCalculateItemSize:
    """Tests for _calculate_item_size functionality"""

    def test_calculate_file_size(self, trash_service):
        """Test calculating file size"""
        original_data = json.dumps({"size": 1024, "filename": "test.pdf"})

        size = trash_service._calculate_item_size("file", original_data)

        assert size == 1024

    def test_calculate_file_size_bytes_key(self, trash_service):
        """Test calculating file size with size_bytes key"""
        original_data = json.dumps({"size_bytes": 2048, "filename": "test.pdf"})

        size = trash_service._calculate_item_size("file", original_data)

        assert size == 2048

    def test_calculate_document_size(self, trash_service):
        """Test calculating document size from content"""
        content = "Hello, World!"
        original_data = json.dumps({"content": content})

        size = trash_service._calculate_item_size("document", original_data)

        assert size == len(content.encode('utf-8'))

    def test_calculate_folder_size(self, trash_service):
        """Test calculating folder size (always 0)"""
        original_data = json.dumps({"name": "My Folder"})

        size = trash_service._calculate_item_size("folder", original_data)

        assert size == 0

    def test_calculate_size_invalid_json(self, trash_service):
        """Test calculating size with invalid JSON"""
        size = trash_service._calculate_item_size("file", "not valid json")

        assert size == 0

    def test_calculate_size_missing_fields(self, trash_service):
        """Test calculating size with missing fields"""
        original_data = json.dumps({"other_field": "value"})

        size = trash_service._calculate_item_size("file", original_data)

        assert size == 0
