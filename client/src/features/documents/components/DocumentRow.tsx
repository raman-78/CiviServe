import { useRef } from "react";
import { useTranslation } from "react-i18next";
import { Download, FileText, ScanText, Trash2, Upload } from "lucide-react";
import type { DocumentStatus, UserDocument } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/formatters";

const STATUS_I18N_KEYS: Record<DocumentStatus, string> = {
  missing: "documents.statusMissing",
  uploaded: "documents.statusUploaded",
  processing: "documents.statusProcessing",
  processed: "documents.statusProcessed",
  needs_review: "documents.statusNeedsReview",
  matches: "documents.statusMatches",
  mismatch: "documents.statusMismatch",
  unsupported: "documents.statusUnsupported",
  ocr_failed: "documents.statusOcrFailed",
  user_confirmed: "documents.statusUserConfirmed",
};

function statusVariant(status: DocumentStatus) {
  switch (status) {
    case "processed":
    case "matches":
    case "user_confirmed":
      return "success" as const;
    case "mismatch":
    case "unsupported":
    case "ocr_failed":
      return "destructive" as const;
    case "needs_review":
      return "warning" as const;
    default:
      return "secondary" as const;
  }
}

interface DocumentRowProps {
  document: UserDocument;
  /** True when this document is mid-scan (OCR running). */
  pending?: boolean;
  onScan: (documentId: string) => void;
  onDownload: (documentId: string) => void;
  onReplace: (documentId: string, file: File) => void;
  onDelete: (documentId: string) => void;
}

/** One row of the uploaded-documents list. */
export function DocumentRow({
  document,
  pending,
  onScan,
  onDownload,
  onReplace,
  onDelete,
}: DocumentRowProps) {
  const { t } = useTranslation();
  const fileRef = useRef<HTMLInputElement>(null);

  return (
    <li className="flex flex-col gap-3 rounded-lg border px-3 py-2.5 sm:flex-row sm:items-center sm:justify-between">
      <input
        ref={fileRef}
        type="file"
        accept=".pdf,.jpg,.jpeg,.png"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onReplace(document.id, file);
          if (fileRef.current) fileRef.current.value = "";
        }}
      />
      <div className="flex min-w-0 items-center gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-muted">
          <FileText className="h-4 w-4 text-muted-foreground" />
        </span>
        <div className="min-w-0 space-y-0.5">
          <p className="truncate text-sm font-medium">{document.fileName}</p>
          <p className="truncate text-xs text-muted-foreground">
            {document.detectedType ?? (document.required?.localizedNames?.en ?? document.required?.name ?? "")}
            {" • "}
            {formatDate(document.updatedAt)}
          </p>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={statusVariant(document.status)}>
          {t(STATUS_I18N_KEYS[document.status] ?? "documents.statusUploaded")}
        </Badge>
        <Button
          variant="outline"
          size="sm"
          disabled={pending}
          onClick={() => onScan(document.id)}
        >
          <ScanText className="h-4 w-4" />
          {t("documents.scanNow")}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          aria-label={t("documents.download")}
          onClick={() => onDownload(document.id)}
        >
          <Download className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          aria-label={t("documents.replaceHint")}
          onClick={() => fileRef.current?.click()}
        >
          <Upload className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          aria-label={t("documents.delete")}
          onClick={() => onDelete(document.id)}
        >
          <Trash2 className="h-4 w-4 text-destructive" />
        </Button>
      </div>
    </li>
  );
}