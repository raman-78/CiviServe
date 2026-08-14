import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { CheckCircle2, Circle, AlertTriangle } from "lucide-react";
import type { DocumentReadiness, RequiredDocument } from "@/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { LoadingState } from "@/components/shared/LoadingState";
import { cn } from "@/lib/utils";

const STATUS_KEYS: Record<string, string> = {
  uploaded: "documents.statusUploaded",
  processing: "documents.statusProcessing",
  processed: "documents.statusProcessed",
  needs_review: "documents.statusNeedsReview",
  matches: "documents.statusMatches",
  mismatch: "documents.statusMismatch",
  unsupported: "documents.statusUnsupported",
  ocr_failed: "documents.statusOcrFailed",
  user_confirmed: "documents.statusUserConfirmed",
  missing: "documents.statusMissing",
};

function itemVariant(status: string) {
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

interface ReadinessSectionProps {
  schemeOptions: { code: string; name: string }[];
  onLoad: (schemeCode: string) => Promise<DocumentReadiness>;
}

/** Scheme document checklist (CiviServe pre-check only). */
export function ReadinessSection({ schemeOptions, onLoad }: ReadinessSectionProps) {
  const { t } = useTranslation();
  const [schemeCode, setSchemeCode] = useState("");
  const [readiness, setReadiness] = useState<DocumentReadiness | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!schemeCode) return;
    let active = true;
    setLoading(true);
    setError(false);
    onLoad(schemeCode)
      .then((data) => {
        if (active) setReadiness(data);
      })
      .catch(() => {
        if (active) setError(true);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [schemeCode, onLoad]);

  const name = (doc: RequiredDocument) => doc.localizedNames?.en ?? doc.name;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("documents.readinessTitle")}</CardTitle>
        <CardDescription>{t("documents.readinessSubtitle")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Select value={schemeCode || undefined} onValueChange={setSchemeCode}>
          <SelectTrigger className="max-w-xs">
            <SelectValue placeholder={t("schemes.title")} />
          </SelectTrigger>
          <SelectContent>
            {schemeOptions.map((s) => (
              <SelectItem key={s.code} value={s.code}>
                {s.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {loading ? <LoadingState compact /> : null}
        {error ? <p className="text-sm text-destructive">{t("documents.uploadError")}</p> : null}

        {readiness ? (
          <>
            <div className="flex flex-wrap items-center gap-4 text-sm">
              <span className="font-medium">
                {readiness.percent}% {t("documents.complete")}
              </span>
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                {readiness.uploadedCount} {t("documents.uploaded")}
              </span>
              {readiness.missingCount > 0 ? (
                <span className="flex items-center gap-1.5 text-muted-foreground">
                  <Circle className="h-4 w-4" />
                  {readiness.missingCount} {t("documents.missing")}
                </span>
              ) : null}
              {readiness.needsReviewCount > 0 ? (
                <span className="flex items-center gap-1.5 text-amber-600">
                  <AlertTriangle className="h-4 w-4" />
                  {readiness.needsReviewCount} {t("documents.needsAttention")}
                </span>
              ) : null}
            </div>

            <ul className="space-y-2">
              {readiness.items.map((item) => (
                <li
                  key={item.required.id}
                  className="flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm"
                >
                  <span className="flex min-w-0 items-center gap-2">
                    {item.status === "missing" ? (
                      <Circle className="h-4 w-4 shrink-0 text-muted-foreground" />
                    ) : item.status === "needs_review" || item.status === "mismatch" || item.status === "unsupported" || item.status === "ocr_failed" ? (
                      <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600" />
                    ) : (
                      <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
                    )}
                    <span className={cn("truncate", item.status === "missing" && "text-muted-foreground")}>
                      {name(item.required)}
                    </span>
                  </span>
                  <Badge variant={itemVariant(item.status)}>
                    {t(STATUS_KEYS[item.status] ?? "documents.statusMissing")}
                  </Badge>
                </li>
              ))}
            </ul>

            <p className="rounded-md bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
              {readiness.disclaimer || t("documents.disclaimer")}
            </p>
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}