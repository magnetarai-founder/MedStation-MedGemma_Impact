"""
Learning System - Project Context Management

Project context detection and management:
- detect_project_context: Analyze project structure and detect type
- switch_context: Switch between projects
- get_active_projects: Query recently active projects
- Project metadata storage and retrieval

Extracted from learning_system.py during Phase 6.3c modularization.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List
from threading import Lock

try:
    from .models import ProjectContext
except ImportError:
    from models import ProjectContext


def detect_project_context(
    conn: sqlite3.Connection,
    lock: Lock,
    cwd: str = None
) -> ProjectContext:
    """
    Detect and store project context.

    Args:
        conn: SQLite database connection
        lock: Thread lock for DB operations
        cwd: Current working directory (defaults to Path.cwd())

    Returns:
        ProjectContext object with detected metadata
    """
    if cwd is None:
        cwd = str(Path.cwd())

    with lock:
        # Check for existing context
        cursor = conn.execute("""
            SELECT project_data, activity_count
            FROM project_contexts
            WHERE project_path = ?
        """, (cwd,))

        row = cursor.fetchone()

        if row:
            # Update activity
            conn.execute("""
                UPDATE project_contexts
                SET activity_count = activity_count + 1,
                    last_active = CURRENT_TIMESTAMP
                WHERE project_path = ?
            """, (cwd,))
            conn.commit()

            data = json.loads(row['project_data'])
            return ProjectContext(
                project_path=cwd,
                project_type=data['project_type'],
                languages=data['languages'],
                frameworks=data['frameworks'],
                dependencies=data['dependencies'],
                typical_workflows=data.get('typical_workflows', []),
                last_active=datetime.now().isoformat(),
                activity_count=row['activity_count'] + 1
            )
        else:
            # Detect new project context
            context = _analyze_project(cwd)
            _store_project_context(conn, context)
            conn.commit()
            return context


def switch_context(
    conn: sqlite3.Connection,
    lock: Lock,
    project_path: str
) -> ProjectContext:
    """
    Switch to a different project context.

    Args:
        conn: SQLite database connection
        lock: Thread lock for DB operations
        project_path: Path to the project

    Returns:
        ProjectContext for the specified project
    """
    return detect_project_context(conn, lock, project_path)


def get_active_projects(
    conn: sqlite3.Connection,
    limit: int = 5
) -> List[ProjectContext]:
    """
    Get recently active projects.

    Args:
        conn: SQLite database connection
        limit: Maximum number of projects to return

    Returns:
        List of ProjectContext objects, ordered by last activity
    """
    cursor = conn.execute("""
        SELECT project_path, project_type, project_data, activity_count, last_active
        FROM project_contexts
        ORDER BY last_active DESC
        LIMIT ?
    """, (limit,))

    projects = []
    for row in cursor:
        data = json.loads(row['project_data'])
        projects.append(ProjectContext(
            project_path=row['project_path'],
            project_type=row['project_type'],
            languages=data['languages'],
            frameworks=data['frameworks'],
            dependencies=data['dependencies'],
            typical_workflows=data.get('typical_workflows', []),
            last_active=row['last_active'],
            activity_count=row['activity_count']
        ))

    return projects


def _analyze_project(project_path: str) -> ProjectContext:
    """
    Analyze project structure and detect context.

    Detects:
    - Programming languages (by file extensions)
    - Project type (Node, Python, Rust, Go, etc.)
    - Frameworks (React, Django, Flask, FastAPI, Express, Vue)
    - Dependencies (from package.json, requirements.txt)
    - Typical workflows (Make, GitHub Actions, Docker)

    Args:
        project_path: Path to the project directory

    Returns:
        ProjectContext with detected metadata
    """
    path = Path(project_path)
    languages = set()
    frameworks = []
    dependencies = []
    project_type = 'unknown'

    # Detect languages
    for ext in ['.py', '.js', '.ts', '.java', '.go', '.rs']:
        if list(path.rglob(f'*{ext}')):
            languages.add(ext[1:])

    # Detect project type and frameworks - Node
    if (path / 'package.json').exists():
        project_type = 'node'
        try:
            with open(path / 'package.json') as f:
                pkg = json.load(f)
                dependencies = list(pkg.get('dependencies', {}).keys())

                # Detect frameworks
                if 'react' in dependencies:
                    frameworks.append('react')
                if 'express' in dependencies:
                    frameworks.append('express')
                if 'vue' in dependencies:
                    frameworks.append('vue')
        except:
            pass

    # Detect project type and frameworks - Python
    elif (path / 'requirements.txt').exists() or (path / 'setup.py').exists():
        project_type = 'python'
        if (path / 'requirements.txt').exists():
            try:
                with open(path / 'requirements.txt') as f:
                    dependencies = [line.split('==')[0].strip()
                                  for line in f if line.strip() and not line.startswith('#')]

                # Detect frameworks
                if 'django' in dependencies:
                    frameworks.append('django')
                if 'flask' in dependencies:
                    frameworks.append('flask')
                if 'fastapi' in dependencies:
                    frameworks.append('fastapi')
            except:
                pass

    # Detect other project types
    elif (path / 'Cargo.toml').exists():
        project_type = 'rust'

    elif (path / 'go.mod').exists():
        project_type = 'go'

    # Detect typical workflows based on files
    workflows = []
    if (path / 'Makefile').exists():
        workflows.append('make')
    if (path / '.github' / 'workflows').exists():
        workflows.append('github-actions')
    if (path / 'Dockerfile').exists():
        workflows.append('docker')

    return ProjectContext(
        project_path=project_path,
        project_type=project_type,
        languages=list(languages),
        frameworks=frameworks,
        dependencies=dependencies[:20],  # Limit stored deps
        typical_workflows=workflows,
        last_active=datetime.now().isoformat(),
        activity_count=1
    )


def _store_project_context(conn: sqlite3.Connection, context: ProjectContext) -> None:
    """
    Store project context in database.

    Args:
        conn: SQLite database connection
        context: ProjectContext to store
    """
    project_data = {
        'project_type': context.project_type,
        'languages': context.languages,
        'frameworks': context.frameworks,
        'dependencies': context.dependencies,
        'typical_workflows': context.typical_workflows
    }

    conn.execute("""
        INSERT OR REPLACE INTO project_contexts
        (project_path, project_type, project_data, activity_count, last_active)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (
        context.project_path,
        context.project_type,
        json.dumps(project_data),
        context.activity_count
    ))
