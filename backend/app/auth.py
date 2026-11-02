import base64
import hashlib
import hmac
import json
import os
import sys
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
from .models import AuditEvent, OtpChallenge, User, Organization, OrganizationInvitation
from .otp_delivery import OtpDeliveryError, is_demo_email_mode_enabled, send_email_otp

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
SUPPORTED_ROLES = {
    "admin",
    "claimant",
    "claim_officer",
    "claims_officer",
    "hospital_coordinator",
    "tpa_reviewer",
    "patient",
}
ROLE_ALIASES = {
    "admin": "admin",
    "Admin": "admin",
    "ADMIN": "admin",
    "administrator": "admin",
    "claimant": "claimant",
    "Claimant": "claimant",
    "User": "claimant",
    "user": "claimant",
    "hospital_coordinator": "claimant",
    "Hospital Coordinator": "claimant",
    "hospital coordinator": "claimant",
    "Coordinator": "claimant",
    "coordinator": "claimant",
    "patient": "claimant",
    "Patient": "claimant",
    "PATIENT": "claimant",
    "claim_officer": "claim_officer",
    "Claim Officer": "claim_officer",
    "claim officer": "claim_officer",
    "claims_officer": "claim_officer",
    "Claims Officer": "claim_officer",
    "claims officer": "claim_officer",
    "tpa_reviewer": "claim_officer",
    "TPA Reviewer": "claim_officer",
    "tpa reviewer": "claim_officer",
    "Reviewer": "claim_officer",
    "reviewer": "claim_officer",
}
OTP_TTL = timedelta(minutes=10)


def _get_env_int(name: str, default: int, minimum: int = 1) -> int:
    raw_value = os.environ.get(name)
    if raw_value is None or not str(raw_value).strip():
        return default
    try:
        parsed = int(str(raw_value).strip())
    except ValueError:
        return default
    return max(minimum, parsed)


def _otp_rate_window() -> timedelta:
    return timedelta(seconds=max(60, _get_env_int("CLAIMBRIDGE_OTP_RATE_WINDOW_SECONDS", 3600)))


def _otp_max_requests() -> int:
    return _get_env_int("CLAIMBRIDGE_OTP_SEND_LIMIT", 5)


def _otp_ip_max_requests() -> int:
    return _get_env_int("CLAIMBRIDGE_OTP_IP_SEND_LIMIT", 200)


def _otp_ip_limit_disabled() -> bool:
    env_name = (os.environ.get("CLAIMBRIDGE_ENV") or "").strip().lower()
    if env_name in {"test", "testing"}:
        return True
    raw = (os.environ.get("CLAIMBRIDGE_OTP_DISABLE_IP_LIMIT") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


OTP_MAX_ATTEMPTS = _get_env_int("CLAIMBRIDGE_OTP_MAX_ATTEMPTS", 5)


def _parse_retry_after_seconds(now: datetime, oldest_timestamp: Optional[datetime], window: timedelta) -> int:
    if oldest_timestamp is None:
        return max(1, int(window.total_seconds()))
    retry_after = int((oldest_timestamp + window - now).total_seconds())
    return max(1, retry_after)


def _raise_otp_rate_limit(now: datetime, request: Request, retry_after_seconds: Optional[int] = None, window: Optional[timedelta] = None) -> None:
    retry_after = retry_after_seconds or max(1, int((window or _otp_rate_window()).total_seconds()))
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=f"Too many verification requests. Please wait {retry_after} seconds before trying again.",
        headers={"Retry-After": str(retry_after)},
    )


def _normalized_email_key(email: Optional[str]) -> str:
    return (email or "").strip().lower()


def _check_otp_send_rate_limit(db: Session, request: Request, user: User) -> None:
    if not user or not user.email:
        return

    normalized_email = _normalized_email_key(user.email)
    requester_ip = (request.client.host if request.client else "unknown") or "unknown"
    requester_hash = _fingerprint(requester_ip, "requester")
    recipient_hash = _fingerprint(normalized_email, "recipient")
    rate_window = _otp_rate_window()
    now = datetime.utcnow()
    cutoff = now - rate_window

    recipient_requests = (
        db.query(OtpChallenge)
        .filter(
            OtpChallenge.recipient_hash == recipient_hash,
            OtpChallenge.created_at >= cutoff,
        )
        .order_by(OtpChallenge.created_at.asc())
        .all()
    )
    if len(recipient_requests) >= _otp_max_requests():
        oldest = recipient_requests[0].created_at
        _raise_otp_rate_limit(now, request, _parse_retry_after_seconds(now, oldest, rate_window), rate_window)

    if _otp_ip_limit_disabled():
        return

    ip_requests = (
        db.query(OtpChallenge)
        .filter(
            OtpChallenge.requester_hash == requester_hash,
            OtpChallenge.created_at >= cutoff,
        )
        .order_by(OtpChallenge.created_at.asc())
        .all()
    )

    if len(ip_requests) >= _otp_ip_max_requests():
        oldest = ip_requests[0].created_at
        _raise_otp_rate_limit(now, request, _parse_retry_after_seconds(now, oldest, rate_window), rate_window)


def canonical_role_name(raw_role: Optional[str]) -> str:
    if raw_role is None:
        return ""
    role = str(raw_role).strip()
    return ROLE_ALIASES.get(role, role)


def user_has_supported_role(user: Optional[User]) -> bool:
    if user is None:
        return False
    return canonical_role_name(user.role) in SUPPORTED_ROLES


def user_is_admin(user: Optional[User]) -> bool:
    return user_has_supported_role(user) and canonical_role_name(user.role) == "admin"


def user_is_claimant(user: Optional[User]) -> bool:
    if not user_has_supported_role(user):
        return False
    raw = str(user.role).strip().lower() if user.role else ""
    canonical = canonical_role_name(user.role)
    return canonical == "claimant" or raw in {"claimant", "hospital_coordinator", "patient", "coordinator"}


def user_is_claims_officer(user: Optional[User]) -> bool:
    if not user_has_supported_role(user):
        return False
    raw = str(user.role).strip().lower() if user.role else ""
    canonical = canonical_role_name(user.role)
    return canonical in {"claim_officer", "claims_officer"} or raw in {"claim_officer", "claims_officer", "tpa_reviewer", "reviewer"}


def user_is_patient(user: Optional[User]) -> bool:
    if not user_has_supported_role(user):
        return False
    return canonical_role_name(user.role) == "patient"


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

    normalized_role = canonical_role_name(user.role)
    if normalized_role not in SUPPORTED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not active for the current role system.",
        )

    if user.account_status and user.account_status not in {
        "active",
        "pending_email_verification",
        "pending_role_mapping",
        "pending_tpa_provisioning",
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not active for the current role system.",
        )

    if (
        normalized_role == "claims_officer"
        and user.account_status in {"pending_tpa_provisioning", "pending_role_mapping"}
        and (not user.organization_verified_at or not (user.organization or "").strip())
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
    if not user_is_claimant(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires the claimant role.",
        )
    return user


def require_claims_officer(user: User = Depends(get_current_user)) -> User:
    if user_is_claimant(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hospital coordinators are not authorized to perform TPA adjudication decisions.",
        )
    if not user_is_claims_officer(user) or not (user.organization or "").strip():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires an organization-authorized claims officer.",
        )
    return user


def require_document_reader(user: User = Depends(get_current_user)) -> User:
    if user_is_claimant(user):
        return user
    if user_is_claims_officer(user) and (user.organization or "").strip():
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Document access requires an active claimant or organization-authorized claims officer.",
    )


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user_is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires administrator authorization.",
        )
    return user


# =========================================================
# REQUEST / RESPONSE SCHEMAS
# =========================================================

class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str = Field(min_length=8, max_length=20, pattern=r"^\+?[0-9]{8,15}$")
    password: str = Field(min_length=12, max_length=128)
    role: Optional[str] = Field(default="patient")
    hospital_name: Optional[str] = None
    organization: Optional[str] = None
    designation: Optional[str] = None
    employee_id: Optional[str] = None
    registration_identifier: Optional[str] = None
    invitation_token: Optional[str] = None


class TpaRegistrationRequest(RegisterRequest):
    organization: str = Field(min_length=2, max_length=150)


class InvitedRegisterRequest(BaseModel):
    invitation_token: str = Field(min_length=16, max_length=128)
    full_name: str = Field(min_length=2, max_length=150)
    phone: str = Field(min_length=8, max_length=20, pattern=r"^\+?[0-9]{8,15}$")
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class VerifyEmailRequest(BaseModel):
    challenge_id: uuid.UUID
    code: str = Field(pattern=r"^[0-9]{6}$")


class ResendOtpRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    challenge_id: uuid.UUID
    code: str = Field(pattern=r"^[0-9]{6}$")
    new_password: str = Field(min_length=12, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class AdminUserStatusRequest(BaseModel):
    status: str = Field(pattern=r"^(active|suspended|deactivated)$")
    is_active: Optional[bool] = None


class AdminUserRoleRequest(BaseModel):
    role: str
    organization: Optional[str] = None
    designation: Optional[str] = None


class CreateInvitationRequest(BaseModel):
    email: EmailStr
    role: str
    organization_name: str


class CreateOrganizationRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    org_type: str = Field(pattern=r"^(hospital|tpa)$")
    registration_identifier: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None


class AdminBootstrapRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    phone: str = Field(default="+15555550100")


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
    recipient_hash = _fingerprint(_normalized_email_key(user.email), "recipient")
    requester_ip = request.client.host if request.client else "unknown"
    requester_hash = _fingerprint(requester_ip, "requester")

    _check_otp_send_rate_limit(db, request, user)

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
    send_email_otp(user.email, code, purpose.replace("_", " "))

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
    return challenge_id


def _registration_response(user: User, challenge_id: uuid.UUID) -> dict:
    demo_mode = is_demo_email_mode_enabled()
    response = {
        "message": (
            "Development demo mode: Check the backend console for your verification code."
            if demo_mode
            else "Verification code sent successfully to your registered email address."
        ),
        "user_id": str(user.id),
        "email": user.email,
        "challenge_id": str(challenge_id),
        "verification_required": True,
        "demo_mode": demo_mode,
    }
    if demo_mode:
        response["demo_hint"] = "Development demo mode: Check the backend console for your verification code."
    return response


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

    if getattr(user, "is_active", True) is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been suspended or deactivated. Contact your administrator.",
        )

    normalized_role = canonical_role_name(user.role)
    if normalized_role not in SUPPORTED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not activated or has not been explicitly mapped to a supported role.",
        )
    if user.account_status and user.account_status not in {
        "active",
        "pending_email_verification",
        "pending_role_mapping",
        "pending_tpa_provisioning",
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not activated or has not been explicitly mapped to a supported role.",
        )
    if (
        normalized_role in {"claims_officer", "tpa_reviewer"}
        and user.account_status in {"pending_tpa_provisioning", "pending_role_mapping"}
        and (not user.organization_verified_at or not (user.organization or "").strip())
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Claims officer access requires trusted TPA organization authorization.",
        )

    # Record login timestamp
    user.last_login_at = datetime.utcnow()
    db.add(
        AuditEvent(
            event_type="user_login",
            actor_user_id=user.id,
            details={"email": user.email, "role": user.role},
        )
    )
    db.commit()

    token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        role=user.role,
        portal=user.portal or ("Admin" if normalized_role == "admin" else "TPA" if normalized_role in {"claims_officer", "tpa_reviewer"} else "Hospital" if normalized_role in {"claimant", "hospital_coordinator"} else "Patient"),
        organization=user.organization or "",
    )

    portal = user.portal or ("Admin" if normalized_role == "admin" else "TPA" if normalized_role in {"claim_officer", "claims_officer", "tpa_reviewer"} else "Claimant")
    return {
        "message": "Login successful",
        "token": token,
        "user_id": str(user.id),
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "canonical_role": normalized_role,
        "portal": portal,
        "organization": user.organization or "",
        "designation": getattr(user, "designation", None) or "",
        "employee_id": getattr(user, "employee_id", None) or "",
    }


@router.post("/register")
def register_user(
    user_data: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    requested_role = canonical_role_name(user_data.role or "patient")
    if requested_role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System Administrator accounts cannot be self-registered publicly.",
        )

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

    # Check invitation token if provided
    invitation = None
    if user_data.invitation_token:
        token_hash = hashlib.sha256(user_data.invitation_token.encode("utf-8")).hexdigest()
        invitation = (
            db.query(OrganizationInvitation)
            .filter(
                OrganizationInvitation.token_hash == token_hash,
                OrganizationInvitation.status == "pending",
                OrganizationInvitation.expires_at > datetime.utcnow(),
            )
            .first()
        )
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired invitation token.",
            )
        if invitation.email.lower() != user_data.email.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"This invitation was issued for {invitation.email}.",
            )
        requested_role = canonical_role_name(invitation.role)
        org_name = invitation.organization_name
    else:
        org_name = (user_data.hospital_name or user_data.organization or "").strip()

    raw_req = (user_data.role or "").strip().lower()
    if not raw_req:
        raw_req = "claimant"
    if invitation:
        raw_req = invitation.role.strip().lower()

    if raw_req in ("claims_officer", "claim_officer"):
        if not invitation:
            assigned_role = "claimant"
            portal = "Claimant"
            account_status = "pending_email_verification"
        else:
            assigned_role = raw_req
            portal = "TPA"
            account_status = "active"
    elif raw_req in ("tpa_reviewer", "reviewer"):
        portal = "TPA"
        assigned_role = "tpa_reviewer"
        account_status = "active" if invitation else "pending_tpa_provisioning"
    elif raw_req == "patient":
        portal = "Patient"
        assigned_role = "patient"
        account_status = "pending_email_verification"
    elif raw_req in ("hospital_coordinator", "coordinator"):
        portal = "Hospital"
        assigned_role = "hospital_coordinator"
        account_status = "pending_email_verification"
    else:
        portal = "Claimant"
        assigned_role = "claimant"
        account_status = "pending_email_verification"

    new_user = User(
        full_name=user_data.full_name.strip(),
        email=user_data.email.lower(),
        phone=user_data.phone,
        role=assigned_role,
        portal=portal,
        organization=org_name or None,
        account_status=account_status,
        password_hash=password_hash.hash(user_data.password),
        designation=(user_data.designation or "").strip() or None,
        employee_id=(user_data.employee_id or "").strip() or None,
        is_active=True,
    )
    if invitation:
        new_user.organization_verified_at = datetime.utcnow()
        new_user.provisioned_by = invitation.invited_by

    try:
        db.add(new_user)
        db.flush()
        if invitation:
            invitation.status = "accepted"
            invitation.accepted_at = datetime.utcnow()
        purpose = f"{assigned_role}_registration"
        challenge_id = _create_email_challenge(
            db,
            new_user,
            request,
            purpose,
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
        designation=(user_data.designation or "").strip() or None,
        employee_id=(user_data.employee_id or "").strip() or None,
        is_active=True,
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
    normalized_role = canonical_role_name(user.role)

    if user.account_status in ("pending_email_verification", "pending_role_mapping"):
        user.account_status = "active"
    elif user.account_status == "pending_tpa_provisioning" and user.organization_verified_at:
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
            "message": "Email verified successfully. Your TPA organization is awaiting authorization.",
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
        "message": "Email verified successfully.",
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
            f"{user.role}_registration",
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


@router.post("/forgot-password")
def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(func.lower(User.email) == data.email.lower())
        .first()
    )
    challenge_id = None
    if user and getattr(user, "is_active", True) is not False:
        try:
            challenge_id = _create_email_challenge(db, user, request, "password_reset")
            db.commit()
        except OtpDeliveryError:
            db.rollback()
            pass

    return {
        "message": "If an active account exists with this email, a password reset verification code has been dispatched.",
        "challenge_id": str(challenge_id) if challenge_id else None,
    }


@router.post("/reset-password")
def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    challenge = (
        db.query(OtpChallenge)
        .filter(OtpChallenge.id == data.challenge_id)
        .with_for_update()
        .first()
    )
    now = datetime.utcnow()
    if (
        not challenge
        or challenge.purpose != "password_reset"
        or challenge.consumed_at is not None
        or challenge.expires_at <= now
        or challenge.attempts >= OTP_MAX_ATTEMPTS
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset code is invalid, expired, or already used.",
        )

    expected_digest = _fingerprint(f"{challenge.id}:{data.code}", "otp")
    if not hmac.compare_digest(challenge.code_digest, expected_digest):
        challenge.attempts += 1
        if challenge.attempts >= OTP_MAX_ATTEMPTS:
            challenge.consumed_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset code is invalid, expired, or already used.",
        )

    user = db.query(User).filter(User.id == challenge.user_id).with_for_update().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account no longer exists.")

    challenge.consumed_at = now
    user.password_hash = password_hash.hash(data.new_password)
    db.add(
        AuditEvent(
            event_type="password_reset_completed",
            actor_user_id=user.id,
            details={"channel": "email_otp"},
        )
    )
    db.commit()

    return {"message": "Password has been successfully reset. You may now sign in."}


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.password_hash or not password_hash.verify(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password verification failed.",
        )

    current_user.password_hash = password_hash.hash(data.new_password)
    db.add(
        AuditEvent(
            event_type="password_changed",
            actor_user_id=current_user.id,
            details={"action": "self_service_update"},
        )
    )
    db.commit()
    return {"message": "Password successfully updated."}


@router.post("/logout")
def logout_endpoint(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    if current_user:
        db.add(
            AuditEvent(
                event_type="user_logout",
                actor_user_id=current_user.id,
                details={"ip": request.client.host if request.client else "unknown"},
            )
        )
        db.commit()
    return {"message": "Successfully signed out."}


@router.get("/invitations/{token}")
def get_invitation_details(
    token: str,
    db: Session = Depends(get_db),
):
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    invitation = (
        db.query(OrganizationInvitation)
        .filter(
            OrganizationInvitation.token_hash == token_hash,
            OrganizationInvitation.status == "pending",
            OrganizationInvitation.expires_at > datetime.utcnow(),
        )
        .first()
    )
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation token is invalid or has expired.",
        )

    return {
        "valid": True,
        "email": invitation.email,
        "role": invitation.role,
        "organization_name": invitation.organization_name,
        "expires_at": invitation.expires_at.isoformat(),
    }


@router.post("/register/invited")
def register_invited_employee(
    data: InvitedRegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    token_hash = hashlib.sha256(data.invitation_token.encode("utf-8")).hexdigest()
    invitation = (
        db.query(OrganizationInvitation)
        .filter(
            OrganizationInvitation.token_hash == token_hash,
            OrganizationInvitation.status == "pending",
            OrganizationInvitation.expires_at > datetime.utcnow(),
        )
        .with_for_update()
        .first()
    )
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation token is invalid, expired, or already used.",
        )

    existing_user = db.query(User).filter(func.lower(User.email) == invitation.email.lower()).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="User already registered.")

    canonical_role = canonical_role_name(invitation.role)
    portal = "TPA" if canonical_role in ("tpa_reviewer", "claims_officer", "claim_officer") else "Hospital"
    now = datetime.utcnow()

    new_user = User(
        full_name=data.full_name.strip(),
        email=invitation.email.lower(),
        phone=data.phone.strip(),
        role=invitation.role,
        portal=portal,
        organization=invitation.organization_name,
        account_status="active",
        email_verified_at=now,
        organization_verified_at=now,
        provisioned_by=invitation.invited_by,
        is_active=True,
        password_hash=password_hash.hash(data.password),
    )
    db.add(new_user)
    invitation.status = "accepted"
    invitation.accepted_at = now

    db.add(
        AuditEvent(
            event_type="invited_user_onboarded",
            details={
                "email": invitation.email,
                "role": canonical_role,
                "organization": invitation.organization_name,
            },
        )
    )
    db.commit()

    token = create_access_token(
        user_id=str(new_user.id),
        email=new_user.email,
        role=new_user.role,
        portal=new_user.portal,
        organization=new_user.organization or "",
    )

    return {
        "message": "Onboarding successful. Your account is active.",
        "token": token,
        "user_id": str(new_user.id),
        "full_name": new_user.full_name,
        "email": new_user.email,
        "role": new_user.role,
        "portal": new_user.portal,
        "organization": new_user.organization or "",
    }


@router.post("/admin/bootstrap")
def bootstrap_admin(
    data: AdminBootstrapRequest,
    db: Session = Depends(get_db),
):
    admin_count = (
        db.query(User)
        .filter(func.lower(User.role).in_(["admin", "administrator"]))
        .count()
    )
    if admin_count > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System Administrator already provisioned. Initial setup bootstrap is disabled.",
        )

    now = datetime.utcnow()
    admin_user = User(
        full_name=data.full_name.strip(),
        email=data.email.lower().strip(),
        phone=data.phone.strip(),
        role="admin",
        portal="Admin",
        organization="ClaimBridge System Administration",
        account_status="active",
        email_verified_at=now,
        organization_verified_at=now,
        is_active=True,
        password_hash=password_hash.hash(data.password),
    )
    db.add(admin_user)
    db.add(
        AuditEvent(
            event_type="admin_bootstrap_initialized",
            details={"email": admin_user.email},
        )
    )
    db.commit()

    token = create_access_token(
        user_id=str(admin_user.id),
        email=admin_user.email,
        role="admin",
        portal="Admin",
        organization=admin_user.organization or "",
    )
    return {
        "message": "System Administrator provisioned successfully.",
        "token": token,
        "user_id": str(admin_user.id),
        "email": admin_user.email,
        "role": "admin",
    }


@router.get("/admin/users")
def list_admin_users(
    search: Optional[str] = None,
    role: Optional[str] = None,
    status_filter: Optional[str] = None,
    organization: Optional[str] = None,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.full_name.ilike(term),
                User.email.ilike(term),
                User.organization.ilike(term),
            )
        )
    if role and role.strip() and role.lower() != "all":
        query = query.filter(func.lower(User.role) == role.strip().lower())
    if status_filter and status_filter.strip() and status_filter.lower() != "all":
        query = query.filter(User.account_status == status_filter.strip())
    if organization and organization.strip():
        query = query.filter(User.organization.ilike(f"%{organization.strip()}%"))

    users = query.order_by(User.created_at.desc()).all()
    return [
        {
            "id": str(u.id),
            "full_name": u.full_name,
            "email": u.email,
            "phone": u.phone or "",
            "role": u.role,
            "portal": u.portal or "",
            "organization": u.organization or "",
            "designation": getattr(u, "designation", None) or "",
            "employee_id": getattr(u, "employee_id", None) or "",
            "account_status": u.account_status or "active",
            "is_active": getattr(u, "is_active", True),
            "email_verified_at": u.email_verified_at.isoformat() if u.email_verified_at else None,
            "last_login_at": u.last_login_at.isoformat() if getattr(u, "last_login_at", None) else None,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.patch("/admin/users/{user_id}/status")
def update_user_status(
    user_id: uuid.UUID,
    body: AdminUserStatusRequest,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if body.status == "active":
        user.account_status = "active"
        user.is_active = True
        user.organization_verified_at = datetime.utcnow()
    elif body.status == "suspended":
        user.account_status = "suspended"
        user.is_active = False
    elif body.status == "deactivated":
        user.account_status = "deactivated"
        user.is_active = False

    if body.is_active is not None:
        user.is_active = body.is_active

    db.add(
        AuditEvent(
            event_type="admin_user_status_updated",
            actor_user_id=admin_user.id,
            details={"target_user_id": str(user.id), "status": body.status},
        )
    )
    db.commit()
    return {"message": f"User status updated to {body.status}.", "user_id": str(user.id)}


@router.patch("/admin/users/{user_id}/role")
def update_user_role(
    user_id: uuid.UUID,
    body: AdminUserRoleRequest,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    canonical = canonical_role_name(body.role)
    user.role = body.role.strip().lower()
    if body.organization is not None:
        user.organization = body.organization.strip()
    if body.designation is not None:
        user.designation = body.designation.strip()

    db.add(
        AuditEvent(
            event_type="admin_user_role_updated",
            actor_user_id=admin_user.id,
            details={"target_user_id": str(user.id), "role": canonical},
        )
    )
    db.commit()
    return {"message": "User role updated successfully.", "user_id": str(user.id)}


@router.post("/admin/invitations")
def create_invitation(
    body: CreateInvitationRequest,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(func.lower(User.email) == body.email.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="A user with this email already exists.")

    secret_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(secret_token.encode("utf-8")).hexdigest()
    expires_at = datetime.utcnow() + timedelta(days=7)

    invitation = OrganizationInvitation(
        email=body.email.lower().strip(),
        role=body.role.strip().lower(),
        organization_name=body.organization_name.strip(),
        token_hash=token_hash,
        invited_by=admin_user.id,
        status="pending",
        expires_at=expires_at,
    )
    db.add(invitation)
    db.add(
        AuditEvent(
            event_type="organization_invitation_created",
            actor_user_id=admin_user.id,
            details={
                "email": invitation.email,
                "role": invitation.role,
                "organization": invitation.organization_name,
            },
        )
    )
    db.commit()

    return {
        "message": "Invitation created successfully.",
        "id": str(invitation.id),
        "email": invitation.email,
        "role": invitation.role,
        "organization_name": invitation.organization_name,
        "invitation_token": secret_token,
        "expires_at": expires_at.isoformat(),
    }


@router.get("/admin/organizations")
def list_organizations(
    org_type: Optional[str] = None,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Organization)
    if org_type:
        query = query.filter(Organization.org_type == org_type.lower())
    return [
        {
            "id": str(o.id),
            "name": o.name,
            "org_type": o.org_type,
            "registration_identifier": o.registration_identifier,
            "contact_email": o.contact_email,
            "contact_phone": o.contact_phone,
            "is_active": o.is_active,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in query.order_by(Organization.name.asc()).all()
    ]


@router.post("/admin/organizations")
def create_organization(
    body: CreateOrganizationRequest,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    existing = db.query(Organization).filter(func.lower(Organization.name) == body.name.lower().strip()).first()
    if existing:
        raise HTTPException(status_code=409, detail="An organization with this name already exists.")

    org = Organization(
        name=body.name.strip(),
        org_type=body.org_type.lower().strip(),
        registration_identifier=(body.registration_identifier or "").strip() or None,
        contact_email=body.contact_email,
        contact_phone=(body.contact_phone or "").strip() or None,
        is_active=True,
    )
    db.add(org)
    db.commit()
    return {
        "message": "Organization created successfully.",
        "id": str(org.id),
        "name": org.name,
        "org_type": org.org_type,
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
        "canonical_role": canonical_role_name(current_user.role),
        "portal": current_user.portal or "Claimant",
        "organization": current_user.organization or "",
        "designation": getattr(current_user, "designation", None) or "",
        "employee_id": getattr(current_user, "employee_id", None) or "",
    }
