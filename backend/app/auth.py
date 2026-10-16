import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from pydantic import BaseModel, EmailStr, Field
from pwdlib import PasswordHash
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from .database import get_db
from .models import AuditEvent, OtpChallenge, User
from .otp_delivery import OtpDeliveryError, send_email_otp

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

password_hash = PasswordHash.recommended()

JWT_SECRET_KEY = os.environ.get("CLAIMBRIDGE_JWT_SECRET")
if not JWT_SECRET_KEY or len(JWT_SECRET_KEY.encode("utf-8")) < 32:
    raise RuntimeError(
        "CLAIMBRIDGE_JWT_SECRET must be configured with at least 32 bytes."
    )
TOKEN_EXPIRY_SECONDS = 86400 * 7  # 7 days
SUPPORTED_ROLES = {"claimant", "claims_officer"}
OTP_TTL = timedelta(minutes=10)
OTP_RATE_WINDOW = timedelta(hours=1)
OTP_MAX_REQUESTS = 5
OTP_MAX_ATTEMPTS = 5


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
    """
    if not token:
        return None

    parts = token.split(".")
    if len(parts) != 3:
        return None

    header_b64, payload_b64, sig_b64 = parts
    try:
        header = json.loads(_b64decode(header_b64).decode("utf-8"))
        if header.get("alg") != "HS256" or header.get("typ") != "JWT":
            return None

        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(
            JWT_SECRET_KEY.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()
        actual_sig = _b64decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload_json = _b64decode(payload_b64).decode("utf-8")
        payload = json.loads(payload_json)

        if not isinstance(payload, dict):
            return None
        if not isinstance(payload.get("sub"), str):
            return None
        if not isinstance(payload.get("exp"), (int, float)):
            return None
        if payload["exp"] <= time.time():
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

    if (
        user.role not in SUPPORTED_ROLES
        or user.account_status != "active"
        or not user.email_verified_at
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not active for the current role system.",
        )

    if user.role == "claims_officer" and (
        not user.organization_verified_at or not (user.organization or "").strip()
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A trusted TPA organization authorization is required.",
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


def require_claimant(user: User = Depends(get_current_user)) -> User:
    if user.role != "claimant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires the claimant role.",
        )
    return user


def require_claims_officer(user: User = Depends(get_current_user)) -> User:
    if user.role != "claims_officer" or not (user.organization or "").strip():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires an organization-authorized claims officer.",
        )
    return user


def require_document_reader(user: User = Depends(get_current_user)) -> User:
    if user.role == "claimant":
        return user
    if user.role == "claims_officer" and (user.organization or "").strip():
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Document access requires an active claimant or organization-authorized claims officer.",
    )


# =========================================================
# REQUEST / RESPONSE SCHEMAS
# =========================================================

class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str = Field(min_length=8, max_length=20, pattern=r"^\+?[0-9]{8,15}$")
    password: str = Field(min_length=12, max_length=128)


class TpaRegistrationRequest(RegisterRequest):
    organization: str = Field(min_length=2, max_length=150)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class VerifyEmailRequest(BaseModel):
    challenge_id: uuid.UUID
    code: str = Field(pattern=r"^[0-9]{6}$")


class ResendOtpRequest(BaseModel):
    email: EmailStr


# =========================================================
# AUTH ROUTES
# =========================================================

def _fingerprint(value: str, context: str) -> str:
    return hmac.new(
        JWT_SECRET_KEY.encode("utf-8"),
        f"{context}:{value}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _create_email_challenge(
    db: Session,
    user: User,
    request: Request,
    purpose: str,
) -> uuid.UUID:
    now = datetime.utcnow()
    recipient_hash = _fingerprint(user.email.lower(), "recipient")
    requester_ip = request.client.host if request.client else "unknown"
    requester_hash = _fingerprint(requester_ip, "requester")
    recent_count = (
        db.query(OtpChallenge)
        .filter(
            OtpChallenge.created_at >= now - OTP_RATE_WINDOW,
            or_(
                OtpChallenge.recipient_hash == recipient_hash,
                OtpChallenge.requester_hash == requester_hash,
            ),
        )
        .count()
    )
    if recent_count >= OTP_MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verification requests. Try again later.",
        )

    for previous in (
        db.query(OtpChallenge)
        .filter(
            OtpChallenge.user_id == user.id,
            OtpChallenge.purpose == purpose,
            OtpChallenge.consumed_at.is_(None),
        )
        .all()
    ):
        previous.consumed_at = now

    challenge_id = uuid.uuid4()
    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge = OtpChallenge(
        id=challenge_id,
        user_id=user.id,
        purpose=purpose,
        recipient_hash=recipient_hash,
        requester_hash=requester_hash,
        code_digest=_fingerprint(f"{challenge_id}:{code}", "otp"),
        attempts=0,
        expires_at=now + OTP_TTL,
        created_at=now,
    )
    db.add(challenge)
    db.add(
        AuditEvent(
            event_type="otp_email_requested",
            actor_user_id=user.id,
            details={"purpose": purpose, "channel": "email"},
        )
    )
    db.flush()
    send_email_otp(user.email, code, "account activation")
    return challenge_id


def _registration_response(user: User, challenge_id: uuid.UUID) -> dict:
    return {
        "message": "Verification email accepted by the configured provider.",
        "user_id": str(user.id),
        "email": user.email,
        "challenge_id": str(challenge_id),
        "verification_required": True,
    }


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
            detail="Invalid email or password",
        )

    if not password_hash.verify(
        login_data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    if (
        user.role not in SUPPORTED_ROLES
        or user.account_status != "active"
        or not user.email_verified_at
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not activated or has not been explicitly mapped to a supported role.",
        )
    if user.role == "claims_officer" and (
        not user.organization_verified_at or not (user.organization or "").strip()
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Claims officer access requires trusted TPA organization authorization.",
        )

    token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        role=user.role,
        portal=user.portal or ("TPA" if user.role == "claims_officer" else "Claimant"),
        organization=user.organization or "",
    )

    return {
        "message": "Login successful",
        "token": token,
        "user_id": str(user.id),
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "portal": user.portal or ("TPA" if user.role == "claims_officer" else "Claimant"),
        "organization": user.organization or "",
    }


@router.post("/register")
def register_user(
    user_data: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    existing_user = (
        db.query(User)
        .filter(func.lower(User.email) == user_data.email.lower())
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Email already registered",
        )

    new_user = User(
        full_name=user_data.full_name.strip(),
        email=user_data.email.lower(),
        phone=user_data.phone,
        role="claimant",
        portal="Claimant",
        account_status="pending_email_verification",
        password_hash=password_hash.hash(user_data.password),
    )

    try:
        db.add(new_user)
        db.flush()
        challenge_id = _create_email_challenge(
            db,
            new_user,
            request,
            "claimant_registration",
        )
        db.commit()
    except OtpDeliveryError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return _registration_response(new_user, challenge_id)


@router.post("/register/tpa", status_code=status.HTTP_202_ACCEPTED)
def register_tpa_applicant(
    user_data: TpaRegistrationRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    existing_user = (
        db.query(User)
        .filter(func.lower(User.email) == user_data.email.lower())
        .first()
    )
    if existing_user:
        raise HTTPException(status_code=409, detail="Email already registered")

    applicant = User(
        full_name=user_data.full_name.strip(),
        email=user_data.email.lower(),
        phone=user_data.phone,
        role="claimant",
        portal="TPA",
        organization=user_data.organization.strip(),
        account_status="pending_tpa_provisioning",
        password_hash=password_hash.hash(user_data.password),
    )
    try:
        db.add(applicant)
        db.flush()
        challenge_id = _create_email_challenge(
            db,
            applicant,
            request,
            "tpa_contact_verification",
        )
        db.commit()
    except OtpDeliveryError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return {
        **_registration_response(applicant, challenge_id),
        "message": "Contact email accepted by the configured provider; TPA organization authorization is still required.",
        "organization_authorization_required": True,
    }


@router.post("/verify-email")
def verify_email(
    verification: VerifyEmailRequest,
    db: Session = Depends(get_db),
):
    challenge = (
        db.query(OtpChallenge)
        .filter(OtpChallenge.id == verification.challenge_id)
        .with_for_update()
        .first()
    )
    now = datetime.utcnow()
    if (
        not challenge
        or challenge.purpose not in {
            "claimant_registration",
            "tpa_contact_verification",
            "legacy_account_mapping",
        }
        or challenge.consumed_at is not None
        or challenge.expires_at <= now
        or challenge.attempts >= OTP_MAX_ATTEMPTS
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code is invalid, expired, or already used.",
        )

    expected_digest = _fingerprint(
        f"{challenge.id}:{verification.code}",
        "otp",
    )
    if not hmac.compare_digest(challenge.code_digest, expected_digest):
        challenge.attempts += 1
        if challenge.attempts >= OTP_MAX_ATTEMPTS:
            challenge.consumed_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code is invalid, expired, or already used.",
        )

    user = db.query(User).filter(User.id == challenge.user_id).with_for_update().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification account no longer exists.")

    challenge.consumed_at = now
    user.email_verified_at = now
    if user.account_status == "pending_email_verification" and user.role == "claimant":
        user.account_status = "active"
    db.add(
        AuditEvent(
            event_type="email_verified",
            actor_user_id=user.id,
            details={"channel": "email", "purpose": challenge.purpose},
        )
    )
    db.commit()

    if user.account_status != "active":
        return {
            "verified": True,
            "activated": False,
            "message": "Contact verified. Trusted TPA organization authorization is still required.",
        }

    token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        role=user.role,
        portal=user.portal or "Claimant",
        organization=user.organization or "",
    )
    return {
        "verified": True,
        "activated": True,
        "token": token,
        "user_id": str(user.id),
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "portal": user.portal or "Claimant",
        "organization": user.organization or "",
    }


@router.post("/otp/resend")
def resend_email_otp(
    resend: ResendOtpRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(func.lower(User.email) == resend.email.lower())
        .first()
    )
    if not user or user.email_verified_at or user.account_status not in {
        "pending_email_verification",
        "pending_tpa_provisioning",
        "pending_role_mapping",
    }:
        return {
            "message": "If the account is eligible, a verification email will be sent.",
        }

    try:
        _create_email_challenge(
            db,
            user,
            request,
            "claimant_registration"
            if user.account_status == "pending_email_verification"
            else "legacy_account_mapping"
            if user.account_status == "pending_role_mapping"
            else "tpa_contact_verification",
        )
        db.commit()
    except OtpDeliveryError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return {
        "message": "If the account is eligible, a verification email will be sent.",
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
        "phone": current_user.phone,
        "role": current_user.role,
        "portal": current_user.portal or "Claimant",
        "organization": current_user.organization or "",
    }