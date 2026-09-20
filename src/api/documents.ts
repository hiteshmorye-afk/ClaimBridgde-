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
  category: string,
  claimId: string,
) {
  const formData = new FormData();

  formData.append("file", file);
  formData.append("category", category);
  formData.append("claim_id", claimId);

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
