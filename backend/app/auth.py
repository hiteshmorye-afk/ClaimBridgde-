import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, EmailStr
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from .database import get_db
from .models import User

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

password_hash = PasswordHash.recommended()

JWT_SECRET_KEY = os.environ.get("CLAIMBRIDGE_JWT_SECRET", "claimbridge-secure-signing-secret-key-2026")
TOKEN_EXPIRY_SECONDS = 86400 * 7  # 7 days


# =========================================================
# TOKEN HELPERS (HMAC-SHA256 Signed Tokens)
# =========================================================

def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding and padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode("utf-8"))


def create_access_token(
    user_id: str,
    email: str,
    role: str,
    portal: str = "Hospital",
    organization: Optional[str] = None,
    expires_in: int = TOKEN_EXPIRY_SECONDS,
) -> str:
    """
    Generate a cryptographically signed HMAC-SHA256 JWT-compatible token.
    """
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "portal": portal,
        "organization": organization or "",
        "iat": int(time.time()),
        "exp": int(time.time()) + expires_in,
    }

    header_bytes = _b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_bytes = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_bytes}.{payload_bytes}".encode("utf-8")

    signature = hmac.new(
        JWT_SECRET_KEY.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    sig_b64 = _b64encode(signature)

    return f"{header_bytes}.{payload_bytes}.{sig_b64}"


def verify_access_token(token: str) -> Optional[dict]:
    """
    Verify signature and expiry of token.
    Also handles legacy test format 'token_<uuid>'.
    """
    if not token:
        return None

    # Support legacy test format 'token_<uuid>'
    if token.startswith("token_"):
        raw_id = token.replace("token_", "").strip()
        try:
            uuid.UUID(raw_id)
            return {"sub": raw_id, "legacy": True}
        except ValueError:
            return None

    parts = token.split(".")
    if len(parts) != 3:
        return None

    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

    expected_sig = hmac.new(
        JWT_SECRET_KEY.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()

    try:
        actual_sig = _b64decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload_json = _b64decode(payload_b64).decode("utf-8")
        payload = json.loads(payload_json)

        # Check expiry
        if payload.get("exp") and payload["exp"] < time.time():
            return None

        return payload
    except Exception:
        return None


# =========================================================
# FASTAPI DEPENDENCIES
# =========================================================

def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Extract and verify user from Bearer token if present.
    Returns None if no token provided or token is invalid.
    """
    if not authorization:
        return None

    token = authorization
    if authorization.startswith("Bearer "):
        token = authorization[7:].strip()

    payload = verify_access_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        return None

    return db.query(User).filter(User.id == user_uuid).first()


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """
    Strict authentication dependency.
    Raises HTTP 401 if token is missing or invalid.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization
    if authorization.startswith("Bearer "):
        token = authorization[7:].strip()

    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    try:
        user_uuid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed user ID in token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with token not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_roles(*allowed_roles: str):
    """
    Dependency factory to check user roles.
    """
    def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Action requires role in {allowed_roles}, but user has role '{user.role}'.",
            )
        return user
    return role_checker


def require_tpa_reviewer(user: User = Depends(get_current_user)) -> User:
    """
    Strictly verifies that user is an authorized TPA reviewer or Admin.
    Hospital coordinators calling TPA actions receive HTTP 403.
    """
    if user.role == "Coordinator" or user.portal == "Hospital":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hospital coordinators are not authorized to adjudicate, approve, reject, or escalate claims.",
        )

    if user.role not in {"Reviewer", "Admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Unauthorized: TPA actions require 'Reviewer' or 'Admin' role (current: '{user.role}').",
        )

    return user


# =========================================================
# REQUEST / RESPONSE SCHEMAS
# =========================================================

class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: str = "Coordinator"
    portal: str = "Hospital"
    organization: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# =========================================================
# AUTH ROUTES
# =========================================================

@router.post("/login")
def login_user(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.email == login_data.email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    if not user.password_hash:
        raise HTTPException(
            status_code=401,
            detail="Password is not configured for this user account",
        )

    if not password_hash.verify(
        login_data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        role=user.role,
        portal=user.portal or "Hospital",
        organization=user.organization or "",
    )

    return {
        "message": "Login successful",
        "token": token,
        "user_id": str(user.id),
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "portal": user.portal or "Hospital",
        "organization": user.organization or "",
    }


@router.post("/register")
def register_user(
    user_data: RegisterRequest,
    db: Session = Depends(get_db),
):
    existing_user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )

    hashed_password = password_hash.hash(user_data.password)

    new_user = User(
        full_name=user_data.full_name,
        email=user_data.email,
        role=user_data.role,
        portal=user_data.portal,
        organization=user_data.organization,
        password_hash=hashed_password,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(
        user_id=str(new_user.id),
        email=new_user.email,
        role=new_user.role,
        portal=new_user.portal or "Hospital",
        organization=new_user.organization or "",
    )

    return {
        "message": "User registered successfully",
        "token": token,
        "user_id": str(new_user.id),
        "email": new_user.email,
        "role": new_user.role,
        "portal": new_user.portal,
        "organization": new_user.organization,
    }


@router.get("/me")
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """
    Return currently authenticated user profile.
    """
    return {
        "id": str(current_user.id),
        "full_name": current_user.full_name,
        "email": current_user.email,
        "role": current_user.role,
        "portal": current_user.portal or "Hospital",
        "organization": current_user.organization or "",
    }


def seed_default_users(db: Session):
    """
    Ensure standard portal testing users exist in Neon PostgreSQL.
    """
    default_users = [
        {
            "full_name": "Hospital Coordinator Chong Hua",
            "email": "coordinator@chonghua.com",
            "role": "Coordinator",
            "portal": "Hospital",
            "organization": "Chong Hua Hospital",
            "password": "Password#123",
        },
        {
            "full_name": "Hospital Coordinator Apollo",
            "email": "coordinator@apollo.com",
            "role": "Coordinator",
            "portal": "Hospital",
            "organization": "Apollo Hospital",
            "password": "Password#123",
        },
        {
            "full_name": "TPA Reviewer Pacific",
            "email": "reviewer@pacific.com",
            "role": "Reviewer",
            "portal": "TPA",
            "organization": "Pacific Healthcare TPA",
            "password": "Password#123",
        },
        {
            "full_name": "TPA Reviewer Star Health",
            "email": "reviewer@starhealth.com",
            "role": "Reviewer",
            "portal": "TPA",
            "organization": "Star Health Insurance",
            "password": "Password#123",
        },
        {
            "full_name": "System Administrator",
            "email": "admin@claimbridge.com",
            "role": "Admin",
            "portal": "TPA",
            "organization": "ClaimBridge Global",
            "password": "Password#123",
        },
    ]

    for u in default_users:
        existing = db.query(User).filter(User.email == u["email"]).first()
        if not existing:
            user = User(
                full_name=u["full_name"],
                email=u["email"],
                role=u["role"],
                portal=u["portal"],
                organization=u["organization"],
                password_hash=password_hash.hash(u["password"]),
            )
            db.add(user)
        else:
            if not existing.organization or not existing.portal:
                existing.organization = u["organization"]
                existing.portal = u["portal"]
    db.commit()