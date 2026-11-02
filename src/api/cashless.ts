/**
 * ClaimBridge Cashless Insurance API Client
 * Typed service layer for hospital cashless processing, pre-authorization,
 * treatment tracking, final authorization, and discharge readiness.
 */
import { apiFetch, ApiResponse } from "./client";

export interface InsuranceProvider {
  id: string;
  name: string;
  code: string;
  providerType?: string | null;
  officialWebsite?: string | null;
  officialPortalUrl?: string | null;
  submissionMode?: string | null;
  requiredDocumentCategories?: string[];
  integrationConfig?: Record<string, unknown>;
  providerNotes?: string | null;
  contactEmail?: string | null;
  contactPhone?: string | null;
  portalUrl?: string | null;
  supportedClaimTypes: string[];
  isActive: boolean;
}

export interface PatientConsentRecord {
  id: string;
  consenterName: string;
  consenterRelationship: string;
  purpose: string;
  status: string;
  consentText: string;
  ipAddress?: string | null;
  timestamp?: string | null;
}

export interface ConsentStatusResponse {
  hasConsent: boolean;
  consent: PatientConsentRecord | null;
}

export interface PreAuthDetailsResponse {
  exists: boolean;
  preauth: {
    id: string;
    status: string;
    roomType?: string | null;
    proposedTreatment?: string | null;
    treatingDoctor?: string | null;
    doctorRegistrationNo?: string | null;
    estimatedCost: number;
    costBreakdown: Record<string, number>;
    submissionMode?: string | null;
    submissionReference?: string | null;
    submittedAt?: string | null;
    initialApprovalAmount?: number | null;
    approvalReference?: string | null;
    approvedAt?: string | null;
    approvalConditions?: string | null;
    tpaQueryRemarks?: string | null;
    hospitalQueryResponse?: string | null;
  } | null;
  checklist: Array<{
    type: string;
    label: string;
    uploaded: boolean;
  }>;
  patientName: string;
  policyNumber: string;
  insuranceProvider: string;
  hospitalName?: string | null;
}

export interface TreatmentRecordItem {
  id: string;
  recordDate: string;
  clinicalNotes: string;
  proceduresPerformed: Array<{
    name: string;
    doctor?: string;
    surgeon?: string;
  }>;
  updatedDiagnosis?: string | null;
  cumulativeExpenses?: number | null;
  recordedBy?: string | null;
  createdAt?: string | null;
}

export interface FinalAuthDetailsResponse {
  exists: boolean;
  finalAuth: {
    id: string;
    status: string;
    finalBilledAmount: number;
    submissionReference?: string | null;
    submittedAt?: string | null;
    finalApprovedAmount?: number | null;
    nonPayableDeductions: number;
    deductionBreakdown: Record<string, number>;
    patientResponsibilityAmount: number;
    finalApprovalReference?: string | null;
    finalApprovedAt?: string | null;
    tpaRemarks?: string | null;
  } | null;
  financialComparison: {
    estimatedCost: number;
    initialApprovedAmount: number;
    finalBilledAmount: number;
    varianceFromInitial: number;
    exceedsInitialAuth: boolean;
  };
  patientName: string;
  policyNumber: string;
  hospitalName?: string | null;
}

export interface DischargeReadinessChecklistItem {
  id: string;
  title: string;
  passed: boolean;
  note: string;
}

export interface DischargeReadinessResponse {
  claimId: string;
  claimNumber: string;
  patientName: string;
  hospitalName?: string | null;
  insuranceProvider: string;
  claimType: string;
  preauthStatus: string;
  preauthApprovedAmount?: number | null;
  finalAuthStatus: string;
  finalBilledAmount: number;
  finalApprovedAmount?: number | null;
  nonPayableDeductions: number;
  patientResponsibilityAmount: number;
  missingDocuments: string[];
  checklist: DischargeReadinessChecklistItem[];
  isDischargeReady: boolean;
  readinessStatus: string;
}

// =========================================================
// API METHODS
// =========================================================

export async function fetchInsuranceProviders(
  activeOnly: boolean = true
): Promise<ApiResponse<InsuranceProvider[]>> {
  return apiFetch<InsuranceProvider[]>(`/cashless/providers?active_only=${activeOnly}`);
}

export async function fetchClaimConsent(
  claimId: string
): Promise<ApiResponse<ConsentStatusResponse>> {
  return apiFetch<ConsentStatusResponse>(`/cashless/claims/${claimId}/consent`);
}

export async function recordPatientConsent(
  claimId: string,
  payload: {
    consenter_name: string;
    consenter_relationship: string;
    purpose?: string;
    consent_text: string;
  }
): Promise<ApiResponse<any>> {
  return apiFetch(`/cashless/claims/${claimId}/consent`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchPreAuthDetails(
  claimId: string
): Promise<ApiResponse<PreAuthDetailsResponse>> {
  return apiFetch<PreAuthDetailsResponse>(`/cashless/claims/${claimId}/preauth`);
}

export async function savePreAuthDraft(
  claimId: string,
  payload: {
    patient_name?: string;
    date_of_birth?: string;
    mobile_number?: string;
    policy_number?: string;
    member_id?: string;
    policyholder_name?: string;
    relationship?: string;
    hospital_name?: string;
    diagnosis?: string;
    room_type?: string;
    proposed_treatment?: string;
    admission_date?: string;
    treating_doctor?: string;
    doctor_registration_no?: string;
    estimated_cost: number;
    cost_breakdown?: Record<string, number>;
  }
): Promise<ApiResponse<any>> {
  return apiFetch(`/cashless/claims/${claimId}/preauth`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function submitPreAuthPackage(
  claimId: string,
  payload: {
    submission_mode: string;
    submission_reference: string;
  }
): Promise<ApiResponse<any>> {
  return apiFetch(`/cashless/claims/${claimId}/preauth/submit`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchPreAuthPackage(
  claimId: string
): Promise<ApiResponse<{ packageFingerprint: string; package: any }>> {
  return apiFetch(`/cashless/claims/${claimId}/preauth/package`);
}

export async function adjudicatePreAuth(
  claimId: string,
  payload: {
    decision: "Approved" | "Partially Approved" | "Query Raised" | "Rejected";
    initial_approval_amount?: number;
    approval_reference?: string;
    approval_conditions?: string;
    query_remarks?: string;
  }
): Promise<ApiResponse<any>> {
  return apiFetch(`/cashless/claims/${claimId}/preauth/adjudicate`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function respondPreAuthQuery(
  claimId: string,
  payload: {
    hospital_query_response: string;
  }
): Promise<ApiResponse<any>> {
  return apiFetch(`/cashless/claims/${claimId}/preauth/respond-query`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchTreatmentRecords(
  claimId: string
): Promise<ApiResponse<TreatmentRecordItem[]>> {
  return apiFetch<TreatmentRecordItem[]>(`/cashless/claims/${claimId}/treatment-records`);
}

export async function addTreatmentRecord(
  claimId: string,
  payload: {
    record_date: string;
    clinical_notes: string;
    procedures_performed?: Array<{ name: string; doctor?: string; surgeon?: string }>;
    updated_diagnosis?: string;
    cumulative_expenses?: number;
  }
): Promise<ApiResponse<any>> {
  return apiFetch(`/cashless/claims/${claimId}/treatment-records`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchFinalAuthDetails(
  claimId: string
): Promise<ApiResponse<FinalAuthDetailsResponse>> {
  return apiFetch<FinalAuthDetailsResponse>(`/cashless/claims/${claimId}/final-auth`);
}

export async function saveFinalAuthDraft(
  claimId: string,
  payload: {
    final_billed_amount: number;
    deduction_breakdown?: Record<string, number>;
    patient_responsibility_amount?: number;
  }
): Promise<ApiResponse<any>> {
  return apiFetch(`/cashless/claims/${claimId}/final-auth`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function submitFinalAuth(
  claimId: string,
  payload: {
    submission_reference: string;
  }
): Promise<ApiResponse<any>> {
  return apiFetch(`/cashless/claims/${claimId}/final-auth/submit`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function adjudicateFinalAuth(
  claimId: string,
  payload: {
    decision: "Approved" | "Partially Approved" | "Rejected";
    final_approved_amount: number;
    non_payable_deductions?: number;
    deduction_breakdown?: Record<string, number>;
    patient_responsibility_amount: number;
    final_approval_reference: string;
    tpa_remarks?: string;
  }
): Promise<ApiResponse<any>> {
  return apiFetch(`/cashless/claims/${claimId}/final-auth/adjudicate`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchDischargeReadiness(
  claimId: string
): Promise<ApiResponse<DischargeReadinessResponse>> {
  return apiFetch<DischargeReadinessResponse>(`/cashless/claims/${claimId}/discharge-readiness`);
}
