import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { UploadCloud } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const ACCEPTED_FORMATS = ["pdf", "jpg", "jpeg", "png"];
const MAX_BYTES = 10 * 1024 * 1024;

interface UploadZoneProps {
  onFile: (file: File) => void;
  busy?: boolean;
  disabled?: boolean;
}

/** Dropzone + hidden file input for document uploads (Prompt 11). */
export function UploadZone({ onFile, busy, disabled }: UploadZoneProps) {
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const acceptFile = (file: File | undefined | null) => {
    if (!file) return;
    const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
    if (!ACCEPTED_FORMATS.includes(ext)) {
      setError(t("documents.badType"));
      return;
    }
    if (file.size > MAX_BYTES) {
      setError(t("documents.maxSize"));
      return;
    }
    setError(null);
    onFile(file);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div
      role="button"
      tabIndex={0}
      aria-disabled={busy || disabled}
      onClick={() => {
        if (!busy && !disabled) inputRef.current?.click();
      }}
      onKeyDown={(e) => {
        if ((e.key === "Enter" || e.key === " ") && !busy && !disabled) {
          inputRef.current?.click();
        }
      }}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        acceptFile(e.dataTransfer.files?.[0]);
      }}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed p-8 text-center transition-colors",
        dragging ? "border-primary bg-primary/5" : "border-muted-foreground/30",
        (busy || disabled) && "cursor-not-allowed opacity-60",
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.jpg,.jpeg,.png"
        className="hidden"
        onChange={(e) => acceptFile(e.target.files?.[0])}
      />
      <UploadCloud className="h-8 w-8 text-muted-foreground" />
      <div className="space-y-1">
        <p className="text-sm font-medium">
          {busy ? t("documents.uploading") : t("documents.chooseAFile")}
        </p>
        <p className="text-xs text-muted-foreground">{t("documents.dropHint")}</p>
      </div>
      <Button type="button" variant="outline" size="sm" disabled={busy || disabled}>
        {t("documents.upload")}
      </Button>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
    </div>
  );
}