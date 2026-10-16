import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.models import AuditEvent, User


LEGACY_ROLES = {"Coordinator", "PendingCoordinator", "Reviewer", "Admin"}
TARGET_ROLES = {"claimant", "claims_officer"}


def get_account(db, email: str) -> User:
    user = db.query(User).filter(User.email.ilike(email.strip())).first()
    if not user:
        raise SystemExit("Account not found.")
    return user


def prepare_legacy_account(args) -> None:
    db = SessionLocal()
    try:
        user = get_account(db, args.email)
        if user.role not in LEGACY_ROLES:
            raise SystemExit("Only an existing legacy-role account can be prepared.")
        user.account_status = "pending_role_mapping"
        user.email_verified_at = None
        db.add(
            AuditEvent(
                event_type="legacy_account_mapping_started",
                actor_user_id=None,
                details={
                    "user_id": str(user.id),
                    "legacy_role": user.role,
                    "operator_reference": args.operator_reference,
                },
            )
        )
        db.commit()
        print("Account prepared for email OTP verification; its stored role was not changed.")
    finally:
        db.close()


def map_account(args) -> None:
    db = SessionLocal()
    try:
        user = get_account(db, args.email)
        if user.role not in TARGET_ROLES | LEGACY_ROLES:
            raise SystemExit("Account role is not eligible for explicit mapping.")
        if not user.email_verified_at:
            raise SystemExit("Complete email OTP verification before mapping this account.")
        if not args.operator_reference.strip():
            raise SystemExit("An operator reference is required for the audit record.")

        old_role = user.role
        user.role = args.role
        user.account_status = "active"
        user.provisioned_by = None
        if args.role == "claims_officer":
            if not args.organization or not args.confirm_tpa_authorized:
                raise SystemExit(
                    "Claims officer mapping requires an organization and explicit trusted-authorization confirmation."
                )
            user.organization = args.organization.strip()
            user.organization_verified_at = datetime.utcnow()
            user.portal = "TPA"
        else:
            if args.phone:
                if not re.fullmatch(r"\+?[0-9]{8,15}", args.phone.strip()):
                    raise SystemExit("Phone number must contain 8 to 15 digits.")
                user.phone = args.phone.strip()
            if not user.phone:
                raise SystemExit("A phone number is required when mapping a claimant account.")
            user.organization_verified_at = None
            user.portal = "Claimant"

        db.add(
            AuditEvent(
                event_type="account_role_mapped",
                actor_user_id=None,
                details={
                    "user_id": str(user.id),
                    "previous_role": old_role,
                    "new_role": args.role,
                    "organization": user.organization if args.role == "claims_officer" else None,
                    "operator_reference": args.operator_reference,
                },
            )
        )
        db.commit()
        print(f"Account explicitly mapped to {args.role}.")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Explicitly prepare or map one verified ClaimBridge account."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    prepare = commands.add_parser("prepare-legacy")
    prepare.add_argument("--email", required=True)
    prepare.add_argument("--operator-reference", required=True)
    prepare.set_defaults(run=prepare_legacy_account)

    mapping = commands.add_parser("map")
    mapping.add_argument("--email", required=True)
    mapping.add_argument("--role", choices=sorted(TARGET_ROLES), required=True)
    mapping.add_argument("--organization")
    mapping.add_argument("--phone")
    mapping.add_argument("--confirm-tpa-authorized", action="store_true")
    mapping.add_argument("--operator-reference", required=True)
    mapping.set_defaults(run=map_account)

    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
