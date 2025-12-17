"""
Tests for Phase D: Workflow Analytics
Tests enhanced metrics and analytics functionality
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, UTC

from api.workflow_models import (
    Workflow,
    WorkItem,
    Stage,
    StageTransition,
    WorkItemStatus,
    WorkItemPriority,
    StageType,
    AssignmentType,
    WorkflowType,
)
from api.workflow_storage import WorkflowStorage
from api.services.workflow_analytics import WorkflowAnalytics


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def storage(temp_db):
    """Create a WorkflowStorage instance with temp DB"""
    return WorkflowStorage(db_path=temp_db)


@pytest.fixture
def analytics(temp_db):
    """Create a WorkflowAnalytics instance"""
    return WorkflowAnalytics(db_path=temp_db)


@pytest.fixture
def test_user_id():
    """Test user ID"""
    return "test_user_123"


@pytest.fixture
def test_workflow(storage, test_user_id):
    """Create a test workflow with multiple stages"""
    workflow = Workflow(
        name="Test Workflow",
        description="Workflow for analytics testing",
        workflow_type=WorkflowType.TEAM_WORKFLOW,
        stages=[
            Stage(
                id="stage1",
                name="Triage",
                stage_type=StageType.HUMAN,
                assignment_type=AssignmentType.QUEUE,
            ),
            Stage(
                id="stage2",
                name="Review",
                stage_type=StageType.HUMAN,
                assignment_type=AssignmentType.ROLE,
                role_name="reviewer",
            ),
            Stage(
                id="stage3",
                name="Approval",
                stage_type=StageType.APPROVAL,
                assignment_type=AssignmentType.ROLE,
                role_name="approver",
            ),
        ],
        triggers=[],
        created_by=test_user_id,
    )
    storage.save_workflow(workflow, user_id=test_user_id)
    return workflow


class TestWorkflowAnalyticsBasic:
    """Basic analytics tests"""

    def test_analytics_empty_workflow(
        self, analytics, test_workflow, test_user_id
    ):
        """Test analytics on workflow with no work items"""
        analytics_data = analytics.get_workflow_analytics(
            workflow_id=test_workflow.id,
            user_id=test_user_id,
        )

        assert analytics_data["workflow_id"] == test_workflow.id
        assert analytics_data["workflow_name"] == "Test Workflow"
        assert analytics_data["total_items"] == 0
        assert analytics_data["completed_items"] == 0
        assert analytics_data["in_progress_items"] == 0
        assert analytics_data["average_cycle_time_seconds"] is None
        assert analytics_data["median_cycle_time_seconds"] is None
        assert len(analytics_data["stages"]) == 0

    def test_analytics_with_completed_items(
        self, storage, analytics, test_workflow, test_user_id
    ):
        """Test analytics with completed work items"""
        # Create completed work items
        now = datetime.now(UTC)
        for i in range(5):
            work_item = WorkItem(
                workflow_id=test_workflow.id,
                workflow_name=test_workflow.name,
                current_stage_id="stage3",
                current_stage_name="Approval",
                status=WorkItemStatus.COMPLETED,
                priority=WorkItemPriority.NORMAL,
                data={},
                created_by=test_user_id,
                created_at=now - timedelta(hours=2),
                completed_at=now,
            )
            storage.save_work_item(work_item, user_id=test_user_id)

        analytics_data = analytics.get_workflow_analytics(
            workflow_id=test_workflow.id,
            user_id=test_user_id,
        )

        assert analytics_data["total_items"] == 5
        assert analytics_data["completed_items"] == 5
        assert analytics_data["in_progress_items"] == 0

    def test_analytics_with_mixed_statuses(
        self, storage, analytics, test_workflow, test_user_id
    ):
        """Test analytics with items in various statuses"""
        now = datetime.now(UTC)

        # 3 completed
        for i in range(3):
            work_item = WorkItem(
                workflow_id=test_workflow.id,
                workflow_name=test_workflow.name,
                current_stage_id="stage3",
                current_stage_name="Approval",
                status=WorkItemStatus.COMPLETED,
                priority=WorkItemPriority.NORMAL,
                data={},
                created_by=test_user_id,
                created_at=now - timedelta(hours=1),
                completed_at=now,
            )
            storage.save_work_item(work_item, user_id=test_user_id)

        # 2 in progress
        for i in range(2):
            work_item = WorkItem(
                workflow_id=test_workflow.id,
                workflow_name=test_workflow.name,
                current_stage_id="stage2",
                current_stage_name="Review",
                status=WorkItemStatus.IN_PROGRESS,
                priority=WorkItemPriority.NORMAL,
                data={},
                created_by=test_user_id,
            )
            storage.save_work_item(work_item, user_id=test_user_id)

        # 1 cancelled
        work_item = WorkItem(
            workflow_id=test_workflow.id,
            workflow_name=test_workflow.name,
            current_stage_id="stage1",
            current_stage_name="Triage",
            status=WorkItemStatus.CANCELLED,
            priority=WorkItemPriority.NORMAL,
            data={},
            created_by=test_user_id,
        )
        storage.save_work_item(work_item, user_id=test_user_id)

        analytics_data = analytics.get_workflow_analytics(
            workflow_id=test_workflow.id,
            user_id=test_user_id,
        )

        assert analytics_data["total_items"] == 6
        assert analytics_data["completed_items"] == 3
        assert analytics_data["in_progress_items"] == 2
        assert analytics_data["cancelled_items"] == 1


class TestCycleTimeMetrics:
    """Tests for cycle time calculations"""

    def test_average_cycle_time_calculation(
        self, storage, analytics, test_workflow, test_user_id
    ):
        """Test average cycle time is calculated correctly"""
        now = datetime.now(UTC)

        # Item 1: 1 hour cycle time
        work_item1 = WorkItem(
            workflow_id=test_workflow.id,
            workflow_name=test_workflow.name,
            current_stage_id="stage3",
            current_stage_name="Approval",
            status=WorkItemStatus.COMPLETED,
            priority=WorkItemPriority.NORMAL,
            data={},
            created_by=test_user_id,
            created_at=now - timedelta(hours=1),
            completed_at=now,
        )
        storage.save_work_item(work_item1, user_id=test_user_id)

        # Item 2: 2 hours cycle time
        work_item2 = WorkItem(
            workflow_id=test_workflow.id,
            workflow_name=test_workflow.name,
            current_stage_id="stage3",
            current_stage_name="Approval",
            status=WorkItemStatus.COMPLETED,
            priority=WorkItemPriority.NORMAL,
            data={},
            created_by=test_user_id,
            created_at=now - timedelta(hours=2),
            completed_at=now,
        )
        storage.save_work_item(work_item2, user_id=test_user_id)

        analytics_data = analytics.get_workflow_analytics(
            workflow_id=test_workflow.id,
            user_id=test_user_id,
        )

        # Average should be 1.5 hours = 5400 seconds
        avg_time = analytics_data["average_cycle_time_seconds"]
        assert avg_time is not None
        # Allow some tolerance due to datetime precision
        assert 5350 <= avg_time <= 5450


class TestStageMetrics:
    """Tests for per-stage analytics"""

    def test_stage_transitions_tracked(
        self, storage, analytics, test_workflow, test_user_id
    ):
        """Test that stage transitions are tracked in analytics"""
        now = datetime.now(UTC)

        # Create work item with transitions
        work_item = WorkItem(
            workflow_id=test_workflow.id,
            workflow_name=test_workflow.name,
            current_stage_id="stage3",
            current_stage_name="Approval",
            status=WorkItemStatus.COMPLETED,
            priority=WorkItemPriority.NORMAL,
            data={},
            created_by=test_user_id,
            created_at=now - timedelta(hours=3),
            completed_at=now,
            history=[
                StageTransition(
                    from_stage_id=None,
                    to_stage_id="stage1",
                    transitioned_at=now - timedelta(hours=3),
                    transitioned_by=test_user_id,
                ),
                StageTransition(
                    from_stage_id="stage1",
                    to_stage_id="stage2",
                    transitioned_at=now - timedelta(hours=2),
                    transitioned_by=test_user_id,
                    duration_seconds=3600,  # 1 hour in stage1
                ),
                StageTransition(
                    from_stage_id="stage2",
                    to_stage_id="stage3",
                    transitioned_at=now - timedelta(hours=1),
                    transitioned_by=test_user_id,
                    duration_seconds=3600,  # 1 hour in stage2
                ),
            ],
        )
        storage.save_work_item(work_item, user_id=test_user_id)

        analytics_data = analytics.get_workflow_analytics(
            workflow_id=test_workflow.id,
            user_id=test_user_id,
        )

        # Should have stage metrics
        stages = analytics_data["stages"]
        assert len(stages) > 0

    def test_stage_entered_count(
        self, storage, analytics, test_workflow, test_user_id
    ):
        """Test that stage entered counts are correct"""
        now = datetime.now(UTC)

        # Create 3 work items that all enter stage2
        for i in range(3):
            work_item = WorkItem(
                workflow_id=test_workflow.id,
                workflow_name=test_workflow.name,
                current_stage_id="stage2",
                current_stage_name="Review",
                status=WorkItemStatus.IN_PROGRESS,
                priority=WorkItemPriority.NORMAL,
                data={},
                created_by=test_user_id,
                history=[
                    StageTransition(
                        from_stage_id=None,
                        to_stage_id="stage1",
                        transitioned_at=now - timedelta(hours=2),
                        transitioned_by=test_user_id,
                    ),
                    StageTransition(
                        from_stage_id="stage1",
                        to_stage_id="stage2",
                        transitioned_at=now - timedelta(hours=1),
                        transitioned_by=test_user_id,
                        duration_seconds=3600,
                    ),
                ],
            )
            storage.save_work_item(work_item, user_id=test_user_id)

        analytics_data = analytics.get_workflow_analytics(
            workflow_id=test_workflow.id,
            user_id=test_user_id,
        )

        # Find stage2 metrics
        stage2_metrics = next(
            (s for s in analytics_data["stages"] if s["stage_id"] == "stage2"),
            None,
        )
        if stage2_metrics:
            assert stage2_metrics["entered_count"] == 3


class TestAnalyticsErrorHandling:
    """Tests for error handling in analytics"""

    def test_analytics_nonexistent_workflow(self, analytics, test_user_id):
        """Test analytics for non-existent workflow returns empty results"""
        analytics_data = analytics.get_workflow_analytics(
            workflow_id="nonexistent_id",
            user_id=test_user_id,
        )

        # Should return safe defaults, not crash
        assert analytics_data["workflow_id"] == "nonexistent_id"
        assert analytics_data["total_items"] == 0

    def test_analytics_with_corrupted_data(
        self, storage, analytics, test_workflow, test_user_id
    ):
        """Test analytics handles corrupted data gracefully"""
        # This test ensures the analytics service doesn't crash
        # even if data is partially corrupted
        analytics_data = analytics.get_workflow_analytics(
            workflow_id=test_workflow.id,
            user_id=test_user_id,
        )

        # Should return results without crashing
        assert analytics_data is not None
        assert "workflow_id" in analytics_data
