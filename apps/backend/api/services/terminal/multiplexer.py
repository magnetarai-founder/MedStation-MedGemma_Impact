#!/usr/bin/env python3
"""
Terminal Multiplexer

Provides tmux-like functionality for managing multiple terminal sessions:
- Session groups and workspaces
- Pane splitting and layouts
- Session detach/attach
- Window management
- Persistent sessions across reconnections

Uses the BaseRepository pattern for consistent database operations.
"""
# ruff: noqa: S608

import os
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from api.services.db import BaseRepository, DatabaseConnection

from .pty_session import get_pty_manager


class PaneLayout(Enum):
    """Terminal pane layouts"""

    SINGLE = "single"
    HORIZONTAL = "horizontal"  # Split horizontally (side by side)
    VERTICAL = "vertical"  # Split vertically (top and bottom)
    GRID_2X2 = "grid_2x2"  # 2x2 grid
    MAIN_SIDE = "main_side"  # Main pane with sidebar


@dataclass
class TerminalPane:
    """A terminal pane within a window"""

    pane_id: str
    session_id: str
    size_percentage: float = 100.0  # Percentage of parent space
    is_active: bool = False


@dataclass
class TerminalWindow:
    """A terminal window containing one or more panes"""

    window_id: str
    name: str
    panes: list[TerminalPane] = field(default_factory=list)
    layout: PaneLayout = PaneLayout.SINGLE
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class TerminalWorkspace:
    """A workspace containing multiple windows"""

    workspace_id: str
    name: str
    working_dir: str
    windows: list[TerminalWindow] = field(default_factory=list)
    active_window_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_accessed: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ============================================================================
# Repository Classes
# ============================================================================


class WorkspaceRepository(BaseRepository[TerminalWorkspace]):
    """Repository for terminal workspaces."""

    @property
    def table_name(self) -> str:
        return "workspaces"

    def _create_table_sql(self) -> str:
        return """
            CREATE TABLE IF NOT EXISTS workspaces (
                workspace_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                working_dir TEXT NOT NULL,
                active_window_id TEXT,
                created_at TEXT NOT NULL,
                last_accessed TEXT NOT NULL
            )
        """

    def _row_to_entity(self, row: sqlite3.Row) -> TerminalWorkspace:
        return TerminalWorkspace(
            workspace_id=row["workspace_id"],
            name=row["name"],
            working_dir=row["working_dir"],
            active_window_id=row["active_window_id"],
            created_at=row["created_at"],
            last_accessed=row["last_accessed"],
        )

    def upsert(self, workspace: TerminalWorkspace) -> None:
        """Insert or replace a workspace."""
        self.db.execute(
            """
            INSERT OR REPLACE INTO workspaces
            (workspace_id, name, working_dir, active_window_id, created_at, last_accessed)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                workspace.workspace_id,
                workspace.name,
                workspace.working_dir,
                workspace.active_window_id,
                workspace.created_at,
                workspace.last_accessed,
            ),
        )
        self.db.get().commit()


class WindowRepository(BaseRepository[TerminalWindow]):
    """Repository for terminal windows."""

    @property
    def table_name(self) -> str:
        return "windows"

    def _create_table_sql(self) -> str:
        return """
            CREATE TABLE IF NOT EXISTS windows (
                window_id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                name TEXT NOT NULL,
                layout TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id)
            )
        """

    def _row_to_entity(self, row: sqlite3.Row) -> TerminalWindow:
        return TerminalWindow(
            window_id=row["window_id"],
            name=row["name"],
            layout=PaneLayout(row["layout"]),
            created_at=row["created_at"],
        )

    def _run_migrations(self) -> None:
        """Create indexes for performance."""
        self._create_index(["workspace_id"], name="idx_windows_workspace")

    def upsert(self, workspace_id: str, window: TerminalWindow) -> None:
        """Insert or replace a window."""
        self.db.execute(
            """
            INSERT OR REPLACE INTO windows
            (window_id, workspace_id, name, layout, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (window.window_id, workspace_id, window.name, window.layout.value, window.created_at),
        )
        self.db.get().commit()

    def update_layout(self, window_id: str, layout: PaneLayout) -> None:
        """Update window layout."""
        self.update_where({"layout": layout.value}, "window_id = ?", (window_id,))

    def find_by_workspace(self, workspace_id: str) -> list[TerminalWindow]:
        """Find all windows in a workspace."""
        return self.find_where("workspace_id = ?", (workspace_id,))


class PaneRepository(BaseRepository[TerminalPane]):
    """Repository for terminal panes."""

    @property
    def table_name(self) -> str:
        return "panes"

    def _create_table_sql(self) -> str:
        return """
            CREATE TABLE IF NOT EXISTS panes (
                pane_id TEXT PRIMARY KEY,
                window_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                size_percentage REAL NOT NULL,
                is_active INTEGER DEFAULT 0,
                FOREIGN KEY (window_id) REFERENCES windows(window_id)
            )
        """

    def _row_to_entity(self, row: sqlite3.Row) -> TerminalPane:
        return TerminalPane(
            pane_id=row["pane_id"],
            session_id=row["session_id"],
            size_percentage=row["size_percentage"],
            is_active=bool(row["is_active"]),
        )

    def _run_migrations(self) -> None:
        """Create indexes for performance."""
        self._create_index(["window_id"], name="idx_panes_window")

    def upsert(self, window_id: str, pane: TerminalPane) -> None:
        """Insert or replace a pane."""
        self.db.execute(
            """
            INSERT OR REPLACE INTO panes
            (pane_id, window_id, session_id, size_percentage, is_active)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                pane.pane_id,
                window_id,
                pane.session_id,
                pane.size_percentage,
                1 if pane.is_active else 0,
            ),
        )
        self.db.get().commit()

    def find_by_window(self, window_id: str) -> list[TerminalPane]:
        """Find all panes in a window."""
        return self.find_where("window_id = ?", (window_id,))


class TerminalMultiplexer:
    """
    Terminal multiplexer with tmux-like functionality

    Features:
    - Multiple workspaces per project
    - Multiple windows per workspace
    - Multiple panes per window
    - Session persistence
    - Detach/attach support

    Uses DatabaseConnection and repositories for thread-safe database access.
    """

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            data_dir = Path(os.path.expanduser("~/.magnetarcode/data"))
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = data_dir / "terminal_multiplexer.db"

        # Initialize database connection and repositories
        self._db = DatabaseConnection(db_path)
        self._workspace_repo = WorkspaceRepository(self._db)
        self._window_repo = WindowRepository(self._db)
        self._pane_repo = PaneRepository(self._db)

        self.pty_manager = get_pty_manager()
        self.workspaces: dict[str, TerminalWorkspace] = {}

        self._load_workspaces()

    def _load_workspaces(self) -> None:
        """Load existing workspaces from database using repositories."""
        # Load all workspaces
        for workspace in self._workspace_repo.find_all():
            # Load windows for this workspace
            windows = self._window_repo.find_by_workspace(workspace.workspace_id)
            for window in windows:
                # Load panes for this window
                panes = self._pane_repo.find_by_window(window.window_id)
                window.panes = panes

            workspace.windows = windows
            self.workspaces[workspace.workspace_id] = workspace

    def create_workspace(self, name: str, working_dir: str) -> str:
        """
        Create a new terminal workspace

        Args:
            name: Workspace name
            working_dir: Working directory

        Returns:
            Workspace ID
        """
        workspace_id = f"ws_{uuid.uuid4().hex[:12]}"

        workspace = TerminalWorkspace(workspace_id=workspace_id, name=name, working_dir=working_dir)

        # Create default window
        window_id = self.create_window(workspace_id, "main")
        workspace.active_window_id = window_id

        self.workspaces[workspace_id] = workspace

        # Store in database
        self._workspace_repo.upsert(workspace)

        return workspace_id

    def create_window(
        self, workspace_id: str, name: str, layout: PaneLayout = PaneLayout.SINGLE
    ) -> str:
        """
        Create a new window in a workspace

        Args:
            workspace_id: Workspace ID
            name: Window name
            layout: Initial layout

        Returns:
            Window ID
        """
        workspace = self.workspaces.get(workspace_id)
        if not workspace:
            raise ValueError(f"Workspace not found: {workspace_id}")

        window_id = f"win_{uuid.uuid4().hex[:12]}"

        window = TerminalWindow(window_id=window_id, name=name, layout=layout)

        # Create initial pane
        pane_id = f"pane_{uuid.uuid4().hex[:12]}"

        # Create PTY session for pane
        session_id = self.pty_manager.create_session(working_dir=workspace.working_dir)

        pane = TerminalPane(
            pane_id=pane_id, session_id=session_id, size_percentage=100.0, is_active=True
        )

        window.panes.append(pane)
        workspace.windows.append(window)

        # Store in database using repositories
        self._window_repo.upsert(workspace_id, window)
        self._pane_repo.upsert(window_id, pane)

        return window_id

    def split_pane(self, window_id: str, pane_id: str, direction: str = "horizontal") -> str:
        """
        Split a pane horizontally or vertically

        Args:
            window_id: Window ID
            pane_id: Pane to split
            direction: "horizontal" or "vertical"

        Returns:
            New pane ID
        """
        # Find window
        window = None
        workspace = None
        for ws in self.workspaces.values():
            for win in ws.windows:
                if win.window_id == window_id:
                    window = win
                    workspace = ws
                    break

        if not window or not workspace:
            raise ValueError(f"Window not found: {window_id}")

        # Find pane
        pane = None
        for p in window.panes:
            if p.pane_id == pane_id:
                pane = p
                break

        if not pane:
            raise ValueError(f"Pane not found: {pane_id}")

        # Adjust existing pane size
        pane.size_percentage = 50.0

        # Create new pane
        new_pane_id = f"pane_{uuid.uuid4().hex[:12]}"

        # Create PTY session
        session_id = self.pty_manager.create_session(working_dir=workspace.working_dir)

        new_pane = TerminalPane(
            pane_id=new_pane_id, session_id=session_id, size_percentage=50.0, is_active=False
        )

        window.panes.append(new_pane)

        # Update layout
        if direction == "horizontal" and len(window.panes) == 2:
            window.layout = PaneLayout.HORIZONTAL
        elif direction == "vertical" and len(window.panes) == 2:
            window.layout = PaneLayout.VERTICAL
        elif len(window.panes) >= 4:
            window.layout = PaneLayout.GRID_2X2

        # Store in database using repositories
        self._pane_repo.upsert(window_id, new_pane)
        self._window_repo.update_layout(window_id, window.layout)

        return new_pane_id

    def send_command(self, pane_id: str, command: str) -> bool:
        """
        Send command to a specific pane

        Args:
            pane_id: Pane ID
            command: Command to execute

        Returns:
            True if successful
        """
        # Find pane
        for workspace in self.workspaces.values():
            for window in workspace.windows:
                for pane in window.panes:
                    if pane.pane_id == pane_id:
                        return self.pty_manager.send_command(pane.session_id, command)

        return False

    def get_pane_output(self, pane_id: str, lines: int = 100) -> list[str]:
        """Get output from a specific pane"""
        # Find pane
        for workspace in self.workspaces.values():
            for window in workspace.windows:
                for pane in window.panes:
                    if pane.pane_id == pane_id:
                        return self.pty_manager.get_output(pane.session_id, lines)

        return []

    def close_pane(self, pane_id: str) -> None:
        """Close a specific pane."""
        for workspace in self.workspaces.values():
            for window in workspace.windows:
                for pane in window.panes:
                    if pane.pane_id == pane_id:
                        # Close PTY session
                        self.pty_manager.close_session(pane.session_id)

                        # Remove pane from in-memory list
                        window.panes.remove(pane)

                        # Delete from database using repository
                        self._pane_repo.delete_by_id(pane_id, id_column="pane_id")
                        return

    def close_window(self, window_id: str) -> None:
        """Close a window and all its panes."""
        for workspace in self.workspaces.values():
            for window in workspace.windows:
                if window.window_id == window_id:
                    # Close all PTY sessions
                    for pane in window.panes:
                        self.pty_manager.close_session(pane.session_id)

                    # Remove window from in-memory list
                    workspace.windows.remove(window)

                    # Delete from database using repositories (panes first due to FK)
                    self._pane_repo.delete_where("window_id = ?", (window_id,))
                    self._window_repo.delete_by_id(window_id, id_column="window_id")
                    return

    def get_workspace(self, workspace_id: str) -> dict[str, Any] | None:
        """Get workspace details"""
        workspace = self.workspaces.get(workspace_id)
        if not workspace:
            return None

        return {
            "workspace_id": workspace.workspace_id,
            "name": workspace.name,
            "working_dir": workspace.working_dir,
            "active_window_id": workspace.active_window_id,
            "windows": [
                {
                    "window_id": win.window_id,
                    "name": win.name,
                    "layout": win.layout.value,
                    "panes": [
                        {
                            "pane_id": pane.pane_id,
                            "session_id": pane.session_id,
                            "size_percentage": pane.size_percentage,
                            "is_active": pane.is_active,
                        }
                        for pane in win.panes
                    ],
                }
                for win in workspace.windows
            ],
            "created_at": workspace.created_at,
            "last_accessed": workspace.last_accessed,
        }

    def list_workspaces(self) -> list[dict[str, Any]]:
        """List all workspaces."""
        return [
            {
                "workspace_id": ws.workspace_id,
                "name": ws.name,
                "working_dir": ws.working_dir,
                "window_count": len(ws.windows),
                "created_at": ws.created_at,
                "last_accessed": ws.last_accessed,
            }
            for ws in self.workspaces.values()
        ]


# Global instance
_multiplexer: TerminalMultiplexer | None = None


def get_multiplexer() -> TerminalMultiplexer:
    """Get or create global terminal multiplexer"""
    global _multiplexer
    if _multiplexer is None:
        _multiplexer = TerminalMultiplexer()
    return _multiplexer
