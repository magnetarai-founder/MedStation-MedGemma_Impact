"""
Vault Automation Routes - File organization automation and decoy vault seeding

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
import sqlite3
import uuid
import re
from datetime import datetime
from typing import Dict
from fastapi import APIRouter, HTTPException, Form, Request, Depends, status

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user
from api.services.vault.core import get_vault_service
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter()


# ===== File Organization Automation =====

@router.post(
    "/automation/create-rule",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_201_CREATED,
    name="vault_automation_create_rule",
    summary="Create automation rule",
    description="Create a file organization automation rule"
)
async def create_organization_rule(
    user_id: str = Form(...),
    vault_type: str = Form(...),
    rule_name: str = Form(...),
    rule_type: str = Form(...),
    condition_value: str = Form(...),
    action_type: str = Form(...),
    action_value: str = Form(...),
    priority: int = Form(0)
) -> SuccessResponse[Dict]:
    """
    Create a file organization rule

    Returns:
        Created rule details with ID
    """
    try:
        service = get_vault_service()

        valid_rule_types = ['mime_type', 'file_extension', 'file_size', 'filename_pattern', 'date']
        valid_action_types = ['move_to_folder', 'add_tag', 'set_color']

        if rule_type not in valid_rule_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=f"Invalid rule_type. Must be one of: {valid_rule_types}"
                ).model_dump()
            )

        if action_type not in valid_action_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=f"Invalid action_type. Must be one of: {valid_action_types}"
                ).model_dump()
            )

        rule_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        conn = sqlite3.connect(service.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO vault_organization_rules
                (id, user_id, vault_type, rule_name, rule_type, condition_value,
                 action_type, action_value, priority, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (rule_id, user_id, vault_type, rule_name, rule_type, condition_value,
                  action_type, action_value, priority, now))

            conn.commit()

            rule_data = {
                "rule_id": rule_id,
                "rule_name": rule_name,
                "rule_type": rule_type,
                "action_type": action_type,
                "is_enabled": True,
                "created_at": now
            }

            return SuccessResponse(
                data=rule_data,
                message=f"Automation rule '{rule_name}' created successfully"
            )

        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="Rule with this name already exists"
                ).model_dump()
            )
        finally:
            conn.close()

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to create automation rule", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to create automation rule"
            ).model_dump()
        )


@router.get(
    "/automation/rules",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_automation_get_rules",
    summary="Get automation rules",
    description="Get all organization rules for a user"
)
async def get_organization_rules(user_id: str, vault_type: str = "real") -> SuccessResponse[Dict]:
    """
    Get all organization rules for a user

    Returns:
        List of automation rules sorted by priority
    """
    try:
        service = get_vault_service()

        conn = sqlite3.connect(service.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT * FROM vault_organization_rules
                WHERE user_id = ? AND vault_type = ?
                ORDER BY priority DESC, created_at ASC
            """, (user_id, vault_type))

            rules = []
            for row in cursor.fetchall():
                rules.append({
                    "rule_id": row['id'],
                    "rule_name": row['rule_name'],
                    "rule_type": row['rule_type'],
                    "condition_value": row['condition_value'],
                    "action_type": row['action_type'],
                    "action_value": row['action_value'],
                    "is_enabled": bool(row['is_enabled']),
                    "priority": row['priority'],
                    "files_processed": row['files_processed'],
                    "last_run": row['last_run'],
                    "created_at": row['created_at']
                })

            rules_data = {"rules": rules}

            return SuccessResponse(
                data=rules_data,
                message=f"Retrieved {len(rules)} automation rule{'s' if len(rules) != 1 else ''}"
            )

        finally:
            conn.close()

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get automation rules", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve automation rules"
            ).model_dump()
        )


@router.post(
    "/automation/run-rules",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_automation_run_rules",
    summary="Run automation rules",
    description="Run all enabled organization rules on existing files"
)
async def run_organization_rules(
    user_id: str = Form(...),
    vault_type: str = Form("real")
) -> SuccessResponse[Dict]:
    """
    Run all enabled organization rules on existing files

    Returns:
        Statistics on rules executed and files processed
    """
    try:
        service = get_vault_service()

        conn = sqlite3.connect(service.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Get enabled rules
            cursor.execute("""
                SELECT * FROM vault_organization_rules
                WHERE user_id = ? AND vault_type = ? AND is_enabled = 1
                ORDER BY priority DESC
            """, (user_id, vault_type))

            rules = cursor.fetchall()
            total_processed = 0
            results = []

            for rule in rules:
                files_matched = 0

                # Get all files for this user/vault
                cursor.execute("""
                    SELECT * FROM vault_files
                    WHERE user_id = ? AND vault_type = ? AND is_deleted = 0
                """, (user_id, vault_type))

                files = cursor.fetchall()

                for file in files:
                    matched = False

                    # Check rule condition
                    if rule['rule_type'] == 'mime_type':
                        matched = file['mime_type'].startswith(rule['condition_value'])

                    elif rule['rule_type'] == 'file_extension':
                        matched = file['filename'].endswith(rule['condition_value'])

                    elif rule['rule_type'] == 'file_size':
                        # Format: ">1000000" for files larger than 1MB
                        operator = rule['condition_value'][0]
                        size_limit = int(rule['condition_value'][1:])
                        if operator == '>':
                            matched = file['file_size'] > size_limit
                        elif operator == '<':
                            matched = file['file_size'] < size_limit

                    elif rule['rule_type'] == 'filename_pattern':
                        matched = bool(re.search(rule['condition_value'], file['filename']))

                    # Apply action if matched
                    if matched:
                        if rule['action_type'] == 'move_to_folder':
                            cursor.execute("""
                                UPDATE vault_files
                                SET folder_path = ?, updated_at = ?
                                WHERE id = ?
                            """, (rule['action_value'], datetime.utcnow().isoformat(), file['id']))

                        elif rule['action_type'] == 'add_tag':
                            # Add tag if it doesn't exist
                            tag_id = str(uuid.uuid4())
                            try:
                                cursor.execute("""
                                    INSERT INTO vault_file_tags
                                    (id, file_id, user_id, vault_type, tag_name, created_at)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                """, (tag_id, file['id'], user_id, vault_type,
                                      rule['action_value'], datetime.utcnow().isoformat()))
                            except sqlite3.IntegrityError:
                                pass  # Tag already exists

                        files_matched += 1

                # Update rule stats
                now = datetime.utcnow().isoformat()
                cursor.execute("""
                    UPDATE vault_organization_rules
                    SET last_run = ?, files_processed = files_processed + ?
                    WHERE id = ?
                """, (now, files_matched, rule['id']))

                results.append({
                    "rule_name": rule['rule_name'],
                    "files_matched": files_matched
                })
                total_processed += files_matched

            conn.commit()

            rules_data = {
                "total_rules_run": len(rules),
                "total_files_processed": total_processed,
                "results": results
            }

            return SuccessResponse(
                data=rules_data,
                message=f"Processed {total_processed} file{'s' if total_processed != 1 else ''} across {len(rules)} rule{'s' if len(rules) != 1 else ''}"
            )

        finally:
            conn.close()

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to run automation rules", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to run automation rules"
            ).model_dump()
        )


@router.put(
    "/automation/toggle-rule/{rule_id}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_automation_toggle_rule",
    summary="Toggle automation rule",
    description="Enable or disable an automation rule"
)
async def toggle_rule(rule_id: str, enabled: bool = Form(...)) -> SuccessResponse[Dict]:
    """
    Enable or disable an automation rule

    Args:
        rule_id: Rule ID to toggle
        enabled: New enabled state

    Returns:
        Confirmation of rule toggle
    """
    try:
        service = get_vault_service()

        conn = sqlite3.connect(service.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE vault_organization_rules
                SET is_enabled = ?
                WHERE id = ?
            """, (1 if enabled else 0, rule_id))

            conn.commit()

            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error_code=ErrorCode.NOT_FOUND,
                        message="Rule not found"
                    ).model_dump()
                )

            toggle_data = {
                "success": True,
                "rule_id": rule_id,
                "enabled": enabled
            }

            return SuccessResponse(
                data=toggle_data,
                message=f"Rule {'enabled' if enabled else 'disabled'} successfully"
            )

        finally:
            conn.close()

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to toggle automation rule", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to toggle automation rule"
            ).model_dump()
        )


@router.delete(
    "/automation/delete-rule/{rule_id}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_automation_delete_rule",
    summary="Delete automation rule",
    description="Delete an automation rule"
)
async def delete_rule(rule_id: str) -> SuccessResponse[Dict]:
    """
    Delete an automation rule

    Args:
        rule_id: Rule ID to delete

    Returns:
        Confirmation of rule deletion
    """
    try:
        service = get_vault_service()

        conn = sqlite3.connect(service.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM vault_organization_rules WHERE id = ?", (rule_id,))
            conn.commit()

            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error_code=ErrorCode.NOT_FOUND,
                        message="Rule not found"
                    ).model_dump()
                )

            delete_data = {
                "success": True,
                "rule_id": rule_id
            }

            return SuccessResponse(
                data=delete_data,
                message="Automation rule deleted successfully"
            )

        finally:
            conn.close()

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to delete automation rule", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to delete automation rule"
            ).model_dump()
        )


# ===== Decoy Vault Seeding =====

@router.post(
    "/seed-decoy-vault",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_seed_decoy",
    summary="Seed decoy vault",
    description="Seed decoy vault with realistic documents for plausible deniability (requires authentication)"
)
async def seed_decoy_vault_endpoint(
    request: Request,
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Seed decoy vault with realistic documents for plausible deniability

    This populates the decoy vault with convincing documents like:
    - Budget spreadsheets
    - WiFi passwords
    - Shopping lists
    - Travel plans
    - Meeting notes

    Only seeds if decoy vault is empty.

    Returns:
        Seeding result with status and document count
    """
    user_id = current_user["user_id"]

    try:
        from vault_seed_data import get_seeder

        seeder = get_seeder()
        result = seeder.seed_decoy_vault(user_id)

        logger.info(f"Decoy vault seeding result: {result['status']}")

        return SuccessResponse(
            data=result,
            message=f"Decoy vault seeding completed: {result.get('status', 'unknown')}"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to seed decoy vault", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to seed decoy vault"
            ).model_dump()
        )


@router.delete(
    "/clear-decoy-vault",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_clear_decoy",
    summary="Clear decoy vault",
    description="Clear all decoy vault documents for testing/re-seeding (requires authentication)"
)
async def clear_decoy_vault_endpoint(
    request: Request,
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Clear all decoy vault documents (for testing/re-seeding)

    ⚠️ WARNING: This will delete all decoy vault documents!
    Use this if you want to re-seed the decoy vault with fresh data.

    Returns:
        Deletion result with document count
    """
    user_id = current_user["user_id"]

    try:
        from vault_seed_data import get_seeder

        seeder = get_seeder()
        result = seeder.clear_decoy_vault(user_id)

        logger.info(f"Decoy vault cleared: {result['deleted_count']} documents")

        return SuccessResponse(
            data=result,
            message=f"Cleared {result.get('deleted_count', 0)} decoy vault document{'s' if result.get('deleted_count', 0) != 1 else ''}"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to clear decoy vault", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to clear decoy vault"
            ).model_dump()
        )
