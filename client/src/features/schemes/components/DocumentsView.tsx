import { FileText } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { RequiredDocument } from "@/types";
import { Badge } from "@/components/ui/badge";
import { SectionSpeakerRow } from "@/components/shared/SectionSpeakerRow";

interface DocumentsViewProps {
  documents: RequiredDocument[];
}

/** Required-document checklist with OCR-support hints + section read-aloud. */
export function DocumentsView({ documents }: DocumentsViewProps) {
  const { t } = useTranslation();

  const speechText = documents
    .map((doc) => (doc.localizedNames.en ?? doc.name) + (doc.optional ? " (optional)" : ""))
    .join(". ");

  return (
    <div className="space-y-3">
      <SectionSpeakerRow id="documents" title={t("schemes.documents")} text={speechText} language="en" />
      {documents.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("schemes.noResults")}</p>
      ) : (
        <ul className="space-y-2">
          {documents.map((doc) => (
            <li key={doc.id} className="flex items-center justify-between rounded-lg border px-3 py-2 text-sm">
              <span className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-muted-foreground" />
                {doc.localizedNames.en ?? doc.name}
              </span>
              <div className="flex items-center gap-2">
                {doc.ocrSupported ? <Badge variant="muted">OCR</Badge> : null}
                {doc.optional ? <Badge variant="outline">optional</Badge> : null}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}