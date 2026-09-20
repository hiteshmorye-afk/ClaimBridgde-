import { apiFetch } from "./client";

export interface ClaimApiData {
  id: string;
  patientName: string;
  patientAge: number;
  policyNumber: string;
  insuranceProvider: string;
  diagnosis: string;
  admissionDate: string;
  dischargeDate: string;
  claimedAmount: number;
  status: "Ready for Submission" | "Needs Review" | "Under Analysis" | "Approved" | "Rejected";
  stage: string;
  readiness: number;
  ocrConfidence: number;
  medicalRisk: number;
  medicalConfidence: number;
  policyConfidence: number;
  validationReadiness: number;
  overallConfidence: number;
  documents: Array<{
    category: string;
    fileName: string;
    status: "Verified" | "Processing" | "Missing" | "Mismatch";
    note?: string;
  }>;
  findings: Array<{
    label: string;
    severity: "ok" | "warning" | "error";
    detail: string;
  }>;
}

export async function fetchClaims() {
  const response = await apiFetch<ClaimApiData[]>("/claims");
  return response.data;
}

export async function fetchClaimById(claimId: string) {
  const response = await apiFetch<ClaimApiData>(`/claims/${claimId}`);
  return response.data;
}

export async function createClaim(claimData: Partial<ClaimApiData>) {
  const response = await apiFetch<ClaimApiData>("/claims", {
    method: "POST",
    body: JSON.stringify(claimData),
  });
  return response.data;
}

export async function updateClaimStatus(
  claimId: string,
  action: "Approve" | "Reject" | "RequestInfo" | "Escalate",
  note?: string
) {
  const response = await apiFetch<{ success: boolean; claimId: string }>(
    `/claims/${claimId}/status`,
    {
      method: "PATCH",
      body: JSON.stringify({ action, note }),
    }
  );
  return response;
}
