import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import type { ExtractedField, OcrResult } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface ReviewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  ocr: OcrResult | null;
  catalog: Map<string, string>;
  onConfirmType: (documentType: string) => Promise<void>;
  onSave: (fields: ExtractedField[]) => Promise<void>;
}

/** OCR review: confirm/correct the detected type and extracted fields. */
export function ReviewDialog({
  open,
  onOpenChange,
  ocr,
  catalog,
  onConfirmType,
  onSave,
}: ReviewDialogProps) {
  const { t } = useTranslation();
  const [selectedType, setSelectedType] = useState<string>("");
  const [values, setValues] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  const docId = ocr?.documentId;

  useEffect(() => {
    if (open && ocr) {
      setSelectedType(ocr.detectedType ?? "");
      setValues(Object.fromEntries(ocr.extractedFields.map((f) => [f.key, f.value])));
    }
  }, [open, ocr]);

  const typeOptions = useMemo(() => Array.from(catalog.entries()), [catalog]);

  const needsTypeSelection = Boolean(ocr?.needsManualSelection || (!ocr?.detectedType && typeOptions.length > 0));

  const handleSave = async () => {
    if (!docId) return;
    setBusy(true);
    try {
      if (selectedType) await onConfirmType(selectedType);
      await onSave(
        (ocr?.extractedFields ?? []).map((f) => ({ ...f, value: values[f.key] ?? f.value })),
      );
      onOpenChange(false);
    } catch {
      // errors surface as toasts from the caller
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("documents.extractionTitle")}</DialogTitle>
          <DialogDescription>{t("documents.extractionHint")}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              {t("documents.type")}
              {ocr?.detectedType ? <Badge variant="secondary">{t("documents.detectedTitle")}</Badge> : null}
            </Label>
            {needsTypeSelection ? (
              <Select
                value={selectedType ?? undefined}
                onValueChange={setSelectedType}
                disabled={busy}
              >
                <SelectTrigger>
                  <SelectValue placeholder={t("documents.chooseType")} />
                </SelectTrigger>
                <SelectContent>
                  {typeOptions.map(([code, name]) => (
                    <SelectItem key={code} value={code}>
                      {name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <p className="rounded-md border bg-muted/40 px-3 py-2 text-sm">
                {ocr?.detectedType ? catalog.get(ocr.detectedType) ?? ocr?.detectedType : t("documents.unknownType")}
              </p>
            )}
          </div>

          {(ocr?.extractedFields.length ?? 0) > 0 ? (
            <div className="space-y-3">
              <div className="flex items-baseline justify-between">
                <Label>{t("documents.value")}</Label>
              </div>
              {ocr!.extractedFields.map((field) => (
                <div key={field.key} className="space-y-1">
                  <Label className="text-xs text-muted-foreground">{field.label}</Label>
                  <Input
                    value={values[field.key] ?? field.value}
                    disabled={busy}
                    onChange={(e) =>
                      setValues((prev) => ({ ...prev, [field.key]: e.target.value }))
                    }
                  />
                </div>
              ))}
            </div>
          ) : null}
        </div>

        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline" disabled={busy}>
              {t("common.cancel")}
            </Button>
          </DialogClose>
          <Button onClick={handleSave} disabled={busy}>
            {t("documents.save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}