"""
Centralized router registration for FastAPI app.

This module provides a single function to register all API routers, maintaining
service loading status and error handling.

Usage (in main.py, guarded by environment variable):

    import os
    from contextlib import asynccontextmanager
    from fastapi import FastAPI

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        logger.info("ElohimOS API starting...")

        if os.getenv("ELOHIMOS_USE_ROUTER_REGISTRY") == "1":
            from .router_registry import register_routers
            services_loaded, services_failed = register_routers(app)
            logger.info(f"Loaded: {services_loaded}")
            if services_failed:
                logger.warning(f"Failed: {services_failed}")

        yield

        # Shutdown
        logger.info("ElohimOS API shutting down...")

    app = FastAPI(lifespan=lifespan, title="ElohimOS API")
"""

import logging
from typing import List, Tuple

from fastapi import FastAPI

logger = logging.getLogger(__name__)


def register_routers(app: FastAPI) -> Tuple[List[str], List[str]]:
    """
    Register all API routers to the FastAPI app.

    Args:
        app: FastAPI application instance

    Returns:
        Tuple of (services_loaded, services_failed) with human-readable names
    """
    services_loaded = []
    services_failed = []

    # Chat API
    try:
        from api.routes import chat as _chat_routes
        app.include_router(_chat_routes.router)
        app.include_router(_chat_routes.public_router)
        services_loaded.append("Chat API")
    except Exception as e:
        services_failed.append("Chat API")
        logger.error("Failed to load chat router", exc_info=True)

    # P2P Chat
    try:
        from api.p2p_chat_router import router as p2p_chat_router
        app.include_router(p2p_chat_router)
        services_loaded.append("P2P Chat")
    except Exception as e:
        services_failed.append("P2P Chat")
        logger.error("Failed to load P2P chat router", exc_info=True)

    # LAN Discovery
    try:
        from api.lan_service import router as lan_router
        app.include_router(lan_router)
        services_loaded.append("LAN Discovery")
    except Exception as e:
        services_failed.append("LAN Discovery")
        logger.error("Failed to load LAN discovery router", exc_info=True)

    # P2P Mesh
    try:
        from api.p2p_mesh_service import router as p2p_mesh_router
        app.include_router(p2p_mesh_router)
        services_loaded.append("P2P Mesh")
    except Exception as e:
        services_failed.append("P2P Mesh")
        logger.error("Failed to load P2P mesh router", exc_info=True)

    # Code Editor
    try:
        from api.code_editor_service import router as code_editor_router
        app.include_router(code_editor_router)
        services_loaded.append("Code Editor")
    except Exception as e:
        services_failed.append("Code Editor")
        logger.error("Failed to load code editor router", exc_info=True)

    # Users API
    try:
        from api.routes import users as _users_routes
        app.include_router(_users_routes.router)
        services_loaded.append("Users API")
    except Exception as e:
        services_failed.append("Users API")
        logger.error("Failed to load users router", exc_info=True)

    # Documents API
    try:
        from api.docs_service import router as docs_router
        app.include_router(docs_router)
        services_loaded.append("Documents API")
    except Exception as e:
        services_failed.append("Documents API")
        logger.error("Failed to load documents router", exc_info=True)

    # Insights API
    try:
        from api.insights_service import router as insights_router
        app.include_router(insights_router)
        services_loaded.append("Insights API")
    except Exception as e:
        services_failed.append("Insights API")
        logger.error("Failed to load insights router", exc_info=True)

    # Offline Mesh
    try:
        from api.offline_mesh_router import router as mesh_router
        app.include_router(mesh_router)
        services_loaded.append("Offline Mesh")
    except Exception as e:
        services_failed.append("Offline Mesh")
        logger.error("Failed to load offline mesh router", exc_info=True)

    # Panic Mode
    try:
        from api.panic_mode_router import router as panic_router
        app.include_router(panic_router)
        services_loaded.append("Panic Mode")
    except Exception as e:
        services_failed.append("Panic Mode")
        logger.error("Failed to load panic mode router", exc_info=True)

    # Automation
    try:
        from api.automation_router import router as automation_router
        app.include_router(automation_router)
        services_loaded.append("Automation")
    except Exception as e:
        services_failed.append("Automation")
        logger.error("Failed to load automation router", exc_info=True)

    # Workflow
    try:
        from api.workflow_service import router as workflow_router
        app.include_router(workflow_router)
        services_loaded.append("Workflow")
    except Exception as e:
        services_failed.append("Workflow")
        logger.error("Failed to load workflow router", exc_info=True)

    # Secure Enclave
    try:
        from api.secure_enclave_service import router as secure_enclave_router
        app.include_router(secure_enclave_router)
        services_loaded.append("Secure Enclave")
    except Exception as e:
        services_failed.append("Secure Enclave")
        logger.error("Failed to load secure enclave router", exc_info=True)

    # Auth
    try:
        from api.auth_routes import router as auth_router
        app.include_router(auth_router)
        services_loaded.append("Auth")
    except Exception as e:
        services_failed.append("Auth")
        logger.error("Failed to load auth router", exc_info=True)

    # Backup
    try:
        from api.backup_router import router as backup_router
        app.include_router(backup_router)
        services_loaded.append("Backup")
    except Exception as e:
        services_failed.append("Backup")
        logger.error("Failed to load backup router", exc_info=True)

    # Agent Orchestrator
    try:
        from api.agent import router as agent_router
        app.include_router(agent_router)
        services_loaded.append("Agent Orchestrator")
    except Exception as e:
        services_failed.append("Agent Orchestrator")
        logger.error("Failed to load agent router", exc_info=True)

    # Admin Service (legacy)
    try:
        from api.admin_service import router as admin_service_router
        app.include_router(admin_service_router)
        services_loaded.append("Admin Service")
    except Exception as e:
        services_failed.append("Admin Service")
        logger.error("Failed to load admin service router", exc_info=True)

    # Code Operations
    try:
        from api.code_operations import router as code_router
        app.include_router(code_router)
        services_loaded.append("Code Operations")
    except Exception as e:
        services_failed.append("Code Operations")
        logger.error("Failed to load code operations router", exc_info=True)

    # Audit API
    try:
        from api.routes import audit as _audit_routes
        app.include_router(_audit_routes.router)
        services_loaded.append("Audit API")
    except Exception as e:
        services_failed.append("Audit API")
        logger.error("Failed to load audit router", exc_info=True)

    # Model Downloads API
    try:
        from api.routes import model_downloads as _model_downloads_routes
        app.include_router(_model_downloads_routes.router)
        services_loaded.append("Model Downloads API")
    except Exception as e:
        services_failed.append("Model Downloads API")
        logger.error("Failed to load model downloads router", exc_info=True)

    # Analytics API
    try:
        from api.routes import analytics as _analytics_routes
        app.include_router(_analytics_routes.router)
        services_loaded.append("Analytics API")
    except Exception as e:
        services_failed.append("Analytics API")
        logger.error("Failed to load analytics router", exc_info=True)

    # Search API
    try:
        from api.routes import search as _search_routes
        app.include_router(_search_routes.router)
        services_loaded.append("Search API")
    except Exception as e:
        services_failed.append("Search API")
        logger.error("Failed to load search router", exc_info=True)

    # Feedback API
    try:
        from api.routes import feedback as _feedback_routes
        app.include_router(_feedback_routes.router)
        services_loaded.append("Feedback API")
    except Exception as e:
        services_failed.append("Feedback API")
        logger.error("Failed to load feedback router", exc_info=True)

    # Model Recommendations API
    try:
        from api.routes import models_recommendations as _recommendations_routes
        app.include_router(_recommendations_routes.router)
        services_loaded.append("Model Recommendations API")
    except Exception as e:
        services_failed.append("Model Recommendations API")
        logger.error("Failed to load recommendations router", exc_info=True)

    # Monitoring
    try:
        from api.monitoring_routes import router as monitoring_router
        app.include_router(monitoring_router)
        services_loaded.append("Monitoring")
    except Exception as e:
        services_failed.append("Monitoring")
        logger.error("Failed to load monitoring router", exc_info=True)

    # Terminal
    try:
        from api.terminal_api import router as terminal_router
        app.include_router(terminal_router)
        services_loaded.append("Terminal")
    except Exception as e:
        services_failed.append("Terminal")
        logger.error("Failed to load terminal router", exc_info=True)

    # Metal 4 ML
    try:
        from api.metal4_ml_routes import router as metal4_ml_router
        app.include_router(metal4_ml_router)
        services_loaded.append("Metal 4 ML")
    except Exception as e:
        services_failed.append("Metal 4 ML")
        logger.error("Failed to load Metal 4 ML router", exc_info=True)

    # Founder Setup
    try:
        from api.founder_setup_routes import router as founder_setup_router
        app.include_router(founder_setup_router)
        services_loaded.append("Founder Setup")
    except Exception as e:
        services_failed.append("Founder Setup")
        logger.error("Failed to load founder setup router", exc_info=True)

    # Setup Wizard
    try:
        from api.routes import setup_wizard_routes as _setup_wizard_routes
        app.include_router(_setup_wizard_routes.router)
        services_loaded.append("Setup Wizard")
    except Exception as e:
        services_failed.append("Setup Wizard")
        logger.error("Failed to load setup wizard router", exc_info=True)

    # User Models
    try:
        from api.routes import user_models as _user_models_routes
        app.include_router(_user_models_routes.router)
        services_loaded.append("User Models")
    except Exception as e:
        services_failed.append("User Models")
        logger.error("Failed to load user models router", exc_info=True)

    # System API
    try:
        from api.routes import system as _system_routes
        app.include_router(_system_routes.router)
        services_loaded.append("System API")
    except Exception as e:
        services_failed.append("System API")
        logger.error("Failed to load system router", exc_info=True)

    # Sessions API
    try:
        from api.routes import sessions as _sessions_routes
        app.include_router(_sessions_routes.router, prefix="/api/sessions")
        services_loaded.append("Sessions API")
    except Exception as e:
        services_failed.append("Sessions API")
        logger.error("Failed to load sessions router", exc_info=True)

    # SQL/JSON API
    try:
        from api.routes import sql_json as _sql_json_routes
        app.include_router(_sql_json_routes.router, prefix="/api/sessions")
        services_loaded.append("SQL/JSON API")
    except Exception as e:
        services_failed.append("SQL/JSON API")
        logger.error("Failed to load SQL/JSON router", exc_info=True)

    # Saved Queries API
    try:
        from api.routes import saved_queries as _saved_queries_routes
        app.include_router(_saved_queries_routes.router, prefix="/api/saved-queries")
        services_loaded.append("Saved Queries API")
    except Exception as e:
        services_failed.append("Saved Queries API")
        logger.error("Failed to load saved queries router", exc_info=True)

    # Settings API
    try:
        from api.routes import settings as _settings_routes
        app.include_router(_settings_routes.router, prefix="/api/settings")
        services_loaded.append("Settings API")
    except Exception as e:
        services_failed.append("Settings API")
        logger.error("Failed to load settings router", exc_info=True)

    # Metrics API
    try:
        from api.routes import metrics as _metrics_routes
        app.include_router(_metrics_routes.router, prefix="/metrics")
        services_loaded.append("Metrics API")
    except Exception as e:
        services_failed.append("Metrics API")
        logger.error("Failed to load metrics router", exc_info=True)

    # Metal API
    try:
        from api.routes import metal as _metal_routes
        app.include_router(_metal_routes.router, prefix="/api/v1/metal")
        services_loaded.append("Metal API")
    except Exception as e:
        services_failed.append("Metal API")
        logger.error("Failed to load metal router", exc_info=True)

    # Admin API (v1)
    try:
        from api.routes import admin as _admin_routes
        app.include_router(_admin_routes.router, prefix="/api/admin")
        services_loaded.append("Admin API (v1)")
    except Exception as e:
        services_failed.append("Admin API (v1)")
        logger.error("Failed to load admin v1 router", exc_info=True)

    # Vault API
    try:
        from api.routes import vault as _vault_routes
        app.include_router(_vault_routes.router)  # Router already has prefix="/api/v1/vault"
        services_loaded.append("Vault API")
    except Exception as e:
        services_failed.append("Vault API")
        logger.error("Failed to load vault router", exc_info=True)

    # Vault Auth API (Biometric + Decoy)
    try:
        from api.routes import vault_auth as _vault_auth_routes
        app.include_router(_vault_auth_routes.router)  # Router already has prefix="/api/v1/vault"
        services_loaded.append("Vault Auth API")
    except Exception as e:
        services_failed.append("Vault Auth API")
        logger.error("Failed to load vault auth router", exc_info=True)

    # Team API
    try:
        from api.routes import team as _team_routes
        app.include_router(_team_routes.router)  # Router already has prefix="/api/v1/teams"
        services_loaded.append("Team API")
    except Exception as e:
        services_failed.append("Team API")
        logger.error("Failed to load team router", exc_info=True)

    # Permissions API (v1)
    try:
        from api.routes import permissions as _perm_routes
        app.include_router(_perm_routes.router)  # Router already has prefix="/api/v1/permissions"
        services_loaded.append("Permissions API")
    except Exception as e:
        services_failed.append("Permissions API")
        logger.error("Failed to load permissions v1 router", exc_info=True)

    # Natural Language Query (NLQ) API
    try:
        from api.routes.data import nlq as _nlq_routes
        app.include_router(_nlq_routes.router)  # Router already has prefix="/api/v1/data"
        services_loaded.append("NLQ API")
    except Exception as e:
        services_failed.append("NLQ API")
        logger.error("Failed to load NLQ router", exc_info=True)

    # Diagnostics API (Mission Dashboard)
    try:
        from api.routes import diagnostics as _diag_routes
        app.include_router(_diag_routes.router)  # prefix="/api/v1"
        services_loaded.append("Diagnostics API")
    except Exception as e:
        services_failed.append("Diagnostics API")
        logger.error("Failed to load diagnostics router", exc_info=True)

    # P2P Transfer API (Chunked file transfer)
    try:
        from api.routes.p2p import transfer as _p2p_transfer_routes
        app.include_router(_p2p_transfer_routes.router)  # prefix="/api/v1/p2p/transfer"
        services_loaded.append("P2P Transfer API")
    except Exception as e:
        services_failed.append("P2P Transfer API")
        logger.error("Failed to load P2P transfer router", exc_info=True)

    # Collaboration Snapshots API
    try:
        from api.routes import collab_snapshots as _collab_snapshots
        app.include_router(_collab_snapshots.router)  # prefix="/api/v1/collab"
        services_loaded.append("Collab Snapshots API")
    except Exception as e:
        services_failed.append("Collab Snapshots API")
        logger.error("Failed to load collab snapshots router", exc_info=True)

    # Collaboration ACL Admin API
    try:
        from api.routes import collab_acl_admin as _collab_acl_admin
        app.include_router(_collab_acl_admin.router)  # prefix="/api/v1/collab"
        services_loaded.append("Collab ACL API")
    except Exception as e:
        services_failed.append("Collab ACL API")
        logger.error("Failed to load collab ACL router", exc_info=True)

    # Kanban API
    try:
        from api.routes.kanban import projects as _kb_projects
        from api.routes.kanban import boards as _kb_boards
        from api.routes.kanban import columns as _kb_columns
        from api.routes.kanban import tasks as _kb_tasks
        from api.routes.kanban import comments as _kb_comments
        from api.routes.kanban import wiki as _kb_wiki

        app.include_router(_kb_projects.router)
        app.include_router(_kb_boards.router)
        app.include_router(_kb_columns.router)
        app.include_router(_kb_tasks.router)
        app.include_router(_kb_comments.router)
        app.include_router(_kb_wiki.router)
        services_loaded.append("Kanban API")
    except Exception as e:
        services_failed.append("Kanban API")
        logger.error("Failed to load Kanban API", exc_info=True)

    # Pattern Discovery (Data Profiler) API
    try:
        from api.routes.data import profiler as _profiler_routes
        app.include_router(_profiler_routes.router)  # Router already has prefix="/api/v1/data"
        services_loaded.append("Pattern Discovery API")
    except Exception as e:
        services_failed.append("Pattern Discovery API")
        logger.error("Failed to load pattern discovery router", exc_info=True)

    # Collaborative Editing WebSocket
    try:
        from api import collab_ws as _collab_ws
        app.include_router(_collab_ws.router)  # Router already has prefix="/api/v1/collab"
        services_loaded.append("Collaboration API")
    except Exception as e:
        services_failed.append("Collaboration API")
        logger.error("Failed to load collaboration router", exc_info=True)

    return services_loaded, services_failed
