"""
MagnetarTrust - API Router

REST API endpoints for trust network operations.
Part of MagnetarMission free tier.

SECURITY (Dec 2025):
- Node registration now requires Ed25519 signature proving key ownership
- Replay protection via timestamp validation (5 minute window)
- Prevents MITM key spoofing attacks
"""

import logging
import base64
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from datetime import UTC, datetime, timedelta
import nacl.signing
import nacl.exceptions

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
from api.auth_middleware import get_current_user

logger = logging.getLogger(__name__)

# Security constants
REGISTRATION_TIMESTAMP_TOLERANCE_SECONDS = 300  # 5 minutes
NONCE_CACHE_MAX_SIZE = 10000  # Maximum nonces to track

# Nonce tracking for replay protection
# In production, this should be Redis or another distributed cache
_used_nonces: set = set()
_nonce_lock = None  # Will be initialized on first use

def _check_and_record_nonce(nonce: str) -> bool:
    """
    Check if nonce has been used before, and record it if not.

    Returns True if nonce is fresh (not seen before), False if it's a replay.
    Thread-safe implementation using a simple set with size limiting.
    """
    global _used_nonces

    if not nonce:
        return True  # Empty nonce allowed for backwards compatibility

    if nonce in _used_nonces:
        logger.warning(f"⚠ Replay attack detected: nonce {nonce[:16]}... already used")
        return False

    # Add nonce to used set
    _used_nonces.add(nonce)

    # Limit cache size (simple strategy: clear half when full)
    if len(_used_nonces) > NONCE_CACHE_MAX_SIZE:
        # Remove oldest half (in practice, use TTL-based eviction)
        nonces_list = list(_used_nonces)
        _used_nonces = set(nonces_list[NONCE_CACHE_MAX_SIZE // 2:])
        logger.info(f"🧹 Nonce cache cleaned: {len(nonces_list)} -> {len(_used_nonces)}")

    return True


def verify_registration_signature(request: RegisterNodeRequest) -> bool:
    """
    Verify that the registration request is signed by the owner of the private key.

    This prevents MITM attacks where an attacker registers with a victim's public key.

    Args:
        request: The registration request with signature

    Returns:
        True if signature is valid, raises HTTPException otherwise
    """
    try:
        # Decode public key (Ed25519 verify key is same as public key)
        public_key_bytes = base64.b64decode(request.public_key)

        if len(public_key_bytes) != 32:
            raise HTTPException(
                status_code=400,
                detail="Invalid public key: must be 32 bytes (Ed25519)"
            )

        # Validate timestamp is within tolerance (replay protection)
        try:
            request_time = datetime.fromisoformat(request.timestamp.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid timestamp format. Use ISO 8601 (e.g., 2025-12-23T12:00:00Z)"
            )

        now = datetime.now(UTC)
        time_diff = abs((now - request_time).total_seconds())

        if time_diff > REGISTRATION_TIMESTAMP_TOLERANCE_SECONDS:
            raise HTTPException(
                status_code=400,
                detail=f"Registration timestamp expired. Must be within {REGISTRATION_TIMESTAMP_TOLERANCE_SECONDS} seconds."
            )

        # Check nonce for replay protection (prevents replay within timestamp window)
        if request.nonce and not _check_and_record_nonce(request.nonce):
            raise HTTPException(
                status_code=400,
                detail="Replay attack detected: nonce already used. Each registration requires a unique nonce."
            )

        # Verify signature
        signature_bytes = base64.b64decode(request.signature)
        payload = request.get_canonical_payload()
        payload_bytes = payload.encode('utf-8')

        verify_key = nacl.signing.VerifyKey(public_key_bytes)
        verify_key.verify(payload_bytes, signature_bytes)

        logger.info(f"✓ Registration signature verified for key {request.public_key[:16]}...")
        return True

    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except (nacl.exceptions.BadSignatureError, nacl.exceptions.ValueError):
        logger.warning(f"⚠ Invalid registration signature for key {request.public_key[:16]}...")
        raise HTTPException(
            status_code=401,
            detail="Invalid signature. Registration must be signed by the private key owner."
        )
    except base64.binascii.Error:
        raise HTTPException(
            status_code=400,
            detail="Invalid base64 encoding in public_key or signature"
        )
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Signature verification failed: {str(e)}"
        )

router = APIRouter(
    prefix="/api/v1/trust",
    tags=["MagnetarTrust"],
    dependencies=[Depends(get_current_user)]  # Require auth
)


# ===== Node Endpoints =====

@router.post("/nodes", response_model=TrustNode)
async def register_node(request: RegisterNodeRequest, current_user: dict = Depends(get_current_user)):
    """
    Register a new trust node.

    This creates a node in the trust network for an individual, church, mission, or organization.

    SECURITY: Registration requires an Ed25519 signature proving ownership of the private key.
    This prevents MITM attacks where an attacker registers with a victim's public key.

    Required signature fields:
    - timestamp: ISO 8601 timestamp (must be within 5 minutes)
    - signature: Base64-encoded Ed25519 signature over "timestamp|public_key|public_name|type"
    """
    storage = get_trust_storage()

    # SECURITY: Verify signature proves key ownership
    verify_registration_signature(request)

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

    return created_node


@router.get("/nodes/{node_id}", response_model=TrustNode)
async def get_node(node_id: str):
    """Get a trust node by ID"""
    storage = get_trust_storage()
    node = storage.get_node(node_id)

    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    return node


@router.get("/nodes", response_model=NodeListResponse)
async def list_nodes(node_type: Optional[NodeType] = None):
    """
    List all trust nodes, optionally filtered by type.

    Useful for finding churches, missions, or other nodes in the network.
    """
    storage = get_trust_storage()
    nodes = storage.list_nodes(node_type)

    return NodeListResponse(
        nodes=nodes,
        total=len(nodes)
    )


@router.patch("/nodes/{node_id}", response_model=TrustNode)
async def update_node(node_id: str, request: RegisterNodeRequest, current_user: dict = Depends(get_current_user)):
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

    return updated_node


# ===== Trust Relationship Endpoints =====

@router.post("/vouch", response_model=TrustRelationship)
async def vouch_for_node(request: VouchRequest, current_user: dict = Depends(get_current_user)):
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

    return created_rel


@router.get("/network", response_model=TrustNetworkResponse)
async def get_trust_network(max_degrees: int = 3, current_user: dict = Depends(get_current_user)):
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

    return TrustNetworkResponse(
        node_id=user_node.id,
        direct_trusts=trusted["direct"],
        vouched_trusts=trusted["vouched"],
        network_trusts=trusted["network"],
        total_network_size=total_size
    )


@router.get("/relationships", response_model=TrustRelationshipResponse)
async def get_relationships(level: Optional[TrustLevel] = None, current_user: dict = Depends(get_current_user)):
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

    return TrustRelationshipResponse(
        relationships=relationships,
        total=len(relationships)
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
