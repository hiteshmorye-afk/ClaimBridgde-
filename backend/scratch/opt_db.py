with open("backend/app/documents.py", "r", encoding="utf-8") as f:
    text = f.read()

target = """    claim = None
    if claim_id:
        try:
            claim_uuid = uuid.UUID(claim_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid claim ID.")

        claim = db.query(Claim).filter(Claim.id == claim_uuid).first()
        if not claim:
            raise HTTPException(
                status_code=404,
                detail="Claim not found. Create the claim before uploading documents.",
            )
    else:
        claims_query = (
            db.query(Claim, Policy)
            .outerjoin(Policy, Claim.policy_id == Policy.id)
            .order_by(Claim.created_at.desc())
        )
        claims_query = apply_claim_scope(claims_query, user)
        scoped_claim = claims_query.first()
        claim = scoped_claim[0] if scoped_claim else None"""

replacement = """    claim = None
    claim_policy = None
    if claim_id:
        try:
            claim_uuid = uuid.UUID(claim_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid claim ID.")

        row = (
            db.query(Claim, Policy)
            .outerjoin(Policy, Claim.policy_id == Policy.id)
            .filter(Claim.id == claim_uuid)
            .first()
        )
        if not row or not row[0]:
            raise HTTPException(
                status_code=404,
                detail="Claim not found. Create the claim before uploading documents.",
            )
        claim, claim_policy = row[0], row[1]
    else:
        claims_query = (
            db.query(Claim, Policy)
            .outerjoin(Policy, Claim.policy_id == Policy.id)
            .order_by(Claim.created_at.desc())
        )
        claims_query = apply_claim_scope(claims_query, user)
        scoped_claim = claims_query.first()
        if scoped_claim:
            claim, claim_policy = scoped_claim[0], scoped_claim[1]"""

target_crlf = target.replace("\n", "\r\n")
replacement_crlf = replacement.replace("\n", "\r\n")

if target in text:
    text = text.replace(target, replacement, 1)
    print("Replaced with LF")
elif target_crlf in text:
    text = text.replace(target_crlf, replacement_crlf, 1)
    print("Replaced with CRLF")
else:
    print("Target not found!")

# Also replace claim_policy lookup
old_lookup = '    claim_policy = db.query(Policy).filter(Policy.id == claim.policy_id).first() if (claim and claim.policy_id) else None'
new_lookup = '    if not claim_policy and claim and claim.policy_id:\n        claim_policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()'

if old_lookup in text:
    text = text.replace(old_lookup, new_lookup, 1)
elif old_lookup.replace('\n', '\r\n') in text:
    text = text.replace(old_lookup.replace('\n', '\r\n'), new_lookup.replace('\n', '\r\n'), 1)

with open("backend/app/documents.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Done updating claim/policy lookup.")
