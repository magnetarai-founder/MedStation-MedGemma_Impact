"""
Insights Lab Template Routes

CRUD endpoints for templates.
"""

import logging
from typing import Optional, List, Any
from datetime import datetime, UTC
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, Depends, Body

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user
from api.schemas.insights_models import (
    Template, CreateTemplateRequest, UpdateTemplateRequest, TemplateListResponse,
    TemplateCategory, OutputFormat
)

from ..database import get_db, build_safe_update, TEMPLATE_UPDATE_COLUMNS

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Templates"])


@router.get("/templates", response_model=TemplateListResponse)
async def list_templates(
    request: Request,
    category: Optional[str] = None,
    include_builtin: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """List all available templates"""
    user_id = current_user.get("user_id") or current_user.get("id")

    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM templates WHERE (created_by = ? OR is_builtin = 1)"
    params: List[Any] = [user_id]

    if not include_builtin:
        query = "SELECT * FROM templates WHERE created_by = ? AND is_builtin = 0"

    if category:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY is_builtin DESC, name ASC"

    cursor.execute(query, params)
    rows = cursor.fetchall()

    templates = []
    for row in rows:
        templates.append(Template(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            system_prompt=row["system_prompt"],
            category=TemplateCategory(row["category"]),
            is_builtin=bool(row["is_builtin"]),
            output_format=OutputFormat(row["output_format"]),
            created_by=row["created_by"],
            team_id=row["team_id"],
            created_at=row["created_at"]
        ))

    conn.close()

    return TemplateListResponse(templates=templates, total=len(templates))


@router.post("/templates")
async def create_template(
    request: CreateTemplateRequest = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Create a custom template"""
    user_id = current_user.get("user_id") or current_user.get("id")
    template_id = f"tmpl_{uuid4().hex[:12]}"

    conn = get_db()
    cursor = conn.cursor()
    now = datetime.now(UTC).isoformat()

    cursor.execute("""
        INSERT INTO templates
        (id, name, description, system_prompt, category, is_builtin, output_format, created_by, team_id, created_at)
        VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
    """, (
        template_id,
        request.name,
        request.description,
        request.system_prompt,
        request.category.value,
        request.output_format.value,
        user_id,
        request.team_id,
        now
    ))

    conn.commit()
    conn.close()

    return {"template_id": template_id, "message": "Template created"}


@router.put("/templates/{template_id}")
async def update_template(
    template_id: str,
    request: UpdateTemplateRequest = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Update a custom template (cannot update built-in templates)"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT is_builtin FROM templates WHERE id = ?", (template_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Template not found")

    if row["is_builtin"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Cannot modify built-in templates")

    # Build updates dict with whitelisted columns only
    updates_dict = {}
    if request.name is not None:
        updates_dict["name"] = request.name
    if request.description is not None:
        updates_dict["description"] = request.description
    if request.system_prompt is not None:
        updates_dict["system_prompt"] = request.system_prompt
    if request.category is not None:
        updates_dict["category"] = request.category.value
    if request.output_format is not None:
        updates_dict["output_format"] = request.output_format.value

    if updates_dict:
        # Use safe builder with whitelist validation
        updates, params = build_safe_update(updates_dict, TEMPLATE_UPDATE_COLUMNS)
        params.append(template_id)
        cursor.execute(f"UPDATE templates SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()

    conn.close()

    return {"message": "Template updated", "template_id": template_id}


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Delete a custom template (cannot delete built-in templates)"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT is_builtin FROM templates WHERE id = ?", (template_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Template not found")

    if row["is_builtin"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Cannot delete built-in templates")

    cursor.execute("DELETE FROM templates WHERE id = ?", (template_id,))
    conn.commit()
    conn.close()

    return {"message": "Template deleted", "template_id": template_id}


__all__ = ["router"]
