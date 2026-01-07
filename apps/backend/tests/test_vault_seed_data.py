"""
Comprehensive tests for Vault Seed Data Service

Tests cover:
- DecoyVaultSeeder initialization
- Seeding decoy vault with realistic documents
- Idempotent seeding (already seeded check)
- Timestamp generation
- Clearing decoy vault
- DECOY_DOCUMENTS constant structure
- get_seeder helper function
"""

import pytest
import sqlite3
import base64
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


class TestDecoyVaultSeederInit:
    """Tests for DecoyVaultSeeder initialization"""

    def test_init_sets_db_path(self, tmp_path):
        """Test initialization sets db_path from config"""
        mock_paths = Mock()
        mock_paths.data_dir = tmp_path

        with patch('api.vault_seed_data.PATHS', mock_paths):
            with patch('api.vault_seed_data.VAULT_DB_PATH', tmp_path / "vault.db"):
                from api.vault_seed_data import DecoyVaultSeeder
                seeder = DecoyVaultSeeder()

                assert seeder.db_path == tmp_path / "vault.db"


class TestSeedDecoyVault:
    """Tests for seed_decoy_vault method"""

    @pytest.fixture
    def db_path(self, tmp_path):
        """Create test database with vault_documents table"""
        db_path = tmp_path / "test_vault.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE vault_documents (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                vault_type TEXT,
                encrypted_blob TEXT,
                encrypted_metadata TEXT,
                created_at TEXT,
                updated_at TEXT,
                size_bytes INTEGER
            )
        """)
        conn.commit()
        conn.close()

        return db_path

    @pytest.fixture
    def seeder(self, db_path):
        """Create seeder with test database"""
        with patch('api.vault_seed_data.VAULT_DB_PATH', db_path):
            from api.vault_seed_data import DecoyVaultSeeder
            seeder = DecoyVaultSeeder()
            seeder.db_path = db_path
            return seeder

    def test_seed_decoy_vault_success(self, seeder, db_path):
        """Test seeding creates documents"""
        result = seeder.seed_decoy_vault("user_123")

        assert result['status'] == 'success'
        assert result['document_count'] > 0
        assert 'documents' in result
        assert len(result['documents']) > 0

        # Verify documents in database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM vault_documents
            WHERE user_id = ? AND vault_type = 'decoy'
        """, ("user_123",))
        count = cursor.fetchone()[0]
        conn.close()

        assert count == result['document_count']

    def test_seed_decoy_vault_already_seeded(self, seeder, db_path):
        """Test seeding is idempotent"""
        # Seed first time
        result1 = seeder.seed_decoy_vault("user_456")
        assert result1['status'] == 'success'
        count1 = result1['document_count']

        # Seed second time
        result2 = seeder.seed_decoy_vault("user_456")
        assert result2['status'] == 'already_seeded'
        assert result2['document_count'] == count1
        assert "already contains documents" in result2['message']

    def test_seed_decoy_vault_creates_valid_documents(self, seeder, db_path):
        """Test seeded documents have valid structure"""
        result = seeder.seed_decoy_vault("user_789")

        # Check each document
        for doc in result['documents']:
            assert 'id' in doc
            assert 'name' in doc
            assert 'type' in doc

        # Verify database records
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, encrypted_blob, encrypted_metadata, created_at, size_bytes
            FROM vault_documents WHERE user_id = ?
        """, ("user_789",))
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            doc_id, blob, metadata, created_at, size = row
            # Blob should be base64 decodable
            decoded_blob = base64.b64decode(blob)
            assert len(decoded_blob) > 0
            # Metadata should be base64 decodable
            decoded_meta = base64.b64decode(metadata)
            assert len(decoded_meta) > 0
            # Size should be positive
            assert size > 0
            # Created_at should be ISO format
            datetime.fromisoformat(created_at.replace('Z', '+00:00'))

    def test_seed_decoy_vault_different_users(self, seeder, db_path):
        """Test seeding works for different users"""
        result1 = seeder.seed_decoy_vault("user_A")
        result2 = seeder.seed_decoy_vault("user_B")

        assert result1['status'] == 'success'
        assert result2['status'] == 'success'

        # Both should have same number of documents (from DECOY_DOCUMENTS)
        assert result1['document_count'] == result2['document_count']

        # Verify both users have documents
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM vault_documents WHERE user_id = 'user_A'")
        count_a = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM vault_documents WHERE user_id = 'user_B'")
        count_b = cursor.fetchone()[0]

        conn.close()

        assert count_a > 0
        assert count_b > 0

    def test_seed_decoy_vault_document_types(self, seeder, db_path):
        """Test all seeded documents are text type"""
        result = seeder.seed_decoy_vault("user_types")

        for doc in result['documents']:
            assert doc['type'] == 'text'

    def test_seed_decoy_vault_unique_ids(self, seeder, db_path):
        """Test all document IDs are unique UUIDs"""
        result = seeder.seed_decoy_vault("user_uuid")

        ids = [doc['id'] for doc in result['documents']]
        assert len(ids) == len(set(ids))  # All unique

        # Verify UUID format
        import uuid
        for doc_id in ids:
            uuid.UUID(doc_id)  # Raises if invalid


class TestGenerateRealisticTimestamp:
    """Tests for _generate_realistic_timestamp method"""

    @pytest.fixture
    def seeder(self, tmp_path):
        """Create seeder instance"""
        db_path = tmp_path / "vault.db"
        with patch('api.vault_seed_data.VAULT_DB_PATH', db_path):
            from api.vault_seed_data import DecoyVaultSeeder
            return DecoyVaultSeeder()

    def test_timestamp_is_iso_format(self, seeder):
        """Test timestamp is valid ISO format"""
        ts = seeder._generate_realistic_timestamp()

        # Should be parseable
        parsed = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        assert parsed is not None

    def test_timestamp_is_in_past(self, seeder):
        """Test timestamp is in the past"""
        ts = seeder._generate_realistic_timestamp()
        parsed = datetime.fromisoformat(ts.replace('Z', '+00:00'))

        # Should be before now
        now = datetime.now(UTC)
        assert parsed < now

    def test_timestamp_within_180_days(self, seeder):
        """Test timestamp is within 180 days of now"""
        ts = seeder._generate_realistic_timestamp()
        parsed = datetime.fromisoformat(ts.replace('Z', '+00:00'))

        now = datetime.now(UTC)
        days_ago = (now - parsed).days

        assert 0 <= days_ago <= 180

    def test_timestamps_vary(self, seeder):
        """Test multiple timestamps are different (randomized)"""
        timestamps = [seeder._generate_realistic_timestamp() for _ in range(10)]

        # Not all should be identical (random distribution)
        unique_timestamps = set(timestamps)
        # With 10 samples, we expect at least 2 different values
        assert len(unique_timestamps) >= 2


class TestClearDecoyVault:
    """Tests for clear_decoy_vault method"""

    @pytest.fixture
    def db_path(self, tmp_path):
        """Create test database with vault_documents table"""
        db_path = tmp_path / "test_vault.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE vault_documents (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                vault_type TEXT,
                encrypted_blob TEXT,
                encrypted_metadata TEXT,
                created_at TEXT,
                updated_at TEXT,
                size_bytes INTEGER
            )
        """)
        conn.commit()
        conn.close()

        return db_path

    @pytest.fixture
    def seeder(self, db_path):
        """Create seeder with test database"""
        with patch('api.vault_seed_data.VAULT_DB_PATH', db_path):
            from api.vault_seed_data import DecoyVaultSeeder
            seeder = DecoyVaultSeeder()
            seeder.db_path = db_path
            return seeder

    def test_clear_decoy_vault_success(self, seeder, db_path):
        """Test clearing removes all decoy documents"""
        # First seed
        seeder.seed_decoy_vault("user_clear")

        # Verify seeded
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM vault_documents WHERE user_id = 'user_clear'")
        count_before = cursor.fetchone()[0]
        conn.close()
        assert count_before > 0

        # Clear
        result = seeder.clear_decoy_vault("user_clear")

        assert result['status'] == 'success'
        assert result['deleted_count'] == count_before
        assert "Cleared" in result['message']

        # Verify cleared
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM vault_documents WHERE user_id = 'user_clear'")
        count_after = cursor.fetchone()[0]
        conn.close()
        assert count_after == 0

    def test_clear_decoy_vault_empty(self, seeder, db_path):
        """Test clearing empty vault returns zero"""
        result = seeder.clear_decoy_vault("nonexistent_user")

        assert result['status'] == 'success'
        assert result['deleted_count'] == 0

    def test_clear_only_decoy_documents(self, seeder, db_path):
        """Test clear only removes decoy documents, not real ones"""
        # Add a real document manually
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO vault_documents
            (id, user_id, vault_type, encrypted_blob, encrypted_metadata, created_at, updated_at, size_bytes)
            VALUES ('real_doc_1', 'user_mixed', 'real', 'blob', 'meta', '2025-01-01', '2025-01-01', 100)
        """)
        conn.commit()
        conn.close()

        # Seed decoy documents
        seeder.seed_decoy_vault("user_mixed")

        # Verify both types exist
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM vault_documents WHERE user_id = 'user_mixed' AND vault_type = 'real'")
        real_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM vault_documents WHERE user_id = 'user_mixed' AND vault_type = 'decoy'")
        decoy_count = cursor.fetchone()[0]
        conn.close()

        assert real_count == 1
        assert decoy_count > 0

        # Clear decoy vault
        seeder.clear_decoy_vault("user_mixed")

        # Verify only decoy removed
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM vault_documents WHERE user_id = 'user_mixed' AND vault_type = 'real'")
        real_after = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM vault_documents WHERE user_id = 'user_mixed' AND vault_type = 'decoy'")
        decoy_after = cursor.fetchone()[0]
        conn.close()

        assert real_after == 1  # Real doc preserved
        assert decoy_after == 0  # Decoy cleared

    def test_clear_different_users_independent(self, seeder, db_path):
        """Test clearing one user doesn't affect another"""
        # Seed both users
        seeder.seed_decoy_vault("user_X")
        seeder.seed_decoy_vault("user_Y")

        # Clear only user_X
        seeder.clear_decoy_vault("user_X")

        # Verify user_Y still has documents
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM vault_documents WHERE user_id = 'user_Y' AND vault_type = 'decoy'")
        count_y = cursor.fetchone()[0]
        conn.close()

        assert count_y > 0


class TestDecoyDocuments:
    """Tests for DECOY_DOCUMENTS constant"""

    def test_decoy_documents_not_empty(self):
        """Test DECOY_DOCUMENTS is populated"""
        from api.vault_seed_data import DECOY_DOCUMENTS

        assert len(DECOY_DOCUMENTS) > 0

    def test_decoy_documents_have_required_fields(self):
        """Test each decoy document has required fields"""
        from api.vault_seed_data import DECOY_DOCUMENTS

        for doc in DECOY_DOCUMENTS:
            assert 'name' in doc
            assert 'type' in doc
            assert 'content' in doc
            assert isinstance(doc['name'], str)
            assert isinstance(doc['type'], str)
            assert isinstance(doc['content'], str)

    def test_decoy_documents_have_content(self):
        """Test each decoy document has non-empty content"""
        from api.vault_seed_data import DECOY_DOCUMENTS

        for doc in DECOY_DOCUMENTS:
            assert len(doc['content']) > 0
            assert len(doc['name']) > 0

    def test_decoy_documents_realistic_names(self):
        """Test decoy document names look realistic"""
        from api.vault_seed_data import DECOY_DOCUMENTS

        # Should have various realistic file names
        names = [doc['name'] for doc in DECOY_DOCUMENTS]

        # Check for common patterns
        assert any('Budget' in name for name in names)
        assert any('Password' in name or 'WiFi' in name for name in names)

    def test_decoy_documents_count(self):
        """Test there are at least 5 decoy documents"""
        from api.vault_seed_data import DECOY_DOCUMENTS

        assert len(DECOY_DOCUMENTS) >= 5

    def test_decoy_documents_all_text_type(self):
        """Test all decoy documents are text type"""
        from api.vault_seed_data import DECOY_DOCUMENTS

        for doc in DECOY_DOCUMENTS:
            assert doc['type'] == 'text'


class TestGetSeeder:
    """Tests for get_seeder helper function"""

    def test_get_seeder_returns_instance(self, tmp_path):
        """Test get_seeder returns DecoyVaultSeeder instance"""
        db_path = tmp_path / "vault.db"
        with patch('api.vault_seed_data.VAULT_DB_PATH', db_path):
            from api.vault_seed_data import get_seeder, DecoyVaultSeeder

            seeder = get_seeder()

            assert isinstance(seeder, DecoyVaultSeeder)

    def test_get_seeder_returns_new_instances(self, tmp_path):
        """Test get_seeder returns new instance each call (not singleton)"""
        db_path = tmp_path / "vault.db"
        with patch('api.vault_seed_data.VAULT_DB_PATH', db_path):
            from api.vault_seed_data import get_seeder

            seeder1 = get_seeder()
            seeder2 = get_seeder()

            # Each call creates new instance
            assert seeder1 is not seeder2


class TestEdgeCases:
    """Tests for edge cases"""

    @pytest.fixture
    def db_path(self, tmp_path):
        """Create test database"""
        db_path = tmp_path / "test_vault.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE vault_documents (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                vault_type TEXT,
                encrypted_blob TEXT,
                encrypted_metadata TEXT,
                created_at TEXT,
                updated_at TEXT,
                size_bytes INTEGER
            )
        """)
        conn.commit()
        conn.close()
        return db_path

    @pytest.fixture
    def seeder(self, db_path):
        """Create seeder with test database"""
        with patch('api.vault_seed_data.VAULT_DB_PATH', db_path):
            from api.vault_seed_data import DecoyVaultSeeder
            seeder = DecoyVaultSeeder()
            seeder.db_path = db_path
            return seeder

    def test_empty_user_id(self, seeder, db_path):
        """Test seeding with empty user ID"""
        result = seeder.seed_decoy_vault("")

        # Should still work (empty string is valid user_id)
        assert result['status'] == 'success'

    def test_unicode_user_id(self, seeder, db_path):
        """Test seeding with unicode user ID"""
        result = seeder.seed_decoy_vault("用户_123")

        assert result['status'] == 'success'
        assert result['document_count'] > 0

    def test_special_chars_user_id(self, seeder, db_path):
        """Test seeding with special characters in user ID"""
        result = seeder.seed_decoy_vault("user@domain.com")

        assert result['status'] == 'success'

    def test_very_long_user_id(self, seeder, db_path):
        """Test seeding with very long user ID"""
        long_user_id = "u" * 500
        result = seeder.seed_decoy_vault(long_user_id)

        assert result['status'] == 'success'

    def test_seed_then_clear_then_seed(self, seeder, db_path):
        """Test seed -> clear -> seed cycle"""
        # First seed
        result1 = seeder.seed_decoy_vault("cycle_user")
        assert result1['status'] == 'success'
        count1 = result1['document_count']

        # Clear
        clear_result = seeder.clear_decoy_vault("cycle_user")
        assert clear_result['deleted_count'] == count1

        # Seed again
        result2 = seeder.seed_decoy_vault("cycle_user")
        assert result2['status'] == 'success'
        assert result2['document_count'] == count1


class TestBase64Encoding:
    """Tests for base64 encoding of content"""

    @pytest.fixture
    def db_path(self, tmp_path):
        """Create test database"""
        db_path = tmp_path / "test_vault.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE vault_documents (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                vault_type TEXT,
                encrypted_blob TEXT,
                encrypted_metadata TEXT,
                created_at TEXT,
                updated_at TEXT,
                size_bytes INTEGER
            )
        """)
        conn.commit()
        conn.close()
        return db_path

    @pytest.fixture
    def seeder(self, db_path):
        """Create seeder with test database"""
        with patch('api.vault_seed_data.VAULT_DB_PATH', db_path):
            from api.vault_seed_data import DecoyVaultSeeder
            seeder = DecoyVaultSeeder()
            seeder.db_path = db_path
            return seeder

    def test_content_is_base64_encoded(self, seeder, db_path):
        """Test document content is base64 encoded"""
        from api.vault_seed_data import DECOY_DOCUMENTS

        seeder.seed_decoy_vault("base64_user")

        # Get first document from database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT encrypted_blob FROM vault_documents
            WHERE user_id = 'base64_user' LIMIT 1
        """)
        blob = cursor.fetchone()[0]
        conn.close()

        # Decode should work
        decoded = base64.b64decode(blob).decode('utf-8')

        # Decoded content should match one of the DECOY_DOCUMENTS
        contents = [doc['content'] for doc in DECOY_DOCUMENTS]
        assert decoded in contents

    def test_metadata_is_base64_encoded(self, seeder, db_path):
        """Test document metadata is base64 encoded"""
        seeder.seed_decoy_vault("meta_user")

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT encrypted_metadata FROM vault_documents
            WHERE user_id = 'meta_user' LIMIT 1
        """)
        metadata = cursor.fetchone()[0]
        conn.close()

        # Decode should work
        decoded = base64.b64decode(metadata).decode('utf-8')

        # Should contain expected keys (as stringified dict)
        assert 'filename' in decoded
        assert 'type' in decoded
        assert 'size' in decoded


class TestIntegration:
    """Integration tests"""

    @pytest.fixture
    def db_path(self, tmp_path):
        """Create test database"""
        db_path = tmp_path / "test_vault.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE vault_documents (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                vault_type TEXT,
                encrypted_blob TEXT,
                encrypted_metadata TEXT,
                created_at TEXT,
                updated_at TEXT,
                size_bytes INTEGER
            )
        """)
        conn.commit()
        conn.close()
        return db_path

    def test_full_lifecycle(self, db_path):
        """Test complete seed -> verify -> clear lifecycle"""
        with patch('api.vault_seed_data.VAULT_DB_PATH', db_path):
            from api.vault_seed_data import DecoyVaultSeeder, DECOY_DOCUMENTS

            seeder = DecoyVaultSeeder()
            seeder.db_path = db_path

            # 1. Seed
            seed_result = seeder.seed_decoy_vault("lifecycle_user")
            assert seed_result['status'] == 'success'
            assert seed_result['document_count'] == len(DECOY_DOCUMENTS)

            # 2. Verify idempotent
            seed_result2 = seeder.seed_decoy_vault("lifecycle_user")
            assert seed_result2['status'] == 'already_seeded'

            # 3. Clear
            clear_result = seeder.clear_decoy_vault("lifecycle_user")
            assert clear_result['deleted_count'] == len(DECOY_DOCUMENTS)

            # 4. Can reseed
            seed_result3 = seeder.seed_decoy_vault("lifecycle_user")
            assert seed_result3['status'] == 'success'

    def test_multi_user_isolation(self, db_path):
        """Test multiple users are properly isolated"""
        with patch('api.vault_seed_data.VAULT_DB_PATH', db_path):
            from api.vault_seed_data import DecoyVaultSeeder

            seeder = DecoyVaultSeeder()
            seeder.db_path = db_path

            # Seed multiple users
            users = ['alice', 'bob', 'charlie']
            for user in users:
                result = seeder.seed_decoy_vault(user)
                assert result['status'] == 'success'

            # Clear one user
            seeder.clear_decoy_vault('bob')

            # Verify others still have documents
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            for user in users:
                cursor.execute("""
                    SELECT COUNT(*) FROM vault_documents
                    WHERE user_id = ? AND vault_type = 'decoy'
                """, (user,))
                count = cursor.fetchone()[0]

                if user == 'bob':
                    assert count == 0
                else:
                    assert count > 0

            conn.close()
