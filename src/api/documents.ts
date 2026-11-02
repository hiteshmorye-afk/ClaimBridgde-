import { apiFetch } from "./client";

export interface OcrExtractionResult {
  documentId?: string;
  claimId?: string;
  fileName: string;
  confidence: number;
  extractedFields: Record<string, string>;
  boundingBoxes: Array<{
    text: string;
    confidence: number;
    box: {
      x: number;
      y: number;
      w: number;
      h: number;
    };
  }>;
  status?: string;
  message?: string;
}

export interface DocumentUploadResult {
  documentId: string;
  claimId: string;
  fileName: string;
  category: string;
  processingStatus: string;
  message: string;
}

export interface VaultDocument {
  id: string;
  name: string;
  category: string;
  rawCategory?: string;
  claimId: string;
  claimUuid?: string;
  confidence: number;
  status: string;
  size: string;
  date: string;
}

/**
 * Fetch all documents with optional filters and organization scoping.
 */
export async function fetchDocuments(params?: {
  search?: string;
  category?: string;
  claimId?: string;
}): Promise<VaultDocument[]> {
  const query = new URLSearchParams();
  if (params?.search) query.append("search", params.search);
  if (params?.category && params.category !== "All") query.append("category", params.category);
  if (params?.claimId) query.append("claim_id", params.claimId);

  const qs = query.toString();
  const url = qs ? `/documents?${qs}` : "/documents";

  const response = await apiFetch<VaultDocument[]>(url);
  return response.data || [];
}

/**
 * Upload a document for an existing ClaimBridge claim.
 *
 * The backend requires:
 *   file
 *   category
 *   claim_id
 */
export async function uploadDocument(
  file: File,
  category: string = "Auto-Detect",
  claimId?: string,
) {
  const formData = new FormData();

  formData.append("file", file);
  formData.append("category", category || "Auto-Detect");
  if (claimId) {
    formData.append("claim_id", claimId);
  }

  const response = await apiFetch<DocumentUploadResult>(
    "/documents/upload",
    {
      method: "POST",
      body: formData,
    },
  );

  return response.data;
}


/**
 * Fetch OCR information for an uploaded document.
 */
export async function fetchDocumentOcr(
  documentId: string,
) {
  const response = await apiFetch<OcrExtractionResult>(
    `/documents/${documentId}/ocr`,
  );

  return response.data;
}

/**
 * Initiate processing of an uploaded document through the AI pipeline.
 */
export async function processDocument(documentId: string) {
  const response = await apiFetch<{
    documentId: string;
    claimId: string;
    fileName: string;
    processingStatus: string;
    pipeline: any;
    message: string;
  }>(`/documents/${documentId}/process`, {
    method: "POST",
  });

  return response.data;
}


export interface DocumentProcessingStage {
  stage: string;
  status: string;
}

export interface DocumentDetailResponse {
  documentId: string;
  fileName: string;
  category: string;
  claimId: string;
  claimNumber?: string;
  uploadDate?: string | null;
  processingStatus: string;
  ocrStatus: string;
  extractionStatus: string;
  validationStatus: string;
  matchingStatus: string;
  overallStatus: string;
  ocrConfidence?: number;
  extractedText?: string | null;
  extractedFields?: Record<string, any>;
  classification?: Record<string, any>;
  validation?: Record<string, any>;
  medicalAnalysis?: Record<string, any>;
  policyIntelligence?: Record<string, any>;
  matchSummary?: Array<{
    field: string;
    expected: string;
    extracted: string;
    status: string;
    evidence?: string | null;
  }>;
  crossDocumentComparisons?: Array<{
    documentA: string;
    field: string;
    documentB: string;
    comparisonResult: string;
    explanation: string;
  }>;
  pipeline?: {
    stages: DocumentProcessingStage[];
  };
  reliabilityScore?: number;
  reliabilityTier?: string;
  reliabilityTierSummary?: string;
  authenticityStatus?: string;
  plainEnglishExplanation?: string;
  missingFields?: string[];
  foundFields?: string[];
  extractionConfidence?: number;
  recommendedCorrections?: string[];
  reliabilityBreakdown?: Record<string, {
    score: number;
    max: number;
    label: string;
    status: string;
    description: string;
  }>;
  fieldChecks?: Array<{
    information: string;
    foundInPdf: string;
    comparedWith: string;
    result: string;
    explanation?: string;
  }>;
  medicalDiagnoses?: Array<{
    originalDiagnosis: string;
    normalizedDiagnosis: string;
    icd10Code: string;
    description: string;
    confidence: number;
    status: string;
    evidence?: string;
  }>;
  claimReadiness?: {
    readiness_score: number;
    readiness_level: string;
    readiness_status: string;
    stage: string;
    is_provisional: boolean;
    provisional_reasons: string[];
    categories: Record<string, any>;
    category_list: Array<{
      name: string;
      key: string;
      weight: number;
      score: number;
      status: string;
      checks: Array<{
        name: string;
        max_points: number;
        earned_points: number;
        status: string;
        identified_info: string;
        missing_info: string;
        deduction_reason: string;
        recommended_action: string;
      }>;
      identified_info: string[];
      missing_info: string[];
      deductions: string[];
      recommended_actions: string[];
    }>;
    missing_requirements: string[];
    recommended_actions: Array<{
      action: string;
      category: string;
      categoryKey: string;
      targetStep: number;
      targetTab: string;
      targetTitle: string;
    }>;
    disclaimer: string;
    total_weight: number;
  };
  fileUrl?: string;
}

export async function associateDocumentsToClaim(
  claimId: string,
  documentIds: string[],
): Promise<{ message?: string; updatedCount?: number } | null> {
  const response = await apiFetch<{ message?: string; updatedCount?: number }>(
    "/documents/associate-claim",
    {
      method: "POST",
      body: JSON.stringify({ claimId, documentIds }),
    },
  );

  return response.data;
}

export async function fetchDocumentDetail(documentId: string): Promise<DocumentDetailResponse | null> {
  const response = await apiFetch<DocumentDetailResponse>(`/documents/${documentId}`);
  return response.data;
}
