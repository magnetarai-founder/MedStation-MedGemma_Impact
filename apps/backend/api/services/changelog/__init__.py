"""
Changelog Generation Service

Provides comprehensive changelog generation capabilities:
- Parses git commit history
- Categorizes commits using Conventional Commits
- Detects breaking changes
- Generates Keep a Changelog formatted output
- Suggests semantic version bumps
- Links to issues and PRs
- Generates release notes

Usage:
    from services.changelog import ChangelogGenerator, VersionBump

    generator = ChangelogGenerator(repo_path="/path/to/repo")
    changelog = await generator.generate_changelog()
    version_bump = await generator.suggest_version("1.2.3")
"""

from .generator import (
    ChangelogEntry,
    ChangelogGenerator,
    CommitInfo,
    CommitType,
    VersionBump,
)

__all__ = [
    "ChangelogGenerator",
    "CommitInfo",
    "ChangelogEntry",
    "VersionBump",
    "CommitType",
]
