"""
Hot Slots Routes - Model hot slot management for quick switching

Split from models.py for maintainability.
"""

import logging
from fastapi import APIRouter, HTTPException, Request, Depends, status

from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode
from api.errors import http_400, http_500

from api.auth_middleware import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/models/hot-slots",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="chat_get_hot_slots"
)
async def get_hot_slots_endpoint():
    """Get current hot slot assignments (public endpoint)"""
    from api.services import chat

    try:
        slots = await chat.get_hot_slots()
        data = {"hot_slots": slots}
        return SuccessResponse(data=data, message="Hot slots retrieved")
    except Exception as e:
        logger.error(f"Failed to get hot slots: {e}", exc_info=True)
        raise http_500("Failed to get hot slots")


@router.post(
    "/models/hot-slots/{slot_number}",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="chat_assign_to_hot_slot"
)
async def assign_to_hot_slot_endpoint(
    request: Request,
    slot_number: int,
    model_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Assign a model to a specific hot slot"""
    from api.services import chat

    if slot_number not in [1, 2, 3, 4]:
        raise http_400("Slot number must be between 1 and 4")

    try:
        current_slots = await chat.get_hot_slots()
        if current_slots[slot_number] is not None:
            raise http_400(f"Slot {slot_number} is already occupied by {current_slots[slot_number]}")

        result = await chat.assign_to_hot_slot(slot_number, model_name)
        return SuccessResponse(
            data=result,
            message=f"Model '{model_name}' assigned to slot {slot_number}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign to hot slot: {e}", exc_info=True)
        raise http_500("Failed to assign to hot slot")


@router.delete(
    "/models/hot-slots/{slot_number}",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="chat_remove_from_hot_slot"
)
async def remove_from_hot_slot_endpoint(
    request: Request,
    slot_number: int,
    current_user: dict = Depends(get_current_user)
):
    """Remove a model from a specific hot slot"""
    from api.services import chat

    if slot_number not in [1, 2, 3, 4]:
        raise http_400("Slot number must be between 1 and 4")

    try:
        current_slots = await chat.get_hot_slots()
        if current_slots[slot_number] is None:
            raise http_400(f"Slot {slot_number} is already empty")

        result = await chat.remove_from_hot_slot(slot_number)
        return SuccessResponse(
            data=result,
            message=f"Slot {slot_number} cleared successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove from hot slot: {e}", exc_info=True)
        raise http_500("Failed to remove from hot slot")


@router.post(
    "/models/load-hot-slots",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="chat_load_hot_slot_models"
)
async def load_hot_slot_models_endpoint(
    request: Request,
    keep_alive: str = "1h",
    current_user: dict = Depends(get_current_user)
):
    """Load all hot slot models into memory"""
    from api.services import chat

    try:
        result = await chat.load_hot_slot_models(keep_alive)
        return SuccessResponse(data=result, message="Hot slot models loaded")
    except Exception as e:
        logger.error(f"Failed to load hot slots: {e}", exc_info=True)
        raise http_500("Failed to load hot slots")
