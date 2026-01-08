"""
Bash Assist Endpoint

Intelligent bash assistant - NL→bash translation and safety checking.
"""

import logging
from pathlib import Path

from fastapi import Depends, HTTPException, Request

from api.terminal.models import BashAssistRequest, BashAssistResponse

logger = logging.getLogger(__name__)

# Imports with fallbacks
try:
    from api.auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user

try:
    from api.utils import get_user_id
except ImportError:
    from utils import get_user_id

try:
    from api.bash_intelligence import get_bash_intelligence
    from api.unified_context import get_unified_context
except ImportError:
    from bash_intelligence import get_bash_intelligence
    from unified_context import get_unified_context


async def bash_assist(
    request: Request,
    body: BashAssistRequest,
    current_user: dict = Depends(get_current_user)
) -> BashAssistResponse:
    """
    Intelligent bash assist - translate NL to bash, check safety

    Features:
    - Natural language → bash translation
    - Command safety checking
    - Context-aware suggestions
    - Integrated with unified context

    Rate limited: 30/min per user
    """
    user_id = get_user_id(current_user)

    # Rate limiting
    try:
        from api.rate_limiter import rate_limiter
    except ImportError:
        from rate_limiter import rate_limiter

    if not rate_limiter.check_rate_limit(
        f"terminal:assist:{user_id}",
        max_requests=30,
        window_seconds=60
    ):
        raise HTTPException(status_code=429, detail="Too many assist requests. Please try again later.")

    # Get bash intelligence
    bash_intel = get_bash_intelligence()

    # Classify input
    classification = bash_intel.classify_input(body.input)

    # Get suggested command
    suggested_cmd = classification.get('suggestion')
    if not suggested_cmd and classification['type'] == 'bash':
        suggested_cmd = body.input

    # Check safety
    is_safe = True
    safety_warning = None
    if suggested_cmd:
        is_safe, safety_warning = bash_intel.check_safety(suggested_cmd)

    # Get improvements
    improvements = []
    if suggested_cmd:
        improvements = bash_intel.suggest_improvements(suggested_cmd)

    # Add to unified context
    if body.session_id:
        try:
            from api.workspace_session import get_workspace_session_manager

            context_mgr = get_unified_context()
            ws_mgr = get_workspace_session_manager()

            # Ensure session_id is a workspace session
            workspace_session_id = body.session_id
            if not workspace_session_id.startswith('ws_'):
                workspace_session_id = ws_mgr.get_or_create_for_workspace(
                    user_id=user_id,
                    workspace_root=body.cwd or str(Path.home())
                )

            context_mgr.add_entry(
                user_id=user_id,
                session_id=workspace_session_id,
                source='terminal',
                entry_type='command',
                content=suggested_cmd or body.input,
                metadata={
                    'original_input': body.input,
                    'input_type': classification['type'],
                    'is_safe': is_safe,
                    'cwd': body.cwd
                }
            )
        except Exception as e:
            logger.warning(f"Failed to add to unified context: {e}")

    return BashAssistResponse(
        input_type=classification['type'],
        confidence=classification['confidence'],
        suggested_command=suggested_cmd,
        is_safe=is_safe,
        safety_warning=safety_warning,
        improvements=improvements
    )
