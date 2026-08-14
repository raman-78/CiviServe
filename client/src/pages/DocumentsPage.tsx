import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Upload } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/shared/PageHeader";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingState } from "@/components/shared/LoadingState";
import { ConfirmationDialog } from "@/components/shared/ConfirmationDialog";
import { useDocuments } from "@/features/documents/useDocuments";
import { UploadZone } from "@/features/documents/components/UploadZone";
import { DocumentRow } from "@/features/documents/components/DocumentRow";
import { ReviewDialog } from "@/features/documents/components/ReviewDialog";
import { ReadinessSection } from "@/features/documents/components/ReadinessSection";
import { fetchSchemeSummaries } from "@/features/schemes/api";
import { errorMessage } from "@/lib/errors";

/** Documents page: upload → OCR → review → scheme readiness pre-check. */
export function DocumentsPage() {
  const { t } = useTranslation();
  const {
    documents,
    total,
    loading,
    ocr,
    catalog,
    upload,
    runOcr,
    confirmType,
    submitReview,
    replace,
    remove,
    download,
    readiness,
  } = useDocuments();

  const [reviewOpen, setReviewOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [schemeOptions, setSchemeOptions] = useState<{ code: string; name: string }[]>([]);

  useEffect(() => {
    let active = true;
    fetchSchemeSummaries({ page: 1, pageSize: 60 })
      .then((result) => {
        if (active) {
          setSchemeOptions(
            result.items.map((s) => ({ code: s.code, name: s.name.en || s.name.native })),
          );
        }
      })
      .catch(() => {
        // Non-critical selector — leave the options empty on failure.
      });
    return () => {
      active = false;
    };
  }, []);

  const pendingId = ocr.phase === "ocr-running" ? ocr.documentId : undefined;
  const scanDocId = ocr.phase === "awaiting-review" ? ocr.documentId : null;

  useEffect(() => {
    if (ocr.phase === "awaiting-review") setReviewOpen(true);
  }, [ocr.phase]);

  const handleReadiness = useCallback((code: string) => readiness(code), [readiness]);

  const handleFile = async (file: File) => {
    try {
      const doc = await upload(file);
      if (doc.fileExtension.toLowerCase() !== "pdf") void runOcr(doc.id);
    } catch (error) {
      toast.error(t("documents.uploadError"));
      void errorMessage(error);
    }
  };

  const handleReplace = async (id: string, file: File) => {
    try {
      await replace(id, file);
      toast.success(t("documents.replaceHint"));
    } catch (error) {
      toast.error(t("documents.uploadError"));
      void errorMessage(error);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await remove(deleteTarget);
      toast.success(t("common.confirm"));
    } catch (error) {
      toast.error(t("common.retry"));
      void errorMessage(error);
    }
    setDeleteTarget(null);
  };

  if (loading) return <LoadingState />;

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("documents.title")}
        subtitle={t("documents.subtitle")}
      />

      <ReadinessSection schemeOptions={schemeOptions} onLoad={handleReadiness} />

      <div className="space-y-2">
        <h2 className="text-lg font-semibold">
          {t("documents.uploaded")}{" "}
          <span className="text-sm font-normal text-muted-foreground">({total})</span>
        </h2>
        <UploadZone
          onFile={(file) => void handleFile(file)}
          busy={ocr.phase === "uploading"}
          disabled={ocr.phase !== "idle"}
        />
        {documents.length === 0 ? (
          <EmptyState
            icon={Upload}
            title={t("documents.noneYet")}
            description={t("documents.noneYetDesc")}
            compact
          />
        ) : (
          <ul className="space-y-2">
            {documents.map((doc) => (
              <DocumentRow
                key={doc.id}
                document={doc}
                pending={doc.id === pendingId}
                onScan={(id) => void runOcr(id)}
                onDownload={(id) => void download(id)}
                onReplace={(id, file) => void handleReplace(id, file)}
                onDelete={(id) => setDeleteTarget(id)}
              />
            ))}
          </ul>
        )}
      </div>

      <ReviewDialog
        open={reviewOpen}
        onOpenChange={setReviewOpen}
        ocr={ocr.phase === "awaiting-review" ? ocr.ocr : null}
        catalog={catalog}
        onConfirmType={async (documentType) => {
          if (scanDocId) await confirmType(scanDocId, documentType);
        }}
        onSave={async (fields) => {
          if (scanDocId) await submitReview(scanDocId, fields);
        }}
      />

      <ConfirmationDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        title={t("documents.deleteConfirm")}
        description={deleteTarget ? documents.find((d) => d.id === deleteTarget)?.fileName : ""}
        confirmLabel={t("documents.delete")}
        destructive
        onConfirm={() => void handleDelete()}
      />
    </div>
  );
}