#!/usr/bin/env python3
"""
Changelog Generator

Comprehensive changelog generation system that:
- Parses git commit history using Conventional Commits format
- Categorizes commits by type (feat, fix, docs, etc.)
- Detects breaking changes (BREAKING CHANGE: or !)
- Generates Keep a Changelog formatted output
- Suggests semantic version bumps
- Links to GitHub/GitLab issues and PRs
- Generates release notes for specific versions
- Optional LLM enhancement for better descriptions

Architecture:
- CommitInfo: Parsed commit data with type, scope, breaking changes
- ChangelogEntry: Categorized commit entries for changelog
- VersionBump: Semantic version bump recommendations
- ChangelogGenerator: Main service class for all operations
"""

import logging
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CommitType(str, Enum):
    """Conventional Commit types"""

    FEAT = "feat"
    FIX = "fix"
    DOCS = "docs"
    STYLE = "style"
    REFACTOR = "refactor"
    PERF = "perf"
    TEST = "test"
    BUILD = "build"
    CI = "ci"
    CHORE = "chore"
    REVERT = "revert"
    UNKNOWN = "unknown"

    @property
    def display_name(self) -> str:
        """Get display name for changelog section"""
        display_names = {
            CommitType.FEAT: "Features",
            CommitType.FIX: "Bug Fixes",
            CommitType.DOCS: "Documentation",
            CommitType.STYLE: "Styles",
            CommitType.REFACTOR: "Code Refactoring",
            CommitType.PERF: "Performance Improvements",
            CommitType.TEST: "Tests",
            CommitType.BUILD: "Build System",
            CommitType.CI: "Continuous Integration",
            CommitType.CHORE: "Chores",
            CommitType.REVERT: "Reverts",
            CommitType.UNKNOWN: "Other Changes",
        }
        return display_names.get(self, "Other Changes")


class VersionBump(str, Enum):
    """Semantic version bump types"""

    MAJOR = "major"  # Breaking changes (x.0.0)
    MINOR = "minor"  # New features (0.x.0)
    PATCH = "patch"  # Bug fixes (0.0.x)
    NONE = "none"  # No version bump needed


@dataclass
class CommitInfo:
    """Parsed commit information"""

    hash: str
    short_hash: str
    message: str
    author: str
    email: str
    date: datetime
    type: CommitType
    scope: str | None = None
    description: str = ""
    body: str = ""
    breaking: bool = False
    breaking_description: str = ""
    issue_refs: list[str] = field(default_factory=list)
    pr_refs: list[str] = field(default_factory=list)

    @property
    def formatted_description(self) -> str:
        """Get formatted description with scope"""
        if self.scope:
            return f"**{self.scope}**: {self.description}"
        return self.description

    @property
    def is_significant(self) -> bool:
        """Check if commit should appear in changelog"""
        # Only include user-facing changes
        return self.type in {
            CommitType.FEAT,
            CommitType.FIX,
            CommitType.PERF,
            CommitType.REVERT,
        } or self.breaking


@dataclass
class ChangelogEntry:
    """Categorized changelog entry"""

    type: CommitType
    commits: list[CommitInfo] = field(default_factory=list)

    def to_markdown(self, include_links: bool = True, repo_url: str | None = None) -> str:
        """Convert entry to markdown format"""
        if not self.commits:
            return ""

        lines = [f"### {self.type.display_name}\n"]

        for commit in self.commits:
            # Build commit line
            line_parts = [f"- {commit.formatted_description}"]

            # Add commit hash link
            if include_links and repo_url:
                hash_link = f"[`{commit.short_hash}`]({repo_url}/commit/{commit.hash})"
                line_parts.append(f"({hash_link})")
            elif include_links:
                line_parts.append(f"({commit.short_hash})")

            # Add issue/PR references
            if commit.issue_refs and repo_url:
                refs = [f"[#{ref}]({repo_url}/issues/{ref})" for ref in commit.issue_refs]
                line_parts.append(f"(fixes {', '.join(refs)})")
            elif commit.issue_refs:
                refs = [f"#{ref}" for ref in commit.issue_refs]
                line_parts.append(f"(fixes {', '.join(refs)})")

            if commit.pr_refs and repo_url:
                refs = [f"[#{ref}]({repo_url}/pull/{ref})" for ref in commit.pr_refs]
                line_parts.append(f"(PR {', '.join(refs)})")
            elif commit.pr_refs:
                refs = [f"#{ref}" for ref in commit.pr_refs]
                line_parts.append(f"(PR {', '.join(refs)})")

            lines.append(" ".join(line_parts))

        return "\n".join(lines)


class ChangelogGenerator:
    """
    Generates changelogs from git history

    Parses commits, categorizes them, and generates Keep a Changelog
    formatted output with optional LLM enhancement.
    """

    # Conventional Commits regex pattern
    # Format: type(scope)!: description
    COMMIT_PATTERN = re.compile(
        r"^(?P<type>\w+)"  # type (required)
        r"(?:\((?P<scope>[^)]+)\))?"  # scope (optional)
        r"(?P<breaking>!)?"  # breaking change indicator (optional)
        r":\s+"  # colon and space
        r"(?P<description>.+)$",  # description (rest of line)
        re.MULTILINE,
    )

    # Breaking change marker in body
    BREAKING_CHANGE_PATTERN = re.compile(
        r"^BREAKING[- ]CHANGE:\s+(.+)$", re.MULTILINE | re.IGNORECASE
    )

    # Issue/PR reference patterns
    ISSUE_PATTERN = re.compile(
        r"(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)", re.IGNORECASE
    )
    PR_PATTERN = re.compile(r"(?:PR|MR)\s+#?(\d+)", re.IGNORECASE)

    # Keep a Changelog header template
    CHANGELOG_HEADER = """# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

"""

    def __init__(
        self,
        repo_path: str | Path | None = None,
        llm_client=None,
        repo_url: str | None = None,
    ):
        """
        Initialize changelog generator

        Args:
            repo_path: Path to git repository (defaults to current directory)
            llm_client: Optional LLM client for enhanced descriptions
            repo_url: Repository URL for generating links (e.g., https://github.com/user/repo)
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.llm_client = llm_client
        self.repo_url = repo_url

        # Validate git repository
        if not (self.repo_path / ".git").exists():
            raise ValueError(f"Not a git repository: {self.repo_path}")

    def _run_git_command(self, *args: str) -> str:
        """Run git command and return output"""
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e.stderr}")
            raise Exception(f"Git command failed: {e.stderr}") from e

    def parse_commits(
        self,
        from_ref: str | None = None,
        to_ref: str = "HEAD",
        limit: int | None = None,
    ) -> list[CommitInfo]:
        """
        Parse git commits into structured CommitInfo objects

        Args:
            from_ref: Starting git reference (tag, commit, etc.)
            to_ref: Ending git reference (defaults to HEAD)
            limit: Maximum number of commits to parse

        Returns:
            List of parsed CommitInfo objects
        """
        # Build git log command
        git_range = f"{from_ref}..{to_ref}" if from_ref else to_ref
        format_str = "%H%n%h%n%an%n%ae%n%at%n%s%n%b%n--END--"

        cmd_args = ["log", git_range, f"--format={format_str}"]
        if limit:
            cmd_args.append(f"-n{limit}")

        try:
            output = self._run_git_command(*cmd_args)
        except Exception as e:
            logger.warning(f"Failed to get git log: {e}")
            return []

        # Parse commits
        commits = []
        raw_commits = output.split("--END--\n")

        for raw in raw_commits:
            if not raw.strip():
                continue

            try:
                commit = self._parse_single_commit(raw)
                commits.append(commit)
            except Exception as e:
                logger.warning(f"Failed to parse commit: {e}")
                continue

        return commits

    def _parse_single_commit(self, raw_commit: str) -> CommitInfo:
        """Parse a single commit from git log output"""
        lines = raw_commit.split("\n")

        # Extract basic info
        commit_hash = lines[0]
        short_hash = lines[1]
        author = lines[2]
        email = lines[3]
        timestamp = int(lines[4])
        subject = lines[5] if len(lines) > 5 else ""
        body = "\n".join(lines[6:]).strip() if len(lines) > 6 else ""

        # Parse conventional commit format
        commit_type, scope, description, breaking_marker = self._parse_commit_message(subject)

        # Check for breaking changes in body
        breaking = bool(breaking_marker)
        breaking_description = ""

        if not breaking:
            breaking_match = self.BREAKING_CHANGE_PATTERN.search(body)
            if breaking_match:
                breaking = True
                breaking_description = breaking_match.group(1)

        # Extract issue and PR references
        issue_refs = self.ISSUE_PATTERN.findall(subject + " " + body)
        pr_refs = self.PR_PATTERN.findall(subject + " " + body)

        return CommitInfo(
            hash=commit_hash,
            short_hash=short_hash,
            message=subject,
            author=author,
            email=email,
            date=datetime.fromtimestamp(timestamp),
            type=commit_type,
            scope=scope,
            description=description or subject,
            body=body,
            breaking=breaking,
            breaking_description=breaking_description,
            issue_refs=list(set(issue_refs)),  # Remove duplicates
            pr_refs=list(set(pr_refs)),
        )

    def _parse_commit_message(self, message: str) -> tuple[CommitType, str | None, str, bool]:
        """
        Parse commit message using Conventional Commits format

        Returns:
            (type, scope, description, breaking_marker)
        """
        match = self.COMMIT_PATTERN.match(message)

        if not match:
            # Not a conventional commit
            return CommitType.UNKNOWN, None, message, False

        type_str = match.group("type").lower()
        scope = match.group("scope")
        description = match.group("description")
        breaking_marker = bool(match.group("breaking"))

        # Map type string to enum
        try:
            commit_type = CommitType(type_str)
        except ValueError:
            commit_type = CommitType.UNKNOWN

        return commit_type, scope, description, breaking_marker

    def categorize_commits(self, commits: list[CommitInfo]) -> dict[CommitType, ChangelogEntry]:
        """
        Categorize commits by type

        Args:
            commits: List of parsed commits

        Returns:
            Dictionary mapping CommitType to ChangelogEntry
        """
        categorized: dict[CommitType, ChangelogEntry] = defaultdict(
            lambda: ChangelogEntry(type=CommitType.UNKNOWN)
        )

        for commit in commits:
            if commit.is_significant:
                entry = categorized[commit.type]
                entry.type = commit.type
                entry.commits.append(commit)

        return dict(categorized)

    def detect_breaking_changes(self, commits: list[CommitInfo]) -> list[CommitInfo]:
        """
        Extract commits with breaking changes

        Args:
            commits: List of parsed commits

        Returns:
            List of commits with breaking changes
        """
        return [commit for commit in commits if commit.breaking]

    def suggest_version(
        self, current_version: str, commits: list[CommitInfo] | None = None
    ) -> tuple[VersionBump, str]:
        """
        Suggest semantic version bump based on commits

        Args:
            current_version: Current version (e.g., "1.2.3")
            commits: Optional list of commits (if None, uses all unreleased)

        Returns:
            Tuple of (VersionBump, suggested_new_version)
        """
        # Parse current version
        version_match = re.match(r"^v?(\d+)\.(\d+)\.(\d+)", current_version)
        if not version_match:
            raise ValueError(f"Invalid version format: {current_version}")

        major, minor, patch = map(int, version_match.groups())

        # Get commits if not provided
        if commits is None:
            try:
                # Get latest tag
                latest_tag = self._run_git_command("describe", "--tags", "--abbrev=0")
                commits = self.parse_commits(from_ref=latest_tag)
            except Exception:
                # No tags found, use all commits
                commits = self.parse_commits(limit=100)

        if not commits:
            return VersionBump.NONE, current_version

        # Determine version bump
        has_breaking = any(c.breaking for c in commits)
        has_features = any(c.type == CommitType.FEAT for c in commits)
        has_fixes = any(c.type == CommitType.FIX for c in commits)

        if has_breaking:
            bump = VersionBump.MAJOR
            new_version = f"{major + 1}.0.0"
        elif has_features:
            bump = VersionBump.MINOR
            new_version = f"{major}.{minor + 1}.0"
        elif has_fixes:
            bump = VersionBump.PATCH
            new_version = f"{major}.{minor}.{patch + 1}"
        else:
            bump = VersionBump.NONE
            new_version = current_version

        return bump, new_version

    def generate_changelog(
        self,
        from_ref: str | None = None,
        to_ref: str = "HEAD",
        version: str | None = None,
        date: datetime | None = None,
        include_all: bool = False,
    ) -> str:
        """
        Generate complete changelog in Keep a Changelog format

        Args:
            from_ref: Starting git reference
            to_ref: Ending git reference
            version: Version string for this release
            date: Release date (defaults to today)
            include_all: Include all commit types (not just significant)

        Returns:
            Markdown formatted changelog
        """
        # Parse commits
        commits = self.parse_commits(from_ref=from_ref, to_ref=to_ref)

        if not commits:
            logger.warning("No commits found for changelog generation")
            return self.CHANGELOG_HEADER + "\n## [Unreleased]\n\nNo changes yet.\n"

        # Filter to significant commits unless include_all
        if not include_all:
            commits = [c for c in commits if c.is_significant]

        # Categorize commits
        categorized = self.categorize_commits(commits)

        # Build changelog
        lines = []

        # Version header
        version_str = version or "Unreleased"
        date_str = (date or datetime.now()).strftime("%Y-%m-%d")

        if version:
            lines.append(f"## [{version}] - {date_str}")
        else:
            lines.append(f"## [Unreleased]")

        lines.append("")

        # Breaking changes section (always first if present)
        breaking_commits = self.detect_breaking_changes(commits)
        if breaking_commits:
            lines.append("### BREAKING CHANGES\n")
            for commit in breaking_commits:
                desc = commit.breaking_description or commit.description
                lines.append(f"- **{commit.scope or 'core'}**: {desc}")
                if commit.issue_refs and self.repo_url:
                    refs = [f"[#{r}]({self.repo_url}/issues/{r})" for r in commit.issue_refs]
                    lines.append(f"  - Fixes {', '.join(refs)}")
            lines.append("")

        # Other sections in order
        section_order = [
            CommitType.FEAT,
            CommitType.FIX,
            CommitType.PERF,
            CommitType.REFACTOR,
            CommitType.DOCS,
            CommitType.TEST,
            CommitType.BUILD,
            CommitType.CI,
            CommitType.CHORE,
            CommitType.REVERT,
        ]

        for commit_type in section_order:
            if commit_type in categorized:
                entry = categorized[commit_type]
                markdown = entry.to_markdown(include_links=True, repo_url=self.repo_url)
                if markdown:
                    lines.append(markdown)
                    lines.append("")

        return "\n".join(lines)

    def generate_release_notes(
        self,
        version: str,
        from_ref: str | None = None,
        to_ref: str = "HEAD",
        include_stats: bool = True,
    ) -> str:
        """
        Generate release notes for a specific version

        Args:
            version: Version string (e.g., "1.2.0")
            from_ref: Starting git reference
            to_ref: Ending git reference
            include_stats: Include commit statistics

        Returns:
            Markdown formatted release notes
        """
        commits = self.parse_commits(from_ref=from_ref, to_ref=to_ref)

        if not commits:
            return f"# Release {version}\n\nNo changes in this release.\n"

        # Generate changelog section
        changelog = self.generate_changelog(
            from_ref=from_ref, to_ref=to_ref, version=version, date=datetime.now()
        )

        # Build release notes
        lines = [f"# Release {version}\n"]

        # Summary
        lines.append("## Summary\n")
        breaking = self.detect_breaking_changes(commits)
        features = [c for c in commits if c.type == CommitType.FEAT]
        fixes = [c for c in commits if c.type == CommitType.FIX]

        if breaking:
            lines.append(
                f"This release contains **{len(breaking)} breaking change(s)**. "
                "Please review the BREAKING CHANGES section carefully.\n"
            )

        lines.append(
            f"This release includes {len(features)} new feature(s) "
            f"and {len(fixes)} bug fix(es).\n"
        )

        # Statistics
        if include_stats:
            lines.append("## Statistics\n")
            contributors = set(c.author for c in commits)
            lines.append(f"- **Total commits**: {len(commits)}")
            lines.append(f"- **Contributors**: {len(contributors)}")
            lines.append(f"- **New features**: {len(features)}")
            lines.append(f"- **Bug fixes**: {len(fixes)}")
            if breaking:
                lines.append(f"- **Breaking changes**: {len(breaking)}")
            lines.append("")

        # Full changelog
        lines.append("## Changelog\n")
        lines.append(changelog)

        # Contributors
        if contributors:
            lines.append("\n## Contributors\n")
            lines.append(
                "Thank you to all the contributors who made this release possible:\n"
            )
            for contributor in sorted(contributors):
                lines.append(f"- {contributor}")

        return "\n".join(lines)

    async def update_changelog_file(
        self,
        changelog_path: str | Path | None = None,
        from_ref: str | None = None,
        version: str | None = None,
    ) -> None:
        """
        Update CHANGELOG.md file with new entries

        Args:
            changelog_path: Path to CHANGELOG.md (defaults to repo root)
            from_ref: Starting git reference for new entries
            version: Version string for new release
        """
        if changelog_path is None:
            changelog_path = self.repo_path / "CHANGELOG.md"
        else:
            changelog_path = Path(changelog_path)

        # Generate new changelog section
        new_section = self.generate_changelog(
            from_ref=from_ref, version=version, date=datetime.now()
        )

        # Read existing changelog or create new
        if changelog_path.exists():
            with open(changelog_path, "r", encoding="utf-8") as f:
                existing_content = f.read()

            # Check if it has the header
            if "# Changelog" not in existing_content:
                # Add header
                content = self.CHANGELOG_HEADER + new_section + "\n\n" + existing_content
            else:
                # Insert after header
                parts = existing_content.split("\n\n", 2)
                if len(parts) >= 2:
                    content = parts[0] + "\n\n" + new_section + "\n\n" + parts[1]
                    if len(parts) > 2:
                        content += "\n\n" + parts[2]
                else:
                    content = existing_content + "\n\n" + new_section
        else:
            # Create new changelog
            content = self.CHANGELOG_HEADER + new_section

        # Write updated changelog
        with open(changelog_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Updated changelog at {changelog_path}")

    async def enhance_with_llm(self, commits: list[CommitInfo]) -> list[CommitInfo]:
        """
        Enhance commit descriptions using LLM

        Args:
            commits: List of commits to enhance

        Returns:
            List of commits with enhanced descriptions
        """
        if not self.llm_client:
            logger.warning("No LLM client provided, skipping enhancement")
            return commits

        enhanced_commits = []

        for commit in commits:
            try:
                # Build enhancement prompt
                prompt = f"""Improve this git commit description for a changelog:

Original: {commit.description}
Type: {commit.type.value}
Scope: {commit.scope or 'N/A'}

Provide a clear, user-friendly description (one sentence, max 100 chars).
Focus on WHAT changed and WHY it matters to users.
Do not include technical implementation details.
"""

                # Call LLM
                response = await self.llm_client.chat(
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a technical writer creating user-friendly changelogs.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    max_tokens=100,
                )

                # Extract enhanced description
                enhanced_desc = response.get("message", {}).get("content", "").strip()

                if enhanced_desc and len(enhanced_desc) < 200:
                    commit.description = enhanced_desc

                enhanced_commits.append(commit)

            except Exception as e:
                logger.warning(f"Failed to enhance commit {commit.short_hash}: {e}")
                enhanced_commits.append(commit)

        return enhanced_commits
