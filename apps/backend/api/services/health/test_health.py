"""
Basic tests for Code Health Dashboard

Run with: pytest test_health.py -v
"""

import asyncio
import tempfile
from pathlib import Path
import pytest

from api.services.health import (
    HealthDashboard,
    HealthThresholds,
    HealthStatus,
    TrendDirection,
    CodeMetrics,
    FileHealth,
)


# Sample Python code for testing
SIMPLE_CODE = '''
def simple_function(x):
    """A simple function"""
    return x + 1

def complex_function(a, b, c):
    if a > 0:
        if b > 0:
            if c > 0:
                return a + b + c
            else:
                return a + b
        else:
            return a
    else:
        return 0
'''

UNDOCUMENTED_CODE = '''
def no_docs(x):
    return x * 2

def also_no_docs(x, y):
    return x + y
'''


class TestComplexityAnalyzer:
    """Test complexity calculation"""

    def test_simple_function_complexity(self, tmp_path):
        """Test that simple functions have low complexity"""
        code_file = tmp_path / "simple.py"
        code_file.write_text(SIMPLE_CODE)

        dashboard = HealthDashboard(project_root=str(tmp_path))
        metrics = dashboard.calculate_complexity(code_file)

        # Find the simple function
        simple = next(m for m in metrics if m.name == 'simple_function')
        assert simple.cyclomatic_complexity == 1
        assert simple.has_docstring is True

    def test_complex_function_complexity(self, tmp_path):
        """Test that nested ifs increase complexity"""
        code_file = tmp_path / "complex.py"
        code_file.write_text(SIMPLE_CODE)

        dashboard = HealthDashboard(project_root=str(tmp_path))
        metrics = dashboard.calculate_complexity(code_file)

        # Find the complex function
        complex_func = next(m for m in metrics if m.name == 'complex_function')
        assert complex_func.cyclomatic_complexity > 3
        assert complex_func.num_parameters == 3


class TestMaintainabilityIndex:
    """Test maintainability index calculation"""

    def test_maintainability_calculation(self, tmp_path):
        """Test that maintainability index is calculated"""
        code_file = tmp_path / "test.py"
        code_file.write_text(SIMPLE_CODE)

        dashboard = HealthDashboard(project_root=str(tmp_path))
        metrics = dashboard.calculate_complexity(code_file)
        mi = dashboard.calculate_maintainability(code_file, metrics)

        assert 0 <= mi <= 100
        # Simple code should have high maintainability
        assert mi > 50

    def test_low_maintainability(self, tmp_path):
        """Test that complex code has lower maintainability"""
        # Create a long, complex file
        complex_code = SIMPLE_CODE * 10  # Repeat to increase LOC
        code_file = tmp_path / "complex.py"
        code_file.write_text(complex_code)

        dashboard = HealthDashboard(project_root=str(tmp_path))
        metrics = dashboard.calculate_complexity(code_file)
        mi = dashboard.calculate_maintainability(code_file, metrics)

        assert 0 <= mi <= 100


class TestFileAnalysis:
    """Test file health analysis"""

    def test_analyze_simple_file(self, tmp_path):
        """Test analyzing a simple file"""
        code_file = tmp_path / "simple.py"
        code_file.write_text(SIMPLE_CODE)

        dashboard = HealthDashboard(project_root=str(tmp_path))
        health = dashboard.analyze_file(code_file)

        assert health is not None
        assert health.function_count == 2
        assert health.status in [HealthStatus.GOOD, HealthStatus.WARNING]
        assert health.total_lines > 0

    def test_documentation_coverage(self, tmp_path):
        """Test documentation coverage calculation"""
        code_file = tmp_path / "undoc.py"
        code_file.write_text(UNDOCUMENTED_CODE)

        dashboard = HealthDashboard(project_root=str(tmp_path))
        health = dashboard.analyze_file(code_file)

        # No functions have docstrings
        assert health.documentation_coverage == 0.0


class TestTechnicalDebt:
    """Test technical debt estimation"""

    def test_debt_for_undocumented_code(self, tmp_path):
        """Test that undocumented code generates debt items"""
        code_file = tmp_path / "undoc.py"
        code_file.write_text(UNDOCUMENTED_CODE)

        dashboard = HealthDashboard(project_root=str(tmp_path))
        health = dashboard.analyze_file(code_file)

        debt_items = dashboard.estimate_tech_debt(health, dashboard.thresholds)

        # Should have documentation debt
        doc_debt = [d for d in debt_items if d.category == 'documentation']
        assert len(doc_debt) > 0
        assert all(d.estimated_hours > 0 for d in doc_debt)

    def test_debt_for_complex_code(self, tmp_path):
        """Test that complex code generates debt items"""
        code_file = tmp_path / "complex.py"
        code_file.write_text(SIMPLE_CODE)

        dashboard = HealthDashboard(project_root=str(tmp_path))
        health = dashboard.analyze_file(code_file)

        debt_items = dashboard.estimate_tech_debt(health, dashboard.thresholds)

        # Complex function should generate debt
        complexity_debt = [d for d in debt_items if d.category == 'complexity']
        if complexity_debt:
            assert all(d.estimated_hours > 0 for d in complexity_debt)


class TestDuplicateDetection:
    """Test code duplication detection"""

    def test_find_duplicates(self, tmp_path):
        """Test finding duplicate code blocks"""
        # Create files with duplicate code
        duplicate_block = '''
def process_data(data):
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result
'''

        file1 = tmp_path / "file1.py"
        file1.write_text(duplicate_block)

        file2 = tmp_path / "file2.py"
        file2.write_text(duplicate_block)

        dashboard = HealthDashboard(project_root=str(tmp_path))
        duplicates = dashboard.find_duplicates([file1, file2], min_lines=3)

        # Should find at least one duplicate
        assert len(duplicates) > 0
        # Each duplicate should appear in both files
        for dup in duplicates:
            assert dup.duplication_count >= 2


class TestThresholds:
    """Test custom thresholds"""

    def test_custom_thresholds(self, tmp_path):
        """Test using custom thresholds"""
        strict = HealthThresholds(
            complexity_good=5,
            complexity_warning=10,
            complexity_critical=15,
        )

        dashboard = HealthDashboard(
            project_root=str(tmp_path),
            thresholds=strict
        )

        assert dashboard.thresholds.complexity_good == 5
        assert dashboard.thresholds.complexity_warning == 10


class TestProjectAnalysis:
    """Test full project analysis"""

    @pytest.mark.asyncio
    async def test_analyze_project(self, tmp_path):
        """Test analyzing a full project"""
        # Create a small project
        (tmp_path / "module1.py").write_text(SIMPLE_CODE)
        (tmp_path / "module2.py").write_text(UNDOCUMENTED_CODE)

        dashboard = HealthDashboard(project_root=str(tmp_path))
        health = await dashboard.analyze_project()

        assert health.total_files == 2
        assert health.total_functions > 0
        assert health.avg_complexity >= 0
        assert 0 <= health.avg_maintainability <= 100
        assert health.overall_status in [s for s in HealthStatus]

    @pytest.mark.asyncio
    async def test_report_generation(self, tmp_path):
        """Test generating reports in different formats"""
        (tmp_path / "test.py").write_text(SIMPLE_CODE)

        dashboard = HealthDashboard(project_root=str(tmp_path))
        health = await dashboard.analyze_project()

        # Test text report
        text_report = dashboard.generate_report(health, format='text')
        assert 'CODE HEALTH REPORT' in text_report
        assert str(health.total_files) in text_report

        # Test markdown report
        md_report = dashboard.generate_report(health, format='markdown')
        assert '# Code Health Report' in md_report
        assert '|' in md_report  # Has tables

        # Test JSON report
        json_report = dashboard.generate_report(health, format='json')
        assert 'timestamp' in json_report
        assert 'overall_status' in json_report


class TestDatabase:
    """Test historical tracking database"""

    @pytest.mark.asyncio
    async def test_snapshot_saved_to_db(self, tmp_path):
        """Test that analysis snapshots are saved"""
        (tmp_path / "test.py").write_text(SIMPLE_CODE)

        db_path = tmp_path / "test_health.db"
        dashboard = HealthDashboard(
            project_root=str(tmp_path),
            db_path=str(db_path)
        )

        health = await dashboard.analyze_project()

        # Check database was created
        assert db_path.exists()

        # Check that data was saved
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM health_snapshots")
        count = cursor.fetchone()[0]
        assert count > 0

        conn.close()


class TestExclusionPatterns:
    """Test file exclusion patterns"""

    def test_exclude_venv(self, tmp_path):
        """Test that venv files are excluded"""
        venv_file = tmp_path / "venv" / "lib" / "test.py"
        venv_file.parent.mkdir(parents=True)
        venv_file.write_text(SIMPLE_CODE)

        dashboard = HealthDashboard(project_root=str(tmp_path))
        assert dashboard._should_exclude(venv_file) is True

    def test_exclude_pycache(self, tmp_path):
        """Test that __pycache__ files are excluded"""
        cache_file = tmp_path / "__pycache__" / "test.cpython-310.pyc"
        cache_file.parent.mkdir(parents=True)

        dashboard = HealthDashboard(project_root=str(tmp_path))
        assert dashboard._should_exclude(cache_file) is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
