/**
 * Documents feature hook (Prompt 11).
 *
 * Owns the upload → OCR → review lifecycle state on the client: list, upload,
 * OCR submission, type confirmation, review, replace, delete, download, and
 * the per-scheme readiness pre-check.
 */
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import type { DocumentCode, DocumentReadiness, OcrResult, UserDocument } from "@/types";
import {
  confirmDocumentType,
  deleteDocument,
  downloadDocument,
  fetchDocumentCatalog,
  fetchDocuments,
  fetchReadiness,
  replaceDocument,
  reviewDocument,
  submitOcr,
  uploadDocument,
} from "@/features/documents/api";
import { ocrAdapter } from "@/services/ocr";

export type OcrState =
  | { phase: "idle" }
  | { phase: "uploading" }
  | { phase: "ocr-running"; documentId: string }
  | { phase: "awaiting-review"; documentId: string; ocr: OcrResult };

interface UseDocumentsResult {
  documents: UserDocument[];
  total: number;
  loading: boolean;
  ocr: OcrState;
  catalog: Map<string, string>;
  refresh: () => Promise<void>;
  upload: (file: File, opts?: { schemeCode?: string; requiredName?: string }) => Promise<UserDocument>;
  runOcr: (documentId: string) => Promise<void>;
  confirmType: (documentId: string, documentType: string) => Promise<UserDocument>;  submitReview: (
    documentId: string,
    fields: { key: string; label: string; value: string; masked?: string; reliable?: boolean }[],
  ) => Promise<UserDocument>;
  replace: (documentId: string, file: File) => Promise<UserDocument>;
  remove: (documentId: string) => Promise<void>;
  download: (documentId: string) => Promise<void>;
  readiness: (schemeCode: string) => Promise<DocumentReadiness>;
}

export function useDocuments(): UseDocumentsResult {
  const [documents, setDocuments] = useState<UserDocument[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [ocr, setOcr] = useState<OcrState>({ phase: "idle" });
  const [catalog, setCatalog] = useState<Map<string, string>>(new Map());

  const refresh = useCallback(async () => {
    try {
      const data = await fetchDocuments();
      setDocuments(data.items);
      setTotal(data.total);
    } catch {
      // list failure is non-fatal; upload flow still reports errors
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    void (async () => {
      try {
        const catalogItems = await fetchDocumentCatalog();
        setCatalog(
          new Map(catalogItems.map((c) => [c.code, c.nameEn ?? c.code])),
        );
      } catch {
        // catalog is a nice-to-have; fall back to raw codes
      }
    })();
    void ocrAdapter.warmup();
  }, [refresh]);

  const upload = useCallback(
    async (file: File, opts?: { schemeCode?: string; requiredName?: string }) => {
      setOcr({ phase: "uploading" });
      try {
        const doc = await uploadDocument({
          file,
          fileName: file.name,
          schemeCode: opts?.schemeCode,
          requiredName: opts?.requiredName,
        });
        await refresh();
        if (doc.fileExtension === "pdf") {
          setOcr({ phase: "idle" });
          toast.warning("PDF upload stored. OCR works best with photos of documents.");
          return doc;
        }
        setOcr({ phase: "ocr-running", documentId: doc.id });
        return doc;
      } catch (error) {
        setOcr({ phase: "idle" });
        throw error;
      }
    },
    [refresh],
  );

  const runOcr = useCallback(
    async (documentId: string) => {
      setOcr({ phase: "ocr-running", documentId });
      try {
        const file = await downloadDocument(documentId);
        const text = await ocrAdapter.recognize(file);
        if (!text) {
          setOcr({ phase: "idle" });
          toast.error("We couldn't read any text from this document.");
          return;
        }
        const result = await submitOcr(documentId, text);
        setOcr({ phase: "awaiting-review", documentId, ocr: result });
        await refresh();
      } catch {
        setOcr({ phase: "idle" });
        toast.error("OCR failed. You can still label the document manually.");
      }
    },
    [refresh],
  );

  const confirmType = useCallback(
    async (documentId: string, documentType: DocumentCode | string) => {
      const doc = await confirmDocumentType(documentId, {
        documentType: documentType as DocumentCode,
      });
      await refresh();
      setOcr({ phase: "idle" });
      return doc;
    },
    [refresh],
  );

  const submitReview = useCallback(
    async (
      documentId: string,
      fields: { key: string; label: string; value: string; masked?: string; reliable?: boolean }[],
    ) => {
      const doc = await reviewDocument(documentId, { fields });
      await refresh();
      setOcr({ phase: "idle" });
      return doc;
    },
    [refresh],
  );

  const replace = useCallback(
    async (documentId: string, file: File) => {
      const doc = await replaceDocument(documentId, file, file.name);
      await refresh();
      return doc;
    },
    [refresh],
  );

  const remove = useCallback(
    async (documentId: string) => {
      await deleteDocument(documentId);
      await refresh();
    },
    [refresh],
  );

  const download = useCallback(async (documentId: string) => {
    const blob = await downloadDocument(documentId);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "document";
    link.click();
    URL.revokeObjectURL(url);
  }, []);

  const readiness = useCallback((schemeCode: string) => fetchReadiness(schemeCode), []);

  return {
    documents,
    total,
    loading,
    ocr,
    catalog,
    refresh,
    upload,
    runOcr,
    confirmType,
    submitReview,
    replace,
    remove,
    download,
    readiness,
  };
}