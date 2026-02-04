#!/usr/bin/env python3
"""
Example usage of the Changelog Generator

Demonstrates all key features:
- Parsing commits from git history
- Categorizing commits by type
- Detecting breaking changes
- Suggesting version bumps
- Generating changelogs
- Generating release notes
- Updating CHANGELOG.md file
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.changelog import ChangelogGenerator, VersionBump
from services.ollama_client import OllamaClient


async def basic_usage():
    """Basic changelog generation"""
    print("=" * 80)
    print("BASIC USAGE")
    print("=" * 80)

    # Initialize generator
    generator = ChangelogGenerator(
        repo_path="/Users/indiedevhipps/Documents/MagnetarCode",
        repo_url="https://github.com/yourusername/MagnetarCode",
    )

    # Parse recent commits
    print("\n1. Parsing commits...")
    commits = generator.parse_commits(limit=20)
    print(f"Found {len(commits)} commits")

    # Display parsed commits
    for commit in commits[:5]:
        print(f"\n  {commit.short_hash} - {commit.type.value}")
        print(f"  {commit.description}")
        if commit.scope:
            print(f"  Scope: {commit.scope}")
        if commit.breaking:
            print(f"  ⚠️  BREAKING CHANGE")

    # Categorize commits
    print("\n2. Categorizing commits...")
    categorized = generator.categorize_commits(commits)
    for commit_type, entry in categorized.items():
        print(f"  {commit_type.display_name}: {len(entry.commits)} commits")

    # Detect breaking changes
    print("\n3. Detecting breaking changes...")
    breaking = generator.detect_breaking_changes(commits)
    if breaking:
        print(f"  Found {len(breaking)} breaking changes:")
        for commit in breaking:
            print(f"    - {commit.description}")
    else:
        print("  No breaking changes found")


async def version_suggestion():
    """Demonstrate version bump suggestion"""
    print("\n" + "=" * 80)
    print("VERSION SUGGESTION")
    print("=" * 80)

    generator = ChangelogGenerator(
        repo_path="/Users/indiedevhipps/Documents/MagnetarCode"
    )

    # Get commits since last tag
    commits = generator.parse_commits(limit=50)

    # Suggest version bump
    current_version = "1.2.3"
    bump, new_version = generator.suggest_version(current_version, commits)

    print(f"\nCurrent version: {current_version}")
    print(f"Suggested bump: {bump.value}")
    print(f"New version: {new_version}")

    # Explain reasoning
    has_breaking = any(c.breaking for c in commits)
    has_features = any(c.type.value == "feat" for c in commits)
    has_fixes = any(c.type.value == "fix" for c in commits)

    print("\nReasoning:")
    if has_breaking:
        print("  - Contains breaking changes → MAJOR bump")
    if has_features:
        print("  - Contains new features → MINOR bump")
    if has_fixes:
        print("  - Contains bug fixes → PATCH bump")


async def generate_changelog_example():
    """Generate a complete changelog"""
    print("\n" + "=" * 80)
    print("CHANGELOG GENERATION")
    print("=" * 80)

    generator = ChangelogGenerator(
        repo_path="/Users/indiedevhipps/Documents/MagnetarCode",
        repo_url="https://github.com/yourusername/MagnetarCode",
    )

    # Generate changelog for unreleased changes
    print("\nGenerating changelog for unreleased changes...")
    changelog = generator.generate_changelog(version="2.0.0")

    print("\n" + "-" * 80)
    print(changelog)
    print("-" * 80)


async def generate_release_notes_example():
    """Generate release notes"""
    print("\n" + "=" * 80)
    print("RELEASE NOTES GENERATION")
    print("=" * 80)

    generator = ChangelogGenerator(
        repo_path="/Users/indiedevhipps/Documents/MagnetarCode",
        repo_url="https://github.com/yourusername/MagnetarCode",
    )

    # Generate release notes
    print("\nGenerating release notes for v2.0.0...")
    release_notes = generator.generate_release_notes(
        version="2.0.0", include_stats=True
    )

    print("\n" + "-" * 80)
    print(release_notes)
    print("-" * 80)


async def llm_enhanced_example():
    """Generate changelog with LLM-enhanced descriptions"""
    print("\n" + "=" * 80)
    print("LLM-ENHANCED CHANGELOG")
    print("=" * 80)

    # Initialize with LLM client
    llm_client = OllamaClient()

    generator = ChangelogGenerator(
        repo_path="/Users/indiedevhipps/Documents/MagnetarCode",
        repo_url="https://github.com/yourusername/MagnetarCode",
        llm_client=llm_client,
    )

    # Parse commits
    commits = generator.parse_commits(limit=10)

    print(f"\nEnhancing {len(commits)} commit descriptions with LLM...")

    # Enhance descriptions
    try:
        enhanced_commits = await generator.enhance_with_llm(commits)

        print("\nBefore and After:")
        for i, (original, enhanced) in enumerate(zip(commits, enhanced_commits), 1):
            print(f"\n{i}. {original.short_hash}")
            print(f"   Original: {original.description}")
            print(f"   Enhanced: {enhanced.description}")
    except Exception as e:
        print(f"\nLLM enhancement failed: {e}")
        print("(This is expected if Ollama is not running)")


async def update_changelog_file_example():
    """Update CHANGELOG.md file"""
    print("\n" + "=" * 80)
    print("UPDATE CHANGELOG FILE")
    print("=" * 80)

    generator = ChangelogGenerator(
        repo_path="/Users/indiedevhipps/Documents/MagnetarCode",
        repo_url="https://github.com/yourusername/MagnetarCode",
    )

    # This would update the actual CHANGELOG.md file
    # Commented out to prevent accidental modifications
    print("\nWould update CHANGELOG.md with:")
    print("  - New unreleased section")
    print("  - All commits since last tag")
    print("  - Properly categorized entries")

    # Uncomment to actually update:
    # await generator.update_changelog_file(version="Unreleased")
    # print("\n✓ CHANGELOG.md updated successfully!")


async def conventional_commits_examples():
    """Show examples of parsed conventional commits"""
    print("\n" + "=" * 80)
    print("CONVENTIONAL COMMITS PARSING")
    print("=" * 80)

    examples = [
        "feat: add user authentication",
        "feat(api): add JWT token validation",
        "fix(security): prevent SQL injection vulnerability",
        "feat!: remove deprecated API endpoints",
        "feat(auth)!: migrate to OAuth 2.0",
        "docs: update API documentation",
        "refactor(core): simplify error handling",
        "perf(db): optimize database queries",
        "test: add integration tests for auth flow",
        "chore: update dependencies",
    ]

    generator = ChangelogGenerator()

    print("\nParsing example commit messages:\n")

    for example in examples:
        commit_type, scope, description, breaking = generator._parse_commit_message(example)

        breaking_marker = " ⚠️  BREAKING" if breaking else ""
        scope_marker = f" ({scope})" if scope else ""

        print(f"  {example}")
        print(f"    → Type: {commit_type.value}{scope_marker}{breaking_marker}")
        print(f"    → Description: {description}\n")


async def main():
    """Run all examples"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "CHANGELOG GENERATOR EXAMPLES" + " " * 30 + "║")
    print("╚" + "=" * 78 + "╝")

    try:
        # Run examples
        await conventional_commits_examples()
        await basic_usage()
        await version_suggestion()
        await generate_changelog_example()
        await generate_release_notes_example()
        await update_changelog_file_example()

        # LLM enhancement (may fail if Ollama not running)
        print("\n" + "=" * 80)
        print("NOTE: LLM enhancement example requires Ollama to be running")
        print("=" * 80)
        # await llm_enhanced_example()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 80)
    print("Examples completed!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
