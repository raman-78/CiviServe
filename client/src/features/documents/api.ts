/**
 * Typed API for the document endpoints (Prompt 11).
 *
 * Thin wrappers over the shared HTTP client for `/api/v1/documents/*`.
 * Multipart uploads go through `apiRequest` with `multipart: true` so the
 * browser sets the boundary header itself.
 */
import { apiRequest, del, get, post } from "@/lib/api-client";
import { appConfig } from "@/config/env";
import { getAuthToken } from "@/lib/auth-token";
import type {
  DocumentReadiness,
  DocumentTypeConfirmRequest,
  DocumentTypeInfo,
  DocumentReviewRequest,
  OcrResult,
  UserDocument,
  UserDocumentListResponse,
} from "@/types";

export interface UploadDocumentParams {
  file: Blob;
  fileName: string;
  schemeCode?: string;
  requiredName?: string;
}

/** Canonical document-type catalog (accepted formats + OCR support). */
export async function fetchDocumentCatalog(): Promise<DocumentTypeInfo[]> {
  return (await get<DocumentTypeInfo[]>("/api/v1/documents/catalog")).data;
}

/** My documents, freshest first. */
export async function fetchDocuments(page = 1, pageSize = 20): Promise<UserDocumentListResponse> {
  return (
    await get<UserDocumentListResponse>(
      `/api/v1/documents?page=${page}&pageSize=${pageSize}`,
    )
  ).data;
}

/** Multipart upload of a document file. */
export async function uploadDocument(
  payload: UploadDocumentParams,
): Promise<UserDocument> {
  const form = new FormData();
  const extension = payload.fileName.split(".").pop()?.toLowerCase() ?? "png";
  form.append("file", payload.file, payload.fileName || `document.${extension}`);
  if (payload.schemeCode) form.append("scheme_code", payload.schemeCode);
  if (payload.requiredName) form.append("required_name", payload.requiredName);
  const { data } = await apiRequest<{ document: UserDocument; ocrAvailable: boolean }>(
    "/api/v1/documents/upload",
    { method: "POST", body: form },
    { multipart: true, timeoutMs: 60_000 },
  );
  return data.document;
}

/** OCR text extracted in the browser is pushed here for type detection. */
export async function submitOcr(documentId: string, text: string): Promise<OcrResult> {
  return (
    await post<OcrResult>(`/api/v1/documents/${encodeURIComponent(documentId)}/ocr`, { text })
  ).data;
}

/** Manual confirmation/correction of the detected document type. */
export async function confirmDocumentType(
  documentId: string,
  request: DocumentTypeConfirmRequest,
): Promise<UserDocument> {
  return (
    await post<UserDocument>(
      `/api/v1/documents/${encodeURIComponent(documentId)}/confirm-type`,
      request,
    )
  ).data;
}

/** User review/correction of extracted field values. */
export async function reviewDocument(
  documentId: string,
  request: DocumentReviewRequest,
): Promise<UserDocument> {
  return (
    await post<UserDocument>(
      `/api/v1/documents/${encodeURIComponent(documentId)}/review`,
      request,
    )
  ).data;
}

/** Replace the file of an existing document. */
export async function replaceDocument(
  documentId: string,
  file: Blob,
  fileName: string,
): Promise<UserDocument> {
  const form = new FormData();
  form.append("new_file", file, fileName || "document.png");
  const { data } = await apiRequest<{ document: UserDocument }>(
    `/api/v1/documents/${encodeURIComponent(documentId)}/replace`,
    { method: "POST", body: form },
    { multipart: true, timeoutMs: 60_000 },
  );
  return data.document;
}

/** Delete a document (also removes the stored file). */
export async function deleteDocument(documentId: string): Promise<void> {
  await del<{ ok: boolean }>(`/api/v1/documents/${encodeURIComponent(documentId)}`);
}

/** Authenticated, owner-scoped file download (private file, never a public URL). */
export async function downloadDocument(documentId: string): Promise<Blob> {
  const baseUrl = appConfig.apiBaseUrl.replace(/\/$/, "");
  const token = getAuthToken();
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 30_000);
  try {
    const response = await fetch(
      `${baseUrl}/api/v1/documents/${encodeURIComponent(documentId)}/file`,
      { headers: { Authorization: `Bearer ${token ?? ""}` }, signal: controller.signal },
    );
    if (!response.ok) throw new Error(`Download failed (${response.status}).`);
    return await response.blob();
  } finally {
    window.clearTimeout(timer);
  }
}

/** Per-scheme document readiness pre-check. */
export async function fetchReadiness(schemeCode: string): Promise<DocumentReadiness> {
  return (
    await get<DocumentReadiness>(`/api/v1/documents/readiness/${encodeURIComponent(schemeCode)}`)
  ).data;
}