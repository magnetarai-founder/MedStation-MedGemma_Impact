#!/usr/bin/env python3
"""
ElohimOS Changelog Generator

Generates changelog sections from git commit history using conventional commit format.

Usage:
    python3 scripts/generate_changelog.py --from-tag v1.0.0-rc1 --to-tag HEAD --version v1.0.0
    python3 scripts/generate_changelog.py --version v1.0.0  # auto-detect from/to
"""

import subprocess
import argparse
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Conventional commit prefixes
COMMIT_TYPES = {
    "feat": "Features",
    "fix": "Fixes",
    "docs": "Documentation",
    "perf": "Performance",
    "refactor": "Refactoring",
    "test": "Tests",
    "chore": "Chore",
    "ci": "CI/CD",
    "build": "Build",
    "ops": "Operations",
    "security": "Security",
}

def get_latest_tag(before: str = None) -> str:
    """Get the latest git tag before a given ref"""
    cmd = ["git", "describe", "--tags", "--abbrev=0"]
    if before and before != "HEAD":
        cmd.append(before + "^")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None

def get_commits(from_ref: str, to_ref: str) -> List[Tuple[str, str, str]]:
    """
    Get commits between two refs.
    Returns list of (short_sha, subject, body) tuples.
    """
    # Format: <short_sha>|||<subject>|||<body>
    cmd = [
        "git", "log",
        f"{from_ref}..{to_ref}",
        "--no-merges",
        "--pretty=format:%h|||%s|||%b"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if not result.stdout.strip():
            return []

        commits = []
        for line in result.stdout.strip().split('\n'):
            if '|||' in line:
                parts = line.split('|||', 2)
                if len(parts) >= 2:
                    sha = parts[0]
                    subject = parts[1]
                    body = parts[2] if len(parts) > 2 else ""
                    commits.append((sha, subject, body))

        return commits
    except subprocess.CalledProcessError as e:
        print(f"Error getting commits: {e}")
        return []

def parse_commit(subject: str) -> Tuple[str, str, str]:
    """
    Parse conventional commit format: type(scope): subject
    Returns (type, scope, clean_subject)
    """
    # Match: feat(vault): add sharing or feat: add sharing
    match = re.match(r'^(\w+)(?:\(([^)]+)\))?: (.+)$', subject)

    if match:
        commit_type = match.group(1)
        scope = match.group(2) or ""
        clean_subject = match.group(3)
        return (commit_type, scope, clean_subject)

    # No conventional format
    return ("other", "", subject)

def group_commits(commits: List[Tuple[str, str, str]]) -> Dict[str, List[Tuple[str, str, str]]]:
    """Group commits by type"""
    grouped = {key: [] for key in COMMIT_TYPES.keys()}
    grouped["other"] = []

    for sha, subject, body in commits:
        commit_type, scope, clean_subject = parse_commit(subject)

        # Map to known type or "other"
        group_key = commit_type if commit_type in COMMIT_TYPES else "other"
        grouped[group_key].append((sha, scope, clean_subject))

    return grouped

def scan_api_additions(from_ref: str, to_ref: str) -> List[str]:
    """
    Scan API_REFERENCE.md for new sections added in this range.
    Returns list of new section titles.
    """
    api_ref_path = "docs/development/API_REFERENCE.md"

    try:
        # Get diff of API_REFERENCE.md
        cmd = [
            "git", "diff",
            f"{from_ref}..{to_ref}",
            "--unified=0",
            api_ref_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        # Look for new headers (## or ###)
        new_sections = []
        for line in result.stdout.split('\n'):
            if line.startswith('+## ') or line.startswith('+### '):
                # Extract section title
                section = line.lstrip('+').lstrip('#').strip()
                if section and not section.startswith('Changelog'):
                    new_sections.append(section)

        return new_sections
    except subprocess.CalledProcessError:
        return []

def generate_changelog_section(version: str, from_ref: str, to_ref: str) -> str:
    """Generate a changelog section for the given version"""
    commits = get_commits(from_ref, to_ref)

    if not commits:
        return f"No commits found between {from_ref} and {to_ref}"

    grouped = group_commits(commits)

    # Build section
    lines = []
    lines.append(f"## {version} — {datetime.now().strftime('%Y-%m-%d')}")
    lines.append("")

    # Add each section that has commits
    for commit_type, section_title in COMMIT_TYPES.items():
        if grouped[commit_type]:
            lines.append(f"### {section_title}")
            lines.append("")

            for sha, scope, subject in grouped[commit_type]:
                if scope:
                    lines.append(f"- **{scope}**: {subject} (`{sha}`)")
                else:
                    lines.append(f"- {subject} (`{sha}`)")

            lines.append("")

    # Add "Other" section if present
    if grouped["other"]:
        lines.append("### Other")
        lines.append("")
        for sha, scope, subject in grouped["other"]:
            if scope:
                lines.append(f"- **{scope}**: {subject} (`{sha}`)")
            else:
                lines.append(f"- {subject} (`{sha}`)")
        lines.append("")

    # API Additions (optional)
    api_additions = scan_api_additions(from_ref, to_ref)
    if api_additions:
        lines.append("### API Additions")
        lines.append("")
        for section in api_additions:
            lines.append(f"- {section}")
        lines.append("")

    lines.append("---")
    lines.append("")

    return '\n'.join(lines)

def update_changelog(section: str, changelog_path: Path):
    """Prepend new section to CHANGELOG.md"""
    if not changelog_path.exists():
        # Create new CHANGELOG.md
        content = """# Changelog

All notable changes to ElohimOS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Sections are auto-generated from git commit history using conventional commit format:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `perf:` - Performance improvements
- `refactor:` - Code refactoring
- `test:` - Test additions/changes
- `ci:` - CI/CD changes
- `chore:` - Maintenance tasks

---

"""
        content += section
    else:
        # Prepend to existing file
        existing = changelog_path.read_text()

        # Find insertion point (after intro, before first version)
        if '---' in existing:
            parts = existing.split('---', 1)
            content = parts[0] + '---\n\n' + section + parts[1]
        else:
            content = existing + '\n' + section

    changelog_path.write_text(content)
    print(f"✓ Updated {changelog_path}")

def main():
    parser = argparse.ArgumentParser(description="Generate changelog from git commits")
    parser.add_argument("--from-tag", help="Starting tag (default: auto-detect)")
    parser.add_argument("--to-tag", default="HEAD", help="Ending tag/ref (default: HEAD)")
    parser.add_argument("--version", help="Version for section title (default: use --to-tag)")
    parser.add_argument("--print-only", action="store_true", help="Print to stdout only, don't update file")

    args = parser.parse_args()

    # Auto-detect from_tag if not provided
    from_tag = args.from_tag
    if not from_tag:
        from_tag = get_latest_tag(before=args.to_tag)
        if not from_tag:
            print("Error: No previous tag found. Specify --from-tag explicitly.")
            return 1
        print(f"ℹ Auto-detected from-tag: {from_tag}")

    # Use to_tag as version if not specified
    version = args.version or args.to_tag

    # Generate section
    print(f"Generating changelog: {from_tag}..{args.to_tag} → {version}")
    section = generate_changelog_section(version, from_tag, args.to_tag)

    # Print section
    print("\n" + "="*80)
    print(section)
    print("="*80 + "\n")

    # Update file unless --print-only
    if not args.print_only:
        repo_root = Path(__file__).parent.parent
        changelog_path = repo_root / "changelog" / "CHANGELOG.md"
        changelog_path.parent.mkdir(exist_ok=True)
        update_changelog(section, changelog_path)

    return 0

if __name__ == "__main__":
    exit(main())
