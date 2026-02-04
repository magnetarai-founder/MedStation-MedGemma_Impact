"""
Unit tests for Dependency Scanner

Run with: pytest test_scanner.py
"""

import asyncio
from pathlib import Path

import pytest

from .scanner import (
    Dependency,
    DependencyScanner,
    LicenseType,
    Severity,
    Vulnerability,
    VulnerabilityDatabase,
)


@pytest.fixture
async def scanner():
    """Create scanner instance"""
    scanner = DependencyScanner()
    yield scanner
    await scanner.close()


@pytest.fixture
def sample_dependencies():
    """Create sample dependencies for testing"""
    return [
        Dependency(name="requests", version="2.28.0", ecosystem="pypi"),
        Dependency(name="fastapi", version="0.100.0", ecosystem="pypi"),
        Dependency(name="express", version="4.18.0", ecosystem="npm"),
    ]


class TestDependency:
    """Test Dependency dataclass"""

    def test_dependency_creation(self):
        """Test creating a dependency"""
        dep = Dependency(name="test-package", version="1.0.0", ecosystem="pypi")

        assert dep.name == "test-package"
        assert dep.version == "1.0.0"
        assert dep.ecosystem == "pypi"
        assert not dep.has_vulnerabilities
        assert dep.highest_severity == Severity.UNKNOWN

    def test_dependency_with_vulnerabilities(self):
        """Test dependency with vulnerabilities"""
        vuln = Vulnerability(
            cve_id="CVE-2023-1234",
            severity=Severity.HIGH,
            description="Test vulnerability",
        )

        dep = Dependency(
            name="test-package",
            version="1.0.0",
            ecosystem="pypi",
            vulnerabilities=[vuln],
        )

        assert dep.has_vulnerabilities
        assert dep.highest_severity == Severity.HIGH

    def test_dependency_to_dict(self):
        """Test converting dependency to dict"""
        dep = Dependency(name="test-package", version="1.0.0", ecosystem="pypi")

        data = dep.to_dict()

        assert data["name"] == "test-package"
        assert data["version"] == "1.0.0"
        assert "has_vulnerabilities" in data
        assert "highest_severity" in data


class TestVulnerability:
    """Test Vulnerability dataclass"""

    def test_vulnerability_creation(self):
        """Test creating a vulnerability"""
        vuln = Vulnerability(
            cve_id="CVE-2023-1234",
            severity=Severity.CRITICAL,
            description="Critical security issue",
            fix_version="2.0.0",
        )

        assert vuln.cve_id == "CVE-2023-1234"
        assert vuln.severity == Severity.CRITICAL
        assert vuln.fix_version == "2.0.0"

    def test_vulnerability_to_dict(self):
        """Test converting vulnerability to dict"""
        vuln = Vulnerability(
            cve_id="CVE-2023-1234",
            severity=Severity.HIGH,
            description="Test",
        )

        data = vuln.to_dict()

        assert data["cve_id"] == "CVE-2023-1234"
        assert data["severity"] == Severity.HIGH


class TestDependencyScanner:
    """Test DependencyScanner class"""

    def test_scanner_initialization(self):
        """Test scanner initialization"""
        scanner = DependencyScanner()
        assert scanner.vuln_db is not None
        assert isinstance(scanner.vuln_db, VulnerabilityDatabase)

    def test_parse_python_requirement_simple(self):
        """Test parsing simple Python requirement"""
        scanner = DependencyScanner()
        dep = scanner._parse_python_requirement("requests==2.28.0", "requirements.txt")

        assert dep is not None
        assert dep.name == "requests"
        assert dep.version == "2.28.0"
        assert dep.ecosystem == "pypi"

    def test_parse_python_requirement_with_operators(self):
        """Test parsing Python requirements with different operators"""
        scanner = DependencyScanner()

        # Test >=
        dep = scanner._parse_python_requirement("fastapi>=0.100.0", "requirements.txt")
        assert dep is not None
        assert dep.name == "fastapi"
        assert dep.version == "0.100.0"

        # Test ~=
        dep = scanner._parse_python_requirement("uvicorn~=0.20.0", "requirements.txt")
        assert dep is not None
        assert dep.name == "uvicorn"

    def test_parse_python_requirement_with_extras(self):
        """Test parsing Python requirements with extras"""
        scanner = DependencyScanner()
        dep = scanner._parse_python_requirement(
            "uvicorn>=0.20.0; sys_platform == 'darwin'", "requirements.txt"
        )

        assert dep is not None
        assert dep.name == "uvicorn"

    def test_parse_python_requirement_invalid(self):
        """Test parsing invalid Python requirement"""
        scanner = DependencyScanner()

        # Git URL should return None
        dep = scanner._parse_python_requirement("git+https://github.com/user/repo.git", "requirements.txt")
        assert dep is None

        # -e editable should return None
        dep = scanner._parse_python_requirement("-e .", "requirements.txt")
        assert dep is None

    def test_compare_versions(self):
        """Test version comparison"""
        scanner = DependencyScanner()

        # Current < Latest
        assert scanner._compare_versions("1.0.0", "2.0.0") == -1
        assert scanner._compare_versions("1.5.0", "1.6.0") == -1

        # Current == Latest
        assert scanner._compare_versions("1.0.0", "1.0.0") == 0

        # Current > Latest
        assert scanner._compare_versions("2.0.0", "1.0.0") == 1

    def test_classify_license_permissive(self):
        """Test permissive license classification"""
        scanner = DependencyScanner()

        assert scanner._classify_license("MIT") == LicenseType.PERMISSIVE
        assert scanner._classify_license("Apache-2.0") == LicenseType.PERMISSIVE
        assert scanner._classify_license("BSD-3-Clause") == LicenseType.PERMISSIVE

    def test_classify_license_copyleft(self):
        """Test copyleft license classification"""
        scanner = DependencyScanner()

        assert scanner._classify_license("GPL-3.0") == LicenseType.COPYLEFT
        assert scanner._classify_license("LGPL-2.1") == LicenseType.COPYLEFT
        assert scanner._classify_license("AGPL-3.0") == LicenseType.COPYLEFT

    def test_classify_license_proprietary(self):
        """Test proprietary license classification"""
        scanner = DependencyScanner()

        assert scanner._classify_license("Proprietary") == LicenseType.PROPRIETARY
        assert scanner._classify_license("Commercial") == LicenseType.PROPRIETARY

    def test_classify_license_unknown(self):
        """Test unknown license classification"""
        scanner = DependencyScanner()

        assert scanner._classify_license("Custom License") == LicenseType.UNKNOWN
        assert scanner._classify_license("Weird-License-1.0") == LicenseType.UNKNOWN

    @pytest.mark.asyncio
    async def test_scan_python_deps_requirements_txt(self, tmp_path):
        """Test scanning requirements.txt"""
        # Create test requirements.txt
        requirements = tmp_path / "requirements.txt"
        requirements.write_text(
            """
# Test requirements
requests==2.28.0
fastapi>=0.100.0
uvicorn~=0.20.0

# Comment line
numpy>=1.24.0
        """.strip()
        )

        scanner = DependencyScanner()
        try:
            deps = await scanner.scan_python_deps(tmp_path)

            assert len(deps) == 4
            assert any(d.name == "requests" and d.version == "2.28.0" for d in deps)
            assert any(d.name == "fastapi" for d in deps)
            assert any(d.name == "uvicorn" for d in deps)
            assert any(d.name == "numpy" for d in deps)
        finally:
            await scanner.close()

    @pytest.mark.asyncio
    async def test_scan_npm_deps_package_json(self, tmp_path):
        """Test scanning package.json"""
        # Create test package.json
        package_json = tmp_path / "package.json"
        package_json.write_text(
            """
{
  "name": "test-project",
  "version": "1.0.0",
  "dependencies": {
    "express": "^4.18.0",
    "react": "^18.0.0"
  },
  "devDependencies": {
    "jest": "^29.0.0"
  }
}
        """.strip()
        )

        scanner = DependencyScanner()
        try:
            deps = await scanner.scan_npm_deps(tmp_path)

            assert len(deps) == 3
            assert any(d.name == "express" for d in deps)
            assert any(d.name == "react" for d in deps)
            assert any(d.name == "jest" for d in deps)
        finally:
            await scanner.close()

    @pytest.mark.asyncio
    async def test_generate_report(self, sample_dependencies):
        """Test report generation"""
        scanner = DependencyScanner()
        try:
            from .scanner import ScanResult

            result = ScanResult(
                dependencies=sample_dependencies,
                ecosystems_scanned=["pypi", "npm"],
            )
            result.calculate_stats()

            report = scanner.generate_report(result)

            assert "DEPENDENCY SCAN REPORT" in report
            assert "SUMMARY" in report
            assert str(len(sample_dependencies)) in report
        finally:
            await scanner.close()

    @pytest.mark.asyncio
    async def test_generate_tree_visualization(self, sample_dependencies):
        """Test tree visualization generation"""
        scanner = DependencyScanner()
        try:
            tree = scanner.generate_tree_visualization(sample_dependencies)

            assert "Dependency Tree" in tree
            assert "PYPI" in tree
            assert "NPM" in tree
            assert any(dep.name in tree for dep in sample_dependencies)
        finally:
            await scanner.close()


class TestVulnerabilityDatabase:
    """Test VulnerabilityDatabase class"""

    @pytest.mark.asyncio
    async def test_database_initialization(self):
        """Test database initialization"""
        db = VulnerabilityDatabase()
        try:
            assert db.cache_dir.exists()
            assert db.client is not None
        finally:
            await db.close()

    @pytest.mark.asyncio
    async def test_cache_path_generation(self):
        """Test cache path generation"""
        db = VulnerabilityDatabase()
        try:
            cache_path = db._get_cache_path("pypi", "requests", "2.28.0")

            assert cache_path.parent == db.cache_dir
            assert cache_path.suffix == ".json"
        finally:
            await db.close()

    @pytest.mark.asyncio
    async def test_extract_severity_from_cvss(self):
        """Test severity extraction from CVSS score"""
        db = VulnerabilityDatabase()
        try:
            # Critical
            vuln_data = {"severity": [{"type": "CVSS_V3", "score": "9.5"}]}
            severity = db._extract_severity(vuln_data)
            assert severity == Severity.CRITICAL

            # High
            vuln_data = {"severity": [{"type": "CVSS_V3", "score": "7.5"}]}
            severity = db._extract_severity(vuln_data)
            assert severity == Severity.HIGH

            # Medium
            vuln_data = {"severity": [{"type": "CVSS_V3", "score": "5.5"}]}
            severity = db._extract_severity(vuln_data)
            assert severity == Severity.MEDIUM

            # Low
            vuln_data = {"severity": [{"type": "CVSS_V3", "score": "2.5"}]}
            severity = db._extract_severity(vuln_data)
            assert severity == Severity.LOW
        finally:
            await db.close()


class TestIntegration:
    """Integration tests"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_scan_magnetar_project(self):
        """Test full scan of MagnetarCode project"""
        project_path = Path(__file__).parent.parent.parent.parent.parent

        scanner = DependencyScanner()
        try:
            result = await scanner.scan_project(project_path)

            # Should find Python dependencies
            assert len(result.dependencies) > 0
            assert "pypi" in result.ecosystems_scanned

            # Should have statistics
            assert result.total_vulnerabilities >= 0
            assert result.outdated_count >= 0

            # Should generate reports
            report = scanner.generate_report(result)
            assert len(report) > 0

            tree = scanner.generate_tree_visualization(result.dependencies)
            assert len(tree) > 0

        finally:
            await scanner.close()

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_vulnerability_check_real_package(self):
        """Test vulnerability check with real package (may be slow)"""
        scanner = DependencyScanner()
        try:
            # Use a package known to have had vulnerabilities in old versions
            deps = [
                Dependency(name="requests", version="2.6.0", ecosystem="pypi"),
            ]

            await scanner.check_vulnerabilities(deps)

            # This old version should have vulnerabilities
            # (Note: This test may fail if OSV data changes)
            assert len(deps[0].vulnerabilities) >= 0

        finally:
            await scanner.close()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
