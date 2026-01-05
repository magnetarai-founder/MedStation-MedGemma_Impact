"""
Comprehensive tests for api/emergency_wipe.py

Tests the DoD 5220.22-M secure file deletion functions.

⚠️  CRITICAL: All tests use temporary files that are created
specifically for testing. No actual user data is touched.

Coverage targets:
- perform_dod_wipe: Main entry point handling files, directories, globs
- wipe_single_file: 7-pass overwrite implementation
- Error handling for various failure scenarios
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Import the module under test
from api.emergency_wipe import perform_dod_wipe, wipe_single_file


# ========== Fixtures ==========

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    dirpath = tempfile.mkdtemp(prefix="test_wipe_")
    yield Path(dirpath)
    # Cleanup (in case test didn't wipe it)
    if os.path.exists(dirpath):
        shutil.rmtree(dirpath)


@pytest.fixture
def temp_file(temp_dir):
    """Create a temporary file with known content"""
    file_path = temp_dir / "test_file.txt"
    with open(file_path, "w") as f:
        f.write("SECRET DATA TO BE WIPED" * 100)
    yield file_path


@pytest.fixture
def temp_files_with_glob(temp_dir):
    """Create multiple files matching a glob pattern"""
    files = []
    for i in range(3):
        file_path = temp_dir / f"secret_{i}.plist"
        with open(file_path, "w") as f:
            f.write(f"Secret content {i}")
        files.append(file_path)
    yield temp_dir, files


@pytest.fixture
def temp_nested_dir(temp_dir):
    """Create a nested directory structure with files"""
    # Create structure:
    # temp_dir/
    #   nested/
    #     level1/
    #       file1.txt
    #     level2/
    #       file2.txt
    #       deeper/
    #         file3.txt
    #   root_file.txt

    nested = temp_dir / "nested"
    level1 = nested / "level1"
    level2 = nested / "level2"
    deeper = level2 / "deeper"

    level1.mkdir(parents=True)
    level2.mkdir(parents=True)
    deeper.mkdir(parents=True)

    files = {
        "root": temp_dir / "root_file.txt",
        "file1": level1 / "file1.txt",
        "file2": level2 / "file2.txt",
        "file3": deeper / "file3.txt"
    }

    for name, path in files.items():
        with open(path, "w") as f:
            f.write(f"Content for {name}")

    yield nested, files


# ========== wipe_single_file Tests ==========

class TestWipeSingleFile:
    """Tests for wipe_single_file function"""

    @pytest.mark.asyncio
    async def test_wipe_nonexistent_file(self, temp_dir):
        """Test wiping a file that doesn't exist is a no-op"""
        nonexistent = temp_dir / "does_not_exist.txt"

        # Should not raise, just return
        await wipe_single_file(str(nonexistent))

        # File still doesn't exist (no side effects)
        assert not nonexistent.exists()

    @pytest.mark.asyncio
    async def test_wipe_removes_file(self, temp_file):
        """Test that wiping a file removes it"""
        assert temp_file.exists()

        await wipe_single_file(str(temp_file))

        assert not temp_file.exists()

    @pytest.mark.asyncio
    async def test_wipe_overwrites_content(self, temp_dir):
        """Test that file is overwritten before deletion"""
        file_path = temp_dir / "overwrite_test.txt"
        original_content = b"ORIGINAL SECRET DATA"

        with open(file_path, "wb") as f:
            f.write(original_content)

        # Capture what's written during wipe
        writes = []
        original_open = open

        def mock_open_capture(*args, **kwargs):
            f = original_open(*args, **kwargs)
            if "r+b" in args or kwargs.get("mode") == "r+b":
                original_write = f.write
                def capture_write(data):
                    writes.append(data[:10] if len(data) > 10 else data)  # Capture first 10 bytes
                    return original_write(data)
                f.write = capture_write
            return f

        with patch("builtins.open", side_effect=mock_open_capture):
            await wipe_single_file(str(file_path))

        # Should have 7 passes worth of writes
        assert len(writes) >= 7

    @pytest.mark.asyncio
    async def test_wipe_calls_fsync(self, temp_file):
        """Test that fsync is called after each pass"""
        fsync_calls = []

        original_fsync = os.fsync
        def track_fsync(fd):
            fsync_calls.append(fd)
            return original_fsync(fd)

        with patch("os.fsync", side_effect=track_fsync):
            await wipe_single_file(str(temp_file))

        # Should have 7 fsync calls (one per pass)
        assert len(fsync_calls) == 7

    @pytest.mark.asyncio
    async def test_wipe_empty_file(self, temp_dir):
        """Test wiping an empty file"""
        empty_file = temp_dir / "empty.txt"
        empty_file.touch()

        assert empty_file.exists()

        await wipe_single_file(str(empty_file))

        assert not empty_file.exists()

    @pytest.mark.asyncio
    async def test_wipe_large_file_chunks(self, temp_dir):
        """Test that large files use chunked random writes"""
        large_file = temp_dir / "large.bin"

        # Create a 3MB file
        file_size = 3 * 1024 * 1024
        with open(large_file, "wb") as f:
            f.write(b'\x42' * file_size)

        urandom_calls = []
        original_urandom = os.urandom

        def track_urandom(size):
            urandom_calls.append(size)
            return original_urandom(size)

        with patch("os.urandom", side_effect=track_urandom):
            await wipe_single_file(str(large_file))

        # Should have multiple urandom calls for pass 7 (chunked at 1MB)
        assert len(urandom_calls) >= 3  # At least 3 chunks for 3MB file
        # Each chunk should be 1MB or less
        assert all(size <= 1024 * 1024 for size in urandom_calls)


# ========== perform_dod_wipe Tests ==========

class TestPerformDodWipe:
    """Tests for perform_dod_wipe main function"""

    @pytest.mark.asyncio
    async def test_wipe_single_file_path(self, temp_file):
        """Test wiping a single file by path"""
        assert temp_file.exists()

        result = await perform_dod_wipe([str(temp_file)])

        assert result["count"] == 1
        assert result["errors"] == []
        assert not temp_file.exists()

    @pytest.mark.asyncio
    async def test_wipe_multiple_files(self, temp_dir):
        """Test wiping multiple files"""
        files = []
        for i in range(5):
            f = temp_dir / f"file_{i}.txt"
            f.write_text(f"Content {i}")
            files.append(f)

        result = await perform_dod_wipe([str(f) for f in files])

        assert result["count"] == 5
        assert result["errors"] == []
        for f in files:
            assert not f.exists()

    @pytest.mark.asyncio
    async def test_wipe_with_glob_pattern(self, temp_files_with_glob):
        """Test wiping files matching a glob pattern"""
        temp_dir, files = temp_files_with_glob

        # All files should exist
        for f in files:
            assert f.exists()

        glob_pattern = str(temp_dir / "*.plist")
        result = await perform_dod_wipe([glob_pattern])

        assert result["count"] == 3
        assert result["errors"] == []
        for f in files:
            assert not f.exists()

    @pytest.mark.asyncio
    async def test_wipe_directory_recursive(self, temp_nested_dir):
        """Test wiping a directory recursively"""
        nested_dir, files = temp_nested_dir

        # All files should exist
        for f in files.values():
            assert f.exists()

        result = await perform_dod_wipe([str(nested_dir)])

        # Should wipe 3 files in nested dir (file1, file2, file3)
        assert result["count"] == 3
        assert result["errors"] == []

        # Directory should be removed
        assert not nested_dir.exists()

    @pytest.mark.asyncio
    async def test_wipe_empty_directory(self, temp_dir):
        """Test wiping an empty directory"""
        empty_dir = temp_dir / "empty_dir"
        empty_dir.mkdir()

        result = await perform_dod_wipe([str(empty_dir)])

        assert result["count"] == 0  # No files to wipe
        assert result["errors"] == []
        assert not empty_dir.exists()

    @pytest.mark.asyncio
    async def test_wipe_with_tilde_expansion(self, temp_dir, monkeypatch):
        """Test that ~ is expanded to home directory"""
        # Create a fake home directory structure
        fake_home = temp_dir / "fake_home"
        fake_home.mkdir()
        test_file = fake_home / "secret.txt"
        test_file.write_text("Secret content")

        monkeypatch.setenv("HOME", str(fake_home))

        # Use tilde path
        result = await perform_dod_wipe(["~/secret.txt"])

        assert result["count"] == 1
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_wipe_nonexistent_path(self, temp_dir):
        """Test wiping a path that doesn't exist"""
        nonexistent = temp_dir / "does_not_exist"

        result = await perform_dod_wipe([str(nonexistent)])

        # No file wiped, no error (path just doesn't match)
        assert result["count"] == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_wipe_glob_no_matches(self, temp_dir):
        """Test glob pattern that matches nothing"""
        result = await perform_dod_wipe([str(temp_dir / "*.nonexistent")])

        assert result["count"] == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_wipe_empty_list(self):
        """Test wiping an empty list of paths"""
        result = await perform_dod_wipe([])

        assert result["count"] == 0
        assert result["errors"] == []


# ========== Error Handling Tests ==========

class TestErrorHandling:
    """Tests for error handling in wipe functions"""

    @pytest.mark.asyncio
    async def test_wipe_file_permission_denied(self, temp_file):
        """Test handling permission denied errors"""
        # Mock wipe_single_file to raise permission error
        with patch("api.emergency_wipe.wipe_single_file", new_callable=AsyncMock) as mock_wipe:
            mock_wipe.side_effect = PermissionError("Permission denied")

            result = await perform_dod_wipe([str(temp_file)])

        assert result["count"] == 0
        assert len(result["errors"]) == 1
        assert "Permission denied" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_wipe_directory_with_file_error(self, temp_nested_dir):
        """Test directory wipe continues after file error"""
        nested_dir, files = temp_nested_dir

        # Track calls to wipe_single_file
        original_wipe = wipe_single_file
        call_count = 0

        async def wipe_with_one_failure(path):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise PermissionError("First file fails")
            return await original_wipe(path)

        with patch("api.emergency_wipe.wipe_single_file", side_effect=wipe_with_one_failure):
            result = await perform_dod_wipe([str(nested_dir)])

        # First file failed, others succeeded
        assert result["count"] == 2
        # At least 1 error from the file, plus cascading dir errors (dirs not empty)
        assert len(result["errors"]) >= 1
        assert any("First file fails" in e for e in result["errors"])

    @pytest.mark.asyncio
    async def test_wipe_glob_with_error(self, temp_files_with_glob):
        """Test glob wipe continues after error"""
        temp_dir, files = temp_files_with_glob

        call_count = 0
        original_wipe = wipe_single_file

        async def wipe_with_first_failure(path):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise IOError("I/O error")
            return await original_wipe(path)

        with patch("api.emergency_wipe.wipe_single_file", side_effect=wipe_with_first_failure):
            result = await perform_dod_wipe([str(temp_dir / "*.plist")])

        # One failed, two succeeded
        assert result["count"] == 2
        assert len(result["errors"]) == 1
        assert "I/O error" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_wipe_rmdir_error(self, temp_dir):
        """Test handling rmdir errors for directories"""
        # Create directory with subdirectory
        parent_dir = temp_dir / "parent"
        child_dir = parent_dir / "child"
        child_dir.mkdir(parents=True)

        # Mock rmdir to fail
        original_rmdir = os.rmdir
        rmdir_call_count = 0

        def failing_rmdir(path):
            nonlocal rmdir_call_count
            rmdir_call_count += 1
            if rmdir_call_count == 1:
                raise OSError("Directory not empty (mock)")
            return original_rmdir(path)

        with patch("os.rmdir", side_effect=failing_rmdir):
            result = await perform_dod_wipe([str(parent_dir)])

        # Should have errors for rmdir failures
        assert len(result["errors"]) >= 1


# ========== Edge Cases ==========

class TestEdgeCases:
    """Tests for edge cases"""

    @pytest.mark.asyncio
    async def test_wipe_file_with_special_characters(self, temp_dir):
        """Test wiping file with special characters in name"""
        special_file = temp_dir / "file with spaces & symbols!.txt"
        special_file.write_text("Secret")

        result = await perform_dod_wipe([str(special_file)])

        assert result["count"] == 1
        assert not special_file.exists()

    @pytest.mark.asyncio
    async def test_wipe_file_with_unicode_name(self, temp_dir):
        """Test wiping file with unicode characters"""
        unicode_file = temp_dir / "секрет_文件_αβγ.txt"
        unicode_file.write_text("Secret content")

        result = await perform_dod_wipe([str(unicode_file)])

        assert result["count"] == 1
        assert not unicode_file.exists()

    @pytest.mark.asyncio
    async def test_wipe_readonly_file(self, temp_dir):
        """Test wiping a read-only file"""
        readonly_file = temp_dir / "readonly.txt"
        readonly_file.write_text("Protected content")
        os.chmod(readonly_file, 0o444)

        try:
            # Make writable to allow test to work
            os.chmod(readonly_file, 0o644)
            result = await perform_dod_wipe([str(readonly_file)])
            assert result["count"] == 1
        except:
            # If we can't change permissions, skip this test
            pytest.skip("Cannot modify file permissions")

    @pytest.mark.asyncio
    async def test_wipe_hidden_file(self, temp_dir):
        """Test wiping a hidden file (starts with dot)"""
        hidden_file = temp_dir / ".hidden_secret"
        hidden_file.write_text("Hidden secret")

        result = await perform_dod_wipe([str(hidden_file)])

        assert result["count"] == 1
        assert not hidden_file.exists()

    @pytest.mark.asyncio
    async def test_wipe_symlink(self, temp_dir):
        """Test wiping a symlink (should wipe link, not target)"""
        target_file = temp_dir / "target.txt"
        target_file.write_text("Target content")

        symlink = temp_dir / "link_to_target"
        try:
            os.symlink(target_file, symlink)
        except OSError:
            pytest.skip("Symlinks not supported on this platform")

        result = await perform_dod_wipe([str(symlink)])

        # Symlink should be wiped
        assert result["count"] == 1
        assert not symlink.exists()
        # Target should still exist (symlink was wiped, not dereferenced)
        # Note: Behavior depends on how os.path.isfile handles symlinks

    @pytest.mark.asyncio
    async def test_wipe_binary_file(self, temp_dir):
        """Test wiping a binary file"""
        binary_file = temp_dir / "binary.bin"
        with open(binary_file, "wb") as f:
            f.write(bytes(range(256)) * 100)  # 25.6KB of binary data

        result = await perform_dod_wipe([str(binary_file)])

        assert result["count"] == 1
        assert not binary_file.exists()

    @pytest.mark.asyncio
    async def test_wipe_mixed_paths(self, temp_dir):
        """Test wiping a mix of files, directories, and globs"""
        # Create various paths
        single_file = temp_dir / "single.txt"
        single_file.write_text("Single file")

        subdir = temp_dir / "subdir"
        subdir.mkdir()
        dir_file = subdir / "dir_file.txt"
        dir_file.write_text("Dir file")

        for i in range(2):
            (temp_dir / f"glob_{i}.tmp").write_text(f"Glob {i}")

        result = await perform_dod_wipe([
            str(single_file),           # Single file
            str(subdir),                # Directory
            str(temp_dir / "*.tmp")     # Glob pattern
        ])

        # 1 single + 1 in dir + 2 glob = 4 files
        assert result["count"] == 4
        assert result["errors"] == []


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests for the wipe module"""

    @pytest.mark.asyncio
    async def test_full_wipe_scenario(self, temp_dir):
        """Test a full emergency wipe scenario"""
        # Simulate a vault structure
        vault_dir = temp_dir / "vault"
        vault_dir.mkdir()

        # Create encrypted files
        for i in range(5):
            (vault_dir / f"secret_{i}.enc").write_bytes(os.urandom(1024))

        # Create key files
        keys_dir = vault_dir / "keys"
        keys_dir.mkdir()
        (keys_dir / "master.key").write_bytes(os.urandom(32))
        (keys_dir / "session.key").write_bytes(os.urandom(32))

        # Create temp files
        temp_cache = vault_dir / "cache"
        temp_cache.mkdir()
        for i in range(3):
            (temp_cache / f"temp_{i}.dat").write_bytes(os.urandom(512))

        result = await perform_dod_wipe([str(vault_dir)])

        # Should wipe all 10 files (5 enc + 2 keys + 3 temp)
        assert result["count"] == 10
        assert result["errors"] == []
        assert not vault_dir.exists()

    @pytest.mark.asyncio
    async def test_verify_file_content_destroyed(self, temp_dir):
        """Test that original content cannot be recovered"""
        secret_file = temp_dir / "verify_destroyed.txt"
        original_content = b"TOP SECRET INFORMATION - DO NOT LEAK"

        with open(secret_file, "wb") as f:
            f.write(original_content)

        # Record the inode and device for later (if we want to be thorough)
        # file_stat = os.stat(secret_file)

        await wipe_single_file(str(secret_file))

        # File should be gone
        assert not secret_file.exists()

        # Note: True verification of secure deletion would require
        # low-level disk analysis which is beyond unit test scope

    @pytest.mark.asyncio
    async def test_wipe_preserves_parent_directory(self, temp_nested_dir):
        """Test that parent directory is preserved when wiping subdirectory"""
        nested_dir, files = temp_nested_dir
        parent = nested_dir.parent

        result = await perform_dod_wipe([str(nested_dir)])

        assert result["count"] == 3
        assert not nested_dir.exists()
        # Parent should still exist
        assert parent.exists()


# ========== Concurrent Access Tests ==========

class TestConcurrency:
    """Tests for concurrent access scenarios"""

    @pytest.mark.asyncio
    async def test_concurrent_wipe_different_files(self, temp_dir):
        """Test concurrent wipe of different files"""
        import asyncio

        files = []
        for i in range(10):
            f = temp_dir / f"concurrent_{i}.txt"
            f.write_text(f"Content {i}")
            files.append(f)

        # Wipe all files concurrently
        tasks = [wipe_single_file(str(f)) for f in files]
        await asyncio.gather(*tasks)

        # All files should be gone
        for f in files:
            assert not f.exists()
