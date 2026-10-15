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
