"""
Vault Automation Routes - File organization automation and decoy vault seeding
"""

import logging
import sqlite3
import uuid
import re
from datetime import datetime
from typing import Dict
from fastapi import APIRouter, HTTPException, Form, Request, Depends

from api.auth_middleware import get_current_user
from api.services.vault.core import get_vault_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ===== File Organization Automation =====

@router.post("/automation/create-rule")
async def create_organization_rule(
    user_id: str = Form(...),
    vault_type: str = Form(...),
    rule_name: str = Form(...),
    rule_type: str = Form(...),
    condition_value: str = Form(...),
    action_type: str = Form(...),
    action_value: str = Form(...),
    priority: int = Form(0)
):
    """Create a file organization rule"""
    service = get_vault_service()
    
    valid_rule_types = ['mime_type', 'file_extension', 'file_size', 'filename_pattern', 'date']
    valid_action_types = ['move_to_folder', 'add_tag', 'set_color']
    
    if rule_type not in valid_rule_types:
        raise HTTPException(status_code=400, detail=f"Invalid rule_type. Must be one of: {valid_rule_types}")
    
    if action_type not in valid_action_types:
        raise HTTPException(status_code=400, detail=f"Invalid action_type. Must be one of: {valid_action_types}")
    
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
        
        return {
            "rule_id": rule_id,
            "rule_name": rule_name,
            "rule_type": rule_type,
            "action_type": action_type,
            "is_enabled": True,
            "created_at": now
        }
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Rule with this name already exists")
    finally:
        conn.close()


@router.get("/automation/rules")
async def get_organization_rules(user_id: str, vault_type: str = "real"):
    """Get all organization rules for a user"""
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
        
        return {"rules": rules}
    finally:
        conn.close()


@router.post("/automation/run-rules")
async def run_organization_rules(user_id: str = Form(...), vault_type: str = Form("real")):
    """Run all enabled organization rules on existing files"""
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
        
        return {
            "total_rules_run": len(rules),
            "total_files_processed": total_processed,
            "results": results
        }
    finally:
        conn.close()


@router.put("/automation/toggle-rule/{rule_id}")
async def toggle_rule(rule_id: str, enabled: bool = Form(...)):
    """Enable or disable a rule"""
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
            raise HTTPException(status_code=404, detail="Rule not found")
        
        return {"success": True, "rule_id": rule_id, "enabled": enabled}
    finally:
        conn.close()


@router.delete("/automation/delete-rule/{rule_id}")
async def delete_rule(rule_id: str):
    """Delete an organization rule"""
    service = get_vault_service()

    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM vault_organization_rules WHERE id = ?", (rule_id,))
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Rule not found")

        return {"success": True, "rule_id": rule_id}
    finally:
        conn.close()


# ===== Decoy Vault Seeding =====

@router.post("/seed-decoy-vault")
async def seed_decoy_vault_endpoint(request: Request, current_user: Dict = Depends(get_current_user)):
    """
    Seed decoy vault with realistic documents for plausible deniability

    This populates the decoy vault with convincing documents like:
    - Budget spreadsheets
    - WiFi passwords
    - Shopping lists
    - Travel plans
    - Meeting notes

    Only seeds if decoy vault is empty.
    """
    user_id = current_user["user_id"]

    try:
        from vault_seed_data import get_seeder

        seeder = get_seeder()
        result = seeder.seed_decoy_vault(user_id)

        logger.info(f"Decoy vault seeding result: {result['status']}")

        return result

    except Exception as e:
        logger.error(f"Failed to seed decoy vault: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear-decoy-vault")
async def clear_decoy_vault_endpoint(request: Request, current_user: Dict = Depends(get_current_user)):
    """
    Clear all decoy vault documents (for testing/re-seeding)

    WARNING: This will delete all decoy vault documents!
    Use this if you want to re-seed the decoy vault with fresh data.
    """
    user_id = current_user["user_id"]

    try:
        from vault_seed_data import get_seeder

        seeder = get_seeder()
        result = seeder.clear_decoy_vault(user_id)

        logger.info(f"Decoy vault cleared: {result['deleted_count']} documents")

        return result

    except Exception as e:
        logger.error(f"Failed to clear decoy vault: {e}")
        raise HTTPException(status_code=500, detail=str(e))
