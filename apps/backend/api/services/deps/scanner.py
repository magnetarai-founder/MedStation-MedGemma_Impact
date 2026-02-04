"""
Dependency Scanner Implementation

Production-grade dependency scanner with vulnerability detection, license checking,
and comprehensive security analysis for multiple programming languages.
"""

import asyncio
import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    """Vulnerability severity levels (CVSS-based)"""

    CRITICAL = "CRITICAL"  # CVSS 9.0-10.0
    HIGH = "HIGH"  # CVSS 7.0-8.9
    MEDIUM = "MEDIUM"  # CVSS 4.0-6.9
    LOW = "LOW"  # CVSS 0.1-3.9
    UNKNOWN = "UNKNOWN"


class LicenseType(str, Enum):
    """License categories for compliance"""

    PERMISSIVE = "PERMISSIVE"  # MIT, Apache, BSD
    COPYLEFT = "COPYLEFT"  # GPL, LGPL
    PROPRIETARY = "PROPRIETARY"
    UNKNOWN = "UNKNOWN"


@dataclass
class Vulnerability:
    """Represents a security vulnerability in a dependency"""

    cve_id: str
    severity: Severity
    description: str
    fix_version: str | None = None
    cvss_score: float | None = None
    published_date: str | None = None
    references: list[str] = field(default_factory=list)
    affected_versions: list[str] = field(default_factory=list)
    source: str = "OSV"  # OSV, NVD, etc.

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class LicenseIssue:
    """Represents a license compliance issue"""

    dependency_name: str
    license_name: str | None
    license_type: LicenseType
    issue_type: str  # e.g., "incompatible", "proprietary", "unknown"
    severity: str  # "error", "warning", "info"
    details: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class Dependency:
    """Represents a project dependency"""

    name: str
    version: str
    ecosystem: str  # pypi, npm, cargo, go
    latest_version: str | None = None
    is_outdated: bool = False
    is_unused: bool = False
    license: str | None = None
    license_type: LicenseType = LicenseType.UNKNOWN
    vulnerabilities: list[Vulnerability] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)  # Child dependencies
    source_file: str | None = None
    homepage: str | None = None
    repository: str | None = None

    @property
    def has_vulnerabilities(self) -> bool:
        """Check if dependency has any vulnerabilities"""
        return len(self.vulnerabilities) > 0

    @property
    def highest_severity(self) -> Severity:
        """Get highest vulnerability severity"""
        if not self.vulnerabilities:
            return Severity.UNKNOWN

        severity_order = {
            Severity.CRITICAL: 4,
            Severity.HIGH: 3,
            Severity.MEDIUM: 2,
            Severity.LOW: 1,
            Severity.UNKNOWN: 0,
        }

        return max(self.vulnerabilities, key=lambda v: severity_order[v.severity]).severity

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data["has_vulnerabilities"] = self.has_vulnerabilities
        data["highest_severity"] = self.highest_severity.value
        return data


@dataclass
class ScanResult:
    """Results from a dependency scan"""

    dependencies: list[Dependency] = field(default_factory=list)
    license_issues: list[LicenseIssue] = field(default_factory=list)
    scan_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    project_path: str | None = None
    ecosystems_scanned: list[str] = field(default_factory=list)
    total_vulnerabilities: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    outdated_count: int = 0
    unused_count: int = 0

    def calculate_stats(self) -> None:
        """Calculate statistics from dependencies"""
        self.total_vulnerabilities = sum(len(dep.vulnerabilities) for dep in self.dependencies)
        self.outdated_count = sum(1 for dep in self.dependencies if dep.is_outdated)
        self.unused_count = sum(1 for dep in self.dependencies if dep.is_unused)

        for dep in self.dependencies:
            for vuln in dep.vulnerabilities:
                if vuln.severity == Severity.CRITICAL:
                    self.critical_count += 1
                elif vuln.severity == Severity.HIGH:
                    self.high_count += 1
                elif vuln.severity == Severity.MEDIUM:
                    self.medium_count += 1
                elif vuln.severity == Severity.LOW:
                    self.low_count += 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "dependencies": [dep.to_dict() for dep in self.dependencies],
            "license_issues": [issue.to_dict() for issue in self.license_issues],
            "scan_timestamp": self.scan_timestamp,
            "project_path": self.project_path,
            "ecosystems_scanned": self.ecosystems_scanned,
            "statistics": {
                "total_dependencies": len(self.dependencies),
                "total_vulnerabilities": self.total_vulnerabilities,
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count,
                "outdated": self.outdated_count,
                "unused": self.unused_count,
            },
        }


class VulnerabilityDatabase:
    """Client for vulnerability databases (OSV, NVD)"""

    OSV_API_URL = "https://api.osv.dev/v1"
    CACHE_TTL = timedelta(hours=24)

    def __init__(self, cache_dir: Path | None = None):
        """
        Initialize vulnerability database client.

        Args:
            cache_dir: Directory for caching vulnerability data
        """
        self.cache_dir = cache_dir or Path.home() / ".magnetar" / "vuln_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.client = httpx.AsyncClient(timeout=30.0)
        self._cache: dict[str, dict[str, Any]] = {}

    async def close(self) -> None:
        """Close HTTP client"""
        await self.client.aclose()

    def _get_cache_path(self, ecosystem: str, package: str, version: str) -> Path:
        """Get cache file path for a package"""
        cache_key = f"{ecosystem}:{package}:{version}"
        cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
        return self.cache_dir / f"{cache_hash}.json"

    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cache is still valid"""
        if not cache_path.exists():
            return False

        cache_age = datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)
        return cache_age < self.CACHE_TTL

    async def _get_from_cache(self, ecosystem: str, package: str, version: str) -> list[Vulnerability] | None:
        """Get vulnerabilities from cache"""
        cache_path = self._get_cache_path(ecosystem, package, version)

        if not self._is_cache_valid(cache_path):
            return None

        try:
            with open(cache_path, "r") as f:
                data = json.load(f)
                return [
                    Vulnerability(
                        cve_id=v["cve_id"],
                        severity=Severity(v["severity"]),
                        description=v["description"],
                        fix_version=v.get("fix_version"),
                        cvss_score=v.get("cvss_score"),
                        published_date=v.get("published_date"),
                        references=v.get("references", []),
                        affected_versions=v.get("affected_versions", []),
                        source=v.get("source", "OSV"),
                    )
                    for v in data
                ]
        except Exception as e:
            logger.warning(f"Cache read error for {package}: {e}")
            return None

    async def _save_to_cache(self, ecosystem: str, package: str, version: str, vulns: list[Vulnerability]) -> None:
        """Save vulnerabilities to cache"""
        cache_path = self._get_cache_path(ecosystem, package, version)

        try:
            with open(cache_path, "w") as f:
                json.dump([v.to_dict() for v in vulns], f)
        except Exception as e:
            logger.warning(f"Cache write error for {package}: {e}")

    async def query_osv(self, ecosystem: str, package: str, version: str) -> list[Vulnerability]:
        """
        Query OSV API for vulnerabilities.

        Args:
            ecosystem: Package ecosystem (PyPI, npm, crates.io, Go)
            package: Package name
            version: Package version

        Returns:
            List of vulnerabilities
        """
        # Check cache first
        cached = await self._get_from_cache(ecosystem, package, version)
        if cached is not None:
            logger.debug(f"Cache hit for {package}@{version}")
            return cached

        # Map ecosystem names to OSV format
        ecosystem_map = {
            "pypi": "PyPI",
            "npm": "npm",
            "cargo": "crates.io",
            "go": "Go",
        }
        osv_ecosystem = ecosystem_map.get(ecosystem.lower(), ecosystem)

        # Query OSV API
        query = {"package": {"name": package, "ecosystem": osv_ecosystem}, "version": version}

        try:
            response = await self.client.post(f"{self.OSV_API_URL}/query", json=query)
            response.raise_for_status()
            data = response.json()

            vulnerabilities = []
            for vuln_data in data.get("vulns", []):
                vuln = self._parse_osv_vulnerability(vuln_data)
                if vuln:
                    vulnerabilities.append(vuln)

            # Cache results
            await self._save_to_cache(ecosystem, package, version, vulnerabilities)

            return vulnerabilities

        except httpx.HTTPError as e:
            logger.error(f"OSV API error for {package}@{version}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error querying OSV for {package}@{version}: {e}")
            return []

    def _parse_osv_vulnerability(self, vuln_data: dict[str, Any]) -> Vulnerability | None:
        """Parse OSV vulnerability data"""
        try:
            vuln_id = vuln_data.get("id", "UNKNOWN")
            aliases = vuln_data.get("aliases", [])

            # Extract CVE ID
            cve_id = next((alias for alias in aliases if alias.startswith("CVE-")), vuln_id)

            # Extract severity
            severity = self._extract_severity(vuln_data)

            # Extract fix version
            fix_version = None
            for affected in vuln_data.get("affected", []):
                for ranges in affected.get("ranges", []):
                    if "fixed" in ranges.get("events", [{}])[-1]:
                        fix_version = ranges["events"][-1]["fixed"]
                        break

            # Extract affected versions
            affected_versions = []
            for affected in vuln_data.get("affected", []):
                for version_info in affected.get("versions", []):
                    affected_versions.append(version_info)

            return Vulnerability(
                cve_id=cve_id,
                severity=severity,
                description=vuln_data.get("summary", vuln_data.get("details", "No description available"))[:500],
                fix_version=fix_version,
                cvss_score=self._extract_cvss_score(vuln_data),
                published_date=vuln_data.get("published"),
                references=[ref.get("url", "") for ref in vuln_data.get("references", [])],
                affected_versions=affected_versions,
                source="OSV",
            )

        except Exception as e:
            logger.error(f"Error parsing OSV vulnerability: {e}")
            return None

    def _extract_severity(self, vuln_data: dict[str, Any]) -> Severity:
        """Extract severity from vulnerability data"""
        # Check database_specific severity
        db_specific = vuln_data.get("database_specific", {})
        severity_str = db_specific.get("severity", "").upper()

        if severity_str in [s.value for s in Severity]:
            return Severity(severity_str)

        # Check CVSS score
        cvss_score = self._extract_cvss_score(vuln_data)
        if cvss_score is not None:
            if cvss_score >= 9.0:
                return Severity.CRITICAL
            elif cvss_score >= 7.0:
                return Severity.HIGH
            elif cvss_score >= 4.0:
                return Severity.MEDIUM
            elif cvss_score > 0:
                return Severity.LOW

        return Severity.UNKNOWN

    def _extract_cvss_score(self, vuln_data: dict[str, Any]) -> float | None:
        """Extract CVSS score from vulnerability data"""
        # Try severity field
        for severity_entry in vuln_data.get("severity", []):
            if severity_entry.get("type") == "CVSS_V3":
                score_str = severity_entry.get("score", "")
                try:
                    # Parse CVSS vector string
                    if "/" in score_str:
                        return float(score_str.split("/")[0])
                    return float(score_str)
                except (ValueError, IndexError) as e:
                    logger.debug(f"Could not parse CVSS score '{score_str}': {e}")

        # Try database_specific
        db_specific = vuln_data.get("database_specific", {})
        if "cvss" in db_specific:
            try:
                return float(db_specific["cvss"])
            except (ValueError, TypeError) as e:
                logger.debug(f"Could not parse database_specific CVSS: {e}")

        return None


class DependencyScanner:
    """
    Multi-language dependency scanner with vulnerability detection.

    Supports:
    - Python: requirements.txt, pyproject.toml
    - Node.js: package.json, package-lock.json
    - Rust: Cargo.toml, Cargo.lock
    - Go: go.mod, go.sum
    """

    # License classifications
    PERMISSIVE_LICENSES = {
        "MIT",
        "Apache-2.0",
        "Apache",
        "BSD",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "ISC",
        "0BSD",
        "Unlicense",
        "CC0-1.0",
    }

    COPYLEFT_LICENSES = {
        "GPL",
        "GPL-2.0",
        "GPL-3.0",
        "AGPL",
        "AGPL-3.0",
        "LGPL",
        "LGPL-2.1",
        "LGPL-3.0",
        "MPL-2.0",
        "EPL-2.0",
    }

    def __init__(self, cache_dir: Path | None = None):
        """
        Initialize dependency scanner.

        Args:
            cache_dir: Directory for caching vulnerability data
        """
        self.vuln_db = VulnerabilityDatabase(cache_dir)
        self._package_cache: dict[str, dict[str, Any]] = {}

    async def close(self) -> None:
        """Clean up resources"""
        await self.vuln_db.close()

    async def scan_project(self, project_path: str | Path) -> ScanResult:
        """
        Scan a project for dependencies and vulnerabilities.

        Args:
            project_path: Path to project root

        Returns:
            ScanResult with all findings
        """
        project_path = Path(project_path)
        result = ScanResult(project_path=str(project_path))

        # Scan each ecosystem
        ecosystems_to_scan = [
            ("pypi", self.scan_python_deps),
            ("npm", self.scan_npm_deps),
            ("cargo", self.scan_rust_deps),
            ("go", self.scan_go_deps),
        ]

        for ecosystem, scan_func in ecosystems_to_scan:
            try:
                deps = await scan_func(project_path)
                if deps:
                    result.dependencies.extend(deps)
                    result.ecosystems_scanned.append(ecosystem)
                    logger.info(f"Found {len(deps)} {ecosystem} dependencies")
            except Exception as e:
                logger.error(f"Error scanning {ecosystem} dependencies: {e}")

        # Check vulnerabilities for all dependencies
        await self.check_vulnerabilities(result.dependencies)

        # Check for outdated packages
        await self.check_outdated(result.dependencies)

        # Check licenses
        license_issues = await self.check_licenses(result.dependencies)
        result.license_issues.extend(license_issues)

        # Find unused dependencies (if project files exist)
        try:
            await self.find_unused(project_path, result.dependencies)
        except Exception as e:
            logger.warning(f"Could not check for unused dependencies: {e}")

        # Calculate statistics
        result.calculate_stats()

        return result

    async def scan_python_deps(self, project_path: Path) -> list[Dependency]:
        """
        Scan Python dependencies from requirements.txt or pyproject.toml.

        Args:
            project_path: Path to project root

        Returns:
            List of Python dependencies
        """
        dependencies = []

        # Try requirements.txt
        requirements_file = project_path / "requirements.txt"
        if requirements_file.exists():
            deps = await self._parse_requirements_txt(requirements_file)
            dependencies.extend(deps)

        # Try pyproject.toml
        pyproject_file = project_path / "pyproject.toml"
        if pyproject_file.exists():
            deps = await self._parse_pyproject_toml(pyproject_file)
            dependencies.extend(deps)

        return dependencies

    async def _parse_requirements_txt(self, file_path: Path) -> list[Dependency]:
        """Parse requirements.txt file"""
        dependencies = []

        try:
            content = file_path.read_text()
            for line in content.splitlines():
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue

                # Parse package specification
                dep = self._parse_python_requirement(line, str(file_path))
                if dep:
                    dependencies.append(dep)

        except Exception as e:
            logger.error(f"Error parsing requirements.txt: {e}")

        return dependencies

    def _parse_python_requirement(self, requirement: str, source_file: str) -> Dependency | None:
        """Parse a single Python requirement specification"""
        # Remove inline comments
        requirement = requirement.split("#")[0].strip()

        # Handle -e git+https://... and similar
        if requirement.startswith("-e") or requirement.startswith("git+"):
            return None

        # Parse package name and version
        # Support formats: package==1.0.0, package>=1.0.0, package~=1.0.0
        match = re.match(r"^([a-zA-Z0-9_-]+)\s*([><=~!]+)\s*([0-9.]+.*?)(?:;.*)?$", requirement)

        if match:
            name = match.group(1)
            operator = match.group(2)
            version = match.group(3).strip()

            # For ranges, use the base version
            if operator in (">=", ">", "~="):
                version = version.split(",")[0].strip()

            return Dependency(
                name=name,
                version=version,
                ecosystem="pypi",
                source_file=source_file,
            )

        # Try simple name without version
        match = re.match(r"^([a-zA-Z0-9_-]+)$", requirement)
        if match:
            return Dependency(
                name=match.group(1),
                version="unknown",
                ecosystem="pypi",
                source_file=source_file,
            )

        return None

    async def _parse_pyproject_toml(self, file_path: Path) -> list[Dependency]:
        """Parse pyproject.toml file"""
        dependencies = []

        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore
            except ImportError:
                logger.warning("toml library not available, skipping pyproject.toml")
                return dependencies

        try:
            with open(file_path, "rb") as f:
                data = tomllib.load(f)

            # Poetry format
            poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
            for name, spec in poetry_deps.items():
                if name == "python":
                    continue

                version = spec if isinstance(spec, str) else spec.get("version", "unknown")
                # Clean version spec
                version = version.lstrip("^~>=<")

                dependencies.append(
                    Dependency(
                        name=name,
                        version=version,
                        ecosystem="pypi",
                        source_file=str(file_path),
                    )
                )

            # PEP 621 format
            project_deps = data.get("project", {}).get("dependencies", [])
            for dep_spec in project_deps:
                dep = self._parse_python_requirement(dep_spec, str(file_path))
                if dep:
                    dependencies.append(dep)

        except Exception as e:
            logger.error(f"Error parsing pyproject.toml: {e}")

        return dependencies

    async def scan_npm_deps(self, project_path: Path) -> list[Dependency]:
        """
        Scan Node.js dependencies from package.json.

        Args:
            project_path: Path to project root

        Returns:
            List of npm dependencies
        """
        dependencies = []
        package_json = project_path / "package.json"

        if not package_json.exists():
            return dependencies

        try:
            data = json.loads(package_json.read_text())

            # Parse dependencies and devDependencies
            for dep_type in ["dependencies", "devDependencies"]:
                deps = data.get(dep_type, {})
                for name, version_spec in deps.items():
                    # Clean version specification
                    version = version_spec.lstrip("^~>=<")

                    dependencies.append(
                        Dependency(
                            name=name,
                            version=version,
                            ecosystem="npm",
                            source_file=str(package_json),
                        )
                    )

        except Exception as e:
            logger.error(f"Error parsing package.json: {e}")

        return dependencies

    async def scan_rust_deps(self, project_path: Path) -> list[Dependency]:
        """
        Scan Rust dependencies from Cargo.toml.

        Args:
            project_path: Path to project root

        Returns:
            List of Cargo dependencies
        """
        dependencies = []
        cargo_toml = project_path / "Cargo.toml"

        if not cargo_toml.exists():
            return dependencies

        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore
            except ImportError:
                logger.warning("toml library not available, skipping Cargo.toml")
                return dependencies

        try:
            with open(cargo_toml, "rb") as f:
                data = tomllib.load(f)

            # Parse dependencies
            deps = data.get("dependencies", {})
            for name, spec in deps.items():
                version = spec if isinstance(spec, str) else spec.get("version", "unknown")
                version = version.lstrip("^~>=<")

                dependencies.append(
                    Dependency(
                        name=name,
                        version=version,
                        ecosystem="cargo",
                        source_file=str(cargo_toml),
                    )
                )

        except Exception as e:
            logger.error(f"Error parsing Cargo.toml: {e}")

        return dependencies

    async def scan_go_deps(self, project_path: Path) -> list[Dependency]:
        """
        Scan Go dependencies from go.mod.

        Args:
            project_path: Path to project root

        Returns:
            List of Go module dependencies
        """
        dependencies = []
        go_mod = project_path / "go.mod"

        if not go_mod.exists():
            return dependencies

        try:
            content = go_mod.read_text()
            in_require_block = False

            for line in content.splitlines():
                line = line.strip()

                if line.startswith("require ("):
                    in_require_block = True
                    continue
                elif line == ")":
                    in_require_block = False
                    continue

                # Parse require line
                if in_require_block or line.startswith("require "):
                    match = re.match(r"(?:require\s+)?([^\s]+)\s+v?([0-9.]+[^\s]*)", line)
                    if match:
                        name = match.group(1)
                        version = match.group(2)

                        dependencies.append(
                            Dependency(
                                name=name,
                                version=version,
                                ecosystem="go",
                                source_file=str(go_mod),
                            )
                        )

        except Exception as e:
            logger.error(f"Error parsing go.mod: {e}")

        return dependencies

    async def check_vulnerabilities(self, dependencies: list[Dependency]) -> None:
        """
        Check dependencies for known vulnerabilities.

        Args:
            dependencies: List of dependencies to check
        """
        tasks = []
        for dep in dependencies:
            if dep.version and dep.version != "unknown":
                tasks.append(self._check_dependency_vulnerabilities(dep))

        # Check vulnerabilities concurrently (with rate limiting)
        batch_size = 10
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i : i + batch_size]
            await asyncio.gather(*batch, return_exceptions=True)
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.1)

    async def _check_dependency_vulnerabilities(self, dependency: Dependency) -> None:
        """Check a single dependency for vulnerabilities"""
        try:
            vulns = await self.vuln_db.query_osv(dependency.ecosystem, dependency.name, dependency.version)
            dependency.vulnerabilities.extend(vulns)
        except Exception as e:
            logger.error(f"Error checking vulnerabilities for {dependency.name}: {e}")

    async def check_outdated(self, dependencies: list[Dependency]) -> None:
        """
        Check which dependencies are outdated.

        Args:
            dependencies: List of dependencies to check
        """
        tasks = []
        for dep in dependencies:
            tasks.append(self._check_latest_version(dep))

        # Check latest versions concurrently
        batch_size = 20
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i : i + batch_size]
            await asyncio.gather(*batch, return_exceptions=True)

    async def _check_latest_version(self, dependency: Dependency) -> None:
        """Check latest version for a dependency"""
        try:
            if dependency.ecosystem == "pypi":
                latest = await self._get_pypi_latest_version(dependency.name)
            elif dependency.ecosystem == "npm":
                latest = await self._get_npm_latest_version(dependency.name)
            elif dependency.ecosystem == "cargo":
                latest = await self._get_crates_latest_version(dependency.name)
            elif dependency.ecosystem == "go":
                latest = await self._get_go_latest_version(dependency.name)
            else:
                return

            if latest:
                dependency.latest_version = latest
                dependency.is_outdated = self._compare_versions(dependency.version, latest) < 0

        except Exception as e:
            logger.debug(f"Could not check latest version for {dependency.name}: {e}")

    async def _get_pypi_latest_version(self, package: str) -> str | None:
        """Get latest version from PyPI"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"https://pypi.org/pypi/{package}/json", timeout=10.0)
                response.raise_for_status()
                data = response.json()
                return data["info"]["version"]
        except Exception as e:
            logger.debug(f"Could not fetch PyPI latest version for {package}: {e}")
            return None

    async def _get_npm_latest_version(self, package: str) -> str | None:
        """Get latest version from npm registry"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"https://registry.npmjs.org/{package}/latest", timeout=10.0)
                response.raise_for_status()
                data = response.json()
                return data["version"]
        except Exception as e:
            logger.debug(f"Could not fetch npm latest version for {package}: {e}")
            return None

    async def _get_crates_latest_version(self, package: str) -> str | None:
        """Get latest version from crates.io"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"https://crates.io/api/v1/crates/{package}", timeout=10.0)
                response.raise_for_status()
                data = response.json()
                return data["crate"]["newest_version"]
        except Exception as e:
            logger.debug(f"Could not fetch crates.io latest version for {package}: {e}")
            return None

    async def _get_go_latest_version(self, module: str) -> str | None:
        """Get latest version from Go proxy"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"https://proxy.golang.org/{module}/@latest", timeout=10.0)
                response.raise_for_status()
                data = response.json()
                return data["Version"].lstrip("v")
        except Exception as e:
            logger.debug(f"Could not fetch Go proxy latest version for {module}: {e}")
            return None

    def _compare_versions(self, current: str, latest: str) -> int:
        """
        Compare two semantic versions.

        Returns:
            -1 if current < latest
            0 if current == latest
            1 if current > latest
        """
        try:
            # Clean version strings
            current_clean = current.lstrip("v^~>=<").split("+")[0].split("-")[0]
            latest_clean = latest.lstrip("v^~>=<").split("+")[0].split("-")[0]

            current_parts = [int(x) for x in current_clean.split(".")]
            latest_parts = [int(x) for x in latest_clean.split(".")]

            # Pad to same length
            max_len = max(len(current_parts), len(latest_parts))
            current_parts.extend([0] * (max_len - len(current_parts)))
            latest_parts.extend([0] * (max_len - len(latest_parts)))

            if current_parts < latest_parts:
                return -1
            elif current_parts > latest_parts:
                return 1
            else:
                return 0

        except (ValueError, IndexError):
            return 0

    async def check_licenses(self, dependencies: list[Dependency]) -> list[LicenseIssue]:
        """
        Check license compliance for dependencies.

        Args:
            dependencies: List of dependencies to check

        Returns:
            List of license issues found
        """
        issues = []

        for dep in dependencies:
            # Get license info
            await self._fetch_license_info(dep)

            # Check for issues
            if not dep.license:
                issues.append(
                    LicenseIssue(
                        dependency_name=dep.name,
                        license_name=None,
                        license_type=LicenseType.UNKNOWN,
                        issue_type="unknown",
                        severity="warning",
                        details=f"License information not found for {dep.name}",
                    )
                )
            elif dep.license_type == LicenseType.PROPRIETARY:
                issues.append(
                    LicenseIssue(
                        dependency_name=dep.name,
                        license_name=dep.license,
                        license_type=dep.license_type,
                        issue_type="proprietary",
                        severity="error",
                        details=f"{dep.name} uses proprietary license: {dep.license}",
                    )
                )
            elif dep.license_type == LicenseType.COPYLEFT:
                issues.append(
                    LicenseIssue(
                        dependency_name=dep.name,
                        license_name=dep.license,
                        license_type=dep.license_type,
                        issue_type="copyleft",
                        severity="warning",
                        details=f"{dep.name} uses copyleft license: {dep.license}. May require source disclosure.",
                    )
                )

        return issues

    async def _fetch_license_info(self, dependency: Dependency) -> None:
        """Fetch license information for a dependency"""
        try:
            if dependency.ecosystem == "pypi":
                await self._fetch_pypi_license(dependency)
            elif dependency.ecosystem == "npm":
                await self._fetch_npm_license(dependency)
            elif dependency.ecosystem == "cargo":
                await self._fetch_crates_license(dependency)
            # Go modules typically use repository LICENSE files
        except Exception as e:
            logger.debug(f"Could not fetch license for {dependency.name}: {e}")

    async def _fetch_pypi_license(self, dependency: Dependency) -> None:
        """Fetch license from PyPI"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"https://pypi.org/pypi/{dependency.name}/json", timeout=10.0)
                response.raise_for_status()
                data = response.json()
                license_name = data["info"].get("license")
                if license_name:
                    dependency.license = license_name
                    dependency.license_type = self._classify_license(license_name)
        except Exception as e:
            logger.debug(f"Could not fetch PyPI license for {dependency.name}: {e}")

    async def _fetch_npm_license(self, dependency: Dependency) -> None:
        """Fetch license from npm"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"https://registry.npmjs.org/{dependency.name}", timeout=10.0)
                response.raise_for_status()
                data = response.json()
                latest_version = data.get("dist-tags", {}).get("latest")
                if latest_version:
                    version_data = data.get("versions", {}).get(latest_version, {})
                    license_name = version_data.get("license")
                    if license_name:
                        dependency.license = license_name
                        dependency.license_type = self._classify_license(license_name)
        except Exception as e:
            logger.debug(f"Could not fetch npm license for {dependency.name}: {e}")

    async def _fetch_crates_license(self, dependency: Dependency) -> None:
        """Fetch license from crates.io"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"https://crates.io/api/v1/crates/{dependency.name}", timeout=10.0)
                response.raise_for_status()
                data = response.json()
                license_name = data["crate"].get("license")
                if license_name:
                    dependency.license = license_name
                    dependency.license_type = self._classify_license(license_name)
        except Exception as e:
            logger.debug(f"Could not fetch crates.io license for {dependency.name}: {e}")

    def _classify_license(self, license_name: str) -> LicenseType:
        """Classify a license by type"""
        license_upper = license_name.upper()

        # Check permissive
        for perm_license in self.PERMISSIVE_LICENSES:
            if perm_license.upper() in license_upper:
                return LicenseType.PERMISSIVE

        # Check copyleft
        for copyleft_license in self.COPYLEFT_LICENSES:
            if copyleft_license.upper() in license_upper:
                return LicenseType.COPYLEFT

        # Check for proprietary indicators
        if any(word in license_upper for word in ["PROPRIETARY", "COMMERCIAL", "CLOSED"]):
            return LicenseType.PROPRIETARY

        return LicenseType.UNKNOWN

    async def find_unused(self, project_path: Path, dependencies: list[Dependency]) -> None:
        """
        Find unused dependencies by analyzing project source code.

        Args:
            project_path: Path to project root
            dependencies: List of dependencies to check

        Note:
            This is a heuristic approach that may have false positives/negatives.
            Uses safe file system operations to search for import statements.
        """
        for dep in dependencies:
            is_used = await self._is_dependency_used(project_path, dep)
            dep.is_unused = not is_used

    async def _is_dependency_used(self, project_path: Path, dependency: Dependency) -> bool:
        """Check if a dependency is used in the project using safe file scanning"""
        # Search patterns by ecosystem
        search_patterns = {
            "pypi": [
                f"import {dependency.name}",
                f"from {dependency.name}",
            ],
            "npm": [
                f'require("{dependency.name}")',
                f"require('{dependency.name}')",
                f'from "{dependency.name}"',
                f"from '{dependency.name}'",
            ],
            "cargo": [f"use {dependency.name}::"],
            "go": [f'"{dependency.name}"'],
        }

        patterns = search_patterns.get(dependency.ecosystem, [])
        if not patterns:
            return True  # Assume used if we can't check

        # File extensions to search by ecosystem
        extensions = {
            "pypi": [".py"],
            "npm": [".js", ".ts", ".jsx", ".tsx"],
            "cargo": [".rs"],
            "go": [".go"],
        }

        search_extensions = extensions.get(dependency.ecosystem, [])

        # Recursively search project files
        try:
            for ext in search_extensions:
                for file_path in project_path.rglob(f"*{ext}"):
                    # Skip common non-source directories
                    if any(
                        part in file_path.parts
                        for part in [
                            "node_modules",
                            ".git",
                            "__pycache__",
                            "venv",
                            ".venv",
                            "dist",
                            "build",
                            "target",
                        ]
                    ):
                        continue

                    try:
                        # Safe file read with size limit
                        if file_path.stat().st_size > 1_000_000:  # Skip files > 1MB
                            continue

                        content = file_path.read_text(errors="ignore")

                        # Check for any pattern match
                        for pattern in patterns:
                            if pattern in content:
                                return True

                    except (OSError, UnicodeDecodeError):
                        continue

            return False

        except Exception as e:
            logger.debug(f"Error checking if {dependency.name} is used: {e}")
            return True  # Assume used on error

    def generate_report(self, result: ScanResult) -> str:
        """
        Generate a human-readable report from scan results.

        Args:
            result: Scan results

        Returns:
            Formatted report as string
        """
        lines = [
            "=" * 80,
            "DEPENDENCY SCAN REPORT",
            "=" * 80,
            f"Project: {result.project_path}",
            f"Scanned: {result.scan_timestamp}",
            f"Ecosystems: {', '.join(result.ecosystems_scanned)}",
            "",
            "SUMMARY",
            "-" * 80,
            f"Total Dependencies: {len(result.dependencies)}",
            f"Vulnerabilities: {result.total_vulnerabilities} "
            f"(Critical: {result.critical_count}, High: {result.high_count}, "
            f"Medium: {result.medium_count}, Low: {result.low_count})",
            f"Outdated: {result.outdated_count}",
            f"Unused: {result.unused_count}",
            f"License Issues: {len(result.license_issues)}",
            "",
        ]

        # Critical vulnerabilities
        critical_deps = [dep for dep in result.dependencies if dep.highest_severity == Severity.CRITICAL]
        if critical_deps:
            lines.extend(
                [
                    "CRITICAL VULNERABILITIES",
                    "-" * 80,
                ]
            )
            for dep in critical_deps:
                lines.append(f"\n{dep.name} {dep.version}")
                for vuln in dep.vulnerabilities:
                    if vuln.severity == Severity.CRITICAL:
                        lines.append(f"  [{vuln.severity.value}] {vuln.cve_id}")
                        lines.append(f"  {vuln.description[:100]}...")
                        if vuln.fix_version:
                            lines.append(f"  Fix: Upgrade to {vuln.fix_version}")
            lines.append("")

        # High vulnerabilities
        high_deps = [dep for dep in result.dependencies if dep.highest_severity == Severity.HIGH]
        if high_deps:
            lines.extend(
                [
                    "HIGH SEVERITY VULNERABILITIES",
                    "-" * 80,
                ]
            )
            for dep in high_deps[:10]:  # Limit to first 10
                lines.append(f"\n{dep.name} {dep.version}")
                for vuln in dep.vulnerabilities:
                    if vuln.severity == Severity.HIGH:
                        lines.append(f"  [{vuln.severity.value}] {vuln.cve_id}")
                        if vuln.fix_version:
                            lines.append(f"  Fix: Upgrade to {vuln.fix_version}")
            if len(high_deps) > 10:
                lines.append(f"\n... and {len(high_deps) - 10} more")
            lines.append("")

        # Outdated packages
        outdated = [dep for dep in result.dependencies if dep.is_outdated]
        if outdated:
            lines.extend(
                [
                    "OUTDATED PACKAGES",
                    "-" * 80,
                ]
            )
            for dep in outdated[:15]:  # Limit to first 15
                lines.append(f"{dep.name}: {dep.version} -> {dep.latest_version}")
            if len(outdated) > 15:
                lines.append(f"... and {len(outdated) - 15} more")
            lines.append("")

        # License issues
        if result.license_issues:
            lines.extend(
                [
                    "LICENSE ISSUES",
                    "-" * 80,
                ]
            )
            for issue in result.license_issues[:10]:
                lines.append(f"[{issue.severity.upper()}] {issue.dependency_name}: {issue.details}")
            if len(result.license_issues) > 10:
                lines.append(f"... and {len(result.license_issues) - 10} more")
            lines.append("")

        # Recommendations
        lines.extend(
            [
                "RECOMMENDATIONS",
                "-" * 80,
            ]
        )

        if result.critical_count > 0:
            lines.append("1. URGENT: Address critical vulnerabilities immediately")
        if result.high_count > 0:
            lines.append("2. Update packages with high severity vulnerabilities")
        if result.outdated_count > 10:
            lines.append("3. Consider updating outdated packages")
        if result.unused_count > 0:
            lines.append(f"4. Review {result.unused_count} potentially unused dependencies")

        lines.extend(["", "=" * 80])

        return "\n".join(lines)

    def generate_tree_visualization(self, dependencies: list[Dependency]) -> str:
        """
        Generate a simple dependency tree visualization.

        Args:
            dependencies: List of dependencies

        Returns:
            Tree visualization as string
        """
        lines = ["Dependency Tree", "=" * 80]

        # Group by ecosystem
        by_ecosystem: dict[str, list[Dependency]] = {}
        for dep in dependencies:
            by_ecosystem.setdefault(dep.ecosystem, []).append(dep)

        for ecosystem, deps in sorted(by_ecosystem.items()):
            lines.append(f"\n{ecosystem.upper()}")
            for dep in sorted(deps, key=lambda d: d.name):
                prefix = "├──"
                vuln_marker = " ⚠️" if dep.has_vulnerabilities else ""
                outdated_marker = " 📦" if dep.is_outdated else ""
                lines.append(f"{prefix} {dep.name}@{dep.version}{vuln_marker}{outdated_marker}")

                # Show vulnerabilities
                if dep.vulnerabilities:
                    for vuln in dep.vulnerabilities[:2]:  # Limit to 2 per dep
                        lines.append(f"    └─ [{vuln.severity.value}] {vuln.cve_id}")

        return "\n".join(lines)


# Convenience function for quick scans
async def quick_scan(project_path: str | Path) -> ScanResult:
    """
    Perform a quick dependency scan.

    Args:
        project_path: Path to project root

    Returns:
        ScanResult with findings
    """
    scanner = DependencyScanner()
    try:
        result = await scanner.scan_project(project_path)
        return result
    finally:
        await scanner.close()
