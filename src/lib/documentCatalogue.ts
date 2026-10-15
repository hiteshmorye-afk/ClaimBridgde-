/**
 * ClaimBridge Document Intake Catalogue
 *
 * Configurable 15-category insurance document repository organized into
 * 5 logical sections with context-aware requirements (Mandatory, Conditional, Optional),
 * multi-upload definitions, and sensitive data masking.
 */

export type DocumentCategory =
  | "claim_form"
  | "insurance_card"
  | "identity_proof"
  | "bank_proof"
  | "discharge_summary"
  | "consultation_letter"
  | "diagnostic_report"
  | "hospital_bill"
  | "payment_receipt"
  | "pharmacy_bill"
  | "fir_mlc"
  | "implant_invoice"
  | "ambulance_receipt"
  | "pre_authorization"
  | "other_medical_doc";

export type DocumentSectionId =
  | "core"
  | "medical"
  | "financial"
  | "special"
  | "other";

export type DocumentRequirement = "mandatory" | "conditional" | "optional";

export interface ClaimContext {
  claimType: "reimbursement" | "cashless";
  isAccident?: boolean;
  hasImplant?: boolean;
  hasAmbulance?: boolean;
}

export interface DocumentCategoryMeta {
  id: DocumentCategory;
  name: string;
  section: DocumentSectionId;
  description: string;
  acceptedFormats: string[];
  multiple: boolean;
  sensitiveMasking: boolean;
  helpText: string;
}

export interface DocumentSectionMeta {
  id: DocumentSectionId;
  title: string;
  subtitle: string;
  badge: string;
}

export const DOCUMENT_SECTIONS: DocumentSectionMeta[] = [
  {
    id: "core",
    title: "A. Core Claim Documents",
    subtitle: "Principal forms, policy schedule, and KYC identity proofs required for claim registration.",
    badge: "Identity & Policy",
  },
  {
    id: "medical",
    title: "B. Medical & Hospitalisation Documents",
    subtitle: "Clinical course, admission/discharge summaries, doctor orders, and diagnostic evidence.",
    badge: "Clinical Evidence",
  },
  {
    id: "financial",
    title: "C. Financial & Billing Documents",
    subtitle: "Itemized bills, payment settlement receipts, and pharmacy cash memos for arithmetic validation.",
    badge: "Billing & Receipts",
  },
  {
    id: "special",
    title: "D. Special Circumstances",
    subtitle: "Contextual proofs for trauma, surgical implants, emergency transit, or pre-authorizations.",
    badge: "Conditional Protocols",
  },
  {
    id: "other",
    title: "E. Other Supporting Documents",
    subtitle: "Miscellaneous clinical records, fitness certificates, or employer leave documentation.",
    badge: "Supplementary",
  },
];

export const DOCUMENT_CATALOGUE: DocumentCategoryMeta[] = [
  // --- Section A: Core Claim Documents ---
  {
    id: "claim_form",
    name: "Duly Filled Claim Form",
    section: "core",
    description: "Official insurer claim form (Part A: policyholder, Part B: hospital) with signed declarations and requested amounts.",
    acceptedFormats: [".pdf", ".png", ".jpg", ".jpeg"],
    multiple: false,
    sensitiveMasking: false,
    helpText: "Extracts claim number, policy number, hospitalization details, and requested reimbursement amount.",
  },
  {
    id: "insurance_card",
    name: "Health Insurance Card / Policy Schedule",
    section: "core",
    description: "Insurer health ID card or active policy document establishing coverage period and sum insured.",
    acceptedFormats: [".pdf", ".png", ".jpg", ".jpeg"],
    multiple: false,
    sensitiveMasking: false,
    helpText: "Extracts policy number, insurer/TPA name, insured members, and valid coverage dates.",
  },
  {
    id: "identity_proof",
    name: "KYC / Identity Proof",
    section: "core",
    description: "Government-approved photo ID (Aadhaar, PAN, Passport, or Voter ID) for claimant identification.",
    acceptedFormats: [".pdf", ".png", ".jpg", ".jpeg"],
    multiple: false,
    sensitiveMasking: true,
    helpText: "Extracts identity holder name, DOB, and masked unique identifier (e.g. XXXX-XXXX-1234).",
  },
  {
    id: "bank_proof",
    name: "Bank Details Proof",
    section: "core",
    description: "Cancelled cheque, bank passbook front page, or recent statement displaying printed IFSC and account number.",
    acceptedFormats: [".pdf", ".png", ".jpg", ".jpeg"],
    multiple: false,
    sensitiveMasking: true,
    helpText: "Mandatory for reimbursement claims to disburse settlement funds directly to policyholder account.",
  },

  // --- Section B: Medical & Hospitalisation Documents ---
  {
    id: "discharge_summary",
    name: "Discharge Summary / Discharge Card",
    section: "medical",
    description: "Hospital discharge summary detailing admission & discharge timestamps, clinical history, diagnosis, and treatment given.",
    acceptedFormats: [".pdf", ".png", ".jpg", ".jpeg"],
    multiple: false,
    sensitiveMasking: false,
    helpText: "Extracts admission/discharge dates, primary diagnosis, surgical procedures, and treating consultant.",
  },
  {
    id: "consultation_letter",
    name: "Doctor's Consultation Papers & Prescriptions",
    section: "medical",
    description: "Outpatient consultation sheet, initial prescription slips, and attending physician's clinical notes.",
    acceptedFormats: [".pdf", ".png", ".jpg", ".jpeg"],
    multiple: false,
    sensitiveMasking: false,
    helpText: "Extracts consulting doctor, clinical complaints, symptoms history, and initial medication regimen.",
  },
  {
    id: "diagnostic_report",
    name: "Investigation / Diagnostic Reports",
    section: "medical",
    description: "Laboratory pathology reports (CBC, LFT, KFT), radiology reports (X-ray, USG, CT, MRI), and ECG tracings.",
    acceptedFormats: [".pdf", ".png", ".jpg", ".jpeg"],
    multiple: true,
    sensitiveMasking: false,
    helpText: "Supports multiple reports. Extracts test names, dates, observed values, and abnormal clinical findings.",
  },

  // --- Section C: Financial & Billing Documents ---
  {
    id: "hospital_bill",
    name: "Final Hospital Bill (Itemized / Summary)",
    section: "financial",
    description: "Comprehensive final bill with itemized breakdown of room rent, nursing, ICU, OT charges, pharmacy, and doctor fees.",
    acceptedFormats: [".pdf", ".png", ".jpg", ".jpeg"],
    multiple: false,
    sensitiveMasking: false,
    helpText: "Extracts itemized charges, subtotals, taxes, discounts, and executes automated arithmetic validation.",
  },
  {
    id: "payment_receipt",
    name: "Payment Receipts",
    section: "financial",
    description: "Original payment receipts, advance deposit receipts, and electronic settlement acknowledgements.",
    acceptedFormats: [".pdf", ".png", ".jpg", ".jpeg"],
    multiple: true,
    sensitiveMasking: false,
    helpText: "Supports multiple receipts. Cross-checks total paid against total hospital and pharmacy bills.",
  },
  {
    id: "pharmacy_bill",
    name: "Pharmacy & Medical Store Bills",
    section: "financial",
    description: "Itemized retail pharmacy invoices with drug names, quantities, unit prices, doctor's prescription link, and GST.",
    acceptedFormats: [".pdf", ".png", ".jpg", ".jpeg"],
    multiple: true,
    sensitiveMasking: false,
    helpText: "Supports multiple bills. Extracts pharmacy name, bill date, itemized medicines, and total amount.",
  },

  // --- Section D: Special Circumstances ---
  {
    id: "fir_mlc",
    name: "Medico-Legal Certificate (MLC) / FIR",
    section: "special",
    description: "Police First Information Report (FIR) or hospital Medico-Legal Certificate (MLC) for accident, trauma, or assault cases.",
    acceptedFormats: [".pdf", ".png", ".jpg", ".jpeg"],
    multiple: false,
    sensitiveMasking: false,
    helpText: "Conditionally required for road traffic accidents. Verifies non-influence of alcohol and circumstance of injury.",
  },
  {
    id: "implant_invoice",
    name: "Implant Invoice & Sticker / Outer Pouch",
    section: "special",
    description: "Original manufacturer invoice, batch/serial number sticker, or outer packaging pouch for surgical implants (stents, mesh, joints).",
    acceptedFormats: [".pdf", ".png", ".jpg", ".jpeg"],
    multiple: false,
    sensitiveMasking: false,
    helpText: "Conditionally required when surgical procedures involve implants or prosthetic devices.",
  },
  {
    id: "ambulance_receipt",
    name: "Ambulance Receipt / Certificate",
    section: "special",
    description: "Emergency ambulance transport receipt specifying pickup/drop location, journey date, distance, and vehicle number.",
    acceptedFormats: [".pdf", ".png", ".jpg", ".jpeg"],
    multiple: false,
    sensitiveMasking: false,
    helpText: "Conditionally required when ambulance transit allowance is claimed under emergency medical benefits.",
  },
  {
    id: "pre_authorization",
    name: "Pre-Authorization Approval Letter / Query Sheet",
    section: "special",
    description: "TPA/Insurer cashless pre-authorization sanction letter, initial cashless guarantee, or enhancement clearance sheet.",
    acceptedFormats: [".pdf", ".png", ".jpg", ".jpeg"],
    multiple: false,
    sensitiveMasking: false,
    helpText: "Mandatory for cashless hospital claims. Verifies approved amount, claim reference, and insurer terms.",
  },

  // --- Section E: Other Supporting Documents ---
  {
    id: "other_medical_doc",
    name: "Other Supporting Documents",
    section: "other",
    description: "Miscellaneous clinical documentation, fitness certificate, death certificate (if applicable), or employer verification letter.",
    acceptedFormats: [".pdf", ".png", ".jpg", ".jpeg"],
    multiple: true,
    sensitiveMasking: false,
    helpText: "Supports multiple uploads for any additional documentation requested by policy underwriters.",
  },
];

export const DOCUMENT_CATALOGUE_BY_ID = new Map<DocumentCategory, DocumentCategoryMeta>(
  DOCUMENT_CATALOGUE.map((item) => [item.id, item])
);

/**
 * Determine dynamic document requirement based on claim context
 */
export function getCategoryRequirement(
  categoryId: DocumentCategory,
  context: ClaimContext
): { requirement: DocumentRequirement; reason?: string } {
  // Always mandatory core documents
  if (categoryId === "claim_form") {
    return { requirement: "mandatory", reason: "Standard claim declaration required for all submissions" };
  }
  if (categoryId === "insurance_card") {
    return { requirement: "mandatory", reason: "Required to verify policyholder coverage and active policy" };
  }
  if (categoryId === "identity_proof") {
    return { requirement: "mandatory", reason: "Government ID required for regulatory KYC compliance" };
  }
  if (categoryId === "discharge_summary") {
    return { requirement: "mandatory", reason: "Primary clinical record of hospitalization and diagnosis" };
  }
  if (categoryId === "hospital_bill") {
    return { requirement: "mandatory", reason: "Primary financial record for claimed medical expenditure" };
  }

  // Cashless vs Reimbursement routing
  if (categoryId === "bank_proof") {
    if (context.claimType === "reimbursement") {
      return { requirement: "mandatory", reason: "Mandatory for reimbursement claims to disburse settlement funds" };
    }
    return { requirement: "optional", reason: "Optional for cashless claims (settled directly with hospital)" };
  }

  if (categoryId === "payment_receipt") {
    if (context.claimType === "reimbursement") {
      return { requirement: "mandatory", reason: "Required to prove actual out-of-pocket payment before reimbursement" };
    }
    return { requirement: "optional", reason: "Optional for cashless claims unless non-medical co-pay was paid" };
  }

  if (categoryId === "pre_authorization") {
    if (context.claimType === "cashless") {
      return { requirement: "mandatory", reason: "Mandatory for cashless claims to confirm TPA pre-approval" };
    }
    return { requirement: "optional", reason: "Optional for post-hospitalization reimbursement claims" };
  }

  // Special circumstances
  if (categoryId === "fir_mlc") {
    if (context.isAccident) {
      return { requirement: "conditional", reason: "Mandatory for accident and trauma cases" };
    }
    return { requirement: "optional", reason: "Required only for vehicular accidents, burns, or assault" };
  }

  if (categoryId === "implant_invoice") {
    if (context.hasImplant) {
      return { requirement: "conditional", reason: "Mandatory when surgical implants/devices are billed" };
    }
    return { requirement: "optional", reason: "Required only if surgery involves stents, pacemakers, or implants" };
  }

  if (categoryId === "ambulance_receipt") {
    if (context.hasAmbulance) {
      return { requirement: "conditional", reason: "Mandatory when ambulance charges are claimed" };
    }
    return { requirement: "optional", reason: "Required only if claiming ambulance transit expenses" };
  }

  // Optional/supporting by default
  return { requirement: "optional" };
}

/**
 * Sensitive Data Masking Helpers
 */
export function maskSensitiveValue(
  type: "aadhaar" | "pan" | "account" | "passport",
  value: string
): string {
  if (!value) return "";
  const cleaned = value.trim();

  switch (type) {
    case "aadhaar": {
      // 12 digits: format as XXXX-XXXX-1234
      const digits = cleaned.replace(/\D/g, "");
      if (digits.length === 12) {
        return `XXXX-XXXX-${digits.slice(-4)}`;
      }
      return cleaned.length > 4 ? `XXXX-XXXX-${cleaned.slice(-4)}` : cleaned;
    }
    case "pan": {
      // 10 chars: ABCDE1234F -> ABCDE****F
      if (cleaned.length === 10) {
        return `${cleaned.slice(0, 5)}****${cleaned.slice(-1)}`;
      }
      return cleaned.length > 5 ? `${cleaned.slice(0, 5)}****` : cleaned;
    }
    case "account": {
      // Bank account: show only last 4 digits
      const digits = cleaned.replace(/\s+/g, "");
      if (digits.length > 4) {
        return `XXXXXX${digits.slice(-4)}`;
      }
      return cleaned;
    }
    case "passport": {
      // Passport: mask middle characters
      if (cleaned.length >= 8) {
        return `${cleaned.slice(0, 2)}****${cleaned.slice(-2)}`;
      }
      return cleaned;
    }
    default:
      return cleaned;
  }
}
