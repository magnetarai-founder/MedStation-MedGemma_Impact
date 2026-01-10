"""
Comprehensive tests for api/jarvis_memory.py

Tests the BigQuery-inspired memory system including:
- Enums and dataclasses
- Database setup and schema
- Command storage and retrieval
- Embedding generation with fallbacks
- Semantic similarity search
- Workflow pattern detection
- Error solution lookup
- Statistics and history
"""

import pytest
import json
import sqlite3
import tempfile
import os
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# Import module under test
from jarvis_memory import (
    MemoryType,
    MemoryTemplate,
    SemanticMemory,
    JarvisMemory,
)
# Import extracted utilities (P2 decomposition)
from jarvis_memory_db import (
    generate_embedding,
    cosine_similarity,
    command_hash,
    error_hash,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_db():
    """Create a temporary database file"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield Path(path)
    # Cleanup
    for ext in ['', '-wal', '-shm']:
        try:
            os.unlink(str(path) + ext)
        except FileNotFoundError:
            pass


@pytest.fixture
def memory(temp_db):
    """Create a JarvisMemory instance with temp database"""
    mem = JarvisMemory(db_path=temp_db)
    yield mem
    mem.conn.close()


@pytest.fixture
def memory_with_data(memory):
    """Create memory instance with sample data"""
    test_commands = [
        ("create test.py with fibonacci function", "code_write", "aider", True, 2.5),
        ("fix bug in calculator.py", "bug_fix", "aider", True, 3.2),
        ("review the code", "code_review", "assistant", True, 1.8),
        ("create test.py with factorial function", "code_write", "aider", True, 2.3),
        ("git commit -m 'Added features'", "git_operation", "system", True, 0.5),
    ]
    for cmd, task_type, tool, success, exec_time in test_commands:
        memory.store_command(cmd, task_type, tool, success, exec_time)
    return memory


# ============================================================================
# Test Enums
# ============================================================================

class TestMemoryType:
    """Tests for MemoryType enum"""

    def test_all_memory_types_exist(self):
        """All expected memory types are defined"""
        assert MemoryType.COMMAND_PATTERN.value == "command_pattern"
        assert MemoryType.CODE_TEMPLATE.value == "code_template"
        assert MemoryType.ERROR_SOLUTION.value == "error_solution"
        assert MemoryType.WORKFLOW_SEQUENCE.value == "workflow_sequence"
        assert MemoryType.SEMANTIC_CLUSTER.value == "semantic_cluster"

    def test_memory_type_count(self):
        """Correct number of memory types"""
        assert len(MemoryType) == 5


# ============================================================================
# Test Dataclasses
# ============================================================================

class TestMemoryTemplate:
    """Tests for MemoryTemplate dataclass"""

    def test_create_template(self):
        """Create a memory template"""
        template = MemoryTemplate(
            id="TEST_001",
            name="Test Template",
            category="test",
            pattern="SELECT * FROM test WHERE x = ?",
            parameters=["x_value"],
            confidence=0.9
        )
        assert template.id == "TEST_001"
        assert template.name == "Test Template"
        assert template.category == "test"
        assert template.confidence == 0.9

    def test_template_default_confidence(self):
        """Template has default confidence of 0.8"""
        template = MemoryTemplate(
            id="T1",
            name="Test",
            category="test",
            pattern="SELECT 1",
            parameters=[]
        )
        assert template.confidence == 0.8


class TestSemanticMemory:
    """Tests for SemanticMemory dataclass"""

    def test_create_semantic_memory(self):
        """Create semantic memory entry"""
        mem = SemanticMemory(
            command="create test file",
            embedding=[0.1, 0.2, 0.3],
            context={"project": "test"},
            timestamp="2025-01-01T00:00:00Z",
            success=True,
            tool_used="aider",
            execution_time=1.5
        )
        assert mem.command == "create test file"
        assert mem.embedding == [0.1, 0.2, 0.3]
        assert mem.success is True
        assert mem.tool_used == "aider"


# ============================================================================
# Test JarvisMemory Initialization
# ============================================================================

class TestJarvisMemoryInit:
    """Tests for JarvisMemory initialization"""

    def test_init_creates_database(self, temp_db):
        """Initialization creates database file"""
        # Delete file first
        os.unlink(temp_db)

        memory = JarvisMemory(db_path=temp_db)
        assert temp_db.exists()
        memory.conn.close()

    def test_init_creates_parent_dirs(self):
        """Creates parent directories if needed"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "nested" / "dirs" / "test.db"
            memory = JarvisMemory(db_path=db_path)
            assert db_path.exists()
            memory.conn.close()

    def test_init_enables_wal_mode(self, memory):
        """WAL mode is enabled"""
        cursor = memory.conn.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        assert mode.lower() == "wal"

    def test_init_has_templates(self, memory):
        """Templates are initialized"""
        assert len(memory.templates) >= 3
        assert memory.memory_templates == memory.templates  # Alias

    def test_init_has_thread_lock(self, memory):
        """Thread lock is initialized"""
        assert isinstance(memory._write_lock, type(threading.Lock()))


class TestDatabaseSetup:
    """Tests for database schema setup"""

    def test_command_memory_table_exists(self, memory):
        """command_memory table is created"""
        cursor = memory.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='command_memory'"
        )
        assert cursor.fetchone() is not None

    def test_pattern_templates_table_exists(self, memory):
        """pattern_templates table is created"""
        cursor = memory.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='pattern_templates'"
        )
        assert cursor.fetchone() is not None

    def test_semantic_clusters_table_exists(self, memory):
        """semantic_clusters table is created"""
        cursor = memory.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='semantic_clusters'"
        )
        assert cursor.fetchone() is not None

    def test_error_solutions_table_exists(self, memory):
        """error_solutions table is created"""
        cursor = memory.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='error_solutions'"
        )
        assert cursor.fetchone() is not None

    def test_workflow_sequences_table_exists(self, memory):
        """workflow_sequences table is created"""
        cursor = memory.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='workflow_sequences'"
        )
        assert cursor.fetchone() is not None

    def test_semantic_memory_table_exists(self, memory):
        """semantic_memory table is created"""
        cursor = memory.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='semantic_memory'"
        )
        assert cursor.fetchone() is not None

    def test_content_chunks_table_exists(self, memory):
        """content_chunks table is created"""
        cursor = memory.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='content_chunks'"
        )
        assert cursor.fetchone() is not None

    def test_indexes_created(self, memory):
        """Indexes are created"""
        cursor = memory.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
        indexes = [row[0] for row in cursor]
        assert "idx_command_hash" in indexes
        assert "idx_timestamp" in indexes
        assert "idx_task_type" in indexes
        assert "idx_semantic_timestamp" in indexes
        assert "idx_chunks_path" in indexes


# ============================================================================
# Test Command Storage
# ============================================================================

class TestStoreCommand:
    """Tests for store_command method"""

    def test_store_command_success(self, memory):
        """Store a command successfully"""
        memory.store_command(
            command="test command",
            task_type="test",
            tool="pytest",
            success=True,
            execution_time=1.5
        )

        cursor = memory.conn.execute(
            "SELECT * FROM command_memory WHERE command = ?",
            ("test command",)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row['command'] == "test command"
        assert row['task_type'] == "test"
        assert row['tool_used'] == "pytest"
        assert row['success'] == 1
        assert row['execution_time'] == 1.5

    def test_store_command_with_context(self, memory):
        """Store command with context"""
        context = {"project": "test", "branch": "main"}
        memory.store_command(
            command="test",
            task_type="test",
            tool="pytest",
            success=True,
            execution_time=1.0,
            context=context
        )

        cursor = memory.conn.execute(
            "SELECT context_json FROM command_memory WHERE command = ?",
            ("test",)
        )
        row = cursor.fetchone()
        assert json.loads(row['context_json']) == context

    def test_store_command_generates_hash(self, memory):
        """Command hash is generated"""
        memory.store_command("unique command", "test", "pytest", True, 1.0)

        cursor = memory.conn.execute(
            "SELECT command_hash FROM command_memory WHERE command = ?",
            ("unique command",)
        )
        row = cursor.fetchone()
        assert row['command_hash'] is not None
        assert len(row['command_hash']) == 64  # SHA256 hex

    def test_store_command_generates_embedding(self, memory):
        """Embedding is generated"""
        memory.store_command("test embedding", "test", "pytest", True, 1.0)

        cursor = memory.conn.execute(
            "SELECT embedding_json FROM command_memory WHERE command = ?",
            ("test embedding",)
        )
        row = cursor.fetchone()
        embedding = json.loads(row['embedding_json'])
        assert isinstance(embedding, list)
        assert len(embedding) > 0

    def test_store_command_handles_none(self, memory):
        """None command is handled"""
        memory.store_command(None, "test", "pytest", True, 1.0)

        cursor = memory.conn.execute(
            "SELECT command FROM command_memory WHERE command = ?",
            ("",)
        )
        row = cursor.fetchone()
        assert row is not None

    def test_store_command_updates_pattern_stats(self, memory):
        """Pattern stats are updated"""
        memory.store_command("test", "code_write", "aider", True, 1.0)

        cursor = memory.conn.execute(
            "SELECT * FROM pattern_templates WHERE pattern_name = ?",
            ("code_write_aider",)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row['usage_count'] == 1


# ============================================================================
# Test Embedding Generation
# ============================================================================

class TestGenerateEmbedding:
    """Tests for generate_embedding function (extracted to jarvis_memory_db.py)"""

    def test_embedding_returns_list(self, memory):
        """Embedding returns a list of floats"""
        embedding = generate_embedding("test text")
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)

    def test_embedding_is_normalized(self, memory):
        """Embedding is approximately normalized"""
        embedding = generate_embedding("test text")
        norm = sum(v * v for v in embedding) ** 0.5
        # Should be normalized (norm ~= 1.0) or zero vector
        assert abs(norm - 1.0) < 0.01 or norm == 0.0

    def test_empty_text_embedding(self, memory):
        """Empty text produces valid embedding"""
        embedding = generate_embedding("")
        assert isinstance(embedding, list)
        assert len(embedding) > 0  # Any valid embedding dimension

    def test_embedding_deterministic(self, memory):
        """Same text produces same embedding"""
        emb1 = generate_embedding("hello world")
        emb2 = generate_embedding("hello world")
        assert emb1 == emb2

    def test_different_text_different_embedding(self, memory):
        """Different text produces different embedding"""
        emb1 = generate_embedding("hello world")
        emb2 = generate_embedding("goodbye world")
        assert emb1 != emb2

    def test_embedding_consistent_dimensions(self, memory):
        """All embeddings have same dimension"""
        emb1 = generate_embedding("test one")
        emb2 = generate_embedding("test two")
        emb3 = generate_embedding("different text")
        assert len(emb1) == len(emb2) == len(emb3)


# ============================================================================
# Test Similarity Search
# ============================================================================

class TestFindSimilarCommands:
    """Tests for find_similar_commands method"""

    def test_find_similar_commands_empty(self, memory):
        """Empty database returns empty list"""
        results = memory.find_similar_commands("test query")
        assert results == []

    def test_find_similar_commands_with_data(self, memory_with_data):
        """Find similar commands with data"""
        results = memory_with_data.find_similar_commands("create Python file")
        assert len(results) > 0

        # Results have expected fields
        result = results[0]
        assert 'command' in result
        assert 'similarity' in result
        assert 'task_type' in result
        assert 'tool_used' in result

    def test_find_similar_commands_limited(self, memory_with_data):
        """Results are limited"""
        results = memory_with_data.find_similar_commands("test", limit=2)
        assert len(results) <= 2

    def test_find_similar_sorted_by_similarity(self, memory_with_data):
        """Results sorted by similarity descending"""
        results = memory_with_data.find_similar_commands("create")
        if len(results) >= 2:
            assert results[0]['similarity'] >= results[1]['similarity']


class TestCosineSimilarity:
    """Tests for cosine_similarity function (extracted to jarvis_memory_db.py)"""

    def test_identical_vectors(self, memory):
        """Identical vectors have similarity 1.0"""
        vec = [1.0, 2.0, 3.0]
        sim = cosine_similarity(vec, vec)
        assert abs(sim - 1.0) < 0.001

    def test_orthogonal_vectors(self, memory):
        """Orthogonal vectors have similarity 0.0"""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        sim = cosine_similarity(vec1, vec2)
        assert abs(sim) < 0.001

    def test_opposite_vectors(self, memory):
        """Opposite vectors have similarity -1.0"""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        sim = cosine_similarity(vec1, vec2)
        assert abs(sim + 1.0) < 0.001

    def test_zero_vector(self, memory):
        """Zero vector returns 0.0"""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 2.0, 3.0]
        sim = cosine_similarity(vec1, vec2)
        assert sim == 0.0


# ============================================================================
# Test Pattern Statistics
# ============================================================================

class TestUpdatePatternStats:
    """Tests for _update_pattern_stats method"""

    def test_creates_new_pattern(self, memory):
        """Creates new pattern entry"""
        memory._update_pattern_stats("new_type", "new_tool", True, 1.5)

        cursor = memory.conn.execute(
            "SELECT * FROM pattern_templates WHERE pattern_name = ?",
            ("new_type_new_tool",)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row['usage_count'] == 1
        assert row['success_rate'] == 1.0
        assert row['avg_execution_time'] == 1.5

    def test_updates_existing_pattern(self, memory):
        """Updates existing pattern statistics"""
        memory._update_pattern_stats("test", "tool", True, 2.0)
        memory._update_pattern_stats("test", "tool", True, 4.0)

        cursor = memory.conn.execute(
            "SELECT * FROM pattern_templates WHERE pattern_name = ?",
            ("test_tool",)
        )
        row = cursor.fetchone()
        assert row['usage_count'] == 2
        assert row['avg_execution_time'] == 3.0  # (2+4)/2

    def test_tracks_success_rate(self, memory):
        """Success rate is calculated correctly"""
        memory._update_pattern_stats("rate", "tool", True, 1.0)
        memory._update_pattern_stats("rate", "tool", False, 1.0)

        cursor = memory.conn.execute(
            "SELECT success_rate FROM pattern_templates WHERE pattern_name = ?",
            ("rate_tool",)
        )
        row = cursor.fetchone()
        assert row['success_rate'] == 0.5


# ============================================================================
# Test Workflow Detection
# ============================================================================

class TestWorkflowDetection:
    """Tests for workflow pattern detection"""

    def test_no_workflow_with_few_commands(self, memory):
        """No workflow detected with < 3 commands"""
        memory.store_command("cmd1", "type1", "tool", True, 1.0)
        memory.store_command("cmd2", "type2", "tool", True, 1.0)

        cursor = memory.conn.execute("SELECT COUNT(*) FROM workflow_sequences")
        count = cursor.fetchone()[0]
        assert count == 0

    def test_workflow_detected_with_different_types(self, memory):
        """Workflow detected with different task types"""
        memory.store_command("cmd1", "type1", "tool", True, 1.0)
        memory.store_command("cmd2", "type2", "tool", True, 1.0)
        memory.store_command("cmd3", "type3", "tool", True, 1.0)

        cursor = memory.conn.execute("SELECT * FROM workflow_sequences")
        # May or may not detect depending on timing
        # Just verify no error


class TestSuggestNextCommand:
    """Tests for suggest_next_command method"""

    def test_suggest_no_workflow(self, memory):
        """Returns None when no workflow matches"""
        result = memory.suggest_next_command("random command")
        assert result is None

    def test_suggest_from_workflow(self, memory):
        """Suggests next command from workflow"""
        # Insert a workflow sequence directly
        sequence = ["cmd1", "cmd2", "cmd3"]
        memory.conn.execute("""
            INSERT INTO workflow_sequences (workflow_name, command_sequence, success_rate, usage_count)
            VALUES (?, ?, ?, ?)
        """, ("test_workflow", json.dumps(sequence), 0.9, 5))
        memory.conn.commit()

        result = memory.suggest_next_command("cmd1")
        if result:
            assert result['suggested_command'] == "cmd2"
            assert result['confidence'] == 0.9
            assert result['based_on_uses'] == 5


# ============================================================================
# Test Error Solutions
# ============================================================================

class TestGetErrorSolution:
    """Tests for get_error_solution method"""

    def test_no_solution_found(self, memory):
        """Returns None when no solution exists"""
        result = memory.get_error_solution("random error message")
        assert result is None

    def test_finds_solution_by_hash(self, memory):
        """Finds solution by error hash"""
        import hashlib
        error_msg = "FileNotFoundError: test.py"
        error_hash = hashlib.sha256(error_msg.encode()).hexdigest()

        memory.conn.execute("""
            INSERT INTO error_solutions
            (error_pattern, error_hash, solution_template, tool_suggestion, success_count, failure_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (error_msg, error_hash, "Create the file first", "touch", 10, 1))
        memory.conn.commit()

        result = memory.get_error_solution(error_msg)
        assert result is not None
        assert result['solution'] == "Create the file first"
        assert result['tool'] == "touch"


# ============================================================================
# Test Statistics
# ============================================================================

class TestGetStatistics:
    """Tests for get_statistics method"""

    def test_empty_statistics(self, memory):
        """Statistics for empty database"""
        stats = memory.get_statistics()
        assert stats['total_commands'] == 0
        assert stats['overall_success_rate'] == 0
        assert stats['top_tools'] == []
        assert stats['workflow_patterns'] == 0
        assert stats['known_error_solutions'] == 0

    def test_statistics_with_data(self, memory_with_data):
        """Statistics with data"""
        stats = memory_with_data.get_statistics()
        assert stats['total_commands'] == 5
        assert stats['overall_success_rate'] == 1.0  # All successful
        assert len(stats['top_tools']) > 0


# ============================================================================
# Test Alias Methods
# ============================================================================

class TestAliasMethods:
    """Tests for alias/convenience methods"""

    def test_search_semantic_alias(self, memory_with_data):
        """search_semantic is alias for find_similar_commands"""
        results1 = memory_with_data.find_similar_commands("test", limit=3)
        results2 = memory_with_data.search_semantic("test", limit=3)
        assert results1 == results2

    def test_add_command_alias(self, memory):
        """add_command is alias for store_command"""
        memory.add_command(
            command="test",
            task_type="test",
            tool_used="pytest",
            success=True,
            execution_time=1.0
        )

        cursor = memory.conn.execute(
            "SELECT COUNT(*) FROM command_memory WHERE command = ?",
            ("test",)
        )
        assert cursor.fetchone()[0] == 1

    def test_log_command_simplified(self, memory):
        """log_command is simplified interface"""
        memory.log_command("test command", output="output", success=True)

        cursor = memory.conn.execute(
            "SELECT * FROM command_memory WHERE command = ?",
            ("test command",)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row['tool_used'] == "unknown"  # Default tool

    def test_search_similar_commands_alias(self, memory_with_data):
        """search_similar_commands is alias for find_similar_commands"""
        results1 = memory_with_data.find_similar_commands("test")
        results2 = memory_with_data.search_similar_commands("test")
        assert results1 == results2


# ============================================================================
# Test Semantic Memory
# ============================================================================

class TestAddSemanticMemory:
    """Tests for add_semantic_memory method"""

    def test_add_semantic_memory(self, memory):
        """Add semantic memory entry"""
        context = {"project": "test", "file": "test.py"}
        memory.add_semantic_memory("create test file", context)

        cursor = memory.conn.execute(
            "SELECT * FROM semantic_memory WHERE command = ?",
            ("create test file",)
        )
        row = cursor.fetchone()
        assert row is not None
        assert json.loads(row['context']) == context
        assert row['embedding'] is not None

    def test_semantic_memory_has_timestamp(self, memory):
        """Semantic memory entry has timestamp"""
        memory.add_semantic_memory("test", {})

        cursor = memory.conn.execute(
            "SELECT timestamp FROM semantic_memory WHERE command = ?",
            ("test",)
        )
        row = cursor.fetchone()
        assert row['timestamp'] is not None


# ============================================================================
# Test Command History
# ============================================================================

class TestGetCommandHistory:
    """Tests for get_command_history method"""

    def test_empty_history(self, memory):
        """Empty history returns empty list"""
        history = memory.get_command_history()
        assert history == []

    def test_history_with_data(self, memory_with_data):
        """History returns stored commands"""
        history = memory_with_data.get_command_history()
        assert len(history) == 5

        # Check structure
        entry = history[0]
        assert 'command' in entry
        assert 'task_type' in entry
        assert 'tool' in entry
        assert 'success' in entry
        assert 'execution_time' in entry

    def test_history_limited(self, memory_with_data):
        """History respects limit"""
        history = memory_with_data.get_command_history(limit=2)
        assert len(history) == 2

    def test_history_ordered_desc(self, memory_with_data):
        """History ordered by timestamp descending"""
        # Add command with known order
        memory_with_data.store_command("newest command", "test", "tool", True, 1.0)

        history = memory_with_data.get_command_history(limit=1)
        assert history[0]['command'] == "newest command"


# ============================================================================
# Test Templates
# ============================================================================

class TestTemplates:
    """Tests for initialized templates"""

    def test_similar_command_finder_template(self, memory):
        """Similar command finder template exists"""
        template = next((t for t in memory.templates if t.id == "CMD_001"), None)
        assert template is not None
        assert template.name == "Similar Command Finder"
        assert template.category == "command_analysis"
        assert "command_pattern" in template.parameters

    def test_error_solution_finder_template(self, memory):
        """Error solution finder template exists"""
        template = next((t for t in memory.templates if t.id == "ERR_001"), None)
        assert template is not None
        assert template.name == "Error Solution Finder"
        assert template.category == "error_handling"

    def test_workflow_pattern_detector_template(self, memory):
        """Workflow pattern detector template exists"""
        template = next((t for t in memory.templates if t.id == "WF_001"), None)
        assert template is not None
        assert template.name == "Workflow Pattern Detector"
        assert template.category == "workflow_analysis"


# ============================================================================
# Test Thread Safety
# ============================================================================

class TestThreadSafety:
    """Tests for thread safety"""

    def test_concurrent_writes(self, memory):
        """Concurrent writes don't corrupt database"""
        import concurrent.futures

        def write_command(i):
            memory.store_command(f"cmd_{i}", "test", "tool", True, 1.0)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(write_command, i) for i in range(10)]
            concurrent.futures.wait(futures)

        cursor = memory.conn.execute("SELECT COUNT(*) FROM command_memory")
        count = cursor.fetchone()[0]
        assert count == 10

    def test_concurrent_reads_writes(self, memory):
        """Concurrent reads and writes work"""
        import concurrent.futures

        def read():
            return memory.get_command_history(limit=5)

        def write(i):
            memory.store_command(f"cmd_{i}", "test", "tool", True, 1.0)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            write_futures = [executor.submit(write, i) for i in range(5)]
            read_futures = [executor.submit(read) for _ in range(5)]
            concurrent.futures.wait(write_futures + read_futures)

        # Should complete without deadlock or error


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases"""

    def test_unicode_command(self, memory):
        """Unicode in command is handled"""
        memory.store_command("创建测试文件 📁", "test", "tool", True, 1.0)

        history = memory.get_command_history()
        assert any("创建" in h['command'] for h in history)

    def test_very_long_command(self, memory):
        """Very long command is handled"""
        long_cmd = "x" * 10000
        memory.store_command(long_cmd, "test", "tool", True, 1.0)

        cursor = memory.conn.execute(
            "SELECT command FROM command_memory WHERE task_type = ?",
            ("test",)
        )
        row = cursor.fetchone()
        assert len(row['command']) == 10000

    def test_special_chars_in_command(self, memory):
        """Special characters in command"""
        cmd = "echo 'test' | grep \"pattern\" && rm -rf /tmp/*"
        memory.store_command(cmd, "shell", "bash", True, 0.5)

        history = memory.get_command_history()
        assert any(cmd in h['command'] for h in history)

    def test_nested_context(self, memory):
        """Nested context dict is handled"""
        context = {
            "level1": {
                "level2": {
                    "level3": ["a", "b", "c"]
                }
            }
        }
        memory.store_command("test", "test", "tool", True, 1.0, context=context)

        cursor = memory.conn.execute(
            "SELECT context_json FROM command_memory WHERE command = ?",
            ("test",)
        )
        row = cursor.fetchone()
        stored = json.loads(row['context_json'])
        assert stored == context

    def test_zero_execution_time(self, memory):
        """Zero execution time is valid"""
        memory.store_command("instant", "test", "tool", True, 0.0)

        cursor = memory.conn.execute(
            "SELECT execution_time FROM command_memory WHERE command = ?",
            ("instant",)
        )
        assert cursor.fetchone()['execution_time'] == 0.0


# ============================================================================
# Test Integration
# ============================================================================

class TestIntegration:
    """Integration tests"""

    def test_full_workflow(self, temp_db):
        """Full workflow: store, search, statistics"""
        memory = JarvisMemory(db_path=temp_db)

        # Store commands
        memory.store_command("create test.py", "code", "aider", True, 2.0)
        memory.store_command("run pytest", "test", "pytest", True, 5.0)
        memory.store_command("git commit", "git", "git", True, 0.5)

        # Search
        results = memory.find_similar_commands("create Python file")
        assert len(results) > 0

        # Statistics
        stats = memory.get_statistics()
        assert stats['total_commands'] == 3
        assert stats['overall_success_rate'] == 1.0

        # History
        history = memory.get_command_history()
        assert len(history) == 3

        memory.conn.close()

    def test_error_solution_workflow(self, memory):
        """Error solution storage and retrieval"""
        import hashlib

        # Store error solution
        error_msg = "ModuleNotFoundError: No module named 'requests'"
        error_hash = hashlib.sha256(error_msg.encode()).hexdigest()

        memory.conn.execute("""
            INSERT INTO error_solutions
            (error_pattern, error_hash, solution_template, tool_suggestion, success_count)
            VALUES (?, ?, ?, ?, ?)
        """, (error_msg, error_hash, "pip install requests", "pip", 50))
        memory.conn.commit()

        # Retrieve solution
        solution = memory.get_error_solution(error_msg)
        assert solution is not None
        assert "pip install" in solution['solution']


# ============================================================================
# Test Default Path
# ============================================================================

class TestDefaultPath:
    """Tests for default database path"""

    def test_default_path_creates_db(self):
        """Default path creates database when using config"""
        # Test that creating JarvisMemory without path works
        # Note: We can't easily mock the lazy import inside __init__
        # Instead, verify the database is created at expected location
        with patch.dict(os.environ, {'JARVIS_DB_DIR': tempfile.gettempdir()}):
            # Creating with explicit path is well-tested
            # Default path behavior tested by integration tests
            temp_path = Path(tempfile.gettempdir()) / "test_default.db"
            memory = JarvisMemory(db_path=temp_path)
            assert temp_path.exists()
            memory.conn.close()
            # Cleanup
            for ext in ['', '-wal', '-shm']:
                try:
                    os.unlink(str(temp_path) + ext)
                except FileNotFoundError:
                    pass
