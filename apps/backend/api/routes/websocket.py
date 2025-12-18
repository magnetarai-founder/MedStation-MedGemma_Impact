"""
WebSocket API endpoints.

Real-time WebSocket connections for query progress and streaming updates.
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.main import sessions

router = APIRouter(tags=["WebSocket"])
logger = logging.getLogger(__name__)


@router.websocket("/api/sessions/{session_id}/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket for real-time query progress and logs"""
    if session_id not in sessions:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()

    try:
        while True:
            # Receive query request
            data = await websocket.receive_json()

            if data.get("type") == "query":
                # Execute query and stream progress
                await websocket.send_json({
                    "type": "progress",
                    "message": "Starting query execution..."
                })

                # Security: Validate table access (same as REST endpoint)
                sql_query = data.get("sql", "")
                from neutron_utils.sql_utils import SQLProcessor as SQLUtil
                referenced_tables = SQLUtil.extract_table_names(sql_query)
                allowed_tables = {'excel_file'}

                unauthorized_tables = set(referenced_tables) - allowed_tables
                if unauthorized_tables:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Query references unauthorized tables: {', '.join(unauthorized_tables)}"
                    })
                    continue

                # TODO: Implement actual progress streaming
                # For now, just execute and return result
                engine = sessions[session_id]['engine']
                result = engine.execute_sql(sql_query)

                if result.error:
                    await websocket.send_json({
                        "type": "error",
                        "message": result.error
                    })
                else:
                    await websocket.send_json({
                        "type": "complete",
                        "row_count": result.row_count,
                        "execution_time_ms": result.execution_time_ms
                    })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
