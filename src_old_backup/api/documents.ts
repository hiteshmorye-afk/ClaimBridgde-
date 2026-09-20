import { apiFetch } from "./client";

export interface OcrExtractionResult {
  fileName: string;
  confidence: number;
  extractedFields: Record<string, string>;
  boundingBoxes: Array<{
    text: string;
    confidence: number;
    box: { x: number; y: number; w: number; h: number };
  }>;
}

export async function uploadDocument(file: File, category: string) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("category", category);

  const response = await apiFetch<{ documentId: string; fileName: string }>("/documents/upload", {
    method: "POST",
    headers: {}, // fetch automatically adds multipart boundary when body is FormData
    body: formData as any,
  });

  return response.data;
}

export async function fetchDocumentOcr(documentId: string) {
  const response = await apiFetch<OcrExtractionResult>(`/documents/${documentId}/ocr`);
  return response.data;
}
