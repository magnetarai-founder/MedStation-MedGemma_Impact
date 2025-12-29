"""
Model Preloading Routes - Preload/unload models to/from memory

Split from models.py for maintainability.
"""

import logging
from fastapi import APIRouter, HTTPException, Request, Depends, status

from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from api.auth_middleware import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/models/preload",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="chat_preload_model"
)
async def preload_model_endpoint(
    request: Request,
    model: str,
    keep_alive: str = "1h",
    source: str = "user_manual",
    current_user: dict = Depends(get_current_user)
):
    """Pre-load a model into memory"""
    from api.services import chat

    try:
        success = await chat.preload_model(model, keep_alive, source=source)

        if success:
            data = {
                "status": "success",
                "model": model,
                "keep_alive": keep_alive,
                "source": source
            }
            return SuccessResponse(
                data=data,
                message=f"Model '{model}' pre-loaded successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error_code=ErrorCode.INTERNAL_ERROR,
                    message=f"Failed to pre-load model '{model}'"
                ).model_dump()
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to preload model: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to preload model"
            ).model_dump()
        )


@router.post(
    "/models/unload/{model_name}",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="chat_unload_model"
)
async def unload_model_endpoint(
    request: Request,
    model_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Unload a specific model from memory"""
    from api.services import chat

    try:
        success = await chat.unload_model(model_name)

        if success:
            data = {
                "status": "unloaded",
                "model": model_name
            }
            return SuccessResponse(
                data=data,
                message=f"Model '{model_name}' unloaded successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error_code=ErrorCode.INTERNAL_ERROR,
                    message=f"Failed to unload model '{model_name}'"
                ).model_dump()
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unload model: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to unload model"
            ).model_dump()
        )
