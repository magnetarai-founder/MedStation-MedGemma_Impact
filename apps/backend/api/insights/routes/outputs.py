"""
Insights Lab Output Routes

Template application and formatted output endpoints.
"""

import json
import logging
from datetime import datetime, UTC
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, Depends, Body

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user
from api.schemas.insights_models import (
    FormattedOutput, ApplyTemplateRequest, ApplyTemplateResponse,
    BatchApplyRequest, BatchApplyResponse, OutputFormat
)

from ..database import get_db
from ..template_engine import apply_template_with_ollama

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Outputs"])


@router.post("/recordings/{recording_id}/apply-template", response_model=ApplyTemplateResponse)
async def apply_template(
    recording_id: str,
    request: ApplyTemplateRequest = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Apply a template to a recording"""
    conn = get_db()
    cursor = conn.cursor()

    # Get recording
    cursor.execute("SELECT transcript FROM recordings WHERE id = ?", (recording_id,))
    rec_row = cursor.fetchone()
    if not rec_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Recording not found")
    transcript = rec_row["transcript"]

    # Get template
    cursor.execute("SELECT * FROM templates WHERE id = ?", (request.template_id,))
    tmpl_row = cursor.fetchone()
    if not tmpl_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Template not found")

    # Apply template
    content = await apply_template_with_ollama(transcript, tmpl_row["system_prompt"])

    # Save output
    output_id = f"out_{uuid4().hex[:12]}"
    now = datetime.now(UTC).isoformat()

    cursor.execute("""
        INSERT INTO formatted_outputs
        (id, recording_id, template_id, template_name, content, format, generated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        output_id, recording_id, request.template_id,
        tmpl_row["name"], content, tmpl_row["output_format"], now
    ))

    conn.commit()
    conn.close()

    return ApplyTemplateResponse(
        output_id=output_id,
        content=content,
        template_name=tmpl_row["name"]
    )


@router.post("/recordings/batch-apply", response_model=BatchApplyResponse)
async def batch_apply_templates(
    request: BatchApplyRequest = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Apply multiple templates to multiple recordings"""
    outputs = []
    failed = 0

    conn = get_db()
    cursor = conn.cursor()

    for recording_id in request.recording_ids:
        # Get recording
        cursor.execute("SELECT transcript FROM recordings WHERE id = ?", (recording_id,))
        rec_row = cursor.fetchone()
        if not rec_row:
            failed += 1
            continue
        transcript = rec_row["transcript"]

        for template_id in request.template_ids:
            try:
                # Get template
                cursor.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
                tmpl_row = cursor.fetchone()
                if not tmpl_row:
                    failed += 1
                    continue

                # Apply template
                content = await apply_template_with_ollama(transcript, tmpl_row["system_prompt"])

                # Save output
                output_id = f"out_{uuid4().hex[:12]}"
                now = datetime.now(UTC).isoformat()

                cursor.execute("""
                    INSERT INTO formatted_outputs
                    (id, recording_id, template_id, template_name, content, format, generated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    output_id, recording_id, template_id,
                    tmpl_row["name"], content, tmpl_row["output_format"], now
                ))

                outputs.append(FormattedOutput(
                    id=output_id,
                    recording_id=recording_id,
                    template_id=template_id,
                    template_name=tmpl_row["name"],
                    content=content,
                    format=OutputFormat(tmpl_row["output_format"]),
                    generated_at=now
                ))

            except Exception as e:
                logger.error(f"Batch apply failed for {recording_id}/{template_id}: {e}")
                failed += 1

    conn.commit()
    conn.close()

    return BatchApplyResponse(
        outputs=outputs,
        total_processed=len(outputs),
        failed=failed,
        message=f"Processed {len(outputs)} outputs, {failed} failed"
    )


@router.get("/recordings/{recording_id}/outputs")
async def list_recording_outputs(
    recording_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """List all formatted outputs for a recording"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM formatted_outputs WHERE recording_id = ? ORDER BY generated_at DESC", (recording_id,))
    rows = cursor.fetchall()

    outputs = []
    for row in rows:
        outputs.append(FormattedOutput(
            id=row["id"],
            recording_id=row["recording_id"],
            template_id=row["template_id"],
            template_name=row["template_name"],
            content=row["content"],
            format=OutputFormat(row["format"]),
            generated_at=row["generated_at"]
        ))

    conn.close()

    return {"outputs": outputs, "total": len(outputs)}


@router.delete("/outputs/{output_id}")
async def delete_output(
    output_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Delete a formatted output"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM formatted_outputs WHERE id = ?", (output_id,))

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Output not found")

    conn.commit()
    conn.close()

    return {"message": "Output deleted", "output_id": output_id}


__all__ = ["router"]
