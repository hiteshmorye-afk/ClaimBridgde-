import { useSyncExternalStore } from "react";

export const DOC_CATEGORIES = [
  "Hospital Bill",
  "Discharge Summary",
  "Insurance Card",
  "Prescription",
  "Lab Report",
  "Investigation Report",
  "Pre-Authorization Form",
] as const;

export type DocCategory = (typeof DOC_CATEGORIES)[number];

export const PIPELINE_STAGES = [
  "01 Secure Document Intake",
  "02 Image Preprocessing",
  "03 OCR Extraction",
  "04 Document Classification",
  "05 Information Extraction",
  "06 Medical Intelligence",
  "07 Policy Intelligence (RAG)",
  "08 Cross-Validation Engine",
  "09 Claim Readiness Engine",
  "10 Confidence Scoring Engine",
  "11 Final Decision",
] as const;

export type PipelineStage = (typeof PIPELINE_STAGES)[number];

export type ClaimStatus = "Under Analysis" | "Ready for Submission" | "Needs Review" | "Approved" | "Rejected";

export type ClaimDocument = {
  category: DocCategory;
  fileName: string;
  status: "Verified" | "Processing" | "Missing" | "Mismatch";
  note?: string;
  fileSize?: string;
};

export type MedicalServiceItem = {
  id: string;
  serviceName: string;
  code: string; // ICD-10 or CPT
  category: "Room & Board" | "Surgery" | "Pharmacy" | "Diagnostics" | "Consultation";
  quantity: number;
  unitCost: number;
  totalCost: number;
  coverageStatus: "Covered" | "Co-pay Applied" | "Excluded" | "Needs Review";
};

export type PolicyClauseEvidence = {
  id: string;
  section: string;
  clauseTitle: string;
  textSnippet: string;
  status: "Verified" | "Conditional" | "Exclusion Flag" | "Partial Match";
  confidence: number;
};

export type OcrLine = {
  id: string;
  label: string;
  value: string;
  confidence: number;
  box: { x: number; y: number; w: number; h: number };
};

export type Claim = {
  id: string;
  patientName: string;
  patientAge: number;
  hospital: string;
  policyNumber: string;
  insuranceProvider: string;
  admissionDate: string;
  dischargeDate: string;
  diagnosis: string;
  claimedAmount: number;
  status: ClaimStatus;
  stage: PipelineStage;
  
  // High-Tech Readiness & AI Engine Metrics
  readiness: number; // Final Readiness e.g. 89.47%
  ocrConfidence: number; // e.g. 98.93%
  classification: string; // e.g. "Hospital Bill (60%)"
  medicalRiskScore: number; // e.g. 50/100
  medicalConfidence: number; // e.g. 70%
  policyConfidence: number; // e.g. 68.51%
  validationReadiness: number; // e.g. 100%
  overallConfidence: number; // e.g. 83.36% (Medium)
  routeDecision: "Auto Approval Eligible" | "Human Review Required" | "Escalation Flagged";

  documents: ClaimDocument[];
  findings: { label: string; detail: string; severity: "ok" | "warn" | "error" }[];
  medicalServices: MedicalServiceItem[];
  policyClauses: PolicyClauseEvidence[];
  ocrLines: OcrLine[];
};

const seed: Claim[] = [
  {
    id: "CLM-TEST-001",
    patientName: "Mrs. Tuhod",
    patientAge: 52,
    hospital: "Chong Hua Hospital",
    policyNumber: "POL-CH-99482-B",
    insuranceProvider: "Pacific Healthcare TPA",
    admissionDate: "2019-05-16",
    dischargeDate: "2019-05-19",
    diagnosis: "Acute Gastroenteritis & Severe Dehydration (ICD-10: A09)",
    claimedAmount: 184000.0,
    status: "Needs Review",
    stage: "09 Claim Readiness Engine",
    
    // Exact specs from user request:
    readiness: 89.47,
    ocrConfidence: 98.93,
    classification: "Hospital Bill (60%)",
    medicalRiskScore: 50,
    medicalConfidence: 70,
    policyConfidence: 68.51,
    validationReadiness: 100,
    overallConfidence: 83.36,
    routeDecision: "Human Review Required",

    documents: [
      { category: "Hospital Bill", fileName: "chong_hua_bill_184k.pdf", status: "Verified", fileSize: "2.4 MB" },
      { category: "Discharge Summary", fileName: "discharge_summary_tuhod.pdf", status: "Verified", fileSize: "1.8 MB" },
      { category: "Insurance Card", fileName: "pacific_health_card.png", status: "Verified", fileSize: "850 KB" },
      { category: "Prescription", fileName: "rx_medications_may2019.pdf", status: "Verified", fileSize: "620 KB" },
      { category: "Lab Report", fileName: "lab_stool_blood_work.pdf", status: "Verified", fileSize: "1.1 MB" },
      { category: "Pre-Authorization Form", fileName: "preauth_chonghua_0516.pdf", status: "Verified", fileSize: "940 KB" },
    ],
    findings: [
      {
        label: "OCR High Accuracy Extraction",
        detail: "98.93% confidence across 42 extracted itemized line items and dates.",
        severity: "ok",
      },
      {
        label: "Policy Match & RAG Verification",
        detail: "Policy status: Potentially Covered (68.51% Confidence). Room rent cap verification passed.",
        severity: "warn",
      },
      {
        label: "Medical Necessity & Risk Assessment",
        detail: "Medical Risk Score: 50/100 | Medical Confidence: 70%. 3-day IV electrolyte regimen matches ICD-10 A09 protocol.",
        severity: "warn",
      },
      {
        label: "Cross-Document Validation Engine",
        detail: "Validation Readiness: 100%. Admission dates (16.05.2019 - 19.05.2019) match across bill, summary & pre-auth.",
        severity: "ok",
      },
      {
        label: "Routing Recommendation",
        detail: "Overall Confidence: 83.36% (Medium). Route -> Human Review Required due to policy RAG threshold.",
        severity: "warn",
      },
    ],
    medicalServices: [
      {
        id: "SRV-01",
        serviceName: "Private Room & Nursing Care (3 Days)",
        code: "CPT-99232",
        category: "Room & Board",
        quantity: 3,
        unitCost: 18000,
        totalCost: 54000,
        coverageStatus: "Covered",
      },
      {
        id: "SRV-02",
        serviceName: "IV Rehydration & Electrolyte Therapy",
        code: "CPT-96360",
        category: "Pharmacy",
        quantity: 12,
        unitCost: 4500,
        totalCost: 54000,
        coverageStatus: "Covered",
      },
      {
        id: "SRV-03",
        serviceName: "Comprehensive Diagnostic Stool & Blood Panel",
        code: "CPT-87045",
        category: "Diagnostics",
        quantity: 1,
        unitCost: 26000,
        totalCost: 26000,
        coverageStatus: "Covered",
      },
      {
        id: "SRV-04",
        serviceName: "Attending Gastroenterologist Consultation",
        code: "CPT-99254",
        category: "Consultation",
        quantity: 4,
        unitCost: 7500,
        totalCost: 30000,
        coverageStatus: "Covered",
      },
      {
        id: "SRV-05",
        serviceName: "Emergency Admission & Support Sundries",
        code: "CPT-99285",
        category: "Room & Board",
        quantity: 1,
        unitCost: 20000,
        totalCost: 20000,
        coverageStatus: "Co-pay Applied",
      },
    ],
    policyClauses: [
      {
        id: "POL-SEC-4.2",
        section: "Section 4.2 - Inpatient Hospitalization",
        clauseTitle: "Acute Medical Conditions & Room Rent Limits",
        textSnippet: "Room charges covered up to ₱20,000/day for standard private suite. IV rehydration and gastrointestinal diagnostic panels are 100% reimbursable subject to pre-authorization.",
        status: "Verified",
        confidence: 94.2,
      },
      {
        id: "POL-SEC-8.1",
        section: "Section 8.1 - Pre-Existing Condition Exclusions",
        clauseTitle: "Chronic GI Condition Exclusions",
        textSnippet: "Acute gastroenteritis is non-exclusionary unless linked to documented pre-existing Inflammatory Bowel Disease (IBD) diagnosed within 24 months prior.",
        status: "Conditional",
        confidence: 68.51,
      },
      {
        id: "POL-SEC-12.3",
        section: "Section 12.3 - Co-Payment Terms",
        clauseTitle: "Emergency Room Incidentals",
        textSnippet: "Emergency admission sundries carry a fixed 10% co-payment deductible payable by insured patient.",
        status: "Verified",
        confidence: 98.0,
      },
    ],
    ocrLines: [
      { id: "OCR-1", label: "PATIENT NAME", value: "MRS. TUHOD", confidence: 99.4, box: { x: 12, y: 14, w: 35, h: 4 } },
      { id: "OCR-2", label: "HOSPITAL", value: "CHONG HUA HOSPITAL", confidence: 99.1, box: { x: 12, y: 8, w: 45, h: 5 } },
      { id: "OCR-3", label: "ADMISSION DATE", value: "16.05.2019", confidence: 98.8, box: { x: 60, y: 14, w: 25, h: 4 } },
      { id: "OCR-4", label: "DISCHARGE DATE", value: "19.05.2019", confidence: 98.7, box: { x: 60, y: 19, w: 25, h: 4 } },
      { id: "OCR-5", label: "TOTAL CHARGES", value: "184,000.00", confidence: 98.93, box: { x: 65, y: 82, w: 30, h: 6 } },
      { id: "OCR-6", label: "ATTENDING PHYSICIAN", value: "DR. R. ALVAREZ, M.D.", confidence: 97.6, box: { x: 12, y: 24, w: 40, h: 4 } },
    ],
  },
  {
    id: "CLM-2026-0892",
    patientName: "Ananya Sharma",
    patientAge: 41,
    hospital: "Apollo Hospitals",
    policyNumber: "POL-88213-A",
    insuranceProvider: "Star Health",
    admissionDate: "2026-07-18",
    dischargeDate: "2026-07-22",
    diagnosis: "Acute Appendicitis — Laparoscopic Appendectomy",
    claimedAmount: 184500,
    status: "Ready for Submission",
    stage: "11 Final Decision",
    readiness: 94.5,
    ocrConfidence: 99.1,
    classification: "Hospital Bill & Discharge Summary (95%)",
    medicalRiskScore: 15,
    medicalConfidence: 96.0,
    policyConfidence: 98.2,
    validationReadiness: 100,
    overallConfidence: 95.8,
    routeDecision: "Auto Approval Eligible",
    documents: [
      { category: "Insurance Card", fileName: "star_health_card.pdf", status: "Verified" },
      { category: "Discharge Summary", fileName: "discharge_summary.pdf", status: "Verified" },
      { category: "Hospital Bill", fileName: "final_bill.pdf", status: "Verified" },
      { category: "Prescription", fileName: "rx_appendectomy.pdf", status: "Verified" },
      { category: "Lab Report", fileName: "cbc_pathology.pdf", status: "Verified" },
      { category: "Pre-Authorization Form", fileName: "preauth_approved.pdf", status: "Verified" },
    ],
    findings: [
      { label: "Policy Active & Valid", detail: "Policy active with ₹5,00,000 sum insured.", severity: "ok" },
      { label: "Line Items Reconciled", detail: "All surgical consumables match procedure logs.", severity: "ok" },
      { label: "Room Rent Check", detail: "Sub-limits fully compliant.", severity: "ok" },
    ],
    medicalServices: [
      { id: "S1", serviceName: "Laparoscopic Appendectomy Surgery", code: "CPT-47562", category: "Surgery", quantity: 1, unitCost: 110000, totalCost: 110000, coverageStatus: "Covered" },
      { id: "S2", serviceName: "OR & Anesthesia Fee", code: "CPT-00840", category: "Surgery", quantity: 1, unitCost: 34500, totalCost: 34500, coverageStatus: "Covered" },
      { id: "S3", serviceName: "Inpatient Room Care (4 Days)", code: "CPT-99231", category: "Room & Board", quantity: 4, unitCost: 10000, totalCost: 40000, coverageStatus: "Covered" },
    ],
    policyClauses: [
      { id: "P1", section: "Section 2.1", clauseTitle: "Emergency Surgical Coverage", textSnippet: "Laparoscopic procedures covered at 100%.", status: "Verified", confidence: 98.2 },
    ],
    ocrLines: [
      { id: "O1", label: "TOTAL AMOUNT", value: "184,500.00", confidence: 99.1, box: { x: 60, y: 80, w: 30, h: 5 } },
    ],
  },
  {
    id: "CLM-2026-0891",
    patientName: "Rakesh Menon",
    patientAge: 58,
    hospital: "Fortis Escorts Heart Institute",
    policyNumber: "POL-40117-C",
    insuranceProvider: "HDFC ERGO",
    admissionDate: "2026-07-20",
    dischargeDate: "2026-07-26",
    diagnosis: "Coronary Artery Disease — Angioplasty with DES Stent",
    claimedAmount: 412000,
    status: "Needs Review",
    stage: "08 Cross-Validation Engine",
    readiness: 61.2,
    ocrConfidence: 96.4,
    classification: "Hospital Bill & Angiography Report (88%)",
    medicalRiskScore: 68,
    medicalConfidence: 74.0,
    policyConfidence: 58.0,
    validationReadiness: 55.0,
    overallConfidence: 62.4,
    routeDecision: "Escalation Flagged",
    documents: [
      { category: "Insurance Card", fileName: "hdfc_ergo_card.jpg", status: "Verified" },
      { category: "Discharge Summary", fileName: "cardiac_summary.pdf", status: "Verified" },
      { category: "Hospital Bill", fileName: "stent_bill.pdf", status: "Mismatch", note: "Stent cost exceeds pre-auth limit by ₹38,000" },
      { category: "Prescription", fileName: "cardiac_rx.pdf", status: "Verified" },
      { category: "Pre-Authorization Form", fileName: "preauth_draft.pdf", status: "Missing", note: "Revised pre-auth approval missing" },
    ],
    findings: [
      { label: "Pre-Auth Overrun Discrepancy", detail: "Pre-auth cap was ₹3,74,000 vs bill ₹4,12,000.", severity: "error" },
      { label: "Implant Sticker Required", detail: "DES Stent barcode invoice sticker missing.", severity: "warn" },
    ],
    medicalServices: [
      { id: "S1", serviceName: "PTCA Angioplasty + DES Stent", code: "CPT-92928", category: "Surgery", quantity: 1, unitCost: 280000, totalCost: 280000, coverageStatus: "Needs Review" },
      { id: "S2", serviceName: "Cath Lab Charges", code: "CPT-93458", category: "Diagnostics", quantity: 1, unitCost: 72000, totalCost: 72000, coverageStatus: "Covered" },
      { id: "S3", serviceName: "ICU Bed Charges (2 Days)", code: "CPT-99291", category: "Room & Board", quantity: 2, unitCost: 30000, totalCost: 60000, coverageStatus: "Covered" },
    ],
    policyClauses: [
      { id: "P1", section: "Section 6.4", clauseTitle: "Cardiac Stent Sub-Limits", textSnippet: "Stent reimbursement capped at NPPA ceiling plus 10% handling.", status: "Exclusion Flag", confidence: 58.0 },
    ],
    ocrLines: [
      { id: "O1", label: "TOTAL CHARGES", value: "412,000.00", confidence: 96.4, box: { x: 60, y: 80, w: 30, h: 5 } },
    ],
  },
  {
    id: "CLM-2026-0890",
    patientName: "Fatima Qureshi",
    patientAge: 33,
    hospital: "Max Super Speciality Hospital",
    policyNumber: "POL-77450-B",
    insuranceProvider: "Niva Bupa",
    admissionDate: "2026-07-24",
    dischargeDate: "2026-07-25",
    diagnosis: "Acute Asthma Exacerbation — Emergency Stabilisation",
    claimedAmount: 64200,
    status: "Under Analysis",
    stage: "06 Medical Intelligence",
    readiness: 78.5,
    ocrConfidence: 97.8,
    classification: "Emergency Bill & ER Chart",
    medicalRiskScore: 30,
    medicalConfidence: 82.0,
    policyConfidence: 88.0,
    validationReadiness: 90.0,
    overallConfidence: 84.5,
    routeDecision: "Human Review Required",
    documents: [
      { category: "Insurance Card", fileName: "niva_bupa_card.pdf", status: "Verified" },
      { category: "Hospital Bill", fileName: "er_bill.pdf", status: "Processing" },
      { category: "Prescription", fileName: "nebulization_rx.pdf", status: "Verified" },
    ],
    findings: [
      { label: "Emergency Admission Verified", detail: "Admitted via ER triage protocol.", severity: "ok" },
      { label: "Nebulisation & Oxygen Charges", detail: "Reconciliation in progress.", severity: "ok" },
    ],
    medicalServices: [
      { id: "S1", serviceName: "ER Observation Bed & Nebulisation", code: "CPT-99284", category: "Room & Board", quantity: 1, unitCost: 42000, totalCost: 42000, coverageStatus: "Covered" },
      { id: "S2", serviceName: "ABG & High Resolution CT Chest", code: "CPT-71250", category: "Diagnostics", quantity: 1, unitCost: 22200, totalCost: 22200, coverageStatus: "Covered" },
    ],
    policyClauses: [
      { id: "P1", section: "Section 3.1", clauseTitle: "Daycare Emergency Coverage", textSnippet: "Emergency admissions under 24 hours covered under Daycare Rider.", status: "Verified", confidence: 88.0 },
    ],
    ocrLines: [
      { id: "O1", label: "CLAIM AMOUNT", value: "64,200.00", confidence: 97.8, box: { x: 60, y: 80, w: 30, h: 5 } },
    ],
  },
];

let claimsState: Claim[] = [...seed];
const listeners = new Set<() => void>();

function notify() {
  listeners.forEach((listener) => listener());
}

export function useClaims(): Claim[] {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => claimsState,
    () => seed
  );
}

export function getClaim(id: string): Claim | undefined {
  return claimsState.find((c) => c.id === id);
}

export function addClaim(newClaim: Claim) {
  claimsState = [newClaim, ...claimsState];
  notify();
}

export function updateClaim(id: string, updates: Partial<Claim>) {
  claimsState = claimsState.map((c) => (c.id === id ? { ...c, ...updates } : c));
  notify();
}

export function formatDate(dateString: string): string {
  if (!dateString || dateString === "—") return "—";
  try {
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return dateString;
    return d.toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return dateString;
  }
}

export function formatINR(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(amount);
}