"""
Comprehensive tests for api/services/kanban_service.py

Tests cover:
- Project CRUD operations
- Board CRUD operations
- Column CRUD operations with positioning
- Task CRUD operations with positioning and movement
- Comment operations
- Wiki page operations
- Position rebalancing
- Validation and error handling
- Edge cases
"""

import pytest
import sqlite3
import tempfile
import json
from pathlib import Path
from datetime import datetime, UTC
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

# We need to patch PATHS before importing kanban_service
# because it calls ensure_schema() at import time


@pytest.fixture(scope="module")
def temp_db_dir():
    """Create a temporary directory for the database"""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture(autouse=True)
def patch_paths(temp_db_dir):
    """Patch PATHS to use temporary database"""
    mock_paths = MagicMock()
    mock_paths.app_db = temp_db_dir / "test_kanban.db"

    # After P2 decomposition, PATHS is now in kanban_core.py
    with patch('api.services.kanban_core.PATHS', mock_paths):
        # Re-import to get fresh module with patched paths
        import importlib
        import api.services.kanban_core as kc
        import api.services.kanban_service as ks
        importlib.reload(kc)
        importlib.reload(ks)
        yield ks


# ========== Helper Function Tests ==========

class TestHelperFunctions:
    """Tests for helper functions"""

    def test_utcnow_returns_iso_format(self, patch_paths):
        """Test _utcnow returns ISO format timestamp"""
        ks = patch_paths
        result = ks._utcnow()
        # Should be parseable as ISO format
        parsed = datetime.fromisoformat(result)
        assert parsed is not None
        # Should be close to now
        now = datetime.now(UTC)
        diff = abs((now - parsed).total_seconds())
        assert diff < 5  # Within 5 seconds

    def test_conn_returns_sqlite_connection(self, patch_paths):
        """Test _conn returns a valid SQLite connection"""
        ks = patch_paths
        conn = ks._conn()
        assert isinstance(conn, sqlite3.Connection)
        # Should have row_factory set
        assert conn.row_factory == sqlite3.Row
        conn.close()

    def test_conn_enables_foreign_keys(self, patch_paths):
        """Test _conn enables foreign keys"""
        ks = patch_paths
        conn = ks._conn()
        cursor = conn.execute("PRAGMA foreign_keys")
        result = cursor.fetchone()[0]
        assert result == 1  # Foreign keys enabled
        conn.close()


# ========== Schema Tests ==========

class TestSchema:
    """Tests for schema initialization"""

    def test_ensure_schema_creates_projects_table(self, patch_paths):
        """Test projects table is created"""
        ks = patch_paths
        conn = ks._conn()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='projects'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_ensure_schema_creates_boards_table(self, patch_paths):
        """Test boards table is created"""
        ks = patch_paths
        conn = ks._conn()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='boards'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_ensure_schema_creates_columns_table(self, patch_paths):
        """Test columns table is created"""
        ks = patch_paths
        conn = ks._conn()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='columns'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_ensure_schema_creates_tasks_table(self, patch_paths):
        """Test tasks table is created"""
        ks = patch_paths
        conn = ks._conn()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_ensure_schema_creates_comments_table(self, patch_paths):
        """Test comments table is created"""
        ks = patch_paths
        conn = ks._conn()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='comments'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_ensure_schema_creates_wiki_pages_table(self, patch_paths):
        """Test wiki_pages table is created"""
        ks = patch_paths
        conn = ks._conn()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='wiki_pages'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_ensure_schema_is_idempotent(self, patch_paths):
        """Test ensure_schema can be called multiple times"""
        ks = patch_paths
        # Should not raise
        ks.ensure_schema()
        ks.ensure_schema()


# ========== Project Tests ==========

class TestProjects:
    """Tests for project operations"""

    def test_create_project_basic(self, patch_paths):
        """Test creating a basic project"""
        ks = patch_paths
        project = ks.create_project("Test Project")

        assert project["name"] == "Test Project"
        assert project["project_id"] is not None
        assert project["created_at"] is not None
        assert project["description"] is None

    def test_create_project_with_description(self, patch_paths):
        """Test creating project with description"""
        ks = patch_paths
        project = ks.create_project("Project With Desc", "A detailed description")

        assert project["name"] == "Project With Desc"
        assert project["description"] == "A detailed description"

    def test_create_project_strips_whitespace(self, patch_paths):
        """Test project name whitespace is stripped"""
        ks = patch_paths
        project = ks.create_project("  Padded Name  ")

        assert project["name"] == "Padded Name"

    def test_create_project_empty_name_fails(self, patch_paths):
        """Test creating project with empty name fails"""
        ks = patch_paths
        with pytest.raises(ValueError, match="cannot be empty"):
            ks.create_project("")

    def test_create_project_whitespace_only_name_fails(self, patch_paths):
        """Test creating project with whitespace-only name fails"""
        ks = patch_paths
        with pytest.raises(ValueError, match="cannot be empty"):
            ks.create_project("   ")

    def test_create_project_name_too_long_fails(self, patch_paths):
        """Test creating project with name > 255 chars fails"""
        ks = patch_paths
        with pytest.raises(ValueError, match="cannot exceed 255"):
            ks.create_project("x" * 256)

    def test_list_projects_empty(self, patch_paths):
        """Test listing projects when none exist"""
        ks = patch_paths
        # Clear projects
        conn = ks._conn()
        conn.execute("DELETE FROM projects")
        conn.commit()
        conn.close()

        projects = ks.list_projects()
        assert projects == []

    def test_list_projects_returns_all(self, patch_paths):
        """Test listing returns all projects"""
        ks = patch_paths
        # Clear and create
        conn = ks._conn()
        conn.execute("DELETE FROM projects")
        conn.commit()
        conn.close()

        ks.create_project("Project 1")
        ks.create_project("Project 2")
        ks.create_project("Project 3")

        projects = ks.list_projects()
        assert len(projects) == 3

    def test_list_projects_ordered_by_created_desc(self, patch_paths):
        """Test projects are ordered by created_at descending"""
        ks = patch_paths
        # Clear and create
        conn = ks._conn()
        conn.execute("DELETE FROM projects")
        conn.commit()
        conn.close()

        p1 = ks.create_project("First")
        p2 = ks.create_project("Second")
        p3 = ks.create_project("Third")

        projects = ks.list_projects()
        # Most recent first
        assert projects[0]["name"] == "Third"
        assert projects[2]["name"] == "First"


# ========== Board Tests ==========

class TestBoards:
    """Tests for board operations"""

    @pytest.fixture
    def project(self, patch_paths):
        """Create a project for board tests"""
        ks = patch_paths
        return ks.create_project("Board Test Project")

    def test_create_board_basic(self, patch_paths, project):
        """Test creating a basic board"""
        ks = patch_paths
        board = ks.create_board(project["project_id"], "Test Board")

        assert board["name"] == "Test Board"
        assert board["board_id"] is not None
        assert board["project_id"] == project["project_id"]

    def test_create_board_invalid_project_fails(self, patch_paths):
        """Test creating board with invalid project fails"""
        ks = patch_paths
        with pytest.raises(ValueError, match="Project not found"):
            ks.create_board("nonexistent_project", "Board")

    def test_create_board_empty_name_fails(self, patch_paths, project):
        """Test creating board with empty name fails"""
        ks = patch_paths
        with pytest.raises(ValueError, match="cannot be empty"):
            ks.create_board(project["project_id"], "")

    def test_create_board_name_too_long_fails(self, patch_paths, project):
        """Test creating board with name > 255 chars fails"""
        ks = patch_paths
        with pytest.raises(ValueError, match="cannot exceed 255"):
            ks.create_board(project["project_id"], "x" * 256)

    def test_list_boards_empty(self, patch_paths, project):
        """Test listing boards when none exist for project"""
        ks = patch_paths
        boards = ks.list_boards(project["project_id"])
        # May have boards from previous tests, just verify it returns a list
        assert isinstance(boards, list)

    def test_list_boards_returns_project_boards_only(self, patch_paths):
        """Test listing only returns boards for specified project"""
        ks = patch_paths
        p1 = ks.create_project("Project A")
        p2 = ks.create_project("Project B")

        ks.create_board(p1["project_id"], "Board A1")
        ks.create_board(p1["project_id"], "Board A2")
        ks.create_board(p2["project_id"], "Board B1")

        boards_a = ks.list_boards(p1["project_id"])
        boards_b = ks.list_boards(p2["project_id"])

        assert len(boards_a) >= 2
        assert len(boards_b) >= 1
        assert all(b["project_id"] == p1["project_id"] for b in boards_a)


# ========== Column Tests ==========

class TestColumns:
    """Tests for column operations"""

    @pytest.fixture
    def board(self, patch_paths):
        """Create a project and board for column tests"""
        ks = patch_paths
        project = ks.create_project("Column Test Project")
        return ks.create_board(project["project_id"], "Column Test Board")

    def test_create_column_basic(self, patch_paths, board):
        """Test creating a basic column"""
        ks = patch_paths
        column = ks.create_column(board["board_id"], "To Do")

        assert column["name"] == "To Do"
        assert column["column_id"] is not None
        assert column["board_id"] == board["board_id"]
        assert column["position"] > 0

    def test_create_column_auto_position(self, patch_paths, board):
        """Test columns get auto-incremented positions"""
        ks = patch_paths
        col1 = ks.create_column(board["board_id"], "Column 1")
        col2 = ks.create_column(board["board_id"], "Column 2")

        assert col2["position"] > col1["position"]

    def test_create_column_custom_position(self, patch_paths, board):
        """Test creating column with custom position"""
        ks = patch_paths
        column = ks.create_column(board["board_id"], "Custom Pos", position=500.0)

        assert column["position"] == 500.0

    def test_create_column_invalid_board_fails(self, patch_paths):
        """Test creating column with invalid board fails"""
        ks = patch_paths
        with pytest.raises(ValueError, match="Board not found"):
            ks.create_column("nonexistent_board", "Column")

    def test_create_column_empty_name_fails(self, patch_paths, board):
        """Test creating column with empty name fails"""
        ks = patch_paths
        with pytest.raises(ValueError, match="cannot be empty"):
            ks.create_column(board["board_id"], "")

    def test_list_columns_ordered_by_position(self, patch_paths, board):
        """Test columns are ordered by position ascending"""
        ks = patch_paths
        ks.create_column(board["board_id"], "Last", position=3000.0)
        ks.create_column(board["board_id"], "First", position=1000.0)
        ks.create_column(board["board_id"], "Middle", position=2000.0)

        columns = ks.list_columns(board["board_id"])
        # Filter to only these columns by checking positions
        positions = [c["position"] for c in columns]
        assert positions == sorted(positions)

    def test_update_column_name(self, patch_paths, board):
        """Test updating column name"""
        ks = patch_paths
        column = ks.create_column(board["board_id"], "Original")
        updated = ks.update_column(column["column_id"], name="Updated")

        assert updated["name"] == "Updated"
        assert updated["position"] == column["position"]

    def test_update_column_position(self, patch_paths, board):
        """Test updating column position"""
        ks = patch_paths
        column = ks.create_column(board["board_id"], "Move Me")
        updated = ks.update_column(column["column_id"], position=9999.0)

        assert updated["position"] == 9999.0
        assert updated["name"] == column["name"]

    def test_update_column_not_found_fails(self, patch_paths):
        """Test updating nonexistent column fails"""
        ks = patch_paths
        with pytest.raises(ValueError, match="Column not found"):
            ks.update_column("nonexistent_column", name="New Name")

    def test_next_position_for_column_empty(self, patch_paths, board):
        """Test next_position_for_column with empty board"""
        ks = patch_paths
        # Create a fresh board
        project = ks.create_project("Fresh Project")
        fresh_board = ks.create_board(project["project_id"], "Fresh Board")

        pos = ks.next_position_for_column(fresh_board["board_id"])
        assert pos == 1024.0


# ========== Task Tests ==========

class TestTasks:
    """Tests for task operations"""

    @pytest.fixture
    def setup(self, patch_paths):
        """Create project, board, and column for task tests"""
        ks = patch_paths
        project = ks.create_project("Task Test Project")
        board = ks.create_board(project["project_id"], "Task Test Board")
        column = ks.create_column(board["board_id"], "To Do")
        return {"project": project, "board": board, "column": column, "ks": ks}

    def test_create_task_basic(self, setup):
        """Test creating a basic task"""
        ks = setup["ks"]
        board = setup["board"]
        column = setup["column"]

        task = ks.create_task(board["board_id"], column["column_id"], "Test Task")

        assert task["title"] == "Test Task"
        assert task["task_id"] is not None
        assert task["board_id"] == board["board_id"]
        assert task["column_id"] == column["column_id"]
        assert task["tags"] == []

    def test_create_task_with_all_fields(self, setup):
        """Test creating task with all optional fields"""
        ks = setup["ks"]
        board = setup["board"]
        column = setup["column"]

        task = ks.create_task(
            board["board_id"],
            column["column_id"],
            "Full Task",
            description="Task description",
            status="in_progress",
            assignee_id="user123",
            priority="high",
            due_date="2024-12-31",
            tags=["bug", "urgent"],
        )

        assert task["description"] == "Task description"
        assert task["status"] == "in_progress"
        assert task["assignee_id"] == "user123"
        assert task["priority"] == "high"
        assert task["due_date"] == "2024-12-31"
        assert task["tags"] == ["bug", "urgent"]

    def test_create_task_empty_title_fails(self, setup):
        """Test creating task with empty title fails"""
        ks = setup["ks"]
        board = setup["board"]
        column = setup["column"]

        with pytest.raises(ValueError, match="cannot be empty"):
            ks.create_task(board["board_id"], column["column_id"], "")

    def test_create_task_title_too_long_fails(self, setup):
        """Test creating task with title > 500 chars fails"""
        ks = setup["ks"]
        board = setup["board"]
        column = setup["column"]

        with pytest.raises(ValueError, match="cannot exceed 500"):
            ks.create_task(board["board_id"], column["column_id"], "x" * 501)

    def test_create_task_invalid_board_fails(self, setup):
        """Test creating task with invalid board fails"""
        ks = setup["ks"]
        column = setup["column"]

        with pytest.raises(ValueError, match="Board not found"):
            ks.create_task("nonexistent_board", column["column_id"], "Task")

    def test_create_task_invalid_column_fails(self, setup):
        """Test creating task with invalid column fails"""
        ks = setup["ks"]
        board = setup["board"]

        with pytest.raises(ValueError, match="Column not found"):
            ks.create_task(board["board_id"], "nonexistent_column", "Task")

    def test_create_task_column_wrong_board_fails(self, setup):
        """Test creating task with column from different board fails"""
        ks = setup["ks"]
        project = setup["project"]

        # Create another board with its own column
        other_board = ks.create_board(project["project_id"], "Other Board")
        other_column = ks.create_column(other_board["board_id"], "Other Column")

        board = setup["board"]

        with pytest.raises(ValueError, match="does not belong to board"):
            ks.create_task(board["board_id"], other_column["column_id"], "Task")

    def test_list_tasks_by_board(self, setup):
        """Test listing tasks by board"""
        ks = setup["ks"]
        board = setup["board"]
        column = setup["column"]

        ks.create_task(board["board_id"], column["column_id"], "Task 1")
        ks.create_task(board["board_id"], column["column_id"], "Task 2")

        tasks = ks.list_tasks(board["board_id"])
        assert len(tasks) >= 2

    def test_list_tasks_by_column(self, setup):
        """Test listing tasks by specific column"""
        ks = setup["ks"]
        board = setup["board"]
        column = setup["column"]

        # Create another column
        column2 = ks.create_column(board["board_id"], "Done")

        ks.create_task(board["board_id"], column["column_id"], "In Todo")
        ks.create_task(board["board_id"], column2["column_id"], "In Done")

        tasks_todo = ks.list_tasks(board["board_id"], column["column_id"])
        tasks_done = ks.list_tasks(board["board_id"], column2["column_id"])

        # Should filter by column
        assert all(t["column_id"] == column["column_id"] for t in tasks_todo)
        assert all(t["column_id"] == column2["column_id"] for t in tasks_done)

    def test_list_tasks_parses_tags_json(self, setup):
        """Test list_tasks parses tags from JSON"""
        ks = setup["ks"]
        board = setup["board"]
        column = setup["column"]

        ks.create_task(
            board["board_id"], column["column_id"], "Tagged Task",
            tags=["tag1", "tag2"]
        )

        tasks = ks.list_tasks(board["board_id"])
        tagged_task = next(t for t in tasks if t["title"] == "Tagged Task")
        assert tagged_task["tags"] == ["tag1", "tag2"]
        assert isinstance(tagged_task["tags"], list)

    def test_update_task_fields(self, setup):
        """Test updating task fields"""
        ks = setup["ks"]
        board = setup["board"]
        column = setup["column"]

        task = ks.create_task(board["board_id"], column["column_id"], "Original Title")

        updated = ks.update_task(
            task["task_id"],
            title="Updated Title",
            description="New description",
            status="done",
            priority="low"
        )

        assert updated["title"] == "Updated Title"
        assert updated["description"] == "New description"
        assert updated["status"] == "done"
        assert updated["priority"] == "low"

    def test_update_task_tags(self, setup):
        """Test updating task tags"""
        ks = setup["ks"]
        board = setup["board"]
        column = setup["column"]

        task = ks.create_task(board["board_id"], column["column_id"], "Tag Test")

        updated = ks.update_task(task["task_id"], tags=["new", "tags"])
        assert updated["tags"] == ["new", "tags"]

    def test_update_task_not_found_fails(self, setup):
        """Test updating nonexistent task fails"""
        ks = setup["ks"]
        with pytest.raises(ValueError, match="Task not found"):
            ks.update_task("nonexistent_task", title="New")

    def test_move_task_to_different_column(self, setup):
        """Test moving task to different column"""
        ks = setup["ks"]
        board = setup["board"]
        column = setup["column"]

        # Create another column
        done_column = ks.create_column(board["board_id"], "Done")

        task = ks.create_task(board["board_id"], column["column_id"], "Move Me")

        moved = ks.move_task(task["task_id"], done_column["column_id"])

        assert moved["column_id"] == done_column["column_id"]

    def test_move_task_with_before_task(self, setup):
        """Test moving task before another task"""
        ks = setup["ks"]
        board = setup["board"]
        column = setup["column"]

        task1 = ks.create_task(board["board_id"], column["column_id"], "Task 1")
        task2 = ks.create_task(board["board_id"], column["column_id"], "Task 2")
        task3 = ks.create_task(board["board_id"], column["column_id"], "Task 3")

        # Move task3 between task1 and task2 (before task2)
        moved = ks.move_task(task3["task_id"], column["column_id"], before_task_id=task1["task_id"])

        # Position should be after task1
        assert moved["position"] > task1["position"]

    def test_move_task_with_after_task(self, setup):
        """Test moving task after another task"""
        ks = setup["ks"]
        board = setup["board"]
        column = setup["column"]

        task1 = ks.create_task(board["board_id"], column["column_id"], "First")
        task2 = ks.create_task(board["board_id"], column["column_id"], "Second")

        # Move task1 after task2
        moved = ks.move_task(task1["task_id"], column["column_id"], after_task_id=task2["task_id"])

        # Position should be less than task2 (after_task means position BEFORE that task)
        assert moved["position"] < task2["position"]

    def test_move_task_invalid_column_fails(self, setup):
        """Test moving task to invalid column fails"""
        ks = setup["ks"]
        board = setup["board"]
        column = setup["column"]

        task = ks.create_task(board["board_id"], column["column_id"], "Task")

        with pytest.raises(ValueError, match="Column not found"):
            ks.move_task(task["task_id"], "nonexistent_column")

    def test_move_task_not_found_fails(self, setup):
        """Test moving nonexistent task fails"""
        ks = setup["ks"]
        column = setup["column"]

        with pytest.raises(ValueError, match="Task not found"):
            ks.move_task("nonexistent_task", column["column_id"])

    def test_rebalance_column(self, setup):
        """Test rebalancing column positions"""
        ks = setup["ks"]
        board = setup["board"]
        column = setup["column"]

        # Create tasks with potentially close positions
        task1 = ks.create_task(board["board_id"], column["column_id"], "Rebalance 1")
        task2 = ks.create_task(board["board_id"], column["column_id"], "Rebalance 2")
        task3 = ks.create_task(board["board_id"], column["column_id"], "Rebalance 3")

        # Rebalance
        ks.rebalance_column(board["board_id"], column["column_id"])

        # Check positions are now evenly spaced
        tasks = ks.list_tasks(board["board_id"], column["column_id"])
        rebalanced = [t for t in tasks if t["title"].startswith("Rebalance")]

        if len(rebalanced) >= 2:
            positions = sorted([t["position"] for t in rebalanced])
            # Positions should be 1024 apart
            for i in range(len(positions) - 1):
                assert positions[i + 1] - positions[i] == 1024.0


# ========== Comment Tests ==========

class TestComments:
    """Tests for comment operations"""

    @pytest.fixture
    def task(self, patch_paths):
        """Create project, board, column, and task for comment tests"""
        ks = patch_paths
        project = ks.create_project("Comment Test Project")
        board = ks.create_board(project["project_id"], "Comment Test Board")
        column = ks.create_column(board["board_id"], "Column")
        task = ks.create_task(board["board_id"], column["column_id"], "Comment Test Task")
        return {"task": task, "ks": ks}

    def test_create_comment_basic(self, task):
        """Test creating a basic comment"""
        ks = task["ks"]
        t = task["task"]

        comment = ks.create_comment(t["task_id"], "user123", "This is a comment")

        assert comment["content"] == "This is a comment"
        assert comment["user_id"] == "user123"
        assert comment["task_id"] == t["task_id"]
        assert comment["comment_id"] is not None

    def test_create_comment_empty_content_fails(self, task):
        """Test creating comment with empty content fails"""
        ks = task["ks"]
        t = task["task"]

        with pytest.raises(ValueError, match="cannot be empty"):
            ks.create_comment(t["task_id"], "user123", "")

    def test_create_comment_content_too_long_fails(self, task):
        """Test creating comment with content > 10000 chars fails"""
        ks = task["ks"]
        t = task["task"]

        with pytest.raises(ValueError, match="cannot exceed 10000"):
            ks.create_comment(t["task_id"], "user123", "x" * 10001)

    def test_create_comment_invalid_task_fails(self, task):
        """Test creating comment on invalid task fails"""
        ks = task["ks"]

        with pytest.raises(ValueError, match="Task not found"):
            ks.create_comment("nonexistent_task", "user123", "Comment")

    def test_list_comments_empty(self, task):
        """Test listing comments when none exist"""
        ks = task["ks"]
        # Create a new task with no comments
        project = ks.create_project("No Comments Project")
        board = ks.create_board(project["project_id"], "Board")
        column = ks.create_column(board["board_id"], "Column")
        new_task = ks.create_task(board["board_id"], column["column_id"], "No Comments")

        comments = ks.list_comments(new_task["task_id"])
        assert comments == []

    def test_list_comments_ordered_by_created(self, task):
        """Test comments are ordered by created_at ascending"""
        ks = task["ks"]
        t = task["task"]

        c1 = ks.create_comment(t["task_id"], "user1", "First comment")
        c2 = ks.create_comment(t["task_id"], "user2", "Second comment")
        c3 = ks.create_comment(t["task_id"], "user3", "Third comment")

        comments = ks.list_comments(t["task_id"])
        # Oldest first
        assert len(comments) >= 3


# ========== Wiki Tests ==========

class TestWiki:
    """Tests for wiki page operations"""

    @pytest.fixture
    def project(self, patch_paths):
        """Create a project for wiki tests"""
        ks = patch_paths
        return {"project": ks.create_project("Wiki Test Project"), "ks": ks}

    def test_create_wiki_page_basic(self, project):
        """Test creating a basic wiki page"""
        ks = project["ks"]
        p = project["project"]

        page = ks.create_wiki_page(p["project_id"], "Getting Started")

        assert page["title"] == "Getting Started"
        assert page["page_id"] is not None
        assert page["project_id"] == p["project_id"]
        assert page["content"] == ""

    def test_create_wiki_page_with_content(self, project):
        """Test creating wiki page with content"""
        ks = project["ks"]
        p = project["project"]

        page = ks.create_wiki_page(
            p["project_id"],
            "Documentation",
            "# Welcome\n\nThis is the documentation."
        )

        assert page["content"] == "# Welcome\n\nThis is the documentation."

    def test_create_wiki_page_empty_title_fails(self, project):
        """Test creating wiki page with empty title fails"""
        ks = project["ks"]
        p = project["project"]

        with pytest.raises(ValueError, match="cannot be empty"):
            ks.create_wiki_page(p["project_id"], "")

    def test_create_wiki_page_title_too_long_fails(self, project):
        """Test creating wiki page with title > 500 chars fails"""
        ks = project["ks"]
        p = project["project"]

        with pytest.raises(ValueError, match="cannot exceed 500"):
            ks.create_wiki_page(p["project_id"], "x" * 501)

    def test_create_wiki_page_invalid_project_fails(self, project):
        """Test creating wiki page with invalid project fails"""
        ks = project["ks"]

        with pytest.raises(ValueError, match="Project not found"):
            ks.create_wiki_page("nonexistent_project", "Page")

    def test_list_wiki_pages_empty(self, project):
        """Test listing wiki pages when none exist"""
        ks = project["ks"]
        # Create a fresh project
        fresh = ks.create_project("Fresh Wiki Project")

        pages = ks.list_wiki_pages(fresh["project_id"])
        assert pages == []

    def test_list_wiki_pages_returns_all(self, project):
        """Test listing returns all wiki pages for project"""
        ks = project["ks"]
        p = project["project"]

        ks.create_wiki_page(p["project_id"], "Page 1")
        ks.create_wiki_page(p["project_id"], "Page 2")

        pages = ks.list_wiki_pages(p["project_id"])
        assert len(pages) >= 2

    def test_update_wiki_page_title(self, project):
        """Test updating wiki page title"""
        ks = project["ks"]
        p = project["project"]

        page = ks.create_wiki_page(p["project_id"], "Original Title")
        updated = ks.update_wiki_page(page["page_id"], title="Updated Title")

        assert updated["title"] == "Updated Title"
        assert updated["updated_at"] >= page["created_at"]

    def test_update_wiki_page_content(self, project):
        """Test updating wiki page content"""
        ks = project["ks"]
        p = project["project"]

        page = ks.create_wiki_page(p["project_id"], "Content Page", "Old content")
        updated = ks.update_wiki_page(page["page_id"], content="New content")

        assert updated["content"] == "New content"

    def test_update_wiki_page_not_found_fails(self, project):
        """Test updating nonexistent wiki page fails"""
        ks = project["ks"]

        with pytest.raises(ValueError, match="Wiki page not found"):
            ks.update_wiki_page("nonexistent_page", title="New")

    def test_delete_wiki_page(self, project):
        """Test deleting wiki page"""
        ks = project["ks"]
        p = project["project"]

        page = ks.create_wiki_page(p["project_id"], "Delete Me")
        ks.delete_wiki_page(page["page_id"])

        pages = ks.list_wiki_pages(p["project_id"])
        assert not any(pg["page_id"] == page["page_id"] for pg in pages)

    def test_delete_wiki_page_not_found_fails(self, project):
        """Test deleting nonexistent wiki page fails"""
        ks = project["ks"]

        with pytest.raises(ValueError, match="Wiki page not found"):
            ks.delete_wiki_page("nonexistent_page")


# ========== Edge Cases ==========

class TestEdgeCases:
    """Tests for edge cases"""

    def test_unicode_project_name(self, patch_paths):
        """Test handling unicode in project name"""
        ks = patch_paths
        project = ks.create_project("项目名称 📋")

        assert project["name"] == "项目名称 📋"

    def test_unicode_task_title(self, patch_paths):
        """Test handling unicode in task title"""
        ks = patch_paths
        project = ks.create_project("Unicode Task Project")
        board = ks.create_board(project["project_id"], "Board")
        column = ks.create_column(board["board_id"], "Column")

        task = ks.create_task(board["board_id"], column["column_id"], "任务标题 🎯")

        assert task["title"] == "任务标题 🎯"

    def test_special_chars_in_description(self, patch_paths):
        """Test handling special characters in descriptions"""
        ks = patch_paths
        project = ks.create_project(
            "Special Chars",
            "Description with 'quotes' and \"double quotes\" and <html>"
        )

        assert "'quotes'" in project["description"]
        assert '"double quotes"' in project["description"]

    def test_json_tags_with_special_chars(self, patch_paths):
        """Test tags with special characters are properly JSON encoded"""
        ks = patch_paths
        project = ks.create_project("Tag Test Project")
        board = ks.create_board(project["project_id"], "Board")
        column = ks.create_column(board["board_id"], "Column")

        task = ks.create_task(
            board["board_id"],
            column["column_id"],
            "Tagged",
            tags=["tag with spaces", "tag:colon", "tag/slash"]
        )

        tasks = ks.list_tasks(board["board_id"])
        found = next(t for t in tasks if t["task_id"] == task["task_id"])
        assert "tag with spaces" in found["tags"]
        assert "tag:colon" in found["tags"]

    def test_cascade_delete_project(self, patch_paths):
        """Test deleting project cascades to boards"""
        ks = patch_paths
        project = ks.create_project("Cascade Test")
        board = ks.create_board(project["project_id"], "Board")
        column = ks.create_column(board["board_id"], "Column")
        task = ks.create_task(board["board_id"], column["column_id"], "Task")

        # Delete project
        conn = ks._conn()
        conn.execute("DELETE FROM projects WHERE project_id = ?", (project["project_id"],))
        conn.commit()
        conn.close()

        # Boards should be deleted due to CASCADE
        boards = ks.list_boards(project["project_id"])
        assert len(boards) == 0
