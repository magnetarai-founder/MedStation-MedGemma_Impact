"""
Admin service layer for ElohimOS - Danger Zone operations.

Contains business logic for admin operations with lazy imports to avoid cycles.
All functions use lazy imports to break circular dependencies.
"""

import json
import shutil
from pathlib import Path
from typing import Dict


async def reset_all_data() -> Dict[str, any]:
    """Reset all app data - clears database and temp files"""
    # Lazy imports to avoid cycles
    from api.main import elohimos_memory, sessions, query_results, app_settings
    from api.models import AppSettings

    # Clear all saved queries and history
    elohimos_memory.memory.conn.execute("DELETE FROM query_history")
    elohimos_memory.memory.conn.execute("DELETE FROM saved_queries")
    elohimos_memory.memory.conn.execute("DELETE FROM app_settings")
    elohimos_memory.memory.conn.commit()

    # Reset settings to defaults
    import api.main
    api.main.app_settings = AppSettings()

    # Clear temp directories
    api_dir = Path(__file__).parent.parent
    temp_uploads = api_dir / "temp_uploads"
    temp_exports = api_dir / "temp_exports"

    if temp_uploads.exists():
        shutil.rmtree(temp_uploads)
        temp_uploads.mkdir()

    if temp_exports.exists():
        shutil.rmtree(temp_exports)
        temp_exports.mkdir()

    # Clear all sessions
    sessions.clear()
    query_results.clear()

    return {"success": True, "message": "All data has been reset"}


async def uninstall_app() -> Dict[str, any]:
    """Uninstall app - removes all data directories"""
    from api.main import elohimos_memory
    from api.config import get_settings

    settings = get_settings()

    # Close database connection
    elohimos_memory.close()

    # Get data directories
    data_dir = settings.data_dir

    # Remove data directory
    if data_dir.exists():
        shutil.rmtree(data_dir)

    return {"success": True, "message": "App data has been uninstalled"}


async def clear_chats() -> Dict[str, any]:
    """Clear all AI chat history"""
    api_dir = Path(__file__).parent.parent
    chats_dir = api_dir / ".neutron_data" / "chats"

    if chats_dir.exists():
        shutil.rmtree(chats_dir)
        chats_dir.mkdir(parents=True)
        (chats_dir / "sessions.json").write_text("[]")

    return {"success": True, "message": "AI chat history cleared"}


async def clear_team_messages() -> Dict[str, any]:
    """Clear P2P team chat history"""
    api_dir = Path(__file__).parent.parent
    p2p_dir = api_dir / ".neutron_data" / "p2p"

    if p2p_dir.exists():
        shutil.rmtree(p2p_dir)
        p2p_dir.mkdir(parents=True)

    return {"success": True, "message": "Team messages cleared"}


async def clear_query_library() -> Dict[str, any]:
    """Clear all saved SQL queries"""
    from api.main import elohimos_memory

    elohimos_memory.memory.conn.execute("DELETE FROM saved_queries")
    elohimos_memory.memory.conn.commit()

    return {"success": True, "message": "Query library cleared"}


async def clear_query_history() -> Dict[str, any]:
    """Clear SQL execution history"""
    from api.main import elohimos_memory

    elohimos_memory.memory.conn.execute("DELETE FROM query_history")
    elohimos_memory.memory.conn.commit()

    return {"success": True, "message": "Query history cleared"}


async def clear_temp_files() -> Dict[str, any]:
    """Clear uploaded files and exports"""
    api_dir = Path(__file__).parent.parent

    for temp_dir_name in ["temp_uploads", "temp_exports"]:
        temp_dir = api_dir / temp_dir_name
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            temp_dir.mkdir()

    return {"success": True, "message": "Temp files cleared"}


async def clear_code_files() -> Dict[str, any]:
    """Clear saved code editor files"""
    api_dir = Path(__file__).parent.parent
    code_dir = api_dir / ".neutron_data" / "code"

    if code_dir.exists():
        shutil.rmtree(code_dir)
        code_dir.mkdir(parents=True)

    return {"success": True, "message": "Code files cleared"}


async def reset_settings() -> Dict[str, any]:
    """Reset all settings to defaults"""
    from api.main import elohimos_memory
    from api.models import AppSettings

    elohimos_memory.memory.conn.execute("DELETE FROM app_settings")
    elohimos_memory.memory.conn.commit()

    import api.main
    api.main.app_settings = AppSettings()

    return {"success": True, "message": "Settings reset to defaults"}


async def reset_data() -> Dict[str, any]:
    """Delete all data but keep settings"""
    from api.main import elohimos_memory, sessions, query_results

    # Clear database tables except settings
    elohimos_memory.memory.conn.execute("DELETE FROM query_history")
    elohimos_memory.memory.conn.execute("DELETE FROM saved_queries")
    elohimos_memory.memory.conn.commit()

    # Clear chat data
    api_dir = Path(__file__).parent.parent
    neutron_data = api_dir / ".neutron_data"

    for subdir in ["chats", "p2p", "code", "uploads"]:
        target = neutron_data / subdir
        if target.exists():
            shutil.rmtree(target)
            target.mkdir(parents=True)

    # Clear temp files
    for temp_dir_name in ["temp_uploads", "temp_exports"]:
        temp_dir = api_dir / temp_dir_name
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            temp_dir.mkdir()

    sessions.clear()
    query_results.clear()

    return {"success": True, "message": "All data deleted, settings preserved"}


async def export_all_data(current_user: dict):
    """Export complete backup as ZIP"""
    from datetime import datetime
    from starlette.background import BackgroundTask
    from fastapi.responses import FileResponse
    from api.config import get_settings
    from api.permission_engine import has_permission

    # Check permission
    if not has_permission(current_user, "data.export"):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Permission denied: data.export required")

    settings = get_settings()
    temp_dir = settings.temp_exports_dir

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_path = temp_dir / f"elohimos_backup_{timestamp}.zip"

    import zipfile
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add all data from data directory
        if settings.data_dir.exists():
            for file in settings.data_dir.rglob('*'):
                if file.is_file():
                    zipf.write(file, str(file.relative_to(settings.data_dir.parent)))

    return FileResponse(
        path=zip_path,
        filename=zip_path.name,
        media_type="application/zip",
        background=BackgroundTask(lambda: zip_path.unlink(missing_ok=True))
    )


async def export_chats():
    """Export AI chat history as JSON"""
    from datetime import datetime
    from starlette.background import BackgroundTask
    from fastapi.responses import FileResponse

    api_dir = Path(__file__).parent.parent
    chats_dir = api_dir / ".neutron_data" / "chats"

    all_chats = []
    if chats_dir.exists():
        sessions_file = chats_dir / "sessions.json"
        if sessions_file.exists():
            all_chats = json.loads(sessions_file.read_text())

    temp_dir = api_dir / "temp_exports"
    temp_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    export_path = temp_dir / f"chats_export_{timestamp}.json"
    export_path.write_text(json.dumps(all_chats, indent=2))

    return FileResponse(
        path=export_path,
        filename=export_path.name,
        media_type="application/json",
        background=BackgroundTask(lambda: export_path.unlink(missing_ok=True))
    )


async def export_queries():
    """Export query library as JSON"""
    from datetime import datetime
    from starlette.background import BackgroundTask
    from fastapi.responses import FileResponse
    from api.main import elohimos_memory

    queries = elohimos_memory.get_saved_queries()

    temp_dir = Path(__file__).parent.parent / "temp_exports"
    temp_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    export_path = temp_dir / f"queries_export_{timestamp}.json"
    export_path.write_text(json.dumps(queries, indent=2))

    return FileResponse(
        path=export_path,
        filename=export_path.name,
        media_type="application/json",
        background=BackgroundTask(lambda: export_path.unlink(missing_ok=True))
    )
