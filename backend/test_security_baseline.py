import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app import auth, claims as claims_api
from app.auth import (
    VerifyEmailRequest,
    get_current_user,
    require_claimant,
    require_claims_officer,
    verify_access_token,
)
from app.claims import (
    ClaimAmendmentDecisionRequest,
    ClaimAmendmentRequest,
    UpdateClaimStatusRequest,
    apply_claim_scope,
    check_claim_access,
)
from app.database import get_db
from app.main import app
from app.models import (
    AuditEvent,
    Claim,
    ClaimAmendment,
    OtpChallenge,
    Patient,
    Policy,
    User,
)


class FakeQuery:
    def __init__(self, session, model):
        self.session = session
        self.model = model

    def filter(self, *_args, **_kwargs):
        return self

    def join(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def with_for_update(self):
        return self

    def first(self):
        if self.model in self.session.query_results:
            return self.session.query_results[self.model]
        return next(
            (record for record in self.session.added if isinstance(record, self.model)),
            None,
        )

    def all(self):
        if self.model is OtpChallenge:
            return []
        return [
            record
            for record in self.session.added
            if isinstance(record, self.model)
        ]

    def count(self):
        return 0


class FakeSession:
    def __init__(self, query_results=None):
        self.added = []
        self.query_results = query_results or {}

    def query(self, model):
        return FakeQuery(self, model)

    def add(self, record):
        self.added.append(record)

    def flush(self):
        for record in self.added:
            if hasattr(record, "id") and record.id is None:
                record.id = uuid.uuid4()

    def commit(self):
        self.flush()

    def rollback(self):
        pass

    def refresh(self, _record):
        pass


class CapturedQuery:
    def __init__(self):
        self.criteria = []

    def filter(self, *criteria):
        self.criteria.extend(criteria)
        return self


@pytest.fixture
def client(monkeypatch):
    fake_db = FakeSession()
    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides.pop(get_current_user, None)
    monkeypatch.setattr(auth.password_hash, "hash", lambda password: f"hashed:{password}")
    monkeypatch.setattr(auth, "send_email_otp", lambda *_args: None)
    with TestClient(app) as test_client:
        yield test_client, fake_db
    app.dependency_overrides.clear()


def make_user(role="claimant", organization="North Hospital", **overrides):
    values = {
        "id": uuid.uuid4(),
        "role": role,
        "portal": "Claimant" if role == "claimant" else "TPA",
        "organization": organization,
        "full_name": "Synthetic Test User",
        "email": "test@example.invalid",
        "phone": "+15555550123",
        "account_status": "active",
        "email_verified_at": datetime.utcnow(),
        "organization_verified_at": datetime.utcnow() if role == "claims_officer" else None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_legacy_and_modified_tokens_are_rejected():
    user_id = str(uuid.uuid4())
    assert verify_access_token(f"token_{user_id}") is None

    valid = auth.create_access_token(user_id, "test@example.invalid", "claimant")
    header, payload, signature = valid.split(".")
    assert verify_access_token(valid)["sub"] == user_id
    tampered_signature = ("A" if signature[0] != "A" else "B") + signature[1:]
    assert verify_access_token(f"{header}.{payload}.{tampered_signature}") is None


def test_protected_routes_reject_missing_and_legacy_auth(client):
    test_client, _ = client
    user_id = str(uuid.uuid4())
    requests = [
        ("get", "/claims"),
        ("get", "/claims/summary"),
        ("get", f"/claims/{user_id}"),
        ("get", "/claims/analytics"),
        ("get", "/documents"),
        ("post", f"/documents/{user_id}/process"),
        ("get", f"/documents/{user_id}/ocr"),
    ]

    for method, path in requests:
        for headers in ({}, {"Authorization": f"Bearer token_{user_id}"}):
            response = getattr(test_client, method)(path, headers=headers)
            assert response.status_code == 401, (method, path, response.text)

    for headers in ({}, {"Authorization": f"Bearer token_{user_id}"}):
        response = test_client.post(
            "/documents/upload",
            headers=headers,
            files={"file": ("synthetic.pdf", b"%PDF-test", "application/pdf")},
        )
        assert response.status_code == 401, response.text


def test_public_registration_cannot_select_privileged_role_or_activation(client):
    test_client, fake_db = client
    response = test_client.post(
        "/auth/register",
        json={
            "full_name": "Synthetic Demo User",
            "email": "claimant@example.com",
            "phone": "+15555550123",
            "password": "Example#Pass1234",
            "role": "claims_officer",
            "portal": "TPA",
            "account_status": "active",
            "organization_verified_at": "2026-01-01T00:00:00",
        },
    )

    assert response.status_code == 200, response.text
    result = response.json()
    created_user = next(record for record in fake_db.added if isinstance(record, User))
    assert created_user.role == "claimant"
    assert created_user.portal == "Claimant"
    assert created_user.account_status == "pending_email_verification"
    assert result["verification_required"] is True
    assert "token" not in result


def test_tpa_registration_is_unprivileged_until_trusted_provisioning(client):
    test_client, fake_db = client
    response = test_client.post(
        "/auth/register/tpa",
        json={
            "full_name": "Synthetic TPA Applicant",
            "email": "officer@example.com",
            "phone": "+15555550124",
            "password": "Example#Pass1234",
            "organization": "ClaimBridge Test TPA",
            "role": "claims_officer",
        },
    )

    assert response.status_code == 202, response.text
    applicant = next(record for record in fake_db.added if isinstance(record, User))
    assert applicant.role == "claimant"
    assert applicant.account_status == "pending_tpa_provisioning"
    assert applicant.organization_verified_at is None
    assert response.json()["organization_authorization_required"] is True
    assert "token" not in response.json()


def test_email_otp_is_single_use_and_activates_only_claimant():
    challenge_id = uuid.uuid4()
    user = make_user(
        role="claimant",
        account_status="pending_email_verification",
        email_verified_at=None,
    )
    code = "123456"
    challenge = SimpleNamespace(
        id=challenge_id,
        user_id=user.id,
        purpose="claimant_registration",
        consumed_at=None,
        expires_at=datetime.utcnow() + timedelta(minutes=5),
        attempts=0,
        code_digest=auth._fingerprint(f"{challenge_id}:{code}", "otp"),
    )
    fake_db = FakeSession({OtpChallenge: challenge, User: user})

    result = auth.verify_email(
        VerifyEmailRequest(challenge_id=challenge_id, code=code),
        fake_db,
    )
    assert result["activated"] is True
    assert verify_access_token(result["token"])["sub"] == str(user.id)
    assert user.account_status == "active"
    assert challenge.consumed_at is not None
    assert any(isinstance(record, AuditEvent) for record in fake_db.added)

    with pytest.raises(HTTPException) as exc_info:
        auth.verify_email(
            VerifyEmailRequest(challenge_id=challenge_id, code=code),
            fake_db,
        )
    assert exc_info.value.status_code == 400


def test_role_dependencies_reject_unprovisioned_and_wrong_roles():
    claimant = make_user()
    assert require_claimant(claimant) is claimant
    with pytest.raises(HTTPException) as exc_info:
        require_claims_officer(claimant)
    assert exc_info.value.status_code == 403

    officer = make_user(role="claims_officer", organization="Acme TPA")
    assert require_claims_officer(officer) is officer
    with pytest.raises(HTTPException) as exc_info:
        require_claims_officer(make_user(role="claims_officer", organization=" "))
    assert exc_info.value.status_code == 403
    with pytest.raises(HTTPException) as exc_info:
        require_claimant(make_user(role="Admin"))
    assert exc_info.value.status_code == 403


def test_claim_access_and_query_scope_use_ownership_or_exact_organization():
    claimant = make_user()
    officer = make_user(role="claims_officer", organization="Acme TPA")
    claim = SimpleNamespace(hospital_name="North Hospital", created_by=claimant.id)
    matching_policy = SimpleNamespace(insurance_provider=" acme tpa ")
    other_policy = SimpleNamespace(insurance_provider="Acme TPA Insurance")

    assert check_claim_access(claim, matching_policy, claimant)
    assert not check_claim_access(claim, matching_policy, make_user())
    assert check_claim_access(claim, matching_policy, officer)
    assert not check_claim_access(claim, other_policy, officer)
    assert not check_claim_access(claim, matching_policy, make_user(role="Admin"))

    query = apply_claim_scope(CapturedQuery(), claimant)
    claimant_filter = str(query.criteria[0].compile(dialect=postgresql.dialect())).lower()
    assert "created_by" in claimant_filter

    query = apply_claim_scope(CapturedQuery(), officer)
    compiled_officer_filter = query.criteria[0].compile(dialect=postgresql.dialect())
    officer_filter = str(compiled_officer_filter).lower()
    assert "insurance_provider" in officer_filter
    assert "acme tpa" in str(compiled_officer_filter.params).lower()


def test_claim_creation_ignores_client_decision_and_readiness_fields(client):
    test_client, fake_db = client
    user = make_user()
    app.dependency_overrides[get_current_user] = lambda: user
    response = test_client.post(
        "/claims",
        json={
            "patientName": "Synthetic Test Patient",
            "patientAge": 35,
            "hospital": "North Hospital",
            "policyNumber": "12345678",
            "insuranceProvider": "Acme TPA",
            "diagnosis": "Synthetic diagnosis",
            "admissionDate": "2026-01-01",
            "dischargeDate": "2026-01-03",
            "claimedAmount": 1000,
            "status": "Approved",
            "stage": "11 Final Decision",
            "readiness": 100,
            "ocrConfidence": 100,
        },
    )

    assert response.status_code == 200, response.text
    created_claim = next(record for record in fake_db.added if isinstance(record, Claim))
    assert created_claim.claim_status == "Under Analysis"
    assert created_claim.current_stage == "01 Secure Document Intake"
    assert created_claim.readiness_score == Decimal("0")
    assert created_claim.created_by == user.id


def test_claimant_amendment_is_limited_to_permitted_fields_and_audited():
    claimant = make_user()
    claim = SimpleNamespace(
        id=uuid.uuid4(),
        policy_id=uuid.uuid4(),
        patient_id=uuid.uuid4(),
        created_by=claimant.id,
        claim_status="Under Analysis",
        current_stage="01 Secure Document Intake",
        hospital_name="Original Hospital",
        admission_date=datetime(2026, 1, 1).date(),
        discharge_date=datetime(2026, 1, 3).date(),
        claimed_amount=Decimal("1000"),
    )
    patient = SimpleNamespace(full_name="Synthetic Patient")
    policy = SimpleNamespace(insurance_provider="Acme TPA")
    fake_db = FakeSession({Claim: claim, Patient: patient, Policy: policy})

    with pytest.raises(HTTPException) as exc_info:
        claims_api.request_claim_amendment(
            str(claim.id),
            ClaimAmendmentRequest(
                changes={"readiness": 100},
                reason="Attempt to alter system value",
            ),
            fake_db,
            claimant,
        )
    assert exc_info.value.status_code == 422
    assert not any(isinstance(record, ClaimAmendment) for record in fake_db.added)

    result = claims_api.request_claim_amendment(
        str(claim.id),
        ClaimAmendmentRequest(
            changes={"hospital": "Corrected Synthetic Hospital"},
            reason="Corrected provider detail",
        ),
        fake_db,
        claimant,
    )
    amendment = next(
        record for record in fake_db.added if isinstance(record, ClaimAmendment)
    )
    assert result["status"] == "Pending"
    assert amendment.original_values["hospital"] == "Original Hospital"
    assert amendment.requested_changes["hospital"] == "Corrected Synthetic Hospital"
    assert any(
        isinstance(record, AuditEvent)
        and record.event_type == "claim_amendment_requested"
        for record in fake_db.added
    )


def test_claims_officer_amendment_review_is_org_scoped_and_audited():
    officer = make_user(role="claims_officer", organization="Acme TPA")
    claim_id = uuid.uuid4()
    amendment = SimpleNamespace(
        id=uuid.uuid4(),
        claim_id=claim_id,
        status="Pending",
        requested_changes={"hospital": "Corrected Synthetic Hospital"},
        reviewed_by=None,
        review_note=None,
        reviewed_at=None,
    )
    claim = SimpleNamespace(
        id=claim_id,
        policy_id=uuid.uuid4(),
        patient_id=uuid.uuid4(),
        claim_status="Under Analysis",
        current_stage="01 Secure Document Intake",
        hospital_name="Original Hospital",
    )
    policy = SimpleNamespace(insurance_provider="Acme TPA")
    patient = SimpleNamespace(full_name="Synthetic Patient")
    fake_db = FakeSession(
        {
            ClaimAmendment: amendment,
            Claim: claim,
            Policy: policy,
            Patient: patient,
        }
    )

    result = claims_api.review_claim_amendment(
        str(amendment.id),
        ClaimAmendmentDecisionRequest(
            decision="Approve",
            note="Verified against submitted supporting evidence.",
        ),
        fake_db,
        officer,
    )

    assert result["status"] == "Approved"
    assert claim.hospital_name == "Corrected Synthetic Hospital"
    assert amendment.reviewed_by == officer.id
    assert any(
        isinstance(record, AuditEvent)
        and record.event_type == "claim_amendment_approved"
        for record in fake_db.added
    )


def test_final_tpa_decision_waits_for_pending_amendment():
    officer = make_user(role="claims_officer", organization="Acme TPA")
    claim = SimpleNamespace(
        id=uuid.uuid4(),
        claim_number="CLM-SYNTHETIC-1",
        policy_id=uuid.uuid4(),
        claim_status="Under Analysis",
        current_stage="01 Secure Document Intake",
    )
    policy = SimpleNamespace(insurance_provider="Acme TPA")
    pending_amendment = SimpleNamespace(status="Pending")
    fake_db = FakeSession(
        {
            Claim: claim,
            Policy: policy,
            ClaimAmendment: pending_amendment,
        }
    )

    with pytest.raises(HTTPException) as exc_info:
        claims_api.update_claim_status(
            str(claim.id),
            UpdateClaimStatusRequest(action="Approve", note="Review reason"),
            fake_db,
            officer,
        )

    assert exc_info.value.status_code == 409
    assert claim.claim_status == "Under Analysis"
