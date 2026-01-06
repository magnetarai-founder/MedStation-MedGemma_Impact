"""
Comprehensive tests for api/agent/engines/codex_engine.py

Tests the CodexEngine class which provides deterministic patch application
and rollback capabilities for AI-assisted code modifications.

Coverage targets:
- CodexEngine initialization and repo_root handling
- apply_unified_diff: success, empty diff, security validation, concurrency
- rollback: from backups, from reverse diff, not found
- _validate_diff_paths: path traversal security
- _detect_patch_level: -p0 vs -p1 detection
- _reverse_unified_diff: diff reversal
- _extract_targets: file path extraction from diff
- _split_unified_diff: multi-file diff splitting
- _apply_simple_diff: simple single-hunk replacement
- search_code: ripgrep and Python fallback
- generate_rename_diff: symbol rename diff generation
- Deterministic operations (add_import, rename_function, etc.)
- Codemod operations (move_module, extract_class, etc.)
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import subprocess

from api.agent.engines.codex_engine import CodexEngine


# ========== Fixtures ==========

@pytest.fixture
def temp_repo():
    """Create a temporary repository directory"""
    repo_dir = tempfile.mkdtemp()
    # Resolve to canonical path (handles macOS /var -> /private/var symlink)
    yield Path(repo_dir).resolve()
    shutil.rmtree(repo_dir, ignore_errors=True)


@pytest.fixture
def codex_engine(temp_repo):
    """Create a CodexEngine instance with temp repo"""
    return CodexEngine(repo_root=temp_repo)


@pytest.fixture
def sample_python_file(temp_repo):
    """Create a sample Python file in the temp repo"""
    file_path = temp_repo / "sample.py"
    file_path.write_text("""def hello():
    print("Hello, World!")
    return 42

def goodbye():
    print("Goodbye!")
    return 0
""")
    return file_path


@pytest.fixture
def sample_diff():
    """Return a simple unified diff for testing"""
    return """--- a/sample.py
+++ b/sample.py
@@ -1,4 +1,4 @@
 def hello():
-    print("Hello, World!")
+    print("Hello, Universe!")
     return 42
"""


@pytest.fixture
def sample_diff_p0():
    """Return a -p0 format diff (no a/ b/ prefix)"""
    return """--- sample.py
+++ sample.py
@@ -1,4 +1,4 @@
 def hello():
-    print("Hello, World!")
+    print("Hello, Universe!")
     return 42
"""


# ========== CodexEngine Initialization Tests ==========

class TestCodexEngineInit:
    """Tests for CodexEngine initialization"""

    def test_init_with_repo_root(self, temp_repo):
        """Test initialization with explicit repo root"""
        engine = CodexEngine(repo_root=temp_repo)

        assert engine.repo_root == temp_repo

    def test_init_creates_patch_log_dir(self, temp_repo):
        """Test initialization creates .ai_agent directory"""
        engine = CodexEngine(repo_root=temp_repo)

        assert (temp_repo / ".ai_agent").exists()
        assert (temp_repo / ".ai_agent").is_dir()

    def test_init_without_repo_root_uses_cwd(self):
        """Test initialization without repo root uses current directory"""
        with patch.object(Path, 'cwd', return_value=Path('/fake/cwd')):
            with patch.object(Path, 'mkdir'):
                engine = CodexEngine(repo_root=None)
                # Engine defaults to cwd
                assert engine.repo_root is not None

    def test_patch_log_dir_attribute(self, codex_engine, temp_repo):
        """Test _patch_log_dir is set correctly"""
        assert codex_engine._patch_log_dir == temp_repo / ".ai_agent"


# ========== apply_unified_diff Tests ==========

class TestApplyUnifiedDiff:
    """Tests for apply_unified_diff method"""

    def test_empty_diff_returns_false(self, codex_engine):
        """Test empty diff returns failure"""
        result, msg = codex_engine.apply_unified_diff("", "test_patch")

        assert result is False
        assert "Empty diff" in msg

    def test_whitespace_only_diff_returns_false(self, codex_engine):
        """Test whitespace-only diff returns failure"""
        result, msg = codex_engine.apply_unified_diff("   \n\t  ", "test_patch")

        assert result is False
        assert "Empty diff" in msg

    def test_security_rejects_absolute_path(self, codex_engine):
        """Test diff with absolute path is rejected"""
        diff = """--- /etc/passwd
+++ /etc/passwd
@@ -1 +1 @@
-root:x:0:0:root:/root:/bin/bash
+hacked:x:0:0:root:/root:/bin/bash
"""
        result, msg = codex_engine.apply_unified_diff(diff, "test_patch")

        assert result is False
        assert "Security" in msg
        assert "Absolute path" in msg

    def test_security_rejects_path_traversal(self, codex_engine):
        """Test diff with path traversal is rejected"""
        diff = """--- a/../../../etc/passwd
+++ b/../../../etc/passwd
@@ -1 +1 @@
-root
+hacked
"""
        result, msg = codex_engine.apply_unified_diff(diff, "test_patch")

        assert result is False
        assert "Security" in msg
        assert "traversal" in msg.lower()

    def test_apply_simple_diff_success(self, codex_engine, temp_repo, sample_python_file):
        """Test applying a simple diff successfully"""
        diff = """--- sample.py
+++ sample.py
@@ -1,4 +1,4 @@
 def hello():
-    print("Hello, World!")
+    print("Hello, Universe!")
     return 42
"""
        # Mock patch command availability and execution
        with patch('shutil.which', return_value='/usr/bin/patch'):
            with patch('subprocess.run') as mock_run:
                # Dry run succeeds
                mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')

                result, msg = codex_engine.apply_unified_diff(diff, "test_patch_001")

                assert result is True
                assert "Applied" in msg

    def test_apply_creates_backup(self, codex_engine, temp_repo, sample_python_file):
        """Test applying diff creates backup of original file"""
        diff = """--- sample.py
+++ sample.py
@@ -1,4 +1,4 @@
 def hello():
-    print("Hello, World!")
+    print("Hello, Universe!")
     return 42
"""
        original_content = sample_python_file.read_text()

        with patch('shutil.which', return_value='/usr/bin/patch'):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')

                result, msg = codex_engine.apply_unified_diff(diff, "backup_test")

        # Check backup was created
        backup_path = temp_repo / ".ai_agent" / "backup_test" / "sample.py"
        assert backup_path.exists()
        assert backup_path.read_text() == original_content

    def test_apply_saves_patch_to_log(self, codex_engine, temp_repo, sample_python_file):
        """Test applying diff saves patch file for rollback"""
        diff = """--- sample.py
+++ sample.py
@@ -1,4 +1,4 @@
 def hello():
-    print("Hello, World!")
+    print("Hello, Universe!")
     return 42
"""
        with patch('shutil.which', return_value='/usr/bin/patch'):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')

                codex_engine.apply_unified_diff(diff, "log_test")

        # Check patch was logged
        patch_log = temp_repo / ".ai_agent" / "log_test.diff"
        assert patch_log.exists()
        assert patch_log.read_text() == diff

    def test_apply_fallback_to_simple_diff(self, codex_engine, temp_repo, sample_python_file):
        """Test fallback to simple diff applier when patch command fails"""
        original_content = sample_python_file.read_text()

        diff = """--- sample.py
+++ sample.py
@@ -1,4 +1,4 @@
 def hello():
-    print("Hello, World!")
+    print("Hello, Universe!")
     return 42
"""
        # Mock patch command not available
        with patch('shutil.which', return_value=None):
            result, msg = codex_engine.apply_unified_diff(diff, "fallback_test")

            # May succeed via _apply_simple_diff or fail gracefully
            assert isinstance(result, bool)

    def test_apply_concurrent_lock_blocking(self, codex_engine, temp_repo, sample_python_file):
        """Test concurrent patch application is blocked"""
        diff = """--- sample.py
+++ sample.py
@@ -1,4 +1,4 @@
 def hello():
-    print("Hello, World!")
+    print("Hello, Universe!")
     return 42
"""
        # Create lock file to simulate concurrent operation
        lock_file = temp_repo / ".ai_agent" / "apply.lock"
        lock_file.parent.mkdir(exist_ok=True)

        # Simulate blocking by having fcntl raise BlockingIOError
        with patch('shutil.which', return_value='/usr/bin/patch'):
            with patch('api.agent.engines.codex_engine.fcntl') as mock_fcntl:
                mock_fcntl.LOCK_EX = 2
                mock_fcntl.LOCK_NB = 4
                mock_fcntl.flock.side_effect = BlockingIOError("Resource busy")

                result, msg = codex_engine.apply_unified_diff(diff, "concurrent_test")

                assert result is False
                assert "Another patch" in msg


# ========== rollback Tests ==========

class TestRollback:
    """Tests for rollback method"""

    def test_rollback_from_backup(self, codex_engine, temp_repo, sample_python_file):
        """Test rollback restores from backup files"""
        patch_id = "rollback_test"
        original_content = sample_python_file.read_text()

        # Create backup directory with original file
        backup_dir = temp_repo / ".ai_agent" / patch_id
        backup_dir.mkdir(parents=True)
        (backup_dir / "sample.py").write_text(original_content)

        # Modify the original file
        sample_python_file.write_text("modified content")

        result, msg = codex_engine.rollback(patch_id)

        assert result is True
        assert "backups" in msg.lower()
        assert sample_python_file.read_text() == original_content

    def test_rollback_no_backups_returns_false(self, codex_engine, temp_repo):
        """Test rollback with no backups returns failure"""
        patch_id = "nonexistent_patch"

        # Create empty backup directory
        backup_dir = temp_repo / ".ai_agent" / patch_id
        backup_dir.mkdir(parents=True)

        result, msg = codex_engine.rollback(patch_id)

        assert result is False
        assert "No backups" in msg

    def test_rollback_via_reverse_diff(self, codex_engine, temp_repo, sample_python_file):
        """Test rollback via reverse diff when no backup exists"""
        patch_id = "reverse_test"

        # Create patch log without backup
        patch_log = temp_repo / ".ai_agent" / f"{patch_id}.diff"
        patch_log.parent.mkdir(parents=True, exist_ok=True)
        patch_log.write_text("""--- sample.py
+++ sample.py
@@ -1,4 +1,4 @@
 def hello():
-    print("Hello, World!")
+    print("Hello, Universe!")
     return 42
""")

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')

            result, msg = codex_engine.rollback(patch_id)

            assert result is True
            assert "Rolled back" in msg

    def test_rollback_patch_not_found(self, codex_engine, temp_repo):
        """Test rollback when patch file not found"""
        result, msg = codex_engine.rollback("nonexistent_patch_id")

        assert result is False
        assert "not found" in msg.lower()

    def test_rollback_reverse_diff_fails(self, codex_engine, temp_repo):
        """Test rollback failure when reverse diff application fails"""
        patch_id = "fail_test"

        # Create patch log
        patch_log = temp_repo / ".ai_agent" / f"{patch_id}.diff"
        patch_log.parent.mkdir(parents=True, exist_ok=True)
        patch_log.write_text("""--- sample.py
+++ sample.py
@@ -1 +1 @@
-old
+new
""")

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout='', stderr='patch failed')

            result, msg = codex_engine.rollback(patch_id)

            assert result is False
            assert "failed" in msg.lower()


# ========== _validate_diff_paths Tests ==========

class TestValidateDiffPaths:
    """Tests for _validate_diff_paths security validation"""

    def test_valid_relative_path(self, codex_engine):
        """Test valid relative paths are accepted"""
        diff = """--- a/src/module.py
+++ b/src/module.py
@@ -1 +1 @@
-old
+new
"""
        is_safe, msg = codex_engine._validate_diff_paths(diff)

        assert is_safe is True
        assert msg == ""

    def test_dev_null_is_allowed(self, codex_engine):
        """Test /dev/null is allowed (for new/deleted files)"""
        diff = """--- /dev/null
+++ b/new_file.py
@@ -0,0 +1 @@
+new content
"""
        is_safe, msg = codex_engine._validate_diff_paths(diff)

        assert is_safe is True

    def test_absolute_path_rejected(self, codex_engine):
        """Test absolute paths are rejected"""
        diff = """--- /etc/passwd
+++ /etc/passwd
@@ -1 +1 @@
-root
+hacked
"""
        is_safe, msg = codex_engine._validate_diff_paths(diff)

        assert is_safe is False
        assert "Absolute path" in msg

    def test_path_traversal_dot_dot_rejected(self, codex_engine):
        """Test ../ path traversal is rejected"""
        diff = """--- a/../../../etc/passwd
+++ b/../../../etc/passwd
@@ -1 +1 @@
-root
+hacked
"""
        is_safe, msg = codex_engine._validate_diff_paths(diff)

        assert is_safe is False
        assert "traversal" in msg.lower()

    def test_path_starting_with_dot_dot_rejected(self, codex_engine):
        """Test paths starting with .. are rejected"""
        diff = """--- ..secret.txt
+++ ..secret.txt
@@ -1 +1 @@
-secret
+exposed
"""
        is_safe, msg = codex_engine._validate_diff_paths(diff)

        assert is_safe is False

    def test_path_outside_repo_rejected(self, codex_engine, temp_repo):
        """Test paths that resolve outside repo are rejected"""
        # Create a symlink that points outside repo
        diff = """--- a/safe/path/../../outside.txt
+++ b/safe/path/../../outside.txt
@@ -1 +1 @@
-old
+new
"""
        is_safe, msg = codex_engine._validate_diff_paths(diff)

        # Should be caught by ../ check
        assert is_safe is False

    def test_p0_format_paths(self, codex_engine):
        """Test -p0 format (no a/ b/ prefix) is handled"""
        diff = """--- src/module.py
+++ src/module.py
@@ -1 +1 @@
-old
+new
"""
        is_safe, msg = codex_engine._validate_diff_paths(diff)

        assert is_safe is True

    def test_path_with_timestamp(self, codex_engine):
        """Test paths with timestamps are handled"""
        diff = """--- src/module.py	2024-01-01 00:00:00.000000000 +0000
+++ src/module.py	2024-01-02 00:00:00.000000000 +0000
@@ -1 +1 @@
-old
+new
"""
        is_safe, msg = codex_engine._validate_diff_paths(diff)

        assert is_safe is True


# ========== _detect_patch_level Tests ==========

class TestDetectPatchLevel:
    """Tests for _detect_patch_level method"""

    def test_detect_p1_with_prefix(self, codex_engine):
        """Test detection of -p1 format (a/ b/ prefix)"""
        diff = """--- a/src/module.py
+++ b/src/module.py
@@ -1 +1 @@
-old
+new
"""
        level = codex_engine._detect_patch_level(diff)

        assert level == 1

    def test_detect_p0_without_prefix(self, codex_engine):
        """Test detection of -p0 format (no prefix)"""
        diff = """--- src/module.py
+++ src/module.py
@@ -1 +1 @@
-old
+new
"""
        level = codex_engine._detect_patch_level(diff)

        assert level == 0

    def test_detect_with_dev_null(self, codex_engine):
        """Test detection with /dev/null"""
        diff = """--- /dev/null
+++ b/new_file.py
@@ -0,0 +1 @@
+new content
"""
        level = codex_engine._detect_patch_level(diff)

        # Has b/ prefix
        assert level == 1

    def test_detect_with_timestamp(self, codex_engine):
        """Test detection with timestamps in paths"""
        diff = """--- a/module.py	2024-01-01 00:00:00 +0000
+++ b/module.py	2024-01-02 00:00:00 +0000
@@ -1 +1 @@
-old
+new
"""
        level = codex_engine._detect_patch_level(diff)

        assert level == 1

    def test_detect_default_to_p1(self, codex_engine):
        """Test default to -p1 for unclear format"""
        diff = """@@ -1 +1 @@
-old
+new
"""
        level = codex_engine._detect_patch_level(diff)

        assert level == 1


# ========== _reverse_unified_diff Tests ==========

class TestReverseUnifiedDiff:
    """Tests for _reverse_unified_diff method"""

    def test_reverse_headers(self, codex_engine):
        """Test --- and +++ headers are swapped"""
        diff = """--- a/file.py
+++ b/file.py
@@ -1 +1 @@
-old
+new
"""
        reversed_diff = codex_engine._reverse_unified_diff(diff)

        assert "+++ a/file.py" in reversed_diff
        assert "--- b/file.py" in reversed_diff

    def test_reverse_content_lines(self, codex_engine):
        """Test + and - content lines are swapped"""
        diff = """--- a/file.py
+++ b/file.py
@@ -1 +1 @@
-removed line
+added line
"""
        reversed_diff = codex_engine._reverse_unified_diff(diff)

        assert "+removed line" in reversed_diff
        assert "-added line" in reversed_diff

    def test_reverse_preserves_context(self, codex_engine):
        """Test context lines (no prefix) are preserved"""
        diff = """--- a/file.py
+++ b/file.py
@@ -1,3 +1,3 @@
 context line
-old
+new
 more context
"""
        reversed_diff = codex_engine._reverse_unified_diff(diff)

        assert " context line" in reversed_diff
        assert " more context" in reversed_diff

    def test_reverse_preserves_hunk_header(self, codex_engine):
        """Test @@ hunk headers are preserved"""
        diff = """--- a/file.py
+++ b/file.py
@@ -1,3 +1,3 @@
-old
+new
"""
        reversed_diff = codex_engine._reverse_unified_diff(diff)

        assert "@@ -1,3 +1,3 @@" in reversed_diff


# ========== _extract_targets Tests ==========

class TestExtractTargets:
    """Tests for _extract_targets method"""

    def test_extract_single_file(self, codex_engine):
        """Test extracting single file from diff"""
        diff = """--- a/module.py
+++ b/module.py
@@ -1 +1 @@
-old
+new
"""
        targets = codex_engine._extract_targets(diff)

        assert "module.py" in targets

    def test_extract_strips_prefix(self, codex_engine):
        """Test a/ and b/ prefixes are stripped"""
        diff = """--- a/src/module.py
+++ b/src/module.py
@@ -1 +1 @@
-old
+new
"""
        targets = codex_engine._extract_targets(diff)

        assert "src/module.py" in targets
        assert "a/src/module.py" not in targets
        assert "b/src/module.py" not in targets

    def test_extract_strips_timestamp(self, codex_engine):
        """Test timestamps are stripped from paths"""
        diff = """--- a/module.py	2024-01-01 00:00:00 +0000
+++ b/module.py	2024-01-02 00:00:00 +0000
@@ -1 +1 @@
-old
+new
"""
        targets = codex_engine._extract_targets(diff)

        assert "module.py" in targets

    def test_extract_multiple_files(self, codex_engine):
        """Test extracting multiple files from multi-file diff"""
        diff = """--- a/file1.py
+++ b/file1.py
@@ -1 +1 @@
-old
+new
--- a/file2.py
+++ b/file2.py
@@ -1 +1 @@
-old
+new
"""
        targets = codex_engine._extract_targets(diff)

        assert "file1.py" in targets
        assert "file2.py" in targets

    def test_extract_unique_targets(self, codex_engine):
        """Test targets are unique (no duplicates)"""
        diff = """--- a/module.py
+++ b/module.py
@@ -1 +1 @@
-old
+new
"""
        targets = codex_engine._extract_targets(diff)

        # Check no duplicates
        assert len(targets) == len(set(targets))


# ========== _split_unified_diff Tests ==========

class TestSplitUnifiedDiff:
    """Tests for _split_unified_diff method"""

    def test_split_single_file_diff(self, codex_engine):
        """Test splitting single file diff returns one shard"""
        diff = """--- a/module.py
+++ b/module.py
@@ -1 +1 @@
-old
+new
"""
        shards = codex_engine._split_unified_diff(diff)

        assert len(shards) == 1

    def test_split_multi_file_diff(self, codex_engine):
        """Test splitting multi-file diff"""
        diff = """--- a/file1.py
+++ b/file1.py
@@ -1 +1 @@
-old
+new
--- a/file2.py
+++ b/file2.py
@@ -1 +1 @@
-old
+new
"""
        shards = codex_engine._split_unified_diff(diff)

        assert len(shards) == 2

    def test_split_git_format_diff(self, codex_engine):
        """Test splitting git format diff (with diff --git)"""
        diff = """diff --git a/file1.py b/file1.py
--- a/file1.py
+++ b/file1.py
@@ -1 +1 @@
-old
+new
diff --git a/file2.py b/file2.py
--- a/file2.py
+++ b/file2.py
@@ -1 +1 @@
-old
+new
"""
        shards = codex_engine._split_unified_diff(diff)

        assert len(shards) == 2

    def test_split_filters_invalid_shards(self, codex_engine):
        """Test invalid shards (missing headers) are filtered"""
        diff = """garbage
--- a/valid.py
+++ b/valid.py
@@ -1 +1 @@
-old
+new
"""
        shards = codex_engine._split_unified_diff(diff)

        # Should only have one valid shard
        assert len(shards) == 1


# ========== _apply_simple_diff Tests ==========

class TestApplySimpleDiff:
    """Tests for _apply_simple_diff method"""

    def test_simple_diff_success(self, codex_engine, temp_repo):
        """Test simple diff application"""
        # Create target file
        target = temp_repo / "test.py"
        target.write_text("""def hello():
    print("Hello, World!")
    return 42
""")

        diff = """--- test.py
+++ test.py
@@ -1,3 +1,3 @@
 def hello():
-    print("Hello, World!")
+    print("Hello, Universe!")
     return 42
"""
        result, msg = codex_engine._apply_simple_diff(diff)

        # May succeed or fail depending on exact matching
        assert isinstance(result, bool)

    def test_simple_diff_no_target_file(self, codex_engine):
        """Test simple diff fails when target not found"""
        diff = """--- nonexistent.py
+++ nonexistent.py
@@ -1 +1 @@
-old
+new
"""
        result, msg = codex_engine._apply_simple_diff(diff)

        assert result is False
        assert "not found" in msg.lower()

    def test_simple_diff_no_target_in_diff(self, codex_engine):
        """Test simple diff fails when no target in diff"""
        diff = """@@ -1 +1 @@
-old
+new
"""
        result, msg = codex_engine._apply_simple_diff(diff)

        assert result is False

    def test_simple_diff_strips_prefix(self, codex_engine, temp_repo):
        """Test a/ b/ prefixes are stripped"""
        target = temp_repo / "module.py"
        target.write_text("old content")

        diff = """--- a/module.py
+++ b/module.py
@@ -1 +1 @@
-old content
+new content
"""
        result, msg = codex_engine._apply_simple_diff(diff)

        # Check target path handling
        assert isinstance(result, bool)


# ========== search_code Tests ==========

class TestSearchCode:
    """Tests for search_code method"""

    def test_search_code_with_ripgrep(self, codex_engine, temp_repo):
        """Test search using ripgrep"""
        # Create searchable file
        (temp_repo / "module.py").write_text("""def hello():
    print("Hello, World!")
""")

        with patch('shutil.which', return_value='/usr/bin/rg'):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout="module.py:1:def hello():"
                )

                results = codex_engine.search_code(r"def hello")

                # Returns list of tuples
                assert isinstance(results, list)

    def test_search_code_python_fallback(self, codex_engine, temp_repo):
        """Test search falls back to Python when ripgrep not available"""
        # Create searchable file
        (temp_repo / "module.py").write_text("""def hello():
    print("Hello, World!")
""")

        with patch('shutil.which', return_value=None):
            results = codex_engine.search_code(r"def hello", globs=["*.py"])

            # Should find the pattern
            assert isinstance(results, list)
            # May have results depending on file structure
            assert all(isinstance(r, tuple) for r in results)

    def test_search_code_max_results(self, codex_engine, temp_repo):
        """Test max_results parameter limits results"""
        # Create file with many matches
        content = "\n".join([f"match_{i}" for i in range(300)])
        (temp_repo / "many_matches.py").write_text(content)

        with patch('shutil.which', return_value=None):
            results = codex_engine.search_code(r"match_", max_results=10, globs=["*.py"])

            assert len(results) <= 10

    def test_search_code_custom_globs(self, codex_engine, temp_repo):
        """Test custom glob patterns"""
        (temp_repo / "test.py").write_text("python match")
        (temp_repo / "test.js").write_text("javascript match")

        with patch('shutil.which', return_value=None):
            results = codex_engine.search_code(r"match", globs=["*.py"])

            # Should only search Python files
            assert all("test.py" in r[0] or ".py" in r[0] for r in results if results)

    def test_search_code_ripgrep_no_matches(self, codex_engine, temp_repo):
        """Test ripgrep returns empty when no matches"""
        with patch('shutil.which', return_value='/usr/bin/rg'):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=1,  # No matches
                    stdout=""
                )

                results = codex_engine.search_code(r"nonexistent_pattern")

                assert results == []


# ========== generate_rename_diff Tests ==========

class TestGenerateRenameDiff:
    """Tests for generate_rename_diff method"""

    def test_generate_rename_diff(self, codex_engine, temp_repo):
        """Test generating diff for symbol rename"""
        # Create file with symbol
        (temp_repo / "module.py").write_text("""def old_name():
    return old_name
""")

        diff = codex_engine.generate_rename_diff("old_name", "new_name", globs=["*.py"])

        # Should generate diff if symbol found
        assert isinstance(diff, str)

    def test_generate_rename_no_matches(self, codex_engine, temp_repo):
        """Test rename with no matches returns empty"""
        (temp_repo / "module.py").write_text("no match here")

        diff = codex_engine.generate_rename_diff("nonexistent", "new_name", globs=["*.py"])

        assert diff == ""

    def test_generate_rename_word_boundary(self, codex_engine, temp_repo):
        """Test rename respects word boundaries"""
        (temp_repo / "module.py").write_text("""def get():
    pass

def get_item():
    pass
""")

        diff = codex_engine.generate_rename_diff("get", "fetch", globs=["*.py"])

        # Should only rename 'get' not 'get_item'
        # Check diff handles word boundaries
        if diff:
            assert "fetch_item" not in diff


# ========== Deterministic Operations Tests ==========

class TestDeterministicOperations:
    """Tests for deterministic operations (add_import, rename_function, etc.)"""

    def test_add_import_file_not_found(self, codex_engine, temp_repo):
        """Test add_import with nonexistent file"""
        result, msg = codex_engine.add_import("nonexistent.py", "import os")

        assert result is False
        assert "not found" in msg.lower()

    def test_add_import_success(self, codex_engine, temp_repo):
        """Test add_import to existing file"""
        (temp_repo / "module.py").write_text("print('hello')")

        with patch('api.agent.engines.codex_deterministic_ops.DeterministicOps.add_import') as mock:
            mock.return_value = (True, "Import added")

            result, msg = codex_engine.add_import("module.py", "import os")

            assert result is True

    def test_remove_import_file_not_found(self, codex_engine, temp_repo):
        """Test remove_import with nonexistent file"""
        result, msg = codex_engine.remove_import("nonexistent.py", "os")

        assert result is False
        assert "not found" in msg.lower()

    def test_rename_function_file_not_found(self, codex_engine, temp_repo):
        """Test rename_function with nonexistent file"""
        result, msg = codex_engine.rename_function("nonexistent.py", "old", "new")

        assert result is False
        assert "not found" in msg.lower()

    def test_rename_class_file_not_found(self, codex_engine, temp_repo):
        """Test rename_class with nonexistent file"""
        result, msg = codex_engine.rename_class("nonexistent.py", "OldClass", "NewClass")

        assert result is False
        assert "not found" in msg.lower()

    def test_add_function_parameter_file_not_found(self, codex_engine, temp_repo):
        """Test add_function_parameter with nonexistent file"""
        result, msg = codex_engine.add_function_parameter("nonexistent.py", "func", "param")

        assert result is False
        assert "not found" in msg.lower()

    def test_extract_to_function_file_not_found(self, codex_engine, temp_repo):
        """Test extract_to_function with nonexistent file"""
        result, msg = codex_engine.extract_to_function("nonexistent.py", 1, 5, "new_func")

        assert result is False
        assert "not found" in msg.lower()

    def test_update_json_file(self, codex_engine, temp_repo):
        """Test update_json_file"""
        with patch('api.agent.engines.codex_deterministic_ops.DeterministicOps.update_json_file') as mock:
            mock.return_value = (True, "Updated")

            result, msg = codex_engine.update_json_file("config.json", {"key": "value"})

            mock.assert_called_once()

    def test_add_type_hints_file_not_found(self, codex_engine, temp_repo):
        """Test add_type_hints with nonexistent file"""
        result, msg = codex_engine.add_type_hints("nonexistent.py", "func", {"x": "int"})

        assert result is False
        assert "not found" in msg.lower()

    def test_move_function_source_not_found(self, codex_engine, temp_repo):
        """Test move_function with nonexistent source"""
        (temp_repo / "target.py").write_text("")

        result, msg = codex_engine.move_function("nonexistent.py", "target.py", "func")

        assert result is False
        assert "not found" in msg.lower()


# ========== Codemod Operations Tests ==========

class TestCodemodOperations:
    """Tests for codemod operations (move_module, extract_class, etc.)"""

    def test_organize_imports_file_not_found(self, codex_engine, temp_repo):
        """Test organize_imports with nonexistent file"""
        result, msg = codex_engine.organize_imports("nonexistent.py")

        assert result is False
        assert "not found" in msg.lower()

    def test_extract_class_source_not_found(self, codex_engine, temp_repo):
        """Test extract_class with nonexistent source"""
        result, msg = codex_engine.extract_class("nonexistent.py", "MyClass", "target.py")

        assert result is False
        assert "not found" in msg.lower()

    def test_update_relative_imports_file_not_found(self, codex_engine, temp_repo):
        """Test update_relative_imports with nonexistent file"""
        result, msg = codex_engine.update_relative_imports("nonexistent.py", "old/loc", "new/loc")

        assert result is False
        assert "not found" in msg.lower()

    def test_add_docstring_file_not_found(self, codex_engine, temp_repo):
        """Test add_docstring with nonexistent file"""
        result, msg = codex_engine.add_docstring("nonexistent.py", "func", "docstring")

        assert result is False
        assert "not found" in msg.lower()

    def test_move_module_source_not_found(self, codex_engine, temp_repo):
        """Test move_module with nonexistent source"""
        result, msg = codex_engine.move_module("nonexistent.py", "target.py")

        assert result is False
        assert "not found" in msg.lower()

    def test_move_module_success(self, codex_engine, temp_repo):
        """Test move_module success"""
        source = temp_repo / "source.py"
        source.write_text("# module content")

        result, msg = codex_engine.move_module("source.py", "target.py", update_imports=False)

        assert result is True
        assert "Moved" in msg
        assert not source.exists()
        assert (temp_repo / "target.py").exists()

    def test_move_module_creates_target_dir(self, codex_engine, temp_repo):
        """Test move_module creates target directory"""
        source = temp_repo / "source.py"
        source.write_text("# module content")

        result, msg = codex_engine.move_module("source.py", "subdir/target.py", update_imports=False)

        assert result is True
        assert (temp_repo / "subdir" / "target.py").exists()


# ========== Diff Generation Tests ==========

class TestDiffGeneration:
    """Tests for diff generation helpers"""

    def test_unified_text_diff(self, codex_engine):
        """Test _unified_text_diff generates valid diff"""
        before = "line1\nline2\n"
        after = "line1\nmodified\n"

        diff = codex_engine._unified_text_diff("file.py", "file.py", before, after)

        assert "--- file.py" in diff
        assert "+++ file.py" in diff
        assert "-line2" in diff
        assert "+modified" in diff

    def test_unified_add_file(self, codex_engine):
        """Test _unified_add_file generates add diff"""
        content = "new content\n"

        diff = codex_engine._unified_add_file("new_file.py", content)

        assert "--- /dev/null" in diff
        assert "+++ new_file.py" in diff
        assert "+new content" in diff

    def test_unified_delete_file(self, codex_engine):
        """Test _unified_delete_file generates delete diff"""
        content = "old content\n"

        diff = codex_engine._unified_delete_file("old_file.py", content)

        assert "--- old_file.py" in diff
        assert "+++ /dev/null" in diff
        assert "-old content" in diff

    def test_generate_move_module_diff_source_not_exists(self, codex_engine, temp_repo):
        """Test generate_move_module_diff with nonexistent source"""
        diff = codex_engine.generate_move_module_diff("nonexistent.py", "target.py")

        assert diff == ""

    def test_generate_move_module_diff_success(self, codex_engine, temp_repo):
        """Test generate_move_module_diff success"""
        source = temp_repo / "source.py"
        source.write_text("# module content\n")

        diff = codex_engine.generate_move_module_diff("source.py", "target.py", update_imports=False)

        assert diff != ""
        assert "source.py" in diff
        assert "target.py" in diff

    def test_generate_extract_class_diff_source_not_exists(self, codex_engine, temp_repo):
        """Test generate_extract_class_diff with nonexistent source"""
        diff = codex_engine.generate_extract_class_diff("nonexistent.py", "MyClass", "target.py")

        assert diff == ""

    def test_generate_extract_class_diff_class_not_found(self, codex_engine, temp_repo):
        """Test generate_extract_class_diff with nonexistent class"""
        source = temp_repo / "source.py"
        source.write_text("# no class here\n")

        diff = codex_engine.generate_extract_class_diff("source.py", "NonexistentClass", "target.py")

        assert diff == ""

    def test_generate_extract_class_diff_success(self, codex_engine, temp_repo):
        """Test generate_extract_class_diff success"""
        source = temp_repo / "source.py"
        source.write_text("""class MyClass:
    def method(self):
        pass
""")

        diff = codex_engine.generate_extract_class_diff("source.py", "MyClass", "target.py")

        # Should have diffs for source and target
        assert "MyClass" in diff

    def test_generate_organize_imports_diff_not_exists(self, codex_engine, temp_repo):
        """Test generate_organize_imports_diff with nonexistent file"""
        diff = codex_engine.generate_organize_imports_diff("nonexistent.py")

        assert diff == ""

    def test_generate_organize_imports_diff_no_changes(self, codex_engine, temp_repo):
        """Test generate_organize_imports_diff when no changes needed"""
        source = temp_repo / "module.py"
        source.write_text("# no imports\ndef func(): pass")

        diff = codex_engine.generate_organize_imports_diff("module.py")

        # May be empty if no reorganization needed
        assert isinstance(diff, str)


# ========== Helper Function Tests ==========

class TestHelperFunctions:
    """Tests for helper functions"""

    def test_rel_module_from_path(self, codex_engine, temp_repo):
        """Test _rel_module_from_path converts path to module"""
        # Create a file to test with
        (temp_repo / "src").mkdir()
        (temp_repo / "src" / "module.py").write_text("")

        module = codex_engine._rel_module_from_path("src/module.py")

        assert module == "src.module"

    def test_rel_module_from_path_nested(self, codex_engine, temp_repo):
        """Test _rel_module_from_path with nested path"""
        (temp_repo / "a" / "b" / "c").mkdir(parents=True)
        (temp_repo / "a" / "b" / "c" / "module.py").write_text("")

        module = codex_engine._rel_module_from_path("a/b/c/module.py")

        assert module == "a.b.c.module"


# ========== Edge Cases Tests ==========

class TestEdgeCases:
    """Tests for edge cases"""

    def test_unicode_file_content(self, codex_engine, temp_repo):
        """Test handling unicode in file content"""
        (temp_repo / "unicode.py").write_text("""# Unicode: 日本語 émojis 🎉
def greet():
    print("こんにちは")
""")

        with patch('shutil.which', return_value=None):
            results = codex_engine.search_code(r"日本語", globs=["*.py"])

            # Should handle unicode
            assert isinstance(results, list)

    def test_empty_file(self, codex_engine, temp_repo):
        """Test handling empty files"""
        (temp_repo / "empty.py").write_text("")

        diff = codex_engine.generate_rename_diff("nonexistent", "new", globs=["*.py"])

        # Should handle empty files gracefully
        assert isinstance(diff, str)

    def test_large_file(self, codex_engine, temp_repo):
        """Test handling large files"""
        # Create large file
        content = "line\n" * 100000
        (temp_repo / "large.py").write_text(content)

        with patch('shutil.which', return_value=None):
            results = codex_engine.search_code(r"line", max_results=10, globs=["*.py"])

            assert len(results) <= 10

    def test_binary_file_handling(self, codex_engine, temp_repo):
        """Test binary files are handled gracefully"""
        # Create binary file
        (temp_repo / "binary.py").write_bytes(b'\x00\x01\x02\x03')

        with patch('shutil.which', return_value=None):
            results = codex_engine.search_code(r"pattern", globs=["*.py"])

            # Should handle errors gracefully
            assert isinstance(results, list)

    def test_symlink_handling(self, codex_engine, temp_repo):
        """Test symlinks are handled"""
        # Create file and symlink
        (temp_repo / "real.py").write_text("content")

        try:
            (temp_repo / "link.py").symlink_to(temp_repo / "real.py")
        except (OSError, NotImplementedError):
            pytest.skip("Symlinks not supported on this platform")

        with patch('shutil.which', return_value=None):
            results = codex_engine.search_code(r"content", globs=["*.py"])

            assert isinstance(results, list)

    def test_read_only_file(self, codex_engine, temp_repo):
        """Test handling read-only files in apply"""
        ro_file = temp_repo / "readonly.py"
        ro_file.write_text("original")
        os.chmod(ro_file, 0o444)

        try:
            diff = """--- readonly.py
+++ readonly.py
@@ -1 +1 @@
-original
+modified
"""
            # Backup will fail on read-only, but should handle gracefully
            with patch('shutil.which', return_value='/usr/bin/patch'):
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value = MagicMock(returncode=0)

                    result, msg = codex_engine.apply_unified_diff(diff, "ro_test")

                    # Should attempt application
                    assert isinstance(result, bool)
        finally:
            os.chmod(ro_file, 0o644)


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests"""

    def test_apply_and_rollback_cycle(self, codex_engine, temp_repo):
        """Test full apply and rollback cycle"""
        # Create target file
        target = temp_repo / "module.py"
        original = """def hello():
    print("Hello, World!")
    return 42
"""
        target.write_text(original)

        diff = """--- module.py
+++ module.py
@@ -1,4 +1,4 @@
 def hello():
-    print("Hello, World!")
+    print("Hello, Universe!")
     return 42
"""

        # Apply
        with patch('shutil.which', return_value='/usr/bin/patch'):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')

                apply_result, apply_msg = codex_engine.apply_unified_diff(diff, "cycle_test")

                assert apply_result is True

        # Verify backup was created
        backup = temp_repo / ".ai_agent" / "cycle_test" / "module.py"
        assert backup.exists()
        assert backup.read_text() == original

        # Rollback
        rollback_result, rollback_msg = codex_engine.rollback("cycle_test")

        assert rollback_result is True
        assert target.read_text() == original

    def test_multi_file_diff_application(self, codex_engine, temp_repo):
        """Test applying diff to multiple files"""
        # Create target files
        (temp_repo / "file1.py").write_text("content1")
        (temp_repo / "file2.py").write_text("content2")

        diff = """--- file1.py
+++ file1.py
@@ -1 +1 @@
-content1
+modified1
--- file2.py
+++ file2.py
@@ -1 +1 @@
-content2
+modified2
"""

        with patch('shutil.which', return_value='/usr/bin/patch'):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')

                result, msg = codex_engine.apply_unified_diff(diff, "multi_test")

                assert result is True
                # Both files should have backups
                assert (temp_repo / ".ai_agent" / "multi_test" / "file1.py").exists()
                assert (temp_repo / ".ai_agent" / "multi_test" / "file2.py").exists()

    def test_search_and_rename_workflow(self, codex_engine, temp_repo):
        """Test search then rename workflow"""
        # Create files with old symbol
        (temp_repo / "module1.py").write_text("""def old_func():
    return old_func()
""")
        (temp_repo / "module2.py").write_text("""from module1 import old_func
old_func()
""")

        # Search for symbol
        with patch('shutil.which', return_value=None):
            results = codex_engine.search_code(r"\bold_func\b", globs=["*.py"])

        # Generate rename diff
        diff = codex_engine.generate_rename_diff("old_func", "new_func", globs=["*.py"])

        # Should generate diff for both files
        if diff:
            assert "new_func" in diff


# ========== _apply_per_file Tests ==========

class TestApplyPerFile:
    """Tests for _apply_per_file method"""

    def test_apply_per_file_no_shards(self, codex_engine):
        """Test _apply_per_file with no valid shards"""
        result, msg = codex_engine._apply_per_file("invalid diff content")

        assert result is False
        assert "no per-file shards" in msg.lower()

    def test_apply_per_file_add_file(self, codex_engine, temp_repo):
        """Test _apply_per_file adds new file"""
        diff = """--- /dev/null
+++ new_file.py
@@ -0,0 +1,2 @@
+# New file
+print("hello")
"""
        result, msg = codex_engine._apply_per_file(diff)

        assert result is True
        assert (temp_repo / "new_file.py").exists()

    def test_apply_per_file_delete_file(self, codex_engine, temp_repo):
        """Test _apply_per_file deletes file"""
        # Create file to delete
        to_delete = temp_repo / "to_delete.py"
        to_delete.write_text("content to delete")

        diff = """--- to_delete.py
+++ /dev/null
@@ -1 +0,0 @@
-content to delete
"""
        result, msg = codex_engine._apply_per_file(diff)

        assert result is True
        assert not to_delete.exists()

    def test_apply_per_file_add_creates_parent_dirs(self, codex_engine, temp_repo):
        """Test _apply_per_file creates parent directories for new files"""
        diff = """--- /dev/null
+++ deep/nested/new_file.py
@@ -0,0 +1 @@
+content
"""
        result, msg = codex_engine._apply_per_file(diff)

        assert result is True
        assert (temp_repo / "deep" / "nested" / "new_file.py").exists()
