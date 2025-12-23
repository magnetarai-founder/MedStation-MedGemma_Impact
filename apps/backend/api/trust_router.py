"""
MagnetarTrust - API Router

REST API endpoints for trust network operations.
Part of MagnetarMission free tier.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from datetime import UTC, datetime

from api.trust_models import (
    TrustNode,
    TrustRelationship,
    RegisterNodeRequest,
    VouchRequest,
    TrustNetworkResponse,
    NodeListResponse,
    TrustRelationshipResponse,
    NodeType,
    TrustLevel
)
from api.trust_storage import get_trust_storage
from api.routes.schemas import SuccessResponse
from auth_middleware import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/trust",
    tags=["MagnetarTrust"],
    dependencies=[Depends(get_current_user)]  # Require auth
)


# ===== Node Endpoints =====

@router.post("/nodes", response_model=SuccessResponse[TrustNode])
async def register_node(request: RegisterNodeRequest, current_user: dict = Depends(get_current_user)) -> SuccessResponse[TrustNode]:
    """
    Register a new trust node.

    This creates a node in the trust network for an individual, church, mission, or organization.
    """
    storage = get_trust_storage()

    # Check if node with this public key already exists
    existing = storage.get_node_by_public_key(request.public_key)
    if existing:
        raise HTTPException(status_code=409, detail="Node with this public key already exists")

    # Create node
    node = TrustNode(
        public_key=request.public_key,
        public_name=request.public_name,
        alias=request.alias,
        type=request.type,
        bio=request.bio,
        location=request.location,
        display_mode=request.display_mode
    )

    created_node = storage.create_node(node)
    logger.info(f"✓ Node registered: {created_node.id} ({created_node.public_name})")

    return SuccessResponse(data=created_node, message="Node registered successfully")


@router.get("/nodes/{node_id}", response_model=SuccessResponse[TrustNode])
async def get_node(node_id: str) -> SuccessResponse[TrustNode]:
    """Get a trust node by ID"""
    storage = get_trust_storage()
    node = storage.get_node(node_id)

    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    return SuccessResponse(data=node, message="Node retrieved successfully")


@router.get("/nodes", response_model=SuccessResponse[NodeListResponse])
async def list_nodes(node_type: Optional[NodeType] = None) -> SuccessResponse[NodeListResponse]:
    """
    List all trust nodes, optionally filtered by type.

    Useful for finding churches, missions, or other nodes in the network.
    """
    storage = get_trust_storage()
    nodes = storage.list_nodes(node_type)

    return SuccessResponse(
        data=NodeListResponse(nodes=nodes, total=len(nodes)),
        message=f"Found {len(nodes)} node(s)"
    )


@router.patch("/nodes/{node_id}", response_model=SuccessResponse[TrustNode])
async def update_node(node_id: str, request: RegisterNodeRequest, current_user: dict = Depends(get_current_user)) -> SuccessResponse[TrustNode]:
    """Update a trust node's information"""
    storage = get_trust_storage()
    node = storage.get_node(node_id)

    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    # Update fields
    node.public_name = request.public_name
    node.alias = request.alias
    node.display_mode = request.display_mode
    node.bio = request.bio
    node.location = request.location
    node.last_seen = datetime.now(UTC).isoformat()

    updated_node = storage.update_node(node)
    logger.info(f"✓ Node updated: {node_id}")

    return SuccessResponse(data=updated_node, message="Node updated successfully")


# ===== Trust Relationship Endpoints =====

@router.post("/vouch", response_model=SuccessResponse[TrustRelationship])
async def vouch_for_node(request: VouchRequest, current_user: dict = Depends(get_current_user)) -> SuccessResponse[TrustRelationship]:
    """
    Vouch for another node (create a trust relationship).

    This is how trust spreads through the network. Churches vouch for members,
    churches vouch for other churches, etc.
    """
    storage = get_trust_storage()

    # Get current user's node
    user_node = storage.get_node_by_public_key(current_user.get("public_key"))
    if not user_node:
        raise HTTPException(status_code=404, detail="Your node not found. Please register first.")

    # Verify target node exists
    target_node = storage.get_node(request.target_node_id)
    if not target_node:
        raise HTTPException(status_code=404, detail="Target node not found")

    # Check if relationship already exists
    existing_rels = storage.get_relationships(user_node.id)
    if any(rel.to_node == request.target_node_id for rel in existing_rels):
        raise HTTPException(status_code=409, detail="You already trust this node")

    # Create trust relationship
    relationship = TrustRelationship(
        from_node=user_node.id,
        to_node=request.target_node_id,
        level=request.level,
        vouched_by=user_node.id if request.level == TrustLevel.VOUCHED else None,
        note=request.note
    )

    created_rel = storage.create_relationship(relationship)
    logger.info(f"✓ Vouch created: {user_node.public_name} → {target_node.public_name}")

    return SuccessResponse(data=created_rel, message="Vouch created successfully")


@router.get("/network", response_model=SuccessResponse[TrustNetworkResponse])
async def get_trust_network(max_degrees: int = 3, current_user: dict = Depends(get_current_user)) -> SuccessResponse[TrustNetworkResponse]:
    """
    Get your complete trust network.

    Returns all nodes you trust, up to max_degrees of separation:
    - Direct: Nodes you directly trust
    - Vouched: Nodes vouched for by you
    - Network: Nodes 2-3 degrees out

    This is the foundation for request broadcasting and resource sharing.
    """
    storage = get_trust_storage()

    # Get current user's node
    user_node = storage.get_node_by_public_key(current_user.get("public_key"))
    if not user_node:
        raise HTTPException(status_code=404, detail="Your node not found. Please register first.")

    # Get trusted nodes
    trusted = storage.get_trusted_nodes(user_node.id, max_degrees)

    total_size = len(trusted["direct"]) + len(trusted["vouched"]) + len(trusted["network"])

    network_response = TrustNetworkResponse(
        node_id=user_node.id,
        direct_trusts=trusted["direct"],
        vouched_trusts=trusted["vouched"],
        network_trusts=trusted["network"],
        total_network_size=total_size
    )
    return SuccessResponse(data=network_response, message="Trust network retrieved successfully")


@router.get("/relationships", response_model=SuccessResponse[TrustRelationshipResponse])
async def get_relationships(level: Optional[TrustLevel] = None, current_user: dict = Depends(get_current_user)) -> SuccessResponse[TrustRelationshipResponse]:
    """
    Get all trust relationships for the current user.

    Optionally filter by trust level (direct, vouched, network).
    """
    storage = get_trust_storage()

    # Get current user's node
    user_node = storage.get_node_by_public_key(current_user.get("public_key"))
    if not user_node:
        raise HTTPException(status_code=404, detail="Your node not found. Please register first.")

    relationships = storage.get_relationships(user_node.id, level)

    return SuccessResponse(
        data=TrustRelationshipResponse(relationships=relationships, total=len(relationships)),
        message=f"Found {len(relationships)} relationship(s)"
    )


# ===== Public Endpoints (no auth required) =====

# Create a public router for health check
public_router = APIRouter(
    prefix="/api/v1/trust",
    tags=["MagnetarTrust (Public)"]
)

@public_router.get("/health")
async def trust_health() -> Dict[str, Any]:
    """Health check for MagnetarTrust service (public endpoint)"""
    storage = get_trust_storage()
    all_nodes = storage.list_nodes()

    return {
        "status": "ok",
        "service": "MagnetarTrust",
        "total_nodes": len(all_nodes),
        "timestamp": datetime.now(UTC).isoformat()
    }
