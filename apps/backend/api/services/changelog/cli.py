#!/usr/bin/env python3
"""
Changelog Generator CLI

Command-line interface for changelog generation.

Usage:
    # Generate changelog for unreleased changes
    python cli.py generate

    # Generate changelog with version
    python cli.py generate --version 1.2.0

    # Generate release notes
    python cli.py release --version 1.2.0 --from v1.1.0

    # Suggest version bump
    python cli.py suggest --current 1.1.0

    # Update CHANGELOG.md
    python cli.py update --version 1.2.0

    # List recent commits
    python cli.py list --limit 20
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.changelog import ChangelogGenerator


def list_commits(args):
    """List recent commits"""
    generator = ChangelogGenerator(
        repo_path=args.repo_path, repo_url=args.repo_url
    )

    commits = generator.parse_commits(
        from_ref=args.from_ref, to_ref=args.to_ref, limit=args.limit
    )

    print(f"\nFound {len(commits)} commits:\n")

    for commit in commits:
        breaking = " ⚠️  BREAKING" if commit.breaking else ""
        scope = f"({commit.scope})" if commit.scope else ""

        print(f"  {commit.short_hash} - [{commit.type.value}]{scope} {commit.description}{breaking}")

        if commit.issue_refs:
            print(f"    Issues: {', '.join('#' + r for r in commit.issue_refs)}")
        if commit.pr_refs:
            print(f"    PRs: {', '.join('#' + r for r in commit.pr_refs)}")


def generate_changelog(args):
    """Generate changelog"""
    generator = ChangelogGenerator(
        repo_path=args.repo_path, repo_url=args.repo_url
    )

    changelog = generator.generate_changelog(
        from_ref=args.from_ref,
        to_ref=args.to_ref,
        version=args.version,
        include_all=args.all,
    )

    if args.output:
        # Write to file
        output_path = Path(args.output)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(changelog)
        print(f"✓ Changelog written to {output_path}")
    else:
        # Print to stdout
        print(changelog)


def generate_release_notes(args):
    """Generate release notes"""
    if not args.version:
        print("Error: --version is required for release notes")
        sys.exit(1)

    generator = ChangelogGenerator(
        repo_path=args.repo_path, repo_url=args.repo_url
    )

    release_notes = generator.generate_release_notes(
        version=args.version,
        from_ref=args.from_ref,
        to_ref=args.to_ref,
        include_stats=args.stats,
    )

    if args.output:
        # Write to file
        output_path = Path(args.output)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(release_notes)
        print(f"✓ Release notes written to {output_path}")
    else:
        # Print to stdout
        print(release_notes)


def suggest_version(args):
    """Suggest version bump"""
    if not args.current:
        print("Error: --current version is required")
        sys.exit(1)

    generator = ChangelogGenerator(repo_path=args.repo_path)

    commits = generator.parse_commits(
        from_ref=args.from_ref, to_ref=args.to_ref
    )

    bump, new_version = generator.suggest_version(args.current, commits)

    print(f"\nCurrent version: {args.current}")
    print(f"Suggested version: {new_version}")
    print(f"Bump type: {bump.value}")

    # Show reasoning
    breaking = [c for c in commits if c.breaking]
    features = [c for c in commits if c.type.value == "feat"]
    fixes = [c for c in commits if c.type.value == "fix"]

    print("\nReasoning:")
    if breaking:
        print(f"  - {len(breaking)} breaking change(s) → MAJOR bump")
    if features:
        print(f"  - {len(features)} new feature(s) → MINOR bump")
    if fixes:
        print(f"  - {len(fixes)} bug fix(es) → PATCH bump")


async def update_changelog_file(args):
    """Update CHANGELOG.md file"""
    generator = ChangelogGenerator(
        repo_path=args.repo_path, repo_url=args.repo_url
    )

    changelog_path = args.changelog_path or (Path(args.repo_path) / "CHANGELOG.md")

    await generator.update_changelog_file(
        changelog_path=changelog_path,
        from_ref=args.from_ref,
        version=args.version,
    )

    print(f"✓ Updated {changelog_path}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Changelog Generator CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Global arguments
    parser.add_argument(
        "--repo-path",
        default=".",
        help="Path to git repository (default: current directory)",
    )
    parser.add_argument(
        "--repo-url", help="Repository URL for links (e.g., https://github.com/user/repo)"
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # List command
    list_parser = subparsers.add_parser("list", help="List recent commits")
    list_parser.add_argument("--from", dest="from_ref", help="Starting git reference")
    list_parser.add_argument("--to", dest="to_ref", default="HEAD", help="Ending git reference")
    list_parser.add_argument("--limit", type=int, default=20, help="Max commits to show")

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate changelog")
    gen_parser.add_argument("--from", dest="from_ref", help="Starting git reference")
    gen_parser.add_argument("--to", dest="to_ref", default="HEAD", help="Ending git reference")
    gen_parser.add_argument("--version", help="Version string for release")
    gen_parser.add_argument("--all", action="store_true", help="Include all commit types")
    gen_parser.add_argument("-o", "--output", help="Output file path")

    # Release command
    release_parser = subparsers.add_parser("release", help="Generate release notes")
    release_parser.add_argument("--version", required=True, help="Release version")
    release_parser.add_argument("--from", dest="from_ref", help="Starting git reference")
    release_parser.add_argument("--to", dest="to_ref", default="HEAD", help="Ending git reference")
    release_parser.add_argument(
        "--no-stats", dest="stats", action="store_false", help="Exclude statistics"
    )
    release_parser.add_argument("-o", "--output", help="Output file path")

    # Suggest command
    suggest_parser = subparsers.add_parser("suggest", help="Suggest version bump")
    suggest_parser.add_argument("--current", required=True, help="Current version")
    suggest_parser.add_argument("--from", dest="from_ref", help="Starting git reference")
    suggest_parser.add_argument("--to", dest="to_ref", default="HEAD", help="Ending git reference")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update CHANGELOG.md file")
    update_parser.add_argument("--version", help="Version string for release")
    update_parser.add_argument("--from", dest="from_ref", help="Starting git reference")
    update_parser.add_argument("--changelog-path", help="Path to CHANGELOG.md")

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    try:
        if args.command == "list":
            list_commits(args)
        elif args.command == "generate":
            generate_changelog(args)
        elif args.command == "release":
            generate_release_notes(args)
        elif args.command == "suggest":
            suggest_version(args)
        elif args.command == "update":
            asyncio.run(update_changelog_file(args))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
