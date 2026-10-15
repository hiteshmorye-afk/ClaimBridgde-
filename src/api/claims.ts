import { apiFetch } from "./client";

export interface PipelineStageInfo {
  stageIndex: number;
  name: string;
  description: string;
  status: "Completed" | "Processing" | "Needs Review" | "Pending" | "Failed" | "Not Applicable";
  timestamp?: string | null;
}

export interface FieldValidationRow {
  field: string;
  extractedValue: string | number;
  sourceDocument: string;
  page?: string | number;
  confidence?: number;
  validationRule: string;
  result: "Accepted" | "Warning" | "Missing" | "Mismatch" | "Rejected" | "Needs Human Review" | "Not Evaluated";
  explanation: string;
  conflictingValue?: string | null;
}

export interface DocumentInventoryItem {
  id: string;
  fileName: string;
  category: string;
  rawCategory: string;
  uploadTimestamp?: string | null;
  pageCount?: number;
  uploadStatus: string;
  ocrStatus: string;
  extractionStatus: string;
  ocrConfidence?: number | null;
  validationResult: string;
  missingFields: string[];
  extractedFields: Record<string, any>;
  extractedTextPreview?: string;
  status: "Verified" | "Processing" | "Missing" | "Mismatch" | "Failed";
}

export interface ClaimHistoryItem {
  id: string;
  action: string;
  previousStatus: string;
  newStatus: string;
  previousStage: string;
  newStage: string;
  remarks: string;
  performedBy: string;
  timestamp?: string | null;
}

export interface ReadinessComponentBreakdown {
  score: number;
  weight: number;
  contribution: number;
}

export interface ClaimReadinessBreakdown {
  readinessScore: number;
  readinessStatus: string;
  weights: {
    validation: number;
    medical: number;
    policy: number;
    ocr: number;
  };
  components: {
    validation: ReadinessComponentBreakdown;
    medical: ReadinessComponentBreakdown;
    policy: ReadinessComponentBreakdown;
    ocr: ReadinessComponentBreakdown;
  };
  warnings: string[];
  blockers: string[];
  explanation: string;
}

export interface ConfidenceDetails {
  overallConfidence?: number | null;
  confidenceLevel: "High" | "Medium" | "Low";
  routeDecision: "Auto Approval Eligible" | "Human Review Required";
  routeReasons: string[];
  componentScores: {
    ocr?: number | null;
    medical?: number | null;
    policy?: number | null;
    validation?: number | null;
    readiness?: number | null;
  };
  thresholds: {
    autoProcessing: number;
    readiness: number;
  };
}

export interface ClaimApiData {
  id: string;
  claimNumber: string;
  patientName: string;
  patientAge?: number | null;
  hospital: string;
  policyNumber: string;
  insuranceProvider: string;
  diagnosis: string;
  diagnosisCode?: string;
  diagnosisCodeSystem?: string;
  clinicalNotes?: string;
  admissionDate: string;
  dischargeDate: string;
  claimedAmount: number;
  currency: string;
  status: "Ready for Submission" | "Needs Review" | "Under Analysis" | "Approved" | "Rejected";
  stage: string;
  readiness?: number | null;
  ocrConfidence?: number | null;
  medicalRisk: number;
  medicalConfidence?: number | null;
  policyConfidence?: number | null;
  validationReadiness?: number | null;
  overallConfidence?: number | null;
  routeDecision: "Auto Approval Eligible" | "Human Review Required";
  routeReasons?: string[];
  createdAt?: string | null;
  updatedAt?: string | null;

  documents: DocumentInventoryItem[];
  pipelineStages?: PipelineStageInfo[];
  fieldValidationTable?: FieldValidationRow[];
  medicalEvidence?: {
    diagnosis: string;
    diagnosisCode?: string;
    procedure?: string;
    medicalConfidence?: number | null;
    medicalRiskScore?: number;
    riskIndicators?: string[];
  };
  policyEvidence?: {
    insuranceProvider: string;
    policyNumber: string;
    policyStatus: string;
    retrievalConfidence?: number | null;
    retrievedClauses?: Array<{
      section?: string;
      clauseTitle?: string;
      title?: string;
      textSnippet?: string;
      text?: string;
      confidence?: number;
      similarity?: number;
    }>;
    relevantExclusions?: string[];
  };
  readinessBreakdown?: ClaimReadinessBreakdown;
  confidenceDetails?: ConfidenceDetails;
  history?: ClaimHistoryItem[];
  findings: Array<{
    label: string;
    severity: "ok" | "warn" | "error" | "warning";
    detail: string;
  }>;
}

export interface TpaQueueItem {
  id: string;
  claimNumber: string;
  patientName: string;
  hospital: string;
  policyNumber: string;
  insuranceProvider: string;
  claimedAmount: number;
  status: string;
  stage: string;
  readiness: number;
  confidenceScore?: number | null;
  confidenceCalculated: boolean;
  reasons: string[];
  createdAt?: string | null;
}

export interface ClaimsSummaryData {
  totalClaims: number;
  approvedClaims: number;
  rejectedClaims: number;
  pendingClaims: number;
  averageReadinessScore: number;
}

export async function fetchClaimsSummary(): Promise<ClaimsSummaryData> {
  const response = await apiFetch<ClaimsSummaryData>("/claims/summary");
  if (response.error || !response.data) {
    return {
      totalClaims: 0,
      approvedClaims: 0,
      rejectedClaims: 0,
      pendingClaims: 0,
      averageReadinessScore: 0,
    };
  }
  return response.data;
}

export async function fetchClaims(search?: string, statusFilter?: string) {
  const params = new URLSearchParams();
  if (search) params.append("search", search);
  if (statusFilter) params.append("status", statusFilter);

  const queryStr = params.toString() ? `?${params.toString()}` : "";
  const response = await apiFetch<ClaimApiData[]>(`/claims${queryStr}`);
  return response.data;
}

export async function fetchClaimById(claimId: string) {
  const response = await apiFetch<ClaimApiData>(`/claims/${encodeURIComponent(claimId)}`);
  if (response.error || !response.data) {
    throw new Error(response.error || `Claim ${claimId} not found`);
  }
  return response.data;
}

export async function createClaim(claimData: Partial<ClaimApiData>) {
  const response = await apiFetch<ClaimApiData>("/claims", {
    method: "POST",
    body: JSON.stringify(claimData),
  });
  if (response.error || !response.data) {
    throw new Error(response.error || "Failed to create claim on backend.");
  }
  return response.data;
}

export async function updateClaimStatus(
  claimId: string,
  action: "Approve" | "Reject" | "RequestInfo" | "Escalate" | string,
  note?: string,
  destination?: string,
  policyReference?: string
) {
  const response = await apiFetch<{
    success: boolean;
    claimId: string;
    claimNumber?: string;
    newStatus: string;
    action: string;
  }>(`/claims/${encodeURIComponent(claimId)}/status`, {
    method: "PATCH",
    body: JSON.stringify({ action, note, destination, policyReference }),
  });
  if (response.error) {
    throw new Error(response.error);
  }
  return response;
}

export async function submitHospitalResponse(
  claimId: string,
  notes: string,
  submittedDocuments?: string[]
) {
  const response = await apiFetch<{
    success: boolean;
    claimId: string;
    newStatus: string;
    message: string;
  }>(`/claims/${encodeURIComponent(claimId)}/respond-info`, {
    method: "POST",
    body: JSON.stringify({ notes, submittedDocuments }),
  });
  if (response.error) {
    throw new Error(response.error);
  }
  return response;
}

export async function fetchTpaReviewQueue(
  queueFilter: string = "pending_review",
  hospitalFilter?: string,
  statusFilter?: string
) {
  const params = new URLSearchParams();
  params.append("queue_filter", queueFilter);
  if (hospitalFilter) params.append("hospital_filter", hospitalFilter);
  if (statusFilter) params.append("status_filter", statusFilter);

  const response = await apiFetch<TpaQueueItem[]>(`/claims/tpa/review-queue?${params.toString()}`);
  return response.data || [];
}
