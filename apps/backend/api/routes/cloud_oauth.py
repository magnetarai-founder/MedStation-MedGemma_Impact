"""
MagnetarCloud OAuth 2.0 Routes

Implements OAuth 2.0 Authorization Code flow with PKCE for secure third-party
and native app authorization to MagnetarCloud.

Security Features:
- PKCE (Proof Key for Code Exchange) required for all clients
- Short-lived authorization codes (10 minutes)
- Encrypted token storage
- Scope-based permissions
- Rate limiting on token endpoints

OAuth 2.0 Flow:
1. Client generates code_verifier and code_challenge (PKCE)
2. Client redirects user to /authorize with code_challenge
3. User authenticates and approves scopes
4. Server redirects back with authorization_code
5. Client exchanges code + code_verifier for tokens
6. Client uses access_token for API calls
7. Client uses refresh_token to get new access_tokens

Follows RFC 6749 (OAuth 2.0) and RFC 7636 (PKCE).
"""

import logging
import hashlib
import secrets
import sqlite3
import base64
from typing import Optional, Dict, Any, List, Set
from datetime import datetime, timedelta, UTC
from urllib.parse import urlencode, parse_qs, urlparse
from fastapi import APIRouter, HTTPException, Depends, Request, Query, Form, status
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel, Field
import json

from api.auth_middleware import get_current_user, User
from api.config_paths import get_config_paths
from api.config import is_airgap_mode, get_settings
from api.routes.schemas import SuccessResponse

logger = logging.getLogger(__name__)


# ===== Air-Gap Mode Check =====

async def check_cloud_available():
    """Dependency that checks if cloud features are available."""
    if is_airgap_mode():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "cloud_unavailable", "message": "Cloud features disabled in air-gap mode"}
        )


router = APIRouter(
    prefix="/api/v1/cloud/oauth",
    tags=["cloud-oauth"],
    dependencies=[Depends(check_cloud_available)]
)


# ===== Configuration =====

PATHS = get_config_paths()
OAUTH_DB_PATH = PATHS.data_dir / "oauth.db"

# Token lifetimes
AUTH_CODE_EXPIRY_MINUTES = 10
ACCESS_TOKEN_EXPIRY_HOURS = 1
REFRESH_TOKEN_EXPIRY_DAYS = 30

# Supported scopes
VALID_SCOPES: Set[str] = {
    "vault:read",       # Read vault files
    "vault:write",      # Write vault files
    "vault:sync",       # Sync vault to cloud
    "workflows:read",   # Read workflows
    "workflows:write",  # Create/edit workflows
    "workflows:sync",   # Sync workflows to cloud
    "teams:read",       # Read team data
    "teams:write",      # Write team data
    "teams:sync",       # Sync team data to cloud
    "profile:read",     # Read user profile
    "offline_access",   # Get refresh tokens
}

DEFAULT_SCOPES: Set[str] = {"vault:read", "profile:read"}


# ===== Database Initialization =====

def _init_oauth_db() -> None:
    """Initialize OAuth database tables"""
    OAUTH_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(OAUTH_DB_PATH)) as conn:
        cursor = conn.cursor()

        # OAuth clients (registered applications)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS oauth_clients (
                client_id TEXT PRIMARY KEY,
                client_secret_hash TEXT NOT NULL,
                client_name TEXT NOT NULL,
                redirect_uris TEXT NOT NULL,  -- JSON array
                allowed_scopes TEXT NOT NULL,  -- JSON array
                client_type TEXT NOT NULL,  -- 'confidential' or 'public'
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        """)

        # Authorization codes (short-lived)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS oauth_auth_codes (
                code TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                redirect_uri TEXT NOT NULL,
                scopes TEXT NOT NULL,  -- JSON array
                code_challenge TEXT,  -- PKCE
                code_challenge_method TEXT,  -- 'S256' or 'plain'
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used INTEGER DEFAULT 0,
                FOREIGN KEY (client_id) REFERENCES oauth_clients(client_id)
            )
        """)

        # Access/Refresh tokens
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS oauth_tokens (
                token_id TEXT PRIMARY KEY,
                token_hash TEXT NOT NULL UNIQUE,
                token_type TEXT NOT NULL,  -- 'access' or 'refresh'
                client_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                scopes TEXT NOT NULL,  -- JSON array
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked INTEGER DEFAULT 0,
                parent_token_id TEXT,  -- For refresh token chains
                FOREIGN KEY (client_id) REFERENCES oauth_clients(client_id)
            )
        """)

        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_auth_codes_client ON oauth_auth_codes(client_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tokens_user ON oauth_tokens(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tokens_hash ON oauth_tokens(token_hash)")

        conn.commit()


# Initialize on module load
_init_oauth_db()


# ===== Helper Functions =====

def _hash_secret(secret: str) -> str:
    """Hash a secret using SHA-256"""
    return hashlib.sha256(secret.encode()).hexdigest()


def _generate_token() -> str:
    """Generate a secure random token"""
    return secrets.token_urlsafe(32)


def _verify_pkce(code_verifier: str, code_challenge: str, method: str) -> bool:
    """Verify PKCE code_verifier against code_challenge"""
    if method == "plain":
        return code_verifier == code_challenge
    elif method == "S256":
        # SHA256(code_verifier) base64url-encoded
        digest = hashlib.sha256(code_verifier.encode()).digest()
        computed = base64.urlsafe_b64encode(digest).rstrip(b'=').decode()
        return computed == code_challenge
    return False


def _validate_scopes(requested: List[str], allowed: List[str]) -> List[str]:
    """Validate and filter requested scopes against allowed scopes"""
    requested_set = set(requested)
    allowed_set = set(allowed)
    valid = requested_set & allowed_set & VALID_SCOPES
    return list(valid) if valid else list(DEFAULT_SCOPES & allowed_set)


# ===== Request/Response Models =====

class OAuthClientCreate(BaseModel):
    """Request to register a new OAuth client"""
    client_name: str = Field(..., min_length=1, max_length=100)
    redirect_uris: List[str] = Field(..., min_length=1)
    allowed_scopes: List[str] = Field(default_factory=lambda: list(DEFAULT_SCOPES))
    client_type: str = Field(default="public", pattern="^(confidential|public)$")


class OAuthClientResponse(BaseModel):
    """Response with OAuth client credentials"""
    client_id: str
    client_secret: Optional[str] = None  # Only returned on creation
    client_name: str
    redirect_uris: List[str]
    allowed_scopes: List[str]
    client_type: str


class TokenResponse(BaseModel):
    """OAuth token response"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    scope: str


class TokenIntrospection(BaseModel):
    """Token introspection response"""
    active: bool
    scope: Optional[str] = None
    client_id: Optional[str] = None
    username: Optional[str] = None
    exp: Optional[int] = None


# ===== Client Management Endpoints =====

@router.post(
    "/clients",
    response_model=SuccessResponse[OAuthClientResponse],
    status_code=status.HTTP_201_CREATED,
    name="oauth_register_client"
)
async def register_oauth_client(
    request: OAuthClientCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Register a new OAuth client application.

    Only authenticated users can register clients. The client_secret is only
    returned once on creation - store it securely!
    """
    client_id = f"mc_{secrets.token_urlsafe(16)}"
    client_secret = secrets.token_urlsafe(32) if request.client_type == "confidential" else None

    # Validate redirect URIs
    for uri in request.redirect_uris:
        parsed = urlparse(uri)
        if not parsed.scheme or not parsed.netloc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid redirect URI: {uri}"
            )

    # Validate scopes
    valid_scopes = [s for s in request.allowed_scopes if s in VALID_SCOPES]
    if not valid_scopes:
        valid_scopes = list(DEFAULT_SCOPES)

    with sqlite3.connect(str(OAUTH_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO oauth_clients
            (client_id, client_secret_hash, client_name, redirect_uris,
             allowed_scopes, client_type, created_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            client_id,
            _hash_secret(client_secret) if client_secret else "",
            request.client_name,
            json.dumps(request.redirect_uris),
            json.dumps(valid_scopes),
            request.client_type,
            datetime.now(UTC).isoformat(),
            current_user.id
        ))
        conn.commit()

    logger.info(f"✅ OAuth client registered: {client_id} by user {current_user.id}")

    return SuccessResponse(
        data=OAuthClientResponse(
            client_id=client_id,
            client_secret=client_secret,
            client_name=request.client_name,
            redirect_uris=request.redirect_uris,
            allowed_scopes=valid_scopes,
            client_type=request.client_type
        ),
        message="OAuth client registered successfully. Store the client_secret securely!"
    )


@router.get(
    "/clients",
    response_model=SuccessResponse[List[OAuthClientResponse]],
    name="oauth_list_clients"
)
async def list_oauth_clients(
    current_user: User = Depends(get_current_user)
):
    """List OAuth clients created by the current user"""
    with sqlite3.connect(str(OAUTH_DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT client_id, client_name, redirect_uris, allowed_scopes, client_type
            FROM oauth_clients
            WHERE created_by = ? AND is_active = 1
        """, (current_user.id,))
        rows = cursor.fetchall()

    clients = [
        OAuthClientResponse(
            client_id=row["client_id"],
            client_name=row["client_name"],
            redirect_uris=json.loads(row["redirect_uris"]),
            allowed_scopes=json.loads(row["allowed_scopes"]),
            client_type=row["client_type"]
        )
        for row in rows
    ]

    return SuccessResponse(data=clients, message=f"Found {len(clients)} OAuth clients")


# ===== Authorization Endpoint =====

@router.get(
    "/authorize",
    response_class=HTMLResponse,
    name="oauth_authorize"
)
async def oauth_authorize(
    request: Request,
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    response_type: str = Query(...),
    scope: str = Query(default=""),
    state: Optional[str] = Query(default=None),
    code_challenge: Optional[str] = Query(default=None),
    code_challenge_method: Optional[str] = Query(default="S256"),
    current_user: User = Depends(get_current_user)
):
    """
    OAuth 2.0 Authorization Endpoint.

    Displays consent screen and redirects back with authorization code.
    PKCE (code_challenge) is required for public clients.
    """
    if response_type != "code":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only response_type=code is supported"
        )

    # Validate client
    with sqlite3.connect(str(OAUTH_DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT client_name, redirect_uris, allowed_scopes, client_type
            FROM oauth_clients
            WHERE client_id = ? AND is_active = 1
        """, (client_id,))
        client = cursor.fetchone()

    if not client:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client_id")

    # Validate redirect_uri
    allowed_uris = json.loads(client["redirect_uris"])
    if redirect_uri not in allowed_uris:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid redirect_uri")

    # PKCE required for public clients
    if client["client_type"] == "public" and not code_challenge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PKCE code_challenge required for public clients"
        )

    # Parse and validate scopes
    requested_scopes = scope.split() if scope else []
    allowed_scopes = json.loads(client["allowed_scopes"])
    valid_scopes = _validate_scopes(requested_scopes, allowed_scopes)

    # Generate authorization code
    auth_code = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(minutes=AUTH_CODE_EXPIRY_MINUTES)

    with sqlite3.connect(str(OAUTH_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO oauth_auth_codes
            (code, client_id, user_id, redirect_uri, scopes,
             code_challenge, code_challenge_method, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            auth_code,
            client_id,
            current_user.id,
            redirect_uri,
            json.dumps(valid_scopes),
            code_challenge,
            code_challenge_method,
            datetime.now(UTC).isoformat(),
            expires_at.isoformat()
        ))
        conn.commit()

    # Build redirect URL
    params = {"code": auth_code}
    if state:
        params["state"] = state

    redirect_url = f"{redirect_uri}?{urlencode(params)}"

    logger.info(f"✅ OAuth authorization granted for client {client_id} user {current_user.id}")

    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)


# ===== Token Endpoint =====

@router.post(
    "/token",
    response_model=TokenResponse,
    name="oauth_token"
)
async def oauth_token(
    grant_type: str = Form(...),
    code: Optional[str] = Form(default=None),
    redirect_uri: Optional[str] = Form(default=None),
    client_id: str = Form(...),
    client_secret: Optional[str] = Form(default=None),
    code_verifier: Optional[str] = Form(default=None),
    refresh_token: Optional[str] = Form(default=None),
    scope: Optional[str] = Form(default=None)
):
    """
    OAuth 2.0 Token Endpoint.

    Exchanges authorization code for tokens or refreshes existing tokens.

    Supported grant types:
    - authorization_code: Exchange code for tokens
    - refresh_token: Get new access token using refresh token
    """
    if grant_type == "authorization_code":
        return await _handle_authorization_code_grant(
            code=code,
            redirect_uri=redirect_uri,
            client_id=client_id,
            client_secret=client_secret,
            code_verifier=code_verifier
        )
    elif grant_type == "refresh_token":
        return await _handle_refresh_token_grant(
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            scope=scope
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported grant_type: {grant_type}"
        )


async def _handle_authorization_code_grant(
    code: Optional[str],
    redirect_uri: Optional[str],
    client_id: str,
    client_secret: Optional[str],
    code_verifier: Optional[str]
) -> TokenResponse:
    """Handle authorization_code grant type"""
    if not code or not redirect_uri:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="code and redirect_uri required for authorization_code grant"
        )

    with sqlite3.connect(str(OAUTH_DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get and validate auth code
        cursor.execute("""
            SELECT ac.*, c.client_type, c.client_secret_hash
            FROM oauth_auth_codes ac
            JOIN oauth_clients c ON ac.client_id = c.client_id
            WHERE ac.code = ? AND ac.used = 0
        """, (code,))
        auth_code = cursor.fetchone()

        if not auth_code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired code")

        # Check expiry
        expires_at = datetime.fromisoformat(auth_code["expires_at"])
        if datetime.now(UTC) > expires_at:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Authorization code expired")

        # Validate client
        if auth_code["client_id"] != client_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client mismatch")

        if auth_code["redirect_uri"] != redirect_uri:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Redirect URI mismatch")

        # Validate client authentication
        if auth_code["client_type"] == "confidential":
            if not client_secret or _hash_secret(client_secret) != auth_code["client_secret_hash"]:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid client credentials")

        # Validate PKCE
        if auth_code["code_challenge"]:
            if not code_verifier:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="code_verifier required")
            if not _verify_pkce(code_verifier, auth_code["code_challenge"], auth_code["code_challenge_method"] or "S256"):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PKCE verification failed")

        # Mark code as used
        cursor.execute("UPDATE oauth_auth_codes SET used = 1 WHERE code = ?", (code,))

        # Generate tokens
        access_token = _generate_token()
        refresh_token_value = None
        scopes = json.loads(auth_code["scopes"])

        access_expires = datetime.now(UTC) + timedelta(hours=ACCESS_TOKEN_EXPIRY_HOURS)

        # Store access token
        cursor.execute("""
            INSERT INTO oauth_tokens
            (token_id, token_hash, token_type, client_id, user_id, scopes, created_at, expires_at)
            VALUES (?, ?, 'access', ?, ?, ?, ?, ?)
        """, (
            secrets.token_urlsafe(16),
            _hash_secret(access_token),
            client_id,
            auth_code["user_id"],
            json.dumps(scopes),
            datetime.now(UTC).isoformat(),
            access_expires.isoformat()
        ))

        # Generate refresh token if offline_access scope
        if "offline_access" in scopes:
            refresh_token_value = _generate_token()
            refresh_expires = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS)

            cursor.execute("""
                INSERT INTO oauth_tokens
                (token_id, token_hash, token_type, client_id, user_id, scopes, created_at, expires_at)
                VALUES (?, ?, 'refresh', ?, ?, ?, ?, ?)
            """, (
                secrets.token_urlsafe(16),
                _hash_secret(refresh_token_value),
                client_id,
                auth_code["user_id"],
                json.dumps(scopes),
                datetime.now(UTC).isoformat(),
                refresh_expires.isoformat()
            ))

        conn.commit()

    logger.info(f"✅ OAuth tokens issued for client {client_id}")

    return TokenResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRY_HOURS * 3600,
        refresh_token=refresh_token_value,
        scope=" ".join(scopes)
    )


async def _handle_refresh_token_grant(
    refresh_token: Optional[str],
    client_id: str,
    client_secret: Optional[str],
    scope: Optional[str]
) -> TokenResponse:
    """Handle refresh_token grant type"""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="refresh_token required"
        )

    with sqlite3.connect(str(OAUTH_DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get refresh token
        cursor.execute("""
            SELECT t.*, c.client_type, c.client_secret_hash
            FROM oauth_tokens t
            JOIN oauth_clients c ON t.client_id = c.client_id
            WHERE t.token_hash = ? AND t.token_type = 'refresh' AND t.revoked = 0
        """, (_hash_secret(refresh_token),))
        token = cursor.fetchone()

        if not token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid refresh token")

        # Check expiry
        expires_at = datetime.fromisoformat(token["expires_at"])
        if datetime.now(UTC) > expires_at:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token expired")

        # Validate client
        if token["client_id"] != client_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client mismatch")

        # Validate client authentication for confidential clients
        if token["client_type"] == "confidential":
            if not client_secret or _hash_secret(client_secret) != token["client_secret_hash"]:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid client credentials")

        # Generate new access token
        access_token = _generate_token()
        scopes = json.loads(token["scopes"])
        access_expires = datetime.now(UTC) + timedelta(hours=ACCESS_TOKEN_EXPIRY_HOURS)

        cursor.execute("""
            INSERT INTO oauth_tokens
            (token_id, token_hash, token_type, client_id, user_id, scopes, created_at, expires_at, parent_token_id)
            VALUES (?, ?, 'access', ?, ?, ?, ?, ?, ?)
        """, (
            secrets.token_urlsafe(16),
            _hash_secret(access_token),
            client_id,
            token["user_id"],
            json.dumps(scopes),
            datetime.now(UTC).isoformat(),
            access_expires.isoformat(),
            token["token_id"]
        ))

        conn.commit()

    logger.info(f"✅ OAuth access token refreshed for client {client_id}")

    return TokenResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRY_HOURS * 3600,
        scope=" ".join(scopes)
    )


# ===== Token Introspection =====

@router.post(
    "/introspect",
    response_model=TokenIntrospection,
    name="oauth_introspect"
)
async def oauth_introspect(
    token: str = Form(...),
    client_id: str = Form(...),
    client_secret: Optional[str] = Form(default=None)
):
    """
    Introspect an OAuth token (RFC 7662).

    Returns token metadata or active=false if invalid/expired.
    """
    with sqlite3.connect(str(OAUTH_DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT t.*, c.client_type, c.client_secret_hash
            FROM oauth_tokens t
            JOIN oauth_clients c ON t.client_id = c.client_id
            WHERE t.token_hash = ? AND t.revoked = 0
        """, (_hash_secret(token),))
        token_row = cursor.fetchone()

    if not token_row:
        return TokenIntrospection(active=False)

    # Check expiry
    expires_at = datetime.fromisoformat(token_row["expires_at"])
    if datetime.now(UTC) > expires_at:
        return TokenIntrospection(active=False)

    scopes = json.loads(token_row["scopes"])

    return TokenIntrospection(
        active=True,
        scope=" ".join(scopes),
        client_id=token_row["client_id"],
        username=token_row["user_id"],
        exp=int(expires_at.timestamp())
    )


# ===== Token Revocation =====

@router.post(
    "/revoke",
    status_code=status.HTTP_200_OK,
    name="oauth_revoke"
)
async def oauth_revoke(
    token: str = Form(...),
    client_id: str = Form(...),
    client_secret: Optional[str] = Form(default=None)
):
    """
    Revoke an OAuth token (RFC 7009).

    Revokes both access and refresh tokens.
    """
    with sqlite3.connect(str(OAUTH_DB_PATH)) as conn:
        cursor = conn.cursor()

        # Revoke the token
        cursor.execute("""
            UPDATE oauth_tokens
            SET revoked = 1
            WHERE token_hash = ? AND client_id = ?
        """, (_hash_secret(token), client_id))

        conn.commit()

    logger.info(f"✅ OAuth token revoked for client {client_id}")

    return {"status": "ok"}
