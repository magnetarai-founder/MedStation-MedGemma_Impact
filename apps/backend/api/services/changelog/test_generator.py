#!/usr/bin/env python3
"""
Unit tests for Changelog Generator

Tests all major functionality:
- Conventional Commits parsing
- Commit categorization
- Breaking change detection
- Version suggestion
- Changelog generation
- Release notes generation
"""

import unittest
from datetime import datetime
from pathlib import Path

from .generator import (
    ChangelogEntry,
    ChangelogGenerator,
    CommitInfo,
    CommitType,
    VersionBump,
)


class TestCommitType(unittest.TestCase):
    """Test CommitType enum"""

    def test_display_names(self):
        """Test display name mapping"""
        self.assertEqual(CommitType.FEAT.display_name, "Features")
        self.assertEqual(CommitType.FIX.display_name, "Bug Fixes")
        self.assertEqual(CommitType.DOCS.display_name, "Documentation")
        self.assertEqual(CommitType.PERF.display_name, "Performance Improvements")

    def test_enum_values(self):
        """Test enum values"""
        self.assertEqual(CommitType.FEAT.value, "feat")
        self.assertEqual(CommitType.FIX.value, "fix")


class TestCommitInfo(unittest.TestCase):
    """Test CommitInfo dataclass"""

    def test_formatted_description_with_scope(self):
        """Test formatted description with scope"""
        commit = CommitInfo(
            hash="abc123",
            short_hash="abc123",
            message="feat(api): add user endpoint",
            author="Test User",
            email="test@example.com",
            date=datetime.now(),
            type=CommitType.FEAT,
            scope="api",
            description="add user endpoint",
        )

        self.assertEqual(commit.formatted_description, "**api**: add user endpoint")

    def test_formatted_description_without_scope(self):
        """Test formatted description without scope"""
        commit = CommitInfo(
            hash="abc123",
            short_hash="abc123",
            message="feat: add feature",
            author="Test User",
            email="test@example.com",
            date=datetime.now(),
            type=CommitType.FEAT,
            description="add feature",
        )

        self.assertEqual(commit.formatted_description, "add feature")

    def test_is_significant_feat(self):
        """Test significant commit detection - features"""
        commit = CommitInfo(
            hash="abc123",
            short_hash="abc123",
            message="feat: add feature",
            author="Test User",
            email="test@example.com",
            date=datetime.now(),
            type=CommitType.FEAT,
            description="add feature",
        )

        self.assertTrue(commit.is_significant)

    def test_is_significant_chore(self):
        """Test significant commit detection - chores"""
        commit = CommitInfo(
            hash="abc123",
            short_hash="abc123",
            message="chore: update deps",
            author="Test User",
            email="test@example.com",
            date=datetime.now(),
            type=CommitType.CHORE,
            description="update deps",
        )

        self.assertFalse(commit.is_significant)

    def test_is_significant_breaking(self):
        """Test significant commit detection - breaking changes"""
        commit = CommitInfo(
            hash="abc123",
            short_hash="abc123",
            message="chore!: breaking change",
            author="Test User",
            email="test@example.com",
            date=datetime.now(),
            type=CommitType.CHORE,
            description="breaking change",
            breaking=True,
        )

        self.assertTrue(commit.is_significant)


class TestConventionalCommitsParsing(unittest.TestCase):
    """Test Conventional Commits parsing"""

    def setUp(self):
        """Create generator instance for tests"""
        # Use the MagnetarCode repo root for testing
        self.test_dir = Path(__file__).parent.parent.parent.parent.parent.parent
        self.generator = ChangelogGenerator(repo_path=self.test_dir)

    def test_parse_simple_feat(self):
        """Test parsing simple feature commit"""
        commit_type, scope, description, breaking = self.generator._parse_commit_message(
            "feat: add user authentication"
        )

        self.assertEqual(commit_type, CommitType.FEAT)
        self.assertIsNone(scope)
        self.assertEqual(description, "add user authentication")
        self.assertFalse(breaking)

    def test_parse_feat_with_scope(self):
        """Test parsing feature with scope"""
        commit_type, scope, description, breaking = self.generator._parse_commit_message(
            "feat(api): add JWT token validation"
        )

        self.assertEqual(commit_type, CommitType.FEAT)
        self.assertEqual(scope, "api")
        self.assertEqual(description, "add JWT token validation")
        self.assertFalse(breaking)

    def test_parse_breaking_with_exclamation(self):
        """Test parsing breaking change with exclamation mark"""
        commit_type, scope, description, breaking = self.generator._parse_commit_message(
            "feat!: remove deprecated API endpoints"
        )

        self.assertEqual(commit_type, CommitType.FEAT)
        self.assertIsNone(scope)
        self.assertEqual(description, "remove deprecated API endpoints")
        self.assertTrue(breaking)

    def test_parse_breaking_with_scope_and_exclamation(self):
        """Test parsing breaking change with scope and exclamation"""
        commit_type, scope, description, breaking = self.generator._parse_commit_message(
            "feat(auth)!: migrate to OAuth 2.0"
        )

        self.assertEqual(commit_type, CommitType.FEAT)
        self.assertEqual(scope, "auth")
        self.assertEqual(description, "migrate to OAuth 2.0")
        self.assertTrue(breaking)

    def test_parse_fix(self):
        """Test parsing fix commit"""
        commit_type, scope, description, breaking = self.generator._parse_commit_message(
            "fix(security): prevent SQL injection"
        )

        self.assertEqual(commit_type, CommitType.FIX)
        self.assertEqual(scope, "security")
        self.assertEqual(description, "prevent SQL injection")
        self.assertFalse(breaking)

    def test_parse_docs(self):
        """Test parsing docs commit"""
        commit_type, scope, description, breaking = self.generator._parse_commit_message(
            "docs: update API documentation"
        )

        self.assertEqual(commit_type, CommitType.DOCS)
        self.assertIsNone(scope)
        self.assertEqual(description, "update API documentation")
        self.assertFalse(breaking)

    def test_parse_non_conventional(self):
        """Test parsing non-conventional commit"""
        commit_type, scope, description, breaking = self.generator._parse_commit_message(
            "Update some files"
        )

        self.assertEqual(commit_type, CommitType.UNKNOWN)
        self.assertIsNone(scope)
        self.assertEqual(description, "Update some files")
        self.assertFalse(breaking)

    def test_parse_all_types(self):
        """Test parsing all commit types"""
        types_to_test = [
            ("feat: add feature", CommitType.FEAT),
            ("fix: fix bug", CommitType.FIX),
            ("docs: update docs", CommitType.DOCS),
            ("style: format code", CommitType.STYLE),
            ("refactor: refactor code", CommitType.REFACTOR),
            ("perf: improve performance", CommitType.PERF),
            ("test: add tests", CommitType.TEST),
            ("build: update build", CommitType.BUILD),
            ("ci: update CI", CommitType.CI),
            ("chore: update deps", CommitType.CHORE),
            ("revert: revert commit", CommitType.REVERT),
        ]

        for message, expected_type in types_to_test:
            commit_type, _, _, _ = self.generator._parse_commit_message(message)
            self.assertEqual(commit_type, expected_type, f"Failed for: {message}")


class TestVersionSuggestion(unittest.TestCase):
    """Test version bump suggestion"""

    def setUp(self):
        """Create generator instance"""
        # Use the MagnetarCode repo root for testing
        repo_path = Path(__file__).parent.parent.parent.parent.parent.parent
        self.generator = ChangelogGenerator(repo_path=repo_path)

    def test_suggest_patch_for_fixes(self):
        """Test patch bump for bug fixes"""
        commits = [
            CommitInfo(
                hash="abc",
                short_hash="abc",
                message="fix: bug fix",
                author="Test",
                email="test@test.com",
                date=datetime.now(),
                type=CommitType.FIX,
                description="bug fix",
            )
        ]

        bump, version = self.generator.suggest_version("1.2.3", commits)
        self.assertEqual(bump, VersionBump.PATCH)
        self.assertEqual(version, "1.2.4")

    def test_suggest_minor_for_features(self):
        """Test minor bump for new features"""
        commits = [
            CommitInfo(
                hash="abc",
                short_hash="abc",
                message="feat: new feature",
                author="Test",
                email="test@test.com",
                date=datetime.now(),
                type=CommitType.FEAT,
                description="new feature",
            )
        ]

        bump, version = self.generator.suggest_version("1.2.3", commits)
        self.assertEqual(bump, VersionBump.MINOR)
        self.assertEqual(version, "1.3.0")

    def test_suggest_major_for_breaking(self):
        """Test major bump for breaking changes"""
        commits = [
            CommitInfo(
                hash="abc",
                short_hash="abc",
                message="feat!: breaking change",
                author="Test",
                email="test@test.com",
                date=datetime.now(),
                type=CommitType.FEAT,
                description="breaking change",
                breaking=True,
            )
        ]

        bump, version = self.generator.suggest_version("1.2.3", commits)
        self.assertEqual(bump, VersionBump.MAJOR)
        self.assertEqual(version, "2.0.0")

    def test_suggest_none_for_chores(self):
        """Test no bump for non-significant changes"""
        commits = [
            CommitInfo(
                hash="abc",
                short_hash="abc",
                message="chore: update deps",
                author="Test",
                email="test@test.com",
                date=datetime.now(),
                type=CommitType.CHORE,
                description="update deps",
            )
        ]

        bump, version = self.generator.suggest_version("1.2.3", commits)
        self.assertEqual(bump, VersionBump.NONE)
        self.assertEqual(version, "1.2.3")

    def test_version_with_v_prefix(self):
        """Test version parsing with 'v' prefix"""
        commits = [
            CommitInfo(
                hash="abc",
                short_hash="abc",
                message="fix: bug fix",
                author="Test",
                email="test@test.com",
                date=datetime.now(),
                type=CommitType.FIX,
                description="bug fix",
            )
        ]

        bump, version = self.generator.suggest_version("v1.2.3", commits)
        self.assertEqual(version, "1.2.4")


class TestChangelogEntry(unittest.TestCase):
    """Test ChangelogEntry"""

    def test_to_markdown_basic(self):
        """Test basic markdown conversion"""
        commits = [
            CommitInfo(
                hash="abc123def456",
                short_hash="abc123d",
                message="feat: add feature",
                author="Test",
                email="test@test.com",
                date=datetime.now(),
                type=CommitType.FEAT,
                description="add user authentication",
            )
        ]

        entry = ChangelogEntry(type=CommitType.FEAT, commits=commits)
        markdown = entry.to_markdown(include_links=False)

        self.assertIn("### Features", markdown)
        self.assertIn("- add user authentication", markdown)

    def test_to_markdown_with_links(self):
        """Test markdown with repository links"""
        commits = [
            CommitInfo(
                hash="abc123def456",
                short_hash="abc123d",
                message="feat: add feature",
                author="Test",
                email="test@test.com",
                date=datetime.now(),
                type=CommitType.FEAT,
                description="add feature",
                issue_refs=["123"],
                pr_refs=["45"],
            )
        ]

        entry = ChangelogEntry(type=CommitType.FEAT, commits=commits)
        markdown = entry.to_markdown(
            include_links=True, repo_url="https://github.com/user/repo"
        )

        self.assertIn("### Features", markdown)
        self.assertIn("[`abc123d`]", markdown)
        self.assertIn("https://github.com/user/repo/commit/abc123def456", markdown)
        self.assertIn("[#123]", markdown)
        self.assertIn("[#45]", markdown)


class TestIssueAndPRExtraction(unittest.TestCase):
    """Test issue and PR reference extraction"""

    def test_issue_pattern(self):
        """Test issue reference extraction"""
        text = "Fix a bug\n\nCloses #123\nFixes #456"
        matches = ChangelogGenerator.ISSUE_PATTERN.findall(text)
        self.assertEqual(set(matches), {"123", "456"})

    def test_pr_pattern(self):
        """Test PR reference extraction"""
        text = "Add feature\n\nPR #789\nMR 321"
        matches = ChangelogGenerator.PR_PATTERN.findall(text)
        self.assertEqual(set(matches), {"789", "321"})

    def test_breaking_change_pattern(self):
        """Test breaking change extraction from body"""
        text = "feat: new feature\n\nBREAKING CHANGE: API changed"
        match = ChangelogGenerator.BREAKING_CHANGE_PATTERN.search(text)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "API changed")


class TestChangelogGeneration(unittest.TestCase):
    """Test full changelog generation"""

    def setUp(self):
        """Create generator instance"""
        # Use the MagnetarCode repo root for testing
        repo_path = Path(__file__).parent.parent.parent.parent.parent.parent
        self.generator = ChangelogGenerator(
            repo_path=repo_path, repo_url="https://github.com/user/repo"
        )

    def test_categorize_commits(self):
        """Test commit categorization"""
        commits = [
            CommitInfo(
                hash="a",
                short_hash="a",
                message="feat: feature",
                author="Test",
                email="test@test.com",
                date=datetime.now(),
                type=CommitType.FEAT,
                description="feature",
            ),
            CommitInfo(
                hash="b",
                short_hash="b",
                message="fix: fix",
                author="Test",
                email="test@test.com",
                date=datetime.now(),
                type=CommitType.FIX,
                description="fix",
            ),
            CommitInfo(
                hash="c",
                short_hash="c",
                message="chore: chore",
                author="Test",
                email="test@test.com",
                date=datetime.now(),
                type=CommitType.CHORE,
                description="chore",
            ),
        ]

        categorized = self.generator.categorize_commits(commits)

        # Only significant commits should be categorized
        self.assertIn(CommitType.FEAT, categorized)
        self.assertIn(CommitType.FIX, categorized)
        self.assertNotIn(CommitType.CHORE, categorized)

    def test_detect_breaking_changes(self):
        """Test breaking change detection"""
        commits = [
            CommitInfo(
                hash="a",
                short_hash="a",
                message="feat: feature",
                author="Test",
                email="test@test.com",
                date=datetime.now(),
                type=CommitType.FEAT,
                description="feature",
                breaking=False,
            ),
            CommitInfo(
                hash="b",
                short_hash="b",
                message="feat!: breaking",
                author="Test",
                email="test@test.com",
                date=datetime.now(),
                type=CommitType.FEAT,
                description="breaking",
                breaking=True,
            ),
        ]

        breaking = self.generator.detect_breaking_changes(commits)
        self.assertEqual(len(breaking), 1)
        self.assertEqual(breaking[0].hash, "b")


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCommitType))
    suite.addTests(loader.loadTestsFromTestCase(TestCommitInfo))
    suite.addTests(loader.loadTestsFromTestCase(TestConventionalCommitsParsing))
    suite.addTests(loader.loadTestsFromTestCase(TestVersionSuggestion))
    suite.addTests(loader.loadTestsFromTestCase(TestChangelogEntry))
    suite.addTests(loader.loadTestsFromTestCase(TestIssueAndPRExtraction))
    suite.addTests(loader.loadTestsFromTestCase(TestChangelogGeneration))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    exit(run_tests())
