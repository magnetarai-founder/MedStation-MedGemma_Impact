"""
Phase B Migration: Kanban Workspace

Creates tables for Kanban project management:
- kanban_projects: Top-level project containers
- kanban_boards: Kanban boards within projects
- kanban_columns: Columns within boards
- kanban_tasks: Tasks within columns
- kanban_comments: Comments on tasks
- kanban_wiki: Project wiki pages
"""

import sqlite3
import logging

logger = logging.getLogger(__name__)

def migrate(db_path: str) -> None:
    """Apply Phase B migration: Kanban workspace tables"""
    logger.info("Running Phase B migration: Kanban workspace")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if migration already applied
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='kanban_projects'")
        if cursor.fetchone():
            logger.info("Phase B migration already applied (kanban_projects table exists)")
            return

        # Create kanban_projects table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kanban_projects (
                project_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create kanban_boards table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kanban_boards (
                board_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES kanban_projects(project_id) ON DELETE CASCADE
            )
        """)

        # Create kanban_columns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kanban_columns (
                column_id TEXT PRIMARY KEY,
                board_id TEXT NOT NULL,
                name TEXT NOT NULL,
                position REAL NOT NULL DEFAULT 1.0,
                FOREIGN KEY (board_id) REFERENCES kanban_boards(board_id) ON DELETE CASCADE
            )
        """)

        # Create kanban_tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kanban_tasks (
                task_id TEXT PRIMARY KEY,
                board_id TEXT NOT NULL,
                column_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT,
                assignee_id TEXT,
                priority TEXT,
                due_date TIMESTAMP,
                tags TEXT,
                position REAL NOT NULL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (board_id) REFERENCES kanban_boards(board_id) ON DELETE CASCADE,
                FOREIGN KEY (column_id) REFERENCES kanban_columns(column_id) ON DELETE CASCADE
            )
        """)

        # Create kanban_comments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kanban_comments (
                comment_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES kanban_tasks(task_id) ON DELETE CASCADE
            )
        """)

        # Create kanban_wiki table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kanban_wiki (
                page_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES kanban_projects(project_id) ON DELETE CASCADE
            )
        """)

        # Create indexes for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kanban_boards_project ON kanban_boards(project_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kanban_columns_board ON kanban_columns(board_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kanban_tasks_board ON kanban_tasks(board_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kanban_tasks_column ON kanban_tasks(column_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kanban_comments_task ON kanban_comments(task_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kanban_wiki_project ON kanban_wiki(project_id)")

        # Seed sample project for better first-use UX
        import uuid
        sample_project_id = str(uuid.uuid4())
        sample_board_id = str(uuid.uuid4())

        cursor.execute("""
            INSERT INTO kanban_projects (project_id, name, description)
            VALUES (?, ?, ?)
        """, (sample_project_id, "Welcome to Kanban", "Your first project - feel free to customize or delete"))

        cursor.execute("""
            INSERT INTO kanban_boards (board_id, project_id, name)
            VALUES (?, ?, ?)
        """, (sample_board_id, sample_project_id, "Main Board"))

        # Create default columns
        for idx, (col_name, pos) in enumerate([("To Do", 1.0), ("In Progress", 2.0), ("Done", 3.0)]):
            cursor.execute("""
                INSERT INTO kanban_columns (column_id, board_id, name, position)
                VALUES (?, ?, ?, ?)
            """, (str(uuid.uuid4()), sample_board_id, col_name, pos))

        logger.info("✓ Seeded sample Kanban project and board")

        conn.commit()
        logger.info("✓ Phase B migration completed successfully")

    except Exception as e:
        logger.error(f"Phase B migration failed: {e}", exc_info=True)
        conn.rollback()
        raise
    finally:
        conn.close()
