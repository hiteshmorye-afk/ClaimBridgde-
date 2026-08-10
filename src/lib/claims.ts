import { useSyncExternalStore } from "react";

export const DOC_CATEGORIES = [
  "Insurance Card",
  "Discharge Summary",
  "Hospital Bill",
  "Prescription",
  "Lab Report",
  "Investigation Report",
  "Pre-Authorization Form",
] as const;

export type DocCategory = (typeof DOC_CATEGORIES)[number];

export const PIPELINE_STAGES = [
  "Create Claim",
  "Patient & Policy Details",
  "Upload Claim Documents",
  "AI Document Processing",
  "Medical Analysis",
  "Policy Verification",
  "Cross-Document Validation",
  "Claim Readiness Score",
  "Final Report",
] as const;

export type ClaimStatus = "Under Analysis" | "Ready for Submission" | "Needs Review";

export type ClaimDocument = {
  category: DocCategory;
  fileName: string;
  status: "Verified" | "Processing" | "Missing" | "Mismatch";
  note?: string;
};

export type Claim = {
  id: string;
  patientName: string;
  patientAge: number;
  policyNumber: string;
  insuranceProvider: string;
  admissionDate: string;
  dischargeDate: string;
  diagnosis: string;
  claimedAmount: number;
  status: ClaimStatus;
  readiness: number;
  stage: (typeof PIPELINE_STAGES)[number];
  documents: ClaimDocument[];
  findings: { label: string; detail: string; severity: "ok" | "warn" | "error" }[];
};

function claim(c: Claim) {
  return c;
}

const seed: Claim[] = [
  claim({
    id: "CLM-2026-0148",
    patientName: "Ananya Sharma",
    patientAge: 41,
    policyNumber: "POL-88213-A",
    insuranceProvider: "Star Health",
    admissionDate: "2026-07-18",
    dischargeDate: "2026-07-22",
    diagnosis: "Acute appendicitis — laparoscopic appendectomy",
    claimedAmount: 184500,
    status: "Ready for Submission",
    readiness: 94,
    stage: "Final Report",
    documents: [
      { category: "Insurance Card", fileName: "star-health-card.pdf", status: "Verified" },
      { category: "Discharge Summary", fileName: "discharge-summary.pdf", status: "Verified" },
      { category: "Hospital Bill", fileName: "final-bill.pdf", status: "Verified" },
      { category: "Prescription", fileName: "discharge-rx.pdf", status: "Verified" },
      { category: "Lab Report", fileName: "cbc-crp.pdf", status: "Verified" },
      { category: "Investigation Report", fileName: "usg-abdomen.pdf", status: "Verified" },
      { category: "Pre-Authorization Form", fileName: "preauth-approved.pdf", status: "Verified" },
    ],
    findings: [
      { label: "Policy active on admission date", detail: "Cover valid till 2027-03-31.", severity: "ok" },
      { label: "Bill items match treatment", detail: "All 18 line items map to the recorded procedure.", severity: "ok" },
      { label: "Sub-limit check", detail: "Room rent within 2% of sum insured.", severity: "ok" },
    ],
  }),
  claim({
    id: "CLM-2026-0147",
    patientName: "Rakesh Menon",
    patientAge: 58,
    policyNumber: "POL-40117-C",
    insuranceProvider: "HDFC ERGO",
    admissionDate: "2026-07-20",
    dischargeDate: "2026-07-26",
    diagnosis: "CAD — angioplasty with single stent",
    claimedAmount: 412000,
    status: "Needs Review",
    readiness: 61,
    stage: "Cross-Document Validation",
    documents: [
      { category: "Insurance Card", fileName: "hdfc-ergo-card.jpg", status: "Verified" },
      { category: "Discharge Summary", fileName: "discharge-summary.pdf", status: "Verified" },
      { category: "Hospital Bill", fileName: "final-bill.pdf", status: "Mismatch", note: "Stent cost exceeds pre-auth by ₹38,000" },
      { category: "Prescription", fileName: "cardiac-rx.pdf", status: "Verified" },
      { category: "Lab Report", fileName: "lipid-profile.pdf", status: "Verified" },
      { category: "Investigation Report", fileName: "angiogram-report.pdf", status: "Verified" },
      { category: "Pre-Authorization Form", fileName: "—", status: "Missing", note: "Revised pre-auth approval not uploaded" },
    ],
    findings: [
      { label: "Bill vs pre-authorisation mismatch", detail: "Approved ₹3,74,000 against a claimed ₹4,12,000.", severity: "error" },
      { label: "Implant invoice required", detail: "Insurer mandates the stent sticker and invoice.", severity: "warn" },
      { label: "Policy active on admission date", detail: "Cover valid, 4 years continuous.", severity: "ok" },
    ],
  }),
  claim({
    id: "CLM-2026-0146",
    patientName: "Fatima Qureshi",
    patientAge: 33,
    policyNumber: "POL-77450-B",
    insuranceProvider: "Niva Bupa",
    admissionDate: "2026-07-24",
    dischargeDate: "2026-07-27",
    diagnosis: "Dengue fever with thrombocytopenia",
    claimedAmount: 96750,
    status: "Under Analysis",
    readiness: 48,
    stage: "Medical Analysis",
    documents: [
      { category: "Insurance Card", fileName: "niva-bupa-card.pdf", status: "Verified" },
      { category: "Discharge Summary", fileName: "discharge-summary.pdf", status: "Processing" },
      { category: "Hospital Bill", fileName: "interim-bill.pdf", status: "Processing" },
      { category: "Prescription", fileName: "rx-day3.jpg", status: "Verified" },
      { category: "Lab Report", fileName: "platelet-trend.pdf", status: "Verified" },
      { category: "Investigation Report", fileName: "—", status: "Missing" },
      { category: "Pre-Authorization Form", fileName: "preauth-cashless.pdf", status: "Verified" },
    ],
    findings: [
      { label: "Document processing in progress", detail: "2 of 7 documents still being read.", severity: "warn" },
      { label: "Diagnosis supported by labs", detail: "Platelet trend consistent with dengue.", severity: "ok" },
    ],
  }),
  claim({
    id: "CLM-2026-0145",
    patientName: "Joseph Mathew",
    patientAge: 67,
    policyNumber: "POL-21908-D",
    insuranceProvider: "ICICI Lombard",
    admissionDate: "2026-07-11",
    dischargeDate: "2026-07-15",
    diagnosis: "Total knee replacement — right",
    claimedAmount: 328400,
    status: "Ready for Submission",
    readiness: 88,
    stage: "Final Report",
    documents: [
      { category: "Insurance Card", fileName: "icici-card.pdf", status: "Verified" },
      { category: "Discharge Summary", fileName: "discharge-summary.pdf", status: "Verified" },
      { category: "Hospital Bill", fileName: "final-bill.pdf", status: "Verified" },
      { category: "Prescription", fileName: "post-op-rx.pdf", status: "Verified" },
      { category: "Lab Report", fileName: "pre-op-labs.pdf", status: "Verified" },
      { category: "Investigation Report", fileName: "knee-xray.pdf", status: "Verified" },
      { category: "Pre-Authorization Form", fileName: "preauth-approved.pdf", status: "Verified" },
    ],
    findings: [
      { label: "Waiting period cleared", detail: "Joint replacement waiting period completed in 2024.", severity: "ok" },
      { label: "Implant invoice attached", detail: "Prosthesis invoice matches the bill line item.", severity: "ok" },
    ],
  }),
  claim({
    id: "CLM-2026-0144",
    patientName: "Meera Iyer",
    patientAge: 29,
    policyNumber: "POL-55302-A",
    insuranceProvider: "Care Health",
    admissionDate: "2026-07-25",
    dischargeDate: "2026-07-28",
    diagnosis: "Lower segment caesarean section",
    claimedAmount: 142000,
    status: "Under Analysis",
    readiness: 55,
    stage: "Policy Verification",
    documents: [
      { category: "Insurance Card", fileName: "care-health-card.pdf", status: "Verified" },
      { category: "Discharge Summary", fileName: "discharge-summary.pdf", status: "Verified" },
      { category: "Hospital Bill", fileName: "final-bill.pdf", status: "Processing" },
      { category: "Prescription", fileName: "rx.pdf", status: "Verified" },
      { category: "Lab Report", fileName: "anc-profile.pdf", status: "Verified" },
      { category: "Investigation Report", fileName: "usg-obs.pdf", status: "Verified" },
      { category: "Pre-Authorization Form", fileName: "preauth-pending.pdf", status: "Processing" },
    ],
    findings: [
      { label: "Maternity sub-limit check", detail: "Sub-limit ₹1,25,000 — claimed amount is higher.", severity: "warn" },
      { label: "Policy active on admission date", detail: "Cover valid till 2026-12-31.", severity: "ok" },
    ],
  }),
  claim({
    id: "CLM-2026-0143",
    patientName: "Harpreet Singh",
    patientAge: 46,
    policyNumber: "POL-93641-E",
    insuranceProvider: "Tata AIG",
    admissionDate: "2026-07-08",
    dischargeDate: "2026-07-09",
    diagnosis: "Renal calculus — URSL day care",
    claimedAmount: 73200,
    status: "Needs Review",
    readiness: 42,
    stage: "AI Document Processing",
    documents: [
      { category: "Insurance Card", fileName: "tata-aig-card.jpg", status: "Verified" },
      { category: "Discharge Summary", fileName: "day-care-summary.pdf", status: "Mismatch", note: "Patient name spelling differs from policy" },
      { category: "Hospital Bill", fileName: "final-bill.pdf", status: "Verified" },
      { category: "Prescription", fileName: "—", status: "Missing" },
      { category: "Lab Report", fileName: "urine-culture.pdf", status: "Verified" },
      { category: "Investigation Report", fileName: "ct-kub.pdf", status: "Verified" },
      { category: "Pre-Authorization Form", fileName: "—", status: "Missing" },
    ],
    findings: [
      { label: "Patient name mismatch", detail: "\"Harpreet Sing\" on discharge summary vs policy record.", severity: "error" },
      { label: "Missing documents", detail: "Prescription and pre-authorisation form not uploaded.", severity: "warn" },
    ],
  }),
];

let claims: Claim[] = seed;
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((l) => l());
}

export function useClaims() {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l);
      return () => listeners.delete(l);
    },
    () => claims,
    () => claims,
  );
}

export function getClaim(id: string) {
  return claims.find((c) => c.id === id) ?? null;
}

export function addClaim(input: {
  patientName: string;
  patientAge: number;
  policyNumber: string;
  insuranceProvider: string;
  admissionDate: string;
  dischargeDate: string;
  diagnosis: string;
  claimedAmount: number;
  documents: { category: DocCategory; fileName: string }[];
}) {
  const nextNumber = 149 + claims.filter((c) => c.id.startsWith("CLM-2026-01")).length - seed.length;
  const id = `CLM-2026-0${nextNumber}`;
  const documents: ClaimDocument[] = DOC_CATEGORIES.map((category) => {
    const uploaded = input.documents.find((d) => d.category === category);
    return uploaded
      ? { category, fileName: uploaded.fileName, status: "Processing" as const }
      : { category, fileName: "—", status: "Missing" as const };
  });
  const uploadedCount = input.documents.length;
  const created: Claim = {
    ...input,
    id,
    status: "Under Analysis",
    readiness: Math.round((uploadedCount / DOC_CATEGORIES.length) * 70),
    stage: "AI Document Processing",
    documents,
    findings: [
      {
        label: "Documents queued for processing",
        detail: `${uploadedCount} of ${DOC_CATEGORIES.length} document categories uploaded.`,
        severity: uploadedCount === DOC_CATEGORIES.length ? "ok" : "warn",
      },
    ],
  };
  claims = [created, ...claims];
  emit();
  return created;
}

export function formatINR(value: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatDate(value: string) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}