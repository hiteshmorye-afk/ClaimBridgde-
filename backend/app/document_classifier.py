"""
ClaimBridge Document Classifier

Automatic classification of medical and insurance claim documents
using extracted text, weighted keyword patterns, and structural cues.

Supported 15 Categories:
- Section A: Core Claim Documents
  1. claim_form (Duly Filled Claim Form)
  2. insurance_card (Health Insurance Card / Policy Schedule)
  3. identity_proof (KYC / Identity Proof: Aadhaar, PAN, Passport, Voter ID)
  4. bank_proof (Bank Details Proof: Cancelled Cheque, Passbook, Statement)
- Section B: Medical & Hospitalisation Documents
  5. discharge_summary (Discharge Summary / Discharge Card)
  6. consultation_letter (Doctor's Consultation Papers & Prescriptions)
  7. diagnostic_report (Investigation / Diagnostic Reports: Lab, Radiology)
- Section C: Financial & Billing Documents
  8. hospital_bill (Final Hospital Bill: Itemized / Summary)
  9. payment_receipt (Payment Receipts / Advance Deposits)
  10. pharmacy_bill (Pharmacy & Medical Store Bills)
- Section D: Special Circumstances
  11. fir_mlc (Medico-Legal Certificate / First Information Report)
  12. implant_invoice (Implant Invoice & Sticker / Outer Pouch)
  13. ambulance_receipt (Ambulance Receipt / Certificate)
  14. pre_authorization (Pre-Authorization Approval Letter / Query Sheet)
- Section E: Other Supporting Documents
  15. other_medical_doc (Other Supporting Medical / Non-Medical Documents)
"""

import re
from typing import Any, Dict, List, Optional


# =========================================================
# DOCUMENT TYPE EVIDENCE RULES (WEIGHTED)
# =========================================================

DOCUMENT_EVIDENCE: Dict[str, Dict[str, Any]] = {
    # --- Section A: Core Claim Documents ---
    "claim_form": {
        "strong": [
            r"\bclaim\s+form\b",
            r"\bpart\s*[-–]\s*a\b",
            r"\bpart\s*[-–]\s*b\b",
            r"\bclaimant\s+declaration\b",
            r"\bto\s+be\s+filled\s+by\s+the\s+insured\b",
            r"\bhealth\s+insurance\s+claim\s+form\b",
            r"\bdetails\s+of\s+primary\s+insured\b",
            r"\bhospitalization\s+claim\s+form\b",
        ],
        "medium": [
            r"\bclaim\s+(?:no|number|id)\b",
            r"\bpolicy\s+holder\b",
            r"\bdate\s+of\s+commencement\b",
            r"\battending\s+physician\b",
            r"\bdetails\s+of\s+hospital\b",
            r"\bdetails\s+of\s+claim\b",
            r"\bpre-?hospitalization\s+expenses\b",
            r"\bpost-?hospitalization\s+expenses\b",
            r"\bclaimant\s+signature\b",
        ],
        "standard": [
            r"\bclaim\b",
            r"\binsured\b",
            r"\bdeclaration\b",
            r"\bsignature\b",
            r"\breimbursement\b",
        ],
    },
    "insurance_card": {
        "strong": [
            r"\bhealth\s+card\b",
            r"\binsurance\s+card\b",
            r"\bpolicy\s+schedule\b",
            r"\be-?health\s+card\b",
            r"\bmember\s+id\s+card\b",
            r"\bmediclaim\s+card\b",
            r"\bhealth\s+insurance\s+policy\b",
            r"\bcertificate\s+of\s+insurance\b",
        ],
        "medium": [
            r"\bvalid\s+(?:upto|from|thru|through)\b",
            r"\bpolicy\s+(?:no|number)\b",
            r"\bsum\s+insured\b",
            r"\bcard\s+number\b",
            r"\bbenefit\s+plan\b",
            r"\bgroup\s+policy\b",
            r"\bvalidity\b",
            r"\bmember\s+id\b",
            r"\bpolicy\s+period\b",
        ],
        "standard": [
            r"\binsurance\b",
            r"\bpolicy\b",
            r"\btpa\b",
            r"\bholder\b",
            r"\bcoverage\b",
        ],
    },
    "identity_proof": {
        "strong": [
            r"\baadhaar\b",
            r"\bunique\s+identification\s+authority\s+of\s+india\b",
            r"\buidai\b",
            r"\bincome\s+tax\s+department\b",
            r"\bpermanent\s+account\s+number\b",
            r"\bpan\s+card\b",
            r"\bpassport\b",
            r"\belection\s+commission\s+of\s+india\b",
            r"\bvoter\s+identity\s+card\b",
            r"\bvoter\s+id\b",
        ],
        "medium": [
            r"\bgovernment\s+of\s+india\b",
            r"\bfather['’]?s\s+name\b",
            r"\bdate\s+of\s+birth\b",
            r"\bdob\b",
            r"\bgender\b",
            r"\bmale\b",
            r"\bfemale\b",
            r"\belectoral\s+photo\b",
            r"\brepublic\s+of\s+india\b",
        ],
        "standard": [
            r"\bidentity\b",
            r"\bphoto\b",
            r"\baddress\b",
            r"\byear\s+of\s+birth\b",
        ],
    },
    "bank_proof": {
        "strong": [
            r"\bcancelled\s+cheque\b",
            r"\bcheque\b",
            r"\bbank\s+passbook\b",
            r"\bpassbook\b",
            r"\bbank\s+statement\b",
            r"\baccount\s+statement\b",
        ],
        "medium": [
            r"\bifsc\s*(?:code)?\b",
            r"\baccount\s+(?:no|number)\b",
            r"\ba/c\s+no\b",
            r"\bbranch\s+name\b",
            r"\bmicr\s+code\b",
            r"\baccount\s+holder\b",
            r"\bsavings\s+a/c\b",
            r"\bcurrent\s+a/c\b",
        ],
        "standard": [
            r"\bbank\b",
            r"\bbranch\b",
            r"\bstatement\b",
            r"\bbalance\b",
            r"\bdeposit\b",
        ],
    },

    # --- Section B: Medical & Hospitalisation Documents ---
    "discharge_summary": {
        "strong": [
            r"\bdischarge\s+summary\b",
            r"\bdischarge\s+card\b",
            r"\bclinical\s+discharge\s+summary\b",
            r"\bdischarge\s+diagnosis\b",
            r"\bcondition\s+at\s+discharge\b",
            r"\badvice\s+on\s+discharge\b",
            r"\bhospital\s+course\b",
            r"\bcourse\s+in\s+the\s+hospital\b",
        ],
        "medium": [
            r"\bdate\s+of\s+admission\b",
            r"\bdate\s+of\s+discharge\b",
            r"\bhistory\s+of\s+present\s+illness\b",
            r"\bclinical\s+summary\b",
            r"\btreatment\s+given\b",
            r"\boperative\s+findings\b",
            r"\bprocedure\s+performed\b",
            r"\bphysical\s+findings\b",
            r"\bfollow\s*-\s*up\s+instructions\b",
            r"\battending\s+physician\b",
            r"\bconsultant\s+in\s*charge\b",
        ],
        "standard": [
            r"\badmission\b",
            r"\bdischarge\b",
            r"\bpatient\s+condition\b",
            r"\bvitals\b",
            r"\bmedications\s+advised\b",
        ],
    },
    "prescription": {
        "strong": [
            r"\bprescription\b",
            r"\brx\b",
            r"\bprescribed\s+medications\b",
            r"\bmedical\s+prescription\b",
            r"\bdoctor['’]?s\s+prescription\b",
        ],
        "medium": [
            r"\btab(?:let)?\.?\b",
            r"\bcap(?:sule)?\.?\b",
            r"\bsyp(?:rup)?\.?\b",
            r"\binj(?:ection)?\.?\b",
            r"\bdosage\b",
            r"\bdose\b",
            r"\bfrequency\b",
            r"\bduration\b",
            r"\b1-0-1\b",
            r"\b1-1-1\b",
            r"\b0-0-1\b",
            r"\b1-0-0\b",
        ],
        "standard": [
            r"\bmedicine\b",
            r"\bmg\b",
            r"\bml\b",
            r"\bpharmacy\b",
        ],
    },
    "consultation_letter": {
        "strong": [
            r"\bconsultation\s+paper\b",
            r"\bconsultant\s+notes\b",
            r"\bopd\s+slip\b",
            r"\bout-?patient\s+record\b",
            r"\bclinic\s+visit\b",
            r"\breferral\s+letter\b",
            r"\bdoctor['’]?s\s+consultation\b",
        ],
        "medium": [
            r"\bchief\s+complaints?\b",
            r"\bsymptoms\b",
            r"\bon\s+examination\b",
            r"\bclinical\s+notes\b",
            r"\bfollow\s*-\s*up\b",
        ],
        "standard": [
            r"\bpatient\b",
            r"\bdoctor\b",
            r"\bclinic\b",
            r"\bdiagnosis\b",
        ],
    },
    "lab_report": {
        "strong": [
            r"\blaboratory\s+report\b",
            r"\blab\s+report\b",
            r"\bpathology\s+report\b",
            r"\btest\s+results?\b",
            r"\bclinical\s+laboratory\b",
        ],
        "medium": [
            r"\breference\s+(?:range|interval|values)\b",
            r"\bobserved\s+value\b",
            r"\bhemoglobin\b",
            r"\bcomplete\s+blood\s+count\b",
            r"\bcbc\b",
            r"\bwbc\b",
            r"\brbc\b",
            r"\bplatelets\b",
            r"\bserum\s+creatinine\b",
            r"\bblood\s+glucose\b",
            r"\blipid\s+profile\b",
            r"\blft\b",
            r"\bkft\b",
            r"\bspecimen\b",
        ],
        "standard": [
            r"\bnormal\b",
            r"\babnormal\b",
            r"\bhigh\b",
            r"\blow\b",
            r"\bpositive\b",
            r"\bnegative\b",
        ],
    },
    "diagnostic_report": {
        "strong": [
            r"\bdiagnostic\s+report\b",
            r"\bradiology\s+report\b",
            r"\bultrasound\s+report\b",
            r"\bct\s+scan\b",
            r"\bmri\s+report\b",
            r"\bx-?ray\s+report\b",
            r"\becg\s+report\b",
            r"\binvestigation\s+report\b",
        ],
        "medium": [
            r"\bimpression\b",
            r"\bfindings\b",
            r"\bsonography\b",
            r"\bradiologist\b",
            r"\bobserved\s+value\b",
        ],
        "standard": [
            r"\bnormal\b",
            r"\babnormal\b",
            r"\bscan\b",
        ],
    },
    "insurance_policy": {
        "strong": [
            r"\binsurance\s+policy\b",
            r"\bpolicy\s+schedule\b",
            r"\bpolicy\s+document\b",
            r"\bcertificate\s+of\s+insurance\b",
            r"\bhealth\s+insurance\s+policy\b",
            r"\bpolicy\s+wording\b",
        ],
        "medium": [
            r"\bpolicy\s+number\b",
            r"\bpolicy\s+period\b",
            r"\bperiod\s+of\s+insurance\b",
            r"\bsum\s+insured\b",
            r"\bcumulative\s+bonus\b",
            r"\bdeductible\b",
            r"\bco-?payment\b",
            r"\bwaiting\s+period\b",
            r"\bpermanent\s+exclusions\b",
            r"\broom\s+rent\s+limit\b",
            r"\binsured\s+person\b",
            r"\bproposer\b",
            r"\bpremium\b",
            r"\btpa\b",
        ],
        "standard": [
            r"\bcoverage\b",
            r"\binsurer\b",
            r"\bclaim\s+procedure\b",
            r"\bterms\s+and\s+conditions\b",
        ],
    },
    "medical_report": {
        "strong": [
            r"\bmedical\s+report\b",
            r"\bclinical\s+report\b",
            r"\bmedical\s+certificate\b",
            r"\bconsultation\s+report\b",
            r"\bdoctor['’]?s\s+report\b",
        ],
        "medium": [
            r"\bclinical\s+findings\b",
            r"\bexamination\s+findings\b",
            r"\bimpression\b",
            r"\bprovisional\s+diagnosis\b",
            r"\bfinal\s+diagnosis\b",
            r"\bchief\s+complaints?\b",
            r"\bhistory\s+of\s+presenting\s+illness\b",
            r"\brecommendations?\b",
            r"\bopinion\b",
        ],
        "standard": [
            r"\bdiagnosis\b",
            r"\bexamination\b",
            r"\bfindings\b",
            r"\bclinical\b",
        ],
    },

    # --- Section C: Financial & Billing Documents ---
    "hospital_bill": {
        "strong": [
            r"\btax\s+invoice\b",
            r"\bhospital\s+bill\b",
            r"\bstatement\s+of\s+account\b",
            r"\binterim\s+bill\b",
            r"\bfinal\s+bill\b",
            r"\bbilling\s+summary\b",
            r"\binvoice\s+no\b",
            r"\bbill\s+no\b",
            r"\bamount\s+due\b",
            r"\bamount\s+payable\b",
            r"\btotal\s+charges\b",
        ],
        "medium": [
            r"\broom\s+(?:rent|charges|accommodation)\b",
            r"\bpharmacy\s+charges\b",
            r"\bconsultation\s+fee\b",
            r"\bnursing\s+charges\b",
            r"\blaboratory\s+charges\b",
            r"\bot\s+charges\b",
            r"\boperating\s+room\b",
            r"\bpatient\s+deposit\b",
            r"\bdiscount\b",
            r"\bgst\b",
            r"\btax\b",
            r"\bsubtotal\b",
            r"\badvance\s+paid\b",
            r"\bbalance\s+due\b",
        ],
        "standard": [
            r"\binvoice\b",
            r"\bbill\b",
            r"\bcharges\b",
            r"\bpayment\b",
            r"\brate\b",
            r"\bqty\b",
            r"\bquantity\b",
        ],
    },
    "payment_receipt": {
        "strong": [
            r"\bpayment\s+receipt\b",
            r"\bmoney\s+receipt\b",
            r"\badvance\s+receipt\b",
            r"\bofficial\s+receipt\b",
            r"\bcash\s+receipt\b",
            r"\bsettlement\s+receipt\b",
            r"\backnowledgement\s+receipt\b",
        ],
        "medium": [
            r"\breceived\s+with\s+thanks\b",
            r"\breceived\s+from\b",
            r"\bsum\s+of\s+rupees\b",
            r"\bamount\s+paid\b",
            r"\bpayment\s+mode\b",
            r"\btransaction\s+id\b",
            r"\bneft\b",
            r"\brtgs\b",
            r"\bupi\s+ref\b",
            r"\bcheque\s+no\b",
            r"\breceipt\s+number\b",
        ],
        "standard": [
            r"\breceipt\b",
            r"\bpaid\b",
            r"\bpayment\b",
            r"\bbalance\b",
        ],
    },
    "pharmacy_bill": {
        "strong": [
            r"\bpharmacy\s+bill\b",
            r"\bmedical\s+store\b",
            r"\bchemist\s+bill\b",
            r"\bcash\s+memo\b",
            r"\bdrug\s+invoice\b",
            r"\bpharmacy\s+tax\s+invoice\b",
            r"\bretail\s+pharmacy\b",
        ],
        "medium": [
            r"\bbatch\s+(?:no|number)\b",
            r"\bexp(?:iry)?\.?\s+date\b",
            r"\bmfg\s+date\b",
            r"\bmrp\b",
            r"\bdrug\s+licence\b",
            r"\bdl\s+no\b",
            r"\bhsn\b",
            r"\bgst\b",
        ],
        "standard": [
            r"\btablets?\b",
            r"\bcapsules?\b",
            r"\bqty\b",
            r"\brate\b",
            r"\bamount\b",
            r"\bpharmacy\b",
        ],
    },

    # --- Section D: Special Circumstances ---
    "fir_mlc": {
        "strong": [
            r"\bfirst\s+information\s+report\b",
            r"\bfir\b",
            r"\bmedico-?legal\s+certificate\b",
            r"\bmlc\s*(?:report|no|case)?\b",
            r"\bpolice\s+station\b",
            r"\bpolice\s+report\b",
            r"\brta\b",
            r"\broad\s+traffic\s+accident\b",
        ],
        "medium": [
            r"\balcohol\s+consumed\b",
            r"\bbrought\s+by\s+police\b",
            r"\bhistory\s+of\s+assault\b",
            r"\binjury\s+report\b",
            r"\boffence\b",
            r"\bsection\s+\d+\s+ipc\b",
            r"\btime\s+of\s+incident\b",
            r"\bplace\s+of\s+occurrence\b",
        ],
        "standard": [
            r"\baccident\b",
            r"\binjury\b",
            r"\btrauma\b",
            r"\bpolice\b",
        ],
    },
    "implant_invoice": {
        "strong": [
            r"\bimplant\s+invoice\b",
            r"\bimplant\s+sticker\b",
            r"\bouter\s+pouch\b",
            r"\bstent\s+invoice\b",
            r"\bpacemaker\s+invoice\b",
            r"\borthopaedic\s+implant\b",
            r"\bprosthetic\s+device\b",
        ],
        "medium": [
            r"\blot\s+(?:no|number)\b",
            r"\bbatch\s+(?:no|number)\b",
            r"\bserial\s+(?:no|number)\b",
            r"\bexpiry\s+date\b",
            r"\bmodel\s+(?:no|number)\b",
            r"\bcatheter\b",
            r"\bmesh\b",
            r"\bballoon\b",
            r"\budi\b",
            r"\bunique\s+device\s+id\b",
        ],
        "standard": [
            r"\bimplant\b",
            r"\bdevice\b",
            r"\bmanufacturer\b",
            r"\bsterile\b",
        ],
    },
    "ambulance_receipt": {
        "strong": [
            r"\bambulance\s+receipt\b",
            r"\bambulance\s+service\b",
            r"\bemergency\s+transit\b",
            r"\bpatient\s+transport\b",
            r"\bambulance\s+bill\b",
            r"\blife\s+support\s+ambulance\b",
        ],
        "medium": [
            r"\bvehicle\s+no\b",
            r"\bpickup\s+location\b",
            r"\bfrom\s*:\s*[a-z0-9\s.]+\b",
            r"\bto\s*:\s*[a-z0-9\s.]+\b",
            r"\btotal\s+kms?\b",
            r"\bdistance\b",
            r"\bwaiting\s+charges\b",
            r"\boxygen\s+charges\b",
        ],
        "standard": [
            r"\bambulance\b",
            r"\btransport\b",
            r"\bdriver\b",
            r"\btrip\b",
        ],
    },
    "pre_authorization": {
        "strong": [
            r"\bpre-?authorization\s+letter\b",
            r"\bcashless\s+authorization\b",
            r"\bpre-?auth\s+approval\b",
            r"\binitial\s+authorization\b",
            r"\benhancement\s+authorization\b",
            r"\bguarantee\s+of\s+payment\b",
            r"\bpre-?auth\s+form\b",
        ],
        "medium": [
            r"\bpre-?auth\s+(?:no|number|ref|id)\b",
            r"\bapproved\s+amount\b",
            r"\bsanctioned\s+amount\b",
            r"\btpa\s+approval\b",
            r"\bcashless\s+access\b",
            r"\bdenial\s+of\s+cashless\b",
            r"\bquery\s+sheet\b",
        ],
        "standard": [
            r"\bpre-?auth\b",
            r"\bcashless\b",
            r"\bapproval\b",
            r"\bauthorization\b",
        ],
    },

    # --- Section E: Other Supporting Documents ---
    "other_medical_doc": {
        "strong": [
            r"\bmedical\s+certificate\b",
            r"\bfitness\s+certificate\b",
            r"\bdeath\s+certificate\b",
            r"\bleave\s+certificate\b",
            r"\bemanation\s+certificate\b",
        ],
        "medium": [
            r"\bto\s+whomsoever\s+it\s+may\s+concern\b",
            r"\bthis\s+is\s+to\s+certify\b",
            r"\bsuffering\s+from\b",
            r"\badvised\s+rest\b",
        ],
        "standard": [
            r"\bcertificate\b",
            r"\bdocument\b",
            r"\bstatement\b",
        ],
    },
}


# =========================================================
# CATEGORY NORMALIZATION MAP
# =========================================================

CATEGORY_NORMALIZATION_MAP: Dict[str, str] = {
    # Section A
    "claim form": "claim_form",
    "claim_form": "claim_form",
    "duly filled claim form": "claim_form",
    "part a": "claim_form",
    "insurance card": "insurance_card",
    "insurance_card": "insurance_card",
    "insurance policy": "insurance_card",
    "insurance_policy": "insurance_card",
    "policy schedule": "insurance_card",
    "health insurance card": "insurance_card",
    "health insurance card / policy schedule": "insurance_card",
    "identity proof": "identity_proof",
    "identity_proof": "identity_proof",
    "kyc": "identity_proof",
    "kyc / identity proof": "identity_proof",
    "aadhaar": "identity_proof",
    "pan": "identity_proof",
    "passport": "identity_proof",
    "bank proof": "bank_proof",
    "bank_proof": "bank_proof",
    "bank details proof": "bank_proof",
    "cancelled cheque": "bank_proof",
    "passbook": "bank_proof",

    # Section B
    "discharge summary": "discharge_summary",
    "discharge_summary": "discharge_summary",
    "discharge card": "discharge_summary",
    "discharge summary / discharge card": "discharge_summary",
    "consultation letter": "consultation_letter",
    "consultation_letter": "consultation_letter",
    "doctor's consultation papers": "consultation_letter",
    "doctor's consultation papers & prescriptions": "consultation_letter",
    "prescription": "consultation_letter",
    "rx": "consultation_letter",
    "diagnostic report": "diagnostic_report",
    "diagnostic_report": "diagnostic_report",
    "investigation report": "diagnostic_report",
    "investigation / diagnostic reports": "diagnostic_report",
    "lab report": "diagnostic_report",
    "lab_report": "diagnostic_report",
    "laboratory report": "diagnostic_report",

    # Section C
    "hospital bill": "hospital_bill",
    "hospital_bill": "hospital_bill",
    "final hospital bill": "hospital_bill",
    "final hospital bill (itemized / summary)": "hospital_bill",
    "final hospital bill (itemized)": "hospital_bill",
    "bill": "hospital_bill",
    "invoice": "hospital_bill",
    "payment receipt": "payment_receipt",
    "payment_receipt": "payment_receipt",
    "payment receipts": "payment_receipt",
    "receipt": "payment_receipt",
    "pharmacy bill": "pharmacy_bill",
    "pharmacy_bill": "pharmacy_bill",
    "pharmacy & medical store bills": "pharmacy_bill",
    "medical store bill": "pharmacy_bill",

    # Section D
    "fir": "fir_mlc",
    "mlc": "fir_mlc",
    "fir_mlc": "fir_mlc",
    "fir / mlc": "fir_mlc",
    "medico-legal certificate (mlc) / fir": "fir_mlc",
    "medico-legal certificate": "fir_mlc",
    "first information report": "fir_mlc",
    "implant invoice": "implant_invoice",
    "implant_invoice": "implant_invoice",
    "implant invoice & sticker": "implant_invoice",
    "implant invoice & sticker / outer pouch": "implant_invoice",
    "ambulance receipt": "ambulance_receipt",
    "ambulance_receipt": "ambulance_receipt",
    "ambulance receipt / certificate": "ambulance_receipt",
    "pre authorization": "pre_authorization",
    "pre_authorization": "pre_authorization",
    "pre-authorization": "pre_authorization",
    "pre auth": "pre_authorization",
    "pre-auth": "pre_authorization",
    "pre-authorization approval letter / query sheet": "pre_authorization",
    "pre-authorization form": "pre_authorization",

    # Section E
    "other medical doc": "other_medical_doc",
    "other_medical_doc": "other_medical_doc",
    "other supporting documents": "other_medical_doc",
    "medical report": "other_medical_doc",
    "medical_report": "other_medical_doc",
    "unknown": "unknown",
}


def normalize_category_name(category: Optional[str]) -> str:
    """Normalize user or UI category name into standard backend type."""
    if not category:
        return "unknown"
    cleaned = category.strip().lower()
    return CATEGORY_NORMALIZATION_MAP.get(cleaned, cleaned.replace(" ", "_"))


# =========================================================
# DOCUMENT CLASSIFICATION
# =========================================================

def classify_text_segment(text: str) -> Dict[str, Any]:
    """
    Score and classify a specific segment of text (e.g. a page or document).
    """
    if not text or not text.strip():
        return {
            "document_type": "unknown",
            "confidence": 0.0,
            "matched_keywords": [],
            "scores": {},
        }

    text_lower = text.lower()
    scores: Dict[str, float] = {}
    matched_by_type: Dict[str, List[str]] = {}

    for doc_type, rules in DOCUMENT_EVIDENCE.items():
        matched: List[str] = []
        score = 0.0

        # Strong matches: 3.0 points each
        for pattern in rules.get("strong", []):
            if re.search(pattern, text_lower):
                clean_term = pattern.replace(r"\b", "").replace(r"\s+", " ").replace("\\", "")
                matched.append(clean_term)
                score += 3.0

        # Medium matches: 1.5 points each
        for pattern in rules.get("medium", []):
            if re.search(pattern, text_lower):
                clean_term = pattern.replace(r"\b", "").replace(r"\s+", " ").replace("\\", "")
                matched.append(clean_term)
                score += 1.5

        # Standard matches: 0.5 points each
        for pattern in rules.get("standard", []):
            if re.search(pattern, text_lower):
                clean_term = pattern.replace(r"\b", "").replace(r"\s+", " ").replace("\\", "")
                matched.append(clean_term)
                score += 0.5

        scores[doc_type] = round(score, 2)
        matched_by_type[doc_type] = matched

    # Find the highest-scoring document type
    best_type = max(scores, key=lambda k: scores[k])
    best_score = scores[best_type]
    best_matched = matched_by_type[best_type]

    # If best score is below minimum threshold (e.g., 2.0), consider unknown
    if best_score < 2.0:
        return {
            "document_type": "unknown",
            "confidence": 0.0,
            "matched_keywords": [],
            "scores": scores,
        }

    # Calibrate confidence based on score and evidence count
    # 2.0 pts -> ~0.65, 5.0 pts -> ~0.85, 8.0+ pts -> 0.98
    confidence = min(0.60 + (best_score / 15.0) * 0.38, 0.98)

    return {
        "document_type": best_type,
        "confidence": round(confidence, 2),
        "matched_keywords": best_matched,
        "scores": scores,
    }


def classify_document(
    text: str,
    pages_text: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Classifies a medical/insurance document using OCR text and evidence cues.

    Supports document-level classification and optional page-level classification
    when multi-page texts are provided.
    """
    overall = classify_text_segment(text)

    page_results = []
    if pages_text and len(pages_text) > 1:
        for idx, page_t in enumerate(pages_text, start=1):
            p_class = classify_text_segment(page_t)
            page_results.append({
                "page": idx,
                "document_type": p_class["document_type"],
                "confidence": p_class["confidence"],
                "matched_keywords": p_class["matched_keywords"],
            })

    result = {
        "document_type": overall["document_type"],
        "confidence": overall["confidence"],
        "matched_keywords": overall["matched_keywords"],
        "category_scores": overall["scores"],
    }

    if page_results:
        result["page_classifications"] = page_results

    return result