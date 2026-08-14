import { FileText } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { ChatMessage } from "@/types";
import { cn } from "@/lib/utils";

interface DocumentItem {
  name?: string;
  optional?: boolean;
}

/** Compact document checklist card. */
export function DocumentListBubble({ message }: { message: ChatMessage }) {
  const { t } = useTranslation();
  const payload = (message.payload ?? {}) as {
    documents?: DocumentItem[];
  };

  const documents = payload.documents ?? [];

  return (
    <div className="w-full max-w-md rounded-2xl rounded-bl-sm border bg-background p-4">
      <div className="flex items-center gap-2">
        <FileText className="h-4 w-4 text-muted-foreground" />
        <p className="text-sm font-medium">{t("schemes.documents")}</p>
      </div>
      {documents.length > 0 ? (
        <ul className="mt-3 space-y-1.5">
          {documents.map((doc, index) => (
            <li key={index} className="flex items-center justify-between text-sm">
              <span>{doc.name}</span>
              {doc.optional ? (
                <span className="text-xs text-muted-foreground">optional</span>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className={cn("mt-2 text-sm text-muted-foreground")}>
          {message.renderedText ?? message.content}
        </p>
      )}
    </div>
  );
}
