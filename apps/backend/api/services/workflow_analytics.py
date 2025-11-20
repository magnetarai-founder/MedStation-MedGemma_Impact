"""
Workflow Analytics Service (Phase D)
Provides enhanced metrics and analytics for workflows
"""

import logging
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class WorkflowAnalytics:
    """
    Analytics service for workflow performance metrics.

    Provides per-stage and overall workflow analytics:
    - Items entered/completed per stage
    - Average time spent in each stage
    - Overall cycle time
    - SLA compliance metrics
    """

    def __init__(self, db_path: str | Path):
        """
        Initialize analytics service.

        Args:
            db_path: Path to workflows.db
        """
        self.db_path = Path(db_path)

    def get_workflow_analytics(
        self,
        workflow_id: str,
        user_id: str,
        team_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compute comprehensive analytics for a workflow.

        Args:
            workflow_id: Workflow ID
            user_id: User ID for isolation
            team_id: Optional team ID

        Returns:
            Dictionary with analytics:
            {
                "workflow_id": str,
                "workflow_name": str,
                "total_items": int,
                "completed_items": int,
                "in_progress_items": int,
                "cancelled_items": int,
                "failed_items": int,
                "average_cycle_time_seconds": float | None,
                "median_cycle_time_seconds": float | None,
                "stages": [
                    {
                        "stage_id": str,
                        "stage_name": str,
                        "entered_count": int,
                        "completed_count": int,
                        "avg_time_seconds": float | None,
                        "median_time_seconds": float | None,
                    },
                    ...
                ]
            }
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Get workflow name
            cursor.execute(
                "SELECT name FROM workflows WHERE id = ? AND user_id = ?",
                (workflow_id, user_id),
            )
            workflow_row = cursor.fetchone()
            workflow_name = workflow_row["name"] if workflow_row else "Unknown"

            # Overall metrics
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total_items,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_items,
                    SUM(CASE WHEN status IN ('pending', 'claimed', 'in_progress', 'waiting') THEN 1 ELSE 0 END) as in_progress_items,
                    SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled_items,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_items
                FROM work_items
                WHERE workflow_id = ? AND user_id = ?
                """,
                (workflow_id, user_id),
            )
            overall_row = cursor.fetchone()

            total_items = overall_row["total_items"] or 0
            completed_items = overall_row["completed_items"] or 0
            in_progress_items = overall_row["in_progress_items"] or 0
            cancelled_items = overall_row["cancelled_items"] or 0
            failed_items = overall_row["failed_items"] or 0

            # Cycle time (created_at to completed_at for completed items)
            cursor.execute(
                """
                SELECT
                    (julianday(completed_at) - julianday(created_at)) * 86400 as cycle_time_seconds
                FROM work_items
                WHERE workflow_id = ? AND user_id = ? AND status = 'completed' AND completed_at IS NOT NULL
                ORDER BY cycle_time_seconds
                """,
                (workflow_id, user_id),
            )
            cycle_times = [row["cycle_time_seconds"] for row in cursor.fetchall()]

            avg_cycle_time = sum(cycle_times) / len(cycle_times) if cycle_times else None
            median_cycle_time = (
                cycle_times[len(cycle_times) // 2]
                if cycle_times
                else None
            )

            # Per-stage metrics
            stage_metrics = self._compute_stage_metrics(
                cursor, workflow_id, user_id
            )

            conn.close()

            return {
                "workflow_id": workflow_id,
                "workflow_name": workflow_name,
                "total_items": total_items,
                "completed_items": completed_items,
                "in_progress_items": in_progress_items,
                "cancelled_items": cancelled_items,
                "failed_items": failed_items,
                "average_cycle_time_seconds": avg_cycle_time,
                "median_cycle_time_seconds": median_cycle_time,
                "stages": stage_metrics,
            }

        except Exception as e:
            logger.error(f"Error computing workflow analytics: {e}", exc_info=True)
            conn.close()
            return {
                "workflow_id": workflow_id,
                "workflow_name": "Unknown",
                "total_items": 0,
                "completed_items": 0,
                "in_progress_items": 0,
                "cancelled_items": 0,
                "failed_items": 0,
                "average_cycle_time_seconds": None,
                "median_cycle_time_seconds": None,
                "stages": [],
            }

    def _compute_stage_metrics(
        self,
        cursor: sqlite3.Cursor,
        workflow_id: str,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Compute per-stage metrics.

        Args:
            cursor: Database cursor
            workflow_id: Workflow ID
            user_id: User ID

        Returns:
            List of stage metric dictionaries
        """
        # Get all transitions for this workflow
        cursor.execute(
            """
            SELECT
                st.to_stage_id,
                st.duration_seconds,
                st.from_stage_id
            FROM stage_transitions st
            JOIN work_items wi ON st.work_item_id = wi.id
            WHERE wi.workflow_id = ? AND wi.user_id = ?
            ORDER BY st.transitioned_at
            """,
            (workflow_id, user_id),
        )
        transitions = cursor.fetchall()

        # Aggregate by stage
        stage_data = {}  # stage_id -> {"entered": count, "durations": [seconds, ...]}

        for trans in transitions:
            to_stage_id = trans["to_stage_id"]
            from_stage_id = trans["from_stage_id"]
            duration = trans["duration_seconds"]

            # Count entries
            if to_stage_id:
                if to_stage_id not in stage_data:
                    stage_data[to_stage_id] = {"entered": 0, "durations": []}
                stage_data[to_stage_id]["entered"] += 1

            # Record duration for the FROM stage (time spent in that stage)
            if from_stage_id and duration is not None:
                if from_stage_id not in stage_data:
                    stage_data[from_stage_id] = {"entered": 0, "durations": []}
                stage_data[from_stage_id]["durations"].append(duration)

        # Build metrics list
        stage_metrics = []
        for stage_id, data in stage_data.items():
            durations = data["durations"]
            avg_time = sum(durations) / len(durations) if durations else None
            median_time = (
                sorted(durations)[len(durations) // 2]
                if durations
                else None
            )

            # Try to get stage name (may not be available if stage was deleted)
            stage_name = stage_id  # Fallback to ID

            stage_metrics.append({
                "stage_id": stage_id,
                "stage_name": stage_name,
                "entered_count": data["entered"],
                "completed_count": len(durations),  # Items that exited this stage
                "avg_time_seconds": avg_time,
                "median_time_seconds": median_time,
            })

        return stage_metrics

    def get_stage_analytics(
        self,
        workflow_id: str,
        stage_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Get detailed analytics for a specific stage.

        Args:
            workflow_id: Workflow ID
            stage_id: Stage ID
            user_id: User ID

        Returns:
            Stage analytics dictionary
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Count items currently in this stage
            cursor.execute(
                """
                SELECT COUNT(*) as current_count
                FROM work_items
                WHERE workflow_id = ? AND current_stage_id = ? AND user_id = ?
                AND status IN ('pending', 'claimed', 'in_progress', 'waiting')
                """,
                (workflow_id, stage_id, user_id),
            )
            current_count = cursor.fetchone()["current_count"] or 0

            # Get all transitions TO this stage
            cursor.execute(
                """
                SELECT COUNT(*) as entered_count
                FROM stage_transitions st
                JOIN work_items wi ON st.work_item_id = wi.id
                WHERE wi.workflow_id = ? AND st.to_stage_id = ? AND wi.user_id = ?
                """,
                (workflow_id, stage_id, user_id),
            )
            entered_count = cursor.fetchone()["entered_count"] or 0

            # Get durations FROM this stage
            cursor.execute(
                """
                SELECT duration_seconds
                FROM stage_transitions st
                JOIN work_items wi ON st.work_item_id = wi.id
                WHERE wi.workflow_id = ? AND st.from_stage_id = ? AND wi.user_id = ?
                AND st.duration_seconds IS NOT NULL
                ORDER BY duration_seconds
                """,
                (workflow_id, stage_id, user_id),
            )
            durations = [row["duration_seconds"] for row in cursor.fetchall()]

            avg_time = sum(durations) / len(durations) if durations else None
            median_time = durations[len(durations) // 2] if durations else None

            conn.close()

            return {
                "stage_id": stage_id,
                "workflow_id": workflow_id,
                "items_currently_in_stage": current_count,
                "items_entered": entered_count,
                "items_completed": len(durations),
                "avg_time_seconds": avg_time,
                "median_time_seconds": median_time,
            }

        except Exception as e:
            logger.error(f"Error computing stage analytics: {e}", exc_info=True)
            conn.close()
            return {
                "stage_id": stage_id,
                "workflow_id": workflow_id,
                "items_currently_in_stage": 0,
                "items_entered": 0,
                "items_completed": 0,
                "avg_time_seconds": None,
                "median_time_seconds": None,
            }
