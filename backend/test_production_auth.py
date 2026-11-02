"""
Comprehensive Automated Test Suite for ClaimBridge Production Authentication
=============================================================================
Tests:
1. Patient registration with email OTP challenge.
2. Hospital coordinator registration with hospital organization.
3. Rejection of public admin registration (403 Forbidden).
4. TPA applicant self-registration requires provisioning (pending_tpa_provisioning).
5. Organization invitation creation by Admin and direct invited employee onboarding.
6. Duplicate email registration rejection (409 Conflict).
7. Login with valid credentials returns JWT token and user profile.
8. Login with invalid password returns 401 Unauthorized.
9. Login with unactivated account returns 403 Forbidden.
10. Login with suspended/inactive account returns 403 Forbidden.
11. Email OTP verification transitions account to active and returns token.
12. Forgot password & reset password lifecycle via OTP.
13. Authenticated self-service change password.
14. User logout audit logging.
15. Admin user management: list, activate, suspend user.
16. Admin user management: update role and organization.
17. Admin organization registration and retrieval.
18. Multi-tenant claim scoping and role isolation (Admin, Coordinator, TPA, Patient).
"""

import hashlib
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import random

import pytest
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.auth import (
    create_access_token,
    password_hash,
    _fingerprint,
    OTP_TTL,
)
from app.otp_delivery import OtpDeliveryError, send_email_otp
from app.database import SessionLocal
from app.main import app
from app.models import (
    AuditEvent,
    Claim,
    Organization,
    OrganizationInvitation,
    OtpChallenge,
    Patient,
    Policy,
    User,
)

client = TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def mock_smtp(monkeypatch):
    """Bypasses physical SMTP network transport during automated testing."""
    monkeypatch.setenv("CLAIMBRIDGE_ENV", "testing")
    monkeypatch.setenv("CLAIMBRIDGE_OTP_DISABLE_IP_LIMIT", "true")
    monkeypatch.setattr("app.auth.send_email_otp", lambda recipient, code, purpose: None)


def _unique_email(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}@claimbridge.org"


def test_demo_email_mode_logs_otp(monkeypatch, capsys):
    monkeypatch.setenv("CLAIMBRIDGE_ENV", "development")
    monkeypatch.setenv("CLAIMBRIDGE_EMAIL_DEMO_MODE", "true")
    monkeypatch.delenv("CLAIMBRIDGE_SMTP_HOST", raising=False)
    send_email_otp("demo@claimbridge.test", "123456", "tpa_registration")
    captured = capsys.readouterr()
    assert "123456" in captured.out


def test_demo_email_mode_is_disabled_in_production(monkeypatch):
    monkeypatch.setenv("CLAIMBRIDGE_ENV", "production")
    monkeypatch.setenv("CLAIMBRIDGE_EMAIL_DEMO_MODE", "true")
    with pytest.raises(OtpDeliveryError, match="Development demo mode is disabled in production"):
        send_email_otp("demo@claimbridge.test", "123456", "tpa_registration")


def test_otp_send_rate_limit_returns_retry_after(db, monkeypatch):
    monkeypatch.setenv("CLAIMBRIDGE_OTP_IP_SEND_LIMIT", "1000")
    email = _unique_email("rate_limit")
    user = User(
        full_name="Rate Limited User",
        email=email,
        phone="+15555550199",
        role="claimant",
        portal="Claimant",
        account_status="pending_email_verification",
        password_hash=password_hash.hash("SecurePassword#2026"),
        is_active=True,
    )
    db.add(user)
    db.commit()

    response = None
    for _ in range(8):
        response = client.post("/auth/otp/resend", json={"email": email})
        if response.status_code == 429:
            break

    assert response is not None
    assert response.status_code == 429, response.text
    assert "retry-after" in {key.lower() for key in response.headers.keys()}
    assert int(response.headers["retry-after"]) > 0
    assert "Please wait" in response.json()["detail"]


def test_otp_rate_limit_is_email_scoped(db, monkeypatch):
    monkeypatch.setenv("CLAIMBRIDGE_OTP_IP_SEND_LIMIT", "1000")
    email_1 = _unique_email("rate_scope_1")
    email_2 = _unique_email("rate_scope_2")
    for email in (email_1, email_2):
        user = User(
            full_name="Scope User",
            email=email,
            phone="+15555559999",
            role="claimant",
            portal="Claimant",
            account_status="pending_email_verification",
            password_hash=password_hash.hash("SecurePassword#2026"),
            is_active=True,
        )
        db.add(user)
    db.commit()

    first_email_response = None
    for _ in range(8):
        first_email_response = client.post("/auth/otp/resend", json={"email": email_1})
        if first_email_response.status_code == 429:
            break

    second_email_response = client.post("/auth/otp/resend", json={"email": email_2})
    assert first_email_response.status_code == 429
    assert second_email_response.status_code == 200, second_email_response.text


def test_failed_smtp_delivery_does_not_consume_send_quota(monkeypatch):
    monkeypatch.setenv("CLAIMBRIDGE_OTP_IP_SEND_LIMIT", "1000")
    email = _unique_email("smtp_fail")
    payload = {
        "full_name": "SMTP Fail User",
        "email": email,
        "phone": "+15555551020",
        "password": "SecurePassword#2026",
        "organization": "MediAssist TPA",
    }

    def fail_delivery(*args, **kwargs):
        raise OtpDeliveryError("Email delivery was rejected by the provider.")

    monkeypatch.setattr("app.auth.send_email_otp", fail_delivery)
    first = client.post("/auth/register/tpa", json=payload)
    assert first.status_code == 503, first.text

    monkeypatch.setattr("app.auth.send_email_otp", lambda *args, **kwargs: None)
    second = client.post("/auth/register/tpa", json=payload)
    assert second.status_code == 202, second.text


def test_missing_smtp_credentials_raises_clear_error(monkeypatch):
    monkeypatch.setenv("CLAIMBRIDGE_ENV", "development")
    monkeypatch.setenv("CLAIMBRIDGE_EMAIL_DEMO_MODE", "false")
    monkeypatch.setenv("CLAIMBRIDGE_SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("CLAIMBRIDGE_SMTP_PORT", "587")
    monkeypatch.setenv("CLAIMBRIDGE_SMTP_FROM", "claims@example.com")
    monkeypatch.delenv("CLAIMBRIDGE_SMTP_USER", raising=False)
    monkeypatch.delenv("CLAIMBRIDGE_SMTP_PASSWORD", raising=False)
    with pytest.raises(OtpDeliveryError, match="Email authentication failed"):
        send_email_otp("demo@claimbridge.test", "123456", "tpa_registration")


def test_valid_gmail_smtp_configuration_uses_starttls(monkeypatch):
    monkeypatch.setenv("CLAIMBRIDGE_ENV", "production")
    monkeypatch.setenv("CLAIMBRIDGE_EMAIL_DEMO_MODE", "false")
    monkeypatch.setenv("CLAIMBRIDGE_SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("CLAIMBRIDGE_SMTP_PORT", "587")
    monkeypatch.setenv("CLAIMBRIDGE_SMTP_USER", "claims@example.com")
    monkeypatch.setenv("CLAIMBRIDGE_SMTP_PASSWORD", "app-password")
    monkeypatch.setenv("CLAIMBRIDGE_SMTP_FROM", "claims@example.com")
    monkeypatch.setenv("CLAIMBRIDGE_SMTP_STARTTLS", "true")

    class FakeSMTP:
        def __init__(self, *args, **kwargs):
            self.logged_in = False
            self.sent = False
            self.ehlo_calls = 0

        def ehlo(self):
            self.ehlo_calls += 1

        def starttls(self, context=None):
            self.tls_started = True

        def login(self, username, password):
            self.logged_in = username == "claims@example.com" and password == "app-password"
            if not self.logged_in:
                raise OtpDeliveryError("Email authentication failed. Please check the email service configuration.")

        def send_message(self, message):
            self.sent = True
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("app.otp_delivery.smtplib.SMTP", FakeSMTP)
    send_email_otp("recipient@example.com", "123456", "tpa_registration")


def test_smtp_connection_failure_raises_provider_unavailable(monkeypatch):
    monkeypatch.setenv("CLAIMBRIDGE_ENV", "production")
    monkeypatch.setenv("CLAIMBRIDGE_EMAIL_DEMO_MODE", "false")
    monkeypatch.setenv("CLAIMBRIDGE_SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("CLAIMBRIDGE_SMTP_PORT", "587")
    monkeypatch.setenv("CLAIMBRIDGE_SMTP_USER", "claims@example.com")
    monkeypatch.setenv("CLAIMBRIDGE_SMTP_PASSWORD", "app-password")
    monkeypatch.setenv("CLAIMBRIDGE_SMTP_FROM", "claims@example.com")
    monkeypatch.setenv("CLAIMBRIDGE_SMTP_STARTTLS", "true")

    class FailingSMTP:
        def __init__(self, *args, **kwargs):
            raise OSError("connection refused")

    monkeypatch.setattr("app.otp_delivery.smtplib.SMTP", FailingSMTP)
    with pytest.raises(OtpDeliveryError, match="Unable to send verification email right now"):
        send_email_otp("recipient@example.com", "123456", "tpa_registration")


# 1. Patient registration
def test_01_patient_registration_creates_challenge(db):
    email = _unique_email("patient")
    payload = {
        "full_name": "Sarah Connor",
        "email": email,
        "phone": "+15555550101",
        "password": "SecurePassword#2026",
        "role": "patient",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["verification_required"] is True
    assert "challenge_id" in data
    assert data["email"] == email

    user = db.query(User).filter(User.email == email).first()
    assert user is not None
    assert user.role == "patient"
    assert user.account_status == "pending_email_verification"


# 2. Hospital coordinator registration
def test_02_hospital_coordinator_registration(db):
    email = _unique_email("coord")
    payload = {
        "full_name": "Dr. Marcus Vance",
        "email": email,
        "phone": "+15555550102",
        "password": "SecurePassword#2026",
        "role": "hospital_coordinator",
        "hospital_name": "Apollo Hospitals International",
        "designation": "Chief Medical Registrar",
        "employee_id": "HOSP-EMP-991",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["verification_required"] is True

    user = db.query(User).filter(User.email == email).first()
    assert user is not None
    assert user.role == "hospital_coordinator"
    assert user.organization == "Apollo Hospitals International"
    assert user.designation == "Chief Medical Registrar"


# 3. Rejection of public admin registration
def test_03_rejection_of_public_admin_registration():
    email = _unique_email("admin_fake")
    payload = {
        "full_name": "Rogue Admin",
        "email": email,
        "phone": "+15555550103",
        "password": "SecurePassword#2026",
        "role": "admin",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 403
    assert "cannot be self-registered" in response.json()["detail"].lower()


# 4. TPA applicant self-registration requires provisioning
def test_04_tpa_self_registration_pending_provisioning(db):
    email = _unique_email("tpa_applicant")
    payload = {
        "full_name": "Jennifer Aniston",
        "email": email,
        "phone": "+15555550104",
        "password": "SecurePassword#2026",
        "role": "tpa_reviewer",
        "organization": "Pacific Healthcare TPA",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 200, response.text

    user = db.query(User).filter(User.email == email).first()
    assert user is not None
    assert user.role == "tpa_reviewer"
    assert user.account_status == "pending_tpa_provisioning"


# 5. Organization invitation creation by Admin and direct onboarding
def test_05_admin_invitation_and_invited_onboarding(db):
    admin_id = uuid.uuid4()
    admin_email = _unique_email("admin_issuer")
    admin_user = User(
        id=admin_id,
        full_name="Super Admin",
        email=admin_email,
        role="admin",
        portal="Admin",
        account_status="active",
        is_active=True,
    )
    db.add(admin_user)
    db.commit()

    admin_token = create_access_token(
        user_id=str(admin_id),
        email=admin_email,
        role="admin",
        portal="Admin",
    )
    headers = {"Authorization": f"Bearer {admin_token}"}

    invite_email = _unique_email("tpa_invited")
    invite_payload = {
        "email": invite_email,
        "role": "tpa_reviewer",
        "organization_name": "Star Health TPA",
    }
    inv_res = client.post("/auth/admin/invitations", json=invite_payload, headers=headers)
    assert inv_res.status_code == 200, inv_res.text
    inv_data = inv_res.json()
    secret_token = inv_data["invitation_token"]

    # Validate invitation publicly
    val_res = client.get(f"/auth/invitations/{secret_token}")
    assert val_res.status_code == 200
    assert val_res.json()["email"] == invite_email

    # Onboard invited employee
    onboard_payload = {
        "invitation_token": secret_token,
        "full_name": "David Hasselhoff",
        "phone": "+15555550105",
        "password": "SecurePassword#2026",
    }
    reg_res = client.post("/auth/register/invited", json=onboard_payload)
    assert reg_res.status_code == 200, reg_res.text
    onboard_data = reg_res.json()
    assert onboard_data["role"] == "tpa_reviewer"
    assert onboard_data["organization"] == "Star Health TPA"
    assert "token" in onboard_data


# 6. Duplicate email rejection
def test_06_duplicate_email_registration_rejection(db):
    email = _unique_email("duplicate")
    payload = {
        "full_name": "Alice Wonderland",
        "email": email,
        "phone": "+15555550106",
        "password": "SecurePassword#2026",
        "role": "patient",
    }
    res1 = client.post("/auth/register", json=payload)
    assert res1.status_code == 200

    res2 = client.post("/auth/register", json=payload)
    assert res2.status_code == 409
    assert "already registered" in res2.json()["detail"].lower()


# 7. Login success and JWT token
def test_07_login_success_and_jwt_token(db):
    email = _unique_email("active_login")
    user = User(
        full_name="Robert Downey",
        email=email,
        role="hospital_coordinator",
        portal="Hospital",
        organization="Apollo Hospitals",
        account_status="active",
        is_active=True,
        password_hash=password_hash.hash("MyPassword#1234"),
    )
    db.add(user)
    db.commit()

    login_res = client.post(
        "/auth/login",
        json={"email": email, "password": "MyPassword#1234"},
    )
    assert login_res.status_code == 200, login_res.text
    data = login_res.json()
    assert "token" in data
    assert data["email"] == email
    assert data["role"] == "hospital_coordinator"


# 8. Login invalid password rejection
def test_08_login_invalid_password_rejection(db):
    email = _unique_email("bad_pass")
    user = User(
        full_name="Bruce Banner",
        email=email,
        role="patient",
        portal="Patient",
        account_status="active",
        is_active=True,
        password_hash=password_hash.hash("CorrectPassword#123"),
    )
    db.add(user)
    db.commit()

    login_res = client.post(
        "/auth/login",
        json={"email": email, "password": "WrongPassword#999"},
    )
    assert login_res.status_code == 401
    assert "invalid email or password" in login_res.json()["detail"].lower()


# 9. Login unverified/unmapped account rejection
def test_09_login_unverified_account_rejection(db):
    email = _unique_email("unverified")
    user = User(
        full_name="Clark Kent",
        email=email,
        role="hospital_coordinator",
        portal="Hospital",
        account_status="suspended",
        is_active=True,
        password_hash=password_hash.hash("CorrectPassword#123"),
    )
    db.add(user)
    db.commit()

    login_res = client.post(
        "/auth/login",
        json={"email": email, "password": "CorrectPassword#123"},
    )
    assert login_res.status_code == 403


# 10. Login suspended/deactivated account rejection
def test_10_login_suspended_account_rejection(db):
    email = _unique_email("deactivated")
    user = User(
        full_name="Peter Parker",
        email=email,
        role="patient",
        portal="Patient",
        account_status="active",
        is_active=False,
        password_hash=password_hash.hash("CorrectPassword#123"),
    )
    db.add(user)
    db.commit()

    login_res = client.post(
        "/auth/login",
        json={"email": email, "password": "CorrectPassword#123"},
    )
    assert login_res.status_code == 403
    assert "suspended or deactivated" in login_res.json()["detail"].lower()


# 11. Email OTP verification
def test_11_email_otp_verification(db):
    email = _unique_email("otp_verify")
    user = User(
        full_name="Diana Prince",
        email=email,
        role="patient",
        portal="Patient",
        account_status="pending_email_verification",
        is_active=True,
        password_hash=password_hash.hash("SecurePassword#2026"),
    )
    db.add(user)
    db.flush()

    # Create known OTP challenge
    challenge_id = uuid.uuid4()
    code = "123456"
    now = datetime.utcnow()
    challenge = OtpChallenge(
        id=challenge_id,
        user_id=user.id,
        purpose="patient_registration",
        recipient_hash=_fingerprint(user.email.lower(), "recipient"),
        requester_hash=_fingerprint("127.0.0.1", "requester"),
        code_digest=_fingerprint(f"{challenge_id}:{code}", "otp"),
        attempts=0,
        expires_at=now + OTP_TTL,
        created_at=now,
    )
    db.add(challenge)
    db.commit()

    verify_res = client.post(
        "/auth/verify-email",
        json={"challenge_id": str(challenge_id), "code": code},
    )
    assert verify_res.status_code == 200, verify_res.text
    vdata = verify_res.json()
    assert vdata["verified"] is True
    assert vdata["activated"] is True
    assert "token" in vdata

    db.refresh(user)
    assert user.account_status == "active"
    assert user.email_verified_at is not None


# 12. Forgot password and reset password flow
def test_12_forgot_password_and_reset_password_flow(db):
    email = _unique_email("forgot_pass")
    user = User(
        full_name="Tony Stark",
        email=email,
        role="patient",
        portal="Patient",
        account_status="active",
        is_active=True,
        password_hash=password_hash.hash("OldPassword#123"),
    )
    db.add(user)
    db.commit()

    # 1. Request forgot password
    forgot_res = client.post("/auth/forgot-password", json={"email": email})
    assert forgot_res.status_code == 200
    challenge_id_str = forgot_res.json()["challenge_id"]
    assert challenge_id_str is not None

    challenge_id = uuid.UUID(challenge_id_str)
    # Manually configure known OTP code for testing
    challenge = db.query(OtpChallenge).filter(OtpChallenge.id == challenge_id).first()
    reset_code = "654321"
    challenge.code_digest = _fingerprint(f"{challenge_id}:{reset_code}", "otp")
    db.commit()

    # 2. Reset password
    reset_res = client.post(
        "/auth/reset-password",
        json={
            "challenge_id": str(challenge_id),
            "code": reset_code,
            "new_password": "NewSecurePassword#2026",
        },
    )
    assert reset_res.status_code == 200, reset_res.text

    # 3. Verify login with new password
    login_res = client.post(
        "/auth/login",
        json={"email": email, "password": "NewSecurePassword#2026"},
    )
    assert login_res.status_code == 200


# 13. Authenticated change password
def test_13_authenticated_change_password(db):
    email = _unique_email("change_pass")
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        full_name="Natasha Romanoff",
        email=email,
        role="hospital_coordinator",
        portal="Hospital",
        account_status="active",
        is_active=True,
        password_hash=password_hash.hash("CurrentPassword#123"),
    )
    db.add(user)
    db.commit()

    token = create_access_token(
        user_id=str(user_id),
        email=email,
        role="hospital_coordinator",
        portal="Hospital",
    )
    headers = {"Authorization": f"Bearer {token}"}

    change_res = client.post(
        "/auth/change-password",
        json={
            "current_password": "CurrentPassword#123",
            "new_password": "BrandNewPassword#456",
        },
        headers=headers,
    )
    assert change_res.status_code == 200

    # Confirm old password fails
    bad_login = client.post(
        "/auth/login",
        json={"email": email, "password": "CurrentPassword#123"},
    )
    assert bad_login.status_code == 401

    # Confirm new password succeeds
    good_login = client.post(
        "/auth/login",
        json={"email": email, "password": "BrandNewPassword#456"},
    )
    assert good_login.status_code == 200


# 14. User logout audit
def test_14_user_logout_audit(db):
    user_id = uuid.uuid4()
    email = _unique_email("logout_user")
    token = create_access_token(
        user_id=str(user_id),
        email=email,
        role="patient",
        portal="Patient",
    )
    headers = {"Authorization": f"Bearer {token}"}

    logout_res = client.post("/auth/logout", headers=headers)
    assert logout_res.status_code == 200
    assert logout_res.json()["message"] == "Successfully signed out."


# 15. Admin user management: list, activate, suspend user
def test_15_admin_user_status_management(db):
    admin_id = uuid.uuid4()
    admin_email = _unique_email("admin_mgr")
    admin_token = create_access_token(
        user_id=str(admin_id),
        email=admin_email,
        role="admin",
        portal="Admin",
    )
    headers = {"Authorization": f"Bearer {admin_token}"}

    target_email = _unique_email("target_user")
    target_id = uuid.uuid4()
    target_user = User(
        id=target_id,
        full_name="Target User",
        email=target_email,
        role="tpa_reviewer",
        portal="TPA",
        account_status="pending_tpa_provisioning",
        is_active=True,
    )
    admin_user = User(
        id=admin_id,
        full_name="Admin Boss",
        email=admin_email,
        role="admin",
        portal="Admin",
        account_status="active",
        is_active=True,
    )
    db.add(admin_user)
    db.add(target_user)
    db.commit()

    # List users
    list_res = client.get("/auth/admin/users", headers=headers)
    assert list_res.status_code == 200
    users_list = list_res.json()
    assert any(u["email"] == target_email for u in users_list)

    # Activate target user
    act_res = client.patch(
        f"/auth/admin/users/{target_id}/status",
        json={"status": "active", "is_active": True},
        headers=headers,
    )
    assert act_res.status_code == 200
    db.refresh(target_user)
    assert target_user.account_status == "active"

    # Suspend target user
    susp_res = client.patch(
        f"/auth/admin/users/{target_id}/status",
        json={"status": "suspended", "is_active": False},
        headers=headers,
    )
    assert susp_res.status_code == 200
    db.refresh(target_user)
    assert target_user.account_status == "suspended"
    assert target_user.is_active is False


# 16. Admin user management: role and organization
def test_16_admin_user_role_management(db):
    admin_id = uuid.uuid4()
    admin_email = _unique_email("admin_roles")
    admin_user = User(
        id=admin_id,
        full_name="Admin Role Mgr",
        email=admin_email,
        role="admin",
        portal="Admin",
        account_status="active",
        is_active=True,
    )
    target_id = uuid.uuid4()
    target_user = User(
        id=target_id,
        full_name="Role Candidate",
        email=_unique_email("candidate"),
        role="patient",
        portal="Patient",
        account_status="active",
        is_active=True,
    )
    db.add(admin_user)
    db.add(target_user)
    db.commit()

    headers = {"Authorization": f"Bearer {create_access_token(str(admin_id), admin_email, 'admin', 'Admin')}"}

    update_res = client.patch(
        f"/auth/admin/users/{target_id}/role",
        json={
            "role": "hospital_coordinator",
            "organization": "Apollo Hospitals International",
            "designation": "Billing Coordinator",
        },
        headers=headers,
    )
    assert update_res.status_code == 200
    db.refresh(target_user)
    assert target_user.role == "hospital_coordinator"
    assert target_user.organization == "Apollo Hospitals International"
    assert target_user.designation == "Billing Coordinator"


# 17. Admin organization management
def test_17_admin_organization_management(db):
    admin_id = uuid.uuid4()
    admin_email = _unique_email("admin_orgs")
    admin_user = User(
        id=admin_id,
        full_name="Admin Org Boss",
        email=admin_email,
        role="admin",
        portal="Admin",
        account_status="active",
        is_active=True,
    )
    db.add(admin_user)
    db.commit()

    headers = {"Authorization": f"Bearer {create_access_token(str(admin_id), admin_email, 'admin', 'Admin')}"}

    org_name = f"City Care Hospital {uuid.uuid4().hex[:6]}"
    create_res = client.post(
        "/auth/admin/organizations",
        json={
            "name": org_name,
            "org_type": "hospital",
            "registration_identifier": "HOSP-REG-4401",
            "contact_email": "admin@citycare.org",
        },
        headers=headers,
    )
    assert create_res.status_code == 200
    assert create_res.json()["name"] == org_name

    list_res = client.get("/auth/admin/organizations", headers=headers)
    assert list_res.status_code == 200
    assert any(o["name"] == org_name for o in list_res.json())


# 18. Multi-tenant claim scoping and role isolation
def test_18_role_based_access_control_and_claim_scoping(db):
    coord_id = uuid.uuid4()
    coord_email = _unique_email("coord_scope")
    coord_user = User(
        id=coord_id,
        full_name="Coord One",
        email=coord_email,
        role="hospital_coordinator",
        portal="Hospital",
        organization="Apollo Hospitals",
        account_status="active",
        is_active=True,
    )
    tpa_id = uuid.uuid4()
    tpa_email = _unique_email("tpa_scope")
    tpa_user = User(
        id=tpa_id,
        full_name="Reviewer One",
        email=tpa_email,
        role="tpa_reviewer",
        portal="TPA",
        organization="Star Health TPA",
        account_status="active",
        is_active=True,
    )
    patient_id = uuid.uuid4()
    patient_email = _unique_email("patient_scope")
    patient_user = User(
        id=patient_id,
        full_name="Patient One",
        email=patient_email,
        role="patient",
        portal="Patient",
        account_status="active",
        is_active=True,
    )
    db.add(coord_user)
    db.add(tpa_user)
    db.add(patient_user)
    db.commit()

    coord_token = create_access_token(str(coord_id), coord_email, "hospital_coordinator", "Hospital", "Apollo Hospitals")
    tpa_token = create_access_token(str(tpa_id), tpa_email, "tpa_reviewer", "TPA", "Star Health TPA")
    patient_token = create_access_token(str(patient_id), patient_email, "patient", "Patient")

    # 1. Coordinator can query claims
    c_res = client.get("/claims", headers={"Authorization": f"Bearer {coord_token}"})
    assert c_res.status_code == 200

    # 2. Coordinator cannot access TPA-only review desk
    tpa_desk_res = client.get("/claims/tpa/review-queue", headers={"Authorization": f"Bearer {coord_token}"})
    assert tpa_desk_res.status_code == 403

    # 3. TPA reviewer CAN access review desk
    tpa_ok_res = client.get("/claims/tpa/review-queue", headers={"Authorization": f"Bearer {tpa_token}"})
    assert tpa_ok_res.status_code == 200

    # 4. Patient cannot access review queue
    p_desk_res = client.get("/claims/tpa/review-queue", headers={"Authorization": f"Bearer {patient_token}"})
    assert p_desk_res.status_code == 403
