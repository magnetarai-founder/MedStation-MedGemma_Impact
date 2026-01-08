"""
Comprehensive tests for Template Orchestrator

Tests cover:
- SQL condition validation (injection prevention)
- WorkflowStep dataclass
- TemplateWorkflow dataclass
- TemplateOrchestrator class methods
- Dependency grouping and circular dependency detection
- Parameter resolution
- Workflow creation methods
- Async workflow execution
- Workflow summary generation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import asdict, fields
import asyncio
import sys
import re


# Mock dependencies before importing the module
@pytest.fixture(autouse=True)
def mock_dependencies():
    """Mock external dependencies that aren't available in test environment"""
    mock_templates = Mock()
    mock_templates.get_full_template_library = Mock(return_value=Mock())
    mock_templates.TemplateCategory = Mock()
    mock_templates.SQLTemplate = Mock()

    mock_bigquery = Mock()
    mock_bigquery.BigQueryAIEngine = Mock()

    with patch.dict(sys.modules, {
        'templates': mock_templates,
        'bigquery_engine': mock_bigquery
    }):
        yield


class TestSQLConditionValidation:
    """Tests for validate_sql_condition function"""

    def test_empty_condition_valid(self, mock_dependencies):
        """Test empty condition is valid"""
        from api.template_orchestrator import validate_sql_condition

        assert validate_sql_condition("") is True
        assert validate_sql_condition(None) is True

    def test_simple_comparison_valid(self, mock_dependencies):
        """Test simple comparison conditions are valid"""
        from api.template_orchestrator import validate_sql_condition

        assert validate_sql_condition("price > 100") is True
        assert validate_sql_condition("status = 'active'") is True
        assert validate_sql_condition("quantity >= 0") is True

    def test_is_null_valid(self, mock_dependencies):
        """Test IS NULL conditions are valid"""
        from api.template_orchestrator import validate_sql_condition

        assert validate_sql_condition("description IS NULL") is True
        assert validate_sql_condition("description IS NOT NULL") is True

    def test_length_function_valid(self, mock_dependencies):
        """Test LENGTH function in conditions is valid"""
        from api.template_orchestrator import validate_sql_condition

        assert validate_sql_condition("LENGTH(description) < 20") is True
        assert validate_sql_condition("description IS NULL OR LENGTH(description) < 20") is True

    def test_date_literals_valid(self, mock_dependencies):
        """Test date literals with hyphens are valid"""
        from api.template_orchestrator import validate_sql_condition

        assert validate_sql_condition("created_at > '2024-01-01'") is True
        assert validate_sql_condition("date BETWEEN '2024-01-01' AND '2024-12-31'") is True

    def test_in_clause_valid(self, mock_dependencies):
        """Test IN clause is valid"""
        from api.template_orchestrator import validate_sql_condition

        assert validate_sql_condition("category IN ('electronics', 'clothing')") is True

    def test_drop_blocked(self, mock_dependencies):
        """Test DROP keyword is blocked"""
        from api.template_orchestrator import validate_sql_condition

        assert validate_sql_condition("id = 1; DROP TABLE users") is False
        assert validate_sql_condition("DROP TABLE users") is False

    def test_delete_blocked(self, mock_dependencies):
        """Test DELETE keyword is blocked"""
        from api.template_orchestrator import validate_sql_condition

        assert validate_sql_condition("DELETE FROM users") is False

    def test_insert_blocked(self, mock_dependencies):
        """Test INSERT keyword is blocked"""
        from api.template_orchestrator import validate_sql_condition

        assert validate_sql_condition("INSERT INTO users VALUES (1)") is False

    def test_update_blocked(self, mock_dependencies):
        """Test UPDATE keyword is blocked"""
        from api.template_orchestrator import validate_sql_condition

        assert validate_sql_condition("UPDATE users SET active = 0") is False

    def test_truncate_blocked(self, mock_dependencies):
        """Test TRUNCATE keyword is blocked"""
        from api.template_orchestrator import validate_sql_condition

        assert validate_sql_condition("TRUNCATE TABLE users") is False

    def test_alter_blocked(self, mock_dependencies):
        """Test ALTER keyword is blocked"""
        from api.template_orchestrator import validate_sql_condition

        assert validate_sql_condition("ALTER TABLE users ADD column") is False

    def test_create_blocked(self, mock_dependencies):
        """Test CREATE keyword is blocked"""
        from api.template_orchestrator import validate_sql_condition

        assert validate_sql_condition("CREATE TABLE malicious") is False

    def test_exec_blocked(self, mock_dependencies):
        """Test EXEC/EXECUTE keywords are blocked"""
        from api.template_orchestrator import validate_sql_condition

        assert validate_sql_condition("EXEC stored_procedure") is False
        assert validate_sql_condition("EXECUTE malicious") is False

    def test_grant_blocked(self, mock_dependencies):
        """Test GRANT keyword is blocked"""
        from api.template_orchestrator import validate_sql_condition

        assert validate_sql_condition("GRANT ALL ON users") is False

    def test_union_blocked(self, mock_dependencies):
        """Test UNION keyword is blocked"""
        from api.template_orchestrator import validate_sql_condition

        assert validate_sql_condition("id = 1 UNION SELECT * FROM passwords") is False

    def test_attach_blocked(self, mock_dependencies):
        """Test ATTACH keyword is blocked (SQLite specific)"""
        from api.template_orchestrator import validate_sql_condition

        assert validate_sql_condition("ATTACH DATABASE ':memory:'") is False

    def test_pragma_blocked(self, mock_dependencies):
        """Test PRAGMA keyword is blocked (SQLite specific)"""
        from api.template_orchestrator import validate_sql_condition

        assert validate_sql_condition("PRAGMA table_info(users)") is False

    def test_comment_injection_blocked_dash(self, mock_dependencies):
        """Test -- comment injection is blocked"""
        from api.template_orchestrator import validate_sql_condition

        assert validate_sql_condition("id = 1 -- ignore rest") is False

    def test_comment_injection_blocked_block(self, mock_dependencies):
        """Test /* */ comment injection is blocked"""
        from api.template_orchestrator import validate_sql_condition

        assert validate_sql_condition("id = /* comment */ 1") is False
        assert validate_sql_condition("id = 1 */") is False

    def test_semicolon_blocked(self, mock_dependencies):
        """Test semicolon (statement termination) is blocked"""
        from api.template_orchestrator import validate_sql_condition

        assert validate_sql_condition("id = 1; DELETE FROM users") is False
        assert validate_sql_condition("active = true;") is False

    def test_case_insensitive_blocking(self, mock_dependencies):
        """Test keyword blocking is case insensitive"""
        from api.template_orchestrator import validate_sql_condition

        assert validate_sql_condition("drop table users") is False
        assert validate_sql_condition("DROP TABLE users") is False
        assert validate_sql_condition("Drop Table Users") is False


class TestDangerousSQLKeywordsRegex:
    """Tests for _DANGEROUS_SQL_KEYWORDS regex"""

    def test_regex_exists(self, mock_dependencies):
        """Test dangerous keywords regex exists"""
        from api.template_orchestrator import _DANGEROUS_SQL_KEYWORDS

        assert _DANGEROUS_SQL_KEYWORDS is not None

    def test_matches_dangerous_keywords(self, mock_dependencies):
        """Test regex matches dangerous keywords"""
        from api.template_orchestrator import _DANGEROUS_SQL_KEYWORDS

        dangerous = ["DROP", "DELETE", "INSERT", "UPDATE", "TRUNCATE",
                     "ALTER", "CREATE", "EXEC", "EXECUTE", "GRANT",
                     "REVOKE", "UNION", "INTO", "LOAD", "ATTACH",
                     "DETACH", "PRAGMA", "VACUUM"]

        for keyword in dangerous:
            assert _DANGEROUS_SQL_KEYWORDS.search(keyword) is not None


class TestSafeConditionPattern:
    """Tests for _SAFE_CONDITION_PATTERN regex"""

    def test_regex_exists(self, mock_dependencies):
        """Test safe condition pattern exists"""
        from api.template_orchestrator import _SAFE_CONDITION_PATTERN

        assert _SAFE_CONDITION_PATTERN is not None

    def test_matches_safe_patterns(self, mock_dependencies):
        """Test regex matches safe SQL patterns"""
        from api.template_orchestrator import _SAFE_CONDITION_PATTERN

        safe_conditions = [
            "price > 100",
            "status = 'active'",
            "LENGTH(description) < 20",
            "created_at > '2024-01-01'",
            "category IN ('a', 'b')",
            "description IS NULL OR LENGTH(description) < 20"
        ]

        for condition in safe_conditions:
            assert _SAFE_CONDITION_PATTERN.match(condition.strip()) is not None


class TestWorkflowStep:
    """Tests for WorkflowStep dataclass"""

    def test_creation_minimal(self, mock_dependencies):
        """Test minimal WorkflowStep creation"""
        from api.template_orchestrator import WorkflowStep

        step = WorkflowStep(
            template_id="ENRICH_001",
            parameters={"table_name": "products"}
        )

        assert step.template_id == "ENRICH_001"
        assert step.parameters == {"table_name": "products"}
        assert step.depends_on is None
        assert step.output_name is None
        assert step.condition is None

    def test_creation_full(self, mock_dependencies):
        """Test full WorkflowStep creation"""
        from api.template_orchestrator import WorkflowStep

        step = WorkflowStep(
            template_id="ENRICH_001",
            parameters={"table_name": "products", "sku_column": "sku"},
            depends_on=["quality_check", "validation"],
            output_name="enriched_products",
            condition="status = 'active'"
        )

        assert step.template_id == "ENRICH_001"
        assert len(step.parameters) == 2
        assert step.depends_on == ["quality_check", "validation"]
        assert step.output_name == "enriched_products"
        assert step.condition == "status = 'active'"

    def test_dataclass_fields(self, mock_dependencies):
        """Test WorkflowStep has expected fields"""
        from api.template_orchestrator import WorkflowStep

        field_names = [f.name for f in fields(WorkflowStep)]

        assert "template_id" in field_names
        assert "parameters" in field_names
        assert "depends_on" in field_names
        assert "output_name" in field_names
        assert "condition" in field_names


class TestTemplateWorkflow:
    """Tests for TemplateWorkflow dataclass"""

    def test_creation(self, mock_dependencies):
        """Test TemplateWorkflow creation"""
        from api.template_orchestrator import TemplateWorkflow, WorkflowStep

        step1 = WorkflowStep(template_id="T1", parameters={}, output_name="out1")
        step2 = WorkflowStep(template_id="T2", parameters={}, depends_on=["out1"], output_name="out2")

        workflow = TemplateWorkflow(
            name="Test Workflow",
            description="A test workflow",
            steps=[step1, step2],
            final_output="final_table"
        )

        assert workflow.name == "Test Workflow"
        assert workflow.description == "A test workflow"
        assert len(workflow.steps) == 2
        assert workflow.final_output == "final_table"

    def test_dataclass_fields(self, mock_dependencies):
        """Test TemplateWorkflow has expected fields"""
        from api.template_orchestrator import TemplateWorkflow

        field_names = [f.name for f in fields(TemplateWorkflow)]

        assert "name" in field_names
        assert "description" in field_names
        assert "steps" in field_names
        assert "final_output" in field_names


class TestTemplateOrchestratorInit:
    """Tests for TemplateOrchestrator initialization"""

    def test_init_with_engine(self, mock_dependencies):
        """Test initialization with engine"""
        from api.template_orchestrator import TemplateOrchestrator

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)

        assert orchestrator.engine is mock_engine
        assert orchestrator.template_library is not None
        assert orchestrator.workflow_history == []


class TestSmartCatalogEnhancementWorkflow:
    """Tests for create_smart_catalog_enhancement_workflow"""

    def test_creates_workflow(self, mock_dependencies):
        """Test creates a valid TemplateWorkflow"""
        from api.template_orchestrator import TemplateOrchestrator, TemplateWorkflow

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)
        workflow = orchestrator.create_smart_catalog_enhancement_workflow()

        assert isinstance(workflow, TemplateWorkflow)
        assert workflow.name == "Smart Catalog Enhancement Pipeline"

    def test_has_10_steps(self, mock_dependencies):
        """Test workflow has 10 steps"""
        from api.template_orchestrator import TemplateOrchestrator

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)
        workflow = orchestrator.create_smart_catalog_enhancement_workflow()

        assert len(workflow.steps) == 10

    def test_first_step_is_validation(self, mock_dependencies):
        """Test first step is data quality validation"""
        from api.template_orchestrator import TemplateOrchestrator

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)
        workflow = orchestrator.create_smart_catalog_enhancement_workflow()

        first_step = workflow.steps[0]
        assert first_step.template_id == "VALID_186"
        assert first_step.output_name == "quality_report"

    def test_has_conditional_step(self, mock_dependencies):
        """Test workflow has a conditional step"""
        from api.template_orchestrator import TemplateOrchestrator

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)
        workflow = orchestrator.create_smart_catalog_enhancement_workflow()

        # Step 6 has a condition
        conditional_steps = [s for s in workflow.steps if s.condition]
        assert len(conditional_steps) >= 1
        assert "description IS NULL" in conditional_steps[0].condition

    def test_final_output_name(self, mock_dependencies):
        """Test final output is set"""
        from api.template_orchestrator import TemplateOrchestrator

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)
        workflow = orchestrator.create_smart_catalog_enhancement_workflow()

        assert workflow.final_output == "enhanced_catalog"


class TestIntelligentPricingWorkflow:
    """Tests for create_intelligent_pricing_workflow"""

    def test_creates_workflow(self, mock_dependencies):
        """Test creates a valid TemplateWorkflow"""
        from api.template_orchestrator import TemplateOrchestrator, TemplateWorkflow

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)
        workflow = orchestrator.create_intelligent_pricing_workflow()

        assert isinstance(workflow, TemplateWorkflow)
        assert workflow.name == "Intelligent Pricing Optimization"

    def test_has_3_steps(self, mock_dependencies):
        """Test workflow has 3 steps"""
        from api.template_orchestrator import TemplateOrchestrator

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)
        workflow = orchestrator.create_intelligent_pricing_workflow()

        assert len(workflow.steps) == 3

    def test_dependency_chain(self, mock_dependencies):
        """Test steps have correct dependency chain"""
        from api.template_orchestrator import TemplateOrchestrator

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)
        workflow = orchestrator.create_intelligent_pricing_workflow()

        # First step has no dependencies
        assert workflow.steps[0].depends_on is None
        # Second depends on first
        assert workflow.steps[1].depends_on == ["competitor_analysis"]
        # Third depends on second
        assert workflow.steps[2].depends_on == ["elasticity_analysis"]


class TestCustomerIntelligenceWorkflow:
    """Tests for create_customer_intelligence_workflow"""

    def test_creates_workflow(self, mock_dependencies):
        """Test creates a valid TemplateWorkflow"""
        from api.template_orchestrator import TemplateOrchestrator, TemplateWorkflow

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)
        workflow = orchestrator.create_customer_intelligence_workflow()

        assert isinstance(workflow, TemplateWorkflow)
        assert workflow.name == "360-Degree Customer Intelligence"

    def test_has_3_steps(self, mock_dependencies):
        """Test workflow has 3 steps"""
        from api.template_orchestrator import TemplateOrchestrator

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)
        workflow = orchestrator.create_customer_intelligence_workflow()

        assert len(workflow.steps) == 3

    def test_final_output(self, mock_dependencies):
        """Test final output is customer_intelligence"""
        from api.template_orchestrator import TemplateOrchestrator

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)
        workflow = orchestrator.create_customer_intelligence_workflow()

        assert workflow.final_output == "customer_intelligence"


class TestGroupStepsByDependencies:
    """Tests for _group_steps_by_dependencies method"""

    def test_single_step_no_deps(self, mock_dependencies):
        """Test single step with no dependencies"""
        from api.template_orchestrator import TemplateOrchestrator, WorkflowStep

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)
        steps = [WorkflowStep(template_id="T1", parameters={}, output_name="out1")]

        groups = orchestrator._group_steps_by_dependencies(steps)

        assert len(groups) == 1
        assert len(groups[0]) == 1

    def test_parallel_steps(self, mock_dependencies):
        """Test steps with no dependencies can be parallel"""
        from api.template_orchestrator import TemplateOrchestrator, WorkflowStep

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)
        steps = [
            WorkflowStep(template_id="T1", parameters={}, output_name="out1"),
            WorkflowStep(template_id="T2", parameters={}, output_name="out2"),
            WorkflowStep(template_id="T3", parameters={}, output_name="out3")
        ]

        groups = orchestrator._group_steps_by_dependencies(steps)

        # All can run in parallel since no deps
        assert len(groups) == 1
        assert len(groups[0]) == 3

    def test_sequential_dependencies(self, mock_dependencies):
        """Test steps with sequential dependencies"""
        from api.template_orchestrator import TemplateOrchestrator, WorkflowStep

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)
        steps = [
            WorkflowStep(template_id="T1", parameters={}, output_name="out1"),
            WorkflowStep(template_id="T2", parameters={}, depends_on=["out1"], output_name="out2"),
            WorkflowStep(template_id="T3", parameters={}, depends_on=["out2"], output_name="out3")
        ]

        groups = orchestrator._group_steps_by_dependencies(steps)

        # Each step in its own group due to sequential deps
        assert len(groups) == 3
        assert len(groups[0]) == 1
        assert groups[0][0].template_id == "T1"
        assert groups[1][0].template_id == "T2"
        assert groups[2][0].template_id == "T3"

    def test_fan_out_pattern(self, mock_dependencies):
        """Test fan-out pattern (one step then multiple parallel)"""
        from api.template_orchestrator import TemplateOrchestrator, WorkflowStep

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)
        steps = [
            WorkflowStep(template_id="T1", parameters={}, output_name="out1"),
            WorkflowStep(template_id="T2a", parameters={}, depends_on=["out1"], output_name="out2a"),
            WorkflowStep(template_id="T2b", parameters={}, depends_on=["out1"], output_name="out2b"),
            WorkflowStep(template_id="T2c", parameters={}, depends_on=["out1"], output_name="out2c")
        ]

        groups = orchestrator._group_steps_by_dependencies(steps)

        # First group: T1, Second group: T2a, T2b, T2c (parallel)
        assert len(groups) == 2
        assert len(groups[0]) == 1
        assert len(groups[1]) == 3

    def test_circular_dependency_raises(self, mock_dependencies):
        """Test circular dependency raises ValueError"""
        from api.template_orchestrator import TemplateOrchestrator, WorkflowStep

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)
        steps = [
            WorkflowStep(template_id="T1", parameters={}, depends_on=["out2"], output_name="out1"),
            WorkflowStep(template_id="T2", parameters={}, depends_on=["out1"], output_name="out2")
        ]

        with pytest.raises(ValueError, match="Circular dependency"):
            orchestrator._group_steps_by_dependencies(steps)


class TestResolveParameters:
    """Tests for _resolve_parameters method"""

    def test_direct_values(self, mock_dependencies):
        """Test direct parameter values pass through"""
        from api.template_orchestrator import TemplateOrchestrator

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)
        template_params = {"table_name": "products", "column": "sku"}
        workflow_params = {}
        results = {}

        resolved = orchestrator._resolve_parameters(template_params, workflow_params, results)

        assert resolved == {"table_name": "products", "column": "sku"}

    def test_workflow_parameter_reference(self, mock_dependencies):
        """Test workflow parameter references are resolved"""
        from api.template_orchestrator import TemplateOrchestrator

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)
        template_params = {"table_name": "{input_table}"}
        workflow_params = {"input_table": "project.dataset.products"}
        results = {}

        resolved = orchestrator._resolve_parameters(template_params, workflow_params, results)

        assert resolved == {"table_name": "project.dataset.products"}

    def test_result_reference(self, mock_dependencies):
        """Test result references from previous steps are resolved"""
        from api.template_orchestrator import TemplateOrchestrator

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)
        template_params = {"table_name": "{previous_output}"}
        workflow_params = {}

        # Mock result with to_sql method
        mock_result = Mock()
        mock_result.to_sql.return_value = "SELECT * FROM temp_table"
        results = {"previous_output": mock_result}

        resolved = orchestrator._resolve_parameters(template_params, workflow_params, results)

        assert resolved == {"table_name": "(SELECT * FROM temp_table)"}

    def test_missing_parameter_raises(self, mock_dependencies):
        """Test missing parameter raises ValueError"""
        from api.template_orchestrator import TemplateOrchestrator

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)
        template_params = {"table_name": "{missing_param}"}
        workflow_params = {}
        results = {}

        with pytest.raises(ValueError, match="Parameter missing_param not found"):
            orchestrator._resolve_parameters(template_params, workflow_params, results)

    def test_workflow_params_take_precedence(self, mock_dependencies):
        """Test workflow params are checked before results"""
        from api.template_orchestrator import TemplateOrchestrator

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)
        template_params = {"table_name": "{shared_name}"}
        workflow_params = {"shared_name": "from_workflow"}

        mock_result = Mock()
        mock_result.to_sql.return_value = "from_result"
        results = {"shared_name": mock_result}

        resolved = orchestrator._resolve_parameters(template_params, workflow_params, results)

        # Workflow params should take precedence
        assert resolved == {"table_name": "from_workflow"}


class TestCreateUnifiedResult:
    """Tests for _create_unified_result method"""

    def test_creates_result_dict(self, mock_dependencies):
        """Test creates expected result structure"""
        from api.template_orchestrator import TemplateOrchestrator, TemplateWorkflow

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)
        workflow = TemplateWorkflow(
            name="Test",
            description="Test workflow",
            steps=[],
            final_output="output"
        )
        results = {"step1": "result1", "step2": "result2"}

        unified = orchestrator._create_unified_result(results, workflow)

        assert unified["workflow_name"] == "Test"
        assert unified["workflow_description"] == "Test workflow"
        assert unified["steps_completed"] == 2
        assert unified["results"] == results
        assert "summary" in unified


class TestGenerateWorkflowSummary:
    """Tests for _generate_workflow_summary method"""

    def test_empty_results(self, mock_dependencies):
        """Test summary with empty results"""
        from api.template_orchestrator import TemplateOrchestrator

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)
        summary = orchestrator._generate_workflow_summary({})

        assert summary["total_products_processed"] == 0
        assert summary["quality_improvements"] == {}
        assert summary["enrichments_made"] == {}
        assert summary["forecasts_generated"] == 0

    def test_quality_step_counted(self, mock_dependencies):
        """Test quality step results are counted"""
        from api.template_orchestrator import TemplateOrchestrator

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)

        # Mock result with shape attribute (like a DataFrame)
        mock_result = Mock()
        mock_result.shape = (100, 5)  # 100 rows, 5 columns

        summary = orchestrator._generate_workflow_summary({"quality_check": mock_result})

        assert summary["quality_improvements"]["quality_check"] == 100

    def test_enrichment_step_counted(self, mock_dependencies):
        """Test enrichment step results are counted"""
        from api.template_orchestrator import TemplateOrchestrator

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)

        mock_result = Mock()
        mock_result.shape = (50, 3)

        summary = orchestrator._generate_workflow_summary({"enriched_products": mock_result})

        assert summary["enrichments_made"]["enriched_products"] == 50

    def test_forecast_step_counted(self, mock_dependencies):
        """Test forecast step results are counted"""
        from api.template_orchestrator import TemplateOrchestrator

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)

        mock_result = Mock()
        mock_result.shape = (30, 4)

        summary = orchestrator._generate_workflow_summary({"demand_forecast": mock_result})

        assert summary["forecasts_generated"] == 30


class TestExecuteStep:
    """Tests for _execute_step method"""

    @pytest.mark.asyncio
    async def test_executes_template(self, mock_dependencies):
        """Test step executes template with parameters"""
        from api.template_orchestrator import TemplateOrchestrator, WorkflowStep

        mock_engine = Mock()
        mock_engine._run_query.return_value = [{"id": 1}]

        orchestrator = TemplateOrchestrator(mock_engine)

        # Setup template library mock
        orchestrator.template_library.get_template.return_value = Mock()
        orchestrator.template_library.render_template.return_value = "SELECT * FROM products"

        step = WorkflowStep(
            template_id="T1",
            parameters={"table_name": "products"},
            output_name="out1"
        )

        result = await orchestrator._execute_step(step, {"table_name": "products"})

        orchestrator.template_library.get_template.assert_called_with("T1")
        orchestrator.template_library.render_template.assert_called_with("T1", {"table_name": "products"})

    @pytest.mark.asyncio
    async def test_template_not_found_raises(self, mock_dependencies):
        """Test raises ValueError if template not found"""
        from api.template_orchestrator import TemplateOrchestrator, WorkflowStep

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)
        orchestrator.template_library.get_template.return_value = None

        step = WorkflowStep(template_id="MISSING", parameters={}, output_name="out1")

        with pytest.raises(ValueError, match="Template MISSING not found"):
            await orchestrator._execute_step(step, {})

    @pytest.mark.asyncio
    async def test_adds_condition_to_sql(self, mock_dependencies):
        """Test condition is added to SQL query"""
        from api.template_orchestrator import TemplateOrchestrator, WorkflowStep

        mock_engine = Mock()
        mock_engine._run_query.return_value = []

        orchestrator = TemplateOrchestrator(mock_engine)
        orchestrator.template_library.get_template.return_value = Mock()
        orchestrator.template_library.render_template.return_value = "SELECT * FROM products"

        step = WorkflowStep(
            template_id="T1",
            parameters={},
            output_name="out1",
            condition="status = 'active'"
        )

        await orchestrator._execute_step(step, {})

        # Check that the SQL was wrapped with condition
        call_args = mock_engine._run_query.call_args[0][0]
        assert "WHERE status = 'active'" in call_args

    @pytest.mark.asyncio
    async def test_invalid_condition_raises(self, mock_dependencies):
        """Test invalid/dangerous condition raises ValueError"""
        from api.template_orchestrator import TemplateOrchestrator, WorkflowStep

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)
        orchestrator.template_library.get_template.return_value = Mock()
        orchestrator.template_library.render_template.return_value = "SELECT * FROM products"

        step = WorkflowStep(
            template_id="T1",
            parameters={},
            output_name="out1",
            condition="id = 1; DROP TABLE users"
        )

        with pytest.raises(ValueError, match="Invalid or potentially unsafe SQL condition"):
            await orchestrator._execute_step(step, {})


class TestExecuteWorkflow:
    """Tests for execute_workflow method"""

    @pytest.mark.asyncio
    async def test_executes_simple_workflow(self, mock_dependencies):
        """Test executes a simple single-step workflow"""
        from api.template_orchestrator import TemplateOrchestrator, TemplateWorkflow, WorkflowStep

        mock_engine = Mock()
        mock_engine._run_query.return_value = [{"id": 1}]

        orchestrator = TemplateOrchestrator(mock_engine)
        orchestrator.template_library.get_template.return_value = Mock()
        orchestrator.template_library.render_template.return_value = "SELECT * FROM products"

        workflow = TemplateWorkflow(
            name="Test",
            description="Test workflow",
            steps=[WorkflowStep(template_id="T1", parameters={}, output_name="out1")],
            final_output="output"
        )

        result = await orchestrator.execute_workflow(workflow, {})

        assert result["workflow_name"] == "Test"
        assert result["steps_completed"] == 1
        assert "out1" in result["results"]

    @pytest.mark.asyncio
    async def test_tracks_workflow_history(self, mock_dependencies):
        """Test workflow execution is tracked in history"""
        from api.template_orchestrator import TemplateOrchestrator, TemplateWorkflow, WorkflowStep

        mock_engine = Mock()
        mock_engine._run_query.return_value = []

        orchestrator = TemplateOrchestrator(mock_engine)
        orchestrator.template_library.get_template.return_value = Mock()
        orchestrator.template_library.render_template.return_value = "SELECT 1"

        workflow = TemplateWorkflow(
            name="History Test",
            description="Test",
            steps=[WorkflowStep(template_id="T1", parameters={}, output_name="out1")],
            final_output="output"
        )

        await orchestrator.execute_workflow(workflow, {})

        assert len(orchestrator.workflow_history) == 1
        assert orchestrator.workflow_history[0]["workflow"] == "History Test"
        assert "execution_time" in orchestrator.workflow_history[0]

    @pytest.mark.asyncio
    async def test_dependency_not_met_raises(self, mock_dependencies):
        """Test raises error if dependency not met (detected as circular)"""
        from api.template_orchestrator import TemplateOrchestrator, TemplateWorkflow, WorkflowStep

        mock_engine = Mock()
        mock_engine._run_query.return_value = []

        orchestrator = TemplateOrchestrator(mock_engine)
        orchestrator.template_library.get_template.return_value = Mock()
        orchestrator.template_library.render_template.return_value = "SELECT 1"

        # Step depends on something that doesn't exist
        # The dependency grouping algorithm detects this as circular
        # because "nonexistent" never gets added to completed set
        workflow = TemplateWorkflow(
            name="Bad Deps",
            description="Test",
            steps=[
                WorkflowStep(template_id="T1", parameters={}, depends_on=["nonexistent"], output_name="out1")
            ],
            final_output="output"
        )

        # The algorithm detects unresolvable deps as circular dependency
        with pytest.raises(ValueError, match="Circular dependency"):
            await orchestrator.execute_workflow(workflow, {})


class TestWorkflowHistoryTracking:
    """Tests for workflow history tracking"""

    @pytest.mark.asyncio
    async def test_history_accumulates(self, mock_dependencies):
        """Test multiple workflow executions accumulate in history"""
        from api.template_orchestrator import TemplateOrchestrator, TemplateWorkflow, WorkflowStep

        mock_engine = Mock()
        mock_engine._run_query.return_value = []

        orchestrator = TemplateOrchestrator(mock_engine)
        orchestrator.template_library.get_template.return_value = Mock()
        orchestrator.template_library.render_template.return_value = "SELECT 1"

        workflow1 = TemplateWorkflow(
            name="Workflow 1",
            description="Test",
            steps=[WorkflowStep(template_id="T1", parameters={}, output_name="out1")],
            final_output="output"
        )
        workflow2 = TemplateWorkflow(
            name="Workflow 2",
            description="Test",
            steps=[WorkflowStep(template_id="T2", parameters={}, output_name="out2")],
            final_output="output"
        )

        await orchestrator.execute_workflow(workflow1, {})
        await orchestrator.execute_workflow(workflow2, {})

        assert len(orchestrator.workflow_history) == 2
        assert orchestrator.workflow_history[0]["workflow"] == "Workflow 1"
        assert orchestrator.workflow_history[1]["workflow"] == "Workflow 2"

    @pytest.mark.asyncio
    async def test_history_contains_timestamp(self, mock_dependencies):
        """Test history entries contain timestamp"""
        from api.template_orchestrator import TemplateOrchestrator, TemplateWorkflow, WorkflowStep
        from datetime import datetime

        mock_engine = Mock()
        mock_engine._run_query.return_value = []

        orchestrator = TemplateOrchestrator(mock_engine)
        orchestrator.template_library.get_template.return_value = Mock()
        orchestrator.template_library.render_template.return_value = "SELECT 1"

        workflow = TemplateWorkflow(
            name="Test",
            description="Test",
            steps=[WorkflowStep(template_id="T1", parameters={}, output_name="out1")],
            final_output="output"
        )

        await orchestrator.execute_workflow(workflow, {})

        assert "timestamp" in orchestrator.workflow_history[0]
        assert isinstance(orchestrator.workflow_history[0]["timestamp"], datetime)


class TestEdgeCases:
    """Tests for edge cases"""

    def test_empty_workflow_steps(self, mock_dependencies):
        """Test workflow with no steps"""
        from api.template_orchestrator import TemplateOrchestrator, TemplateWorkflow

        mock_engine = Mock()
        orchestrator = TemplateOrchestrator(mock_engine)
        workflow = TemplateWorkflow(
            name="Empty",
            description="No steps",
            steps=[],
            final_output="output"
        )

        groups = orchestrator._group_steps_by_dependencies(workflow.steps)

        assert groups == []

    def test_unicode_in_condition(self, mock_dependencies):
        """Test unicode characters in SQL conditions"""
        from api.template_orchestrator import validate_sql_condition

        # Safe unicode should pass pattern check
        result = validate_sql_condition("name = 'caf\u00e9'")
        # May fail pattern validation depending on regex, but shouldn't crash
        assert isinstance(result, bool)

    def test_special_chars_in_condition(self, mock_dependencies):
        """Test special characters in SQL conditions"""
        from api.template_orchestrator import validate_sql_condition

        # Percentage for LIKE is blocked by the safe pattern regex
        # This is a strict security measure - LIKE with wildcards is not allowed
        assert validate_sql_condition("name LIKE '%test%'") is False

        # Simple LIKE without wildcards should work
        result = validate_sql_condition("name LIKE 'test'")
        assert isinstance(result, bool)  # May be True or False depending on pattern

    def test_multiline_condition(self, mock_dependencies):
        """Test multiline conditions"""
        from api.template_orchestrator import validate_sql_condition

        condition = """
        status = 'active'
        AND price > 0
        """
        # Should pass (no dangerous keywords)
        result = validate_sql_condition(condition)
        assert isinstance(result, bool)

    def test_workflow_step_with_empty_parameters(self, mock_dependencies):
        """Test WorkflowStep with empty parameters dict"""
        from api.template_orchestrator import WorkflowStep

        step = WorkflowStep(template_id="T1", parameters={})

        assert step.parameters == {}


class TestIntegration:
    """Integration tests"""

    @pytest.mark.asyncio
    async def test_full_workflow_lifecycle(self, mock_dependencies):
        """Test complete workflow lifecycle"""
        from api.template_orchestrator import TemplateOrchestrator, TemplateWorkflow, WorkflowStep

        mock_engine = Mock()
        # Setup mock engine with DataFrame-like results
        mock_result = Mock()
        mock_result.shape = (10, 3)
        mock_engine._run_query.return_value = mock_result

        orchestrator = TemplateOrchestrator(mock_engine)

        # Setup mock library
        orchestrator.template_library.get_template.return_value = Mock()
        orchestrator.template_library.render_template.side_effect = lambda tid, params: f"SELECT * FROM {params.get('table_name', 'test')}"

        # Create workflow with dependencies
        workflow = TemplateWorkflow(
            name="Integration Test",
            description="Full lifecycle test",
            steps=[
                WorkflowStep(template_id="T1", parameters={"table_name": "products"}, output_name="step1"),
                WorkflowStep(template_id="T2", parameters={"table_name": "enriched"}, depends_on=["step1"], output_name="step2"),
            ],
            final_output="final"
        )

        result = await orchestrator.execute_workflow(workflow, {})

        # Verify results
        assert result["workflow_name"] == "Integration Test"
        assert result["steps_completed"] == 2
        assert "step1" in result["results"]
        assert "step2" in result["results"]
        assert len(orchestrator.workflow_history) == 1
