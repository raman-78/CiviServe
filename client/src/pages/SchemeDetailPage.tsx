import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingState } from "@/components/shared/LoadingState";
import { SpeakerButton } from "@/components/shared/SpeakerButton";
import { EligibilityView } from "@/features/schemes/components/EligibilityView";
import { DocumentsView } from "@/features/schemes/components/DocumentsView";
import { ApplicationLinksView } from "@/features/schemes/components/ApplicationLinksView";
import { fetchSchemeByCode } from "@/features/schemes/api";
import { toLabel } from "@/lib/utils";
import { formatDate } from "@/lib/formatters";
import type { Scheme } from "@/types";

/** Single scheme detail page (fetched live from the backend by code). */
export function SchemeDetailPage() {
  const { t } = useTranslation();
  const { code } = useParams<{ code: string }>();
  const [scheme, setScheme] = useState<Scheme | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!code) {
      setLoading(false);
      setScheme(null);
      return;
    }
    let active = true;
    setLoading(true);
    setError(false);
    fetchSchemeByCode(code)
      .then((result) => {
        if (active) setScheme(result);
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
  }, [code, attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  if (loading) return <LoadingState />;

  if (error || !scheme) {
    return (
      <EmptyState title={t("schemes.noResults")} description={t("schemes.noResultsDesc")}>
        <div className="flex gap-2">
          <Button asChild variant="outline">
            <Link to="/schemes">{t("schemes.backToSchemes")}</Link>
          </Button>
          <Button variant="outline" onClick={retry}>
            {t("common.retry")}
          </Button>
        </div>
      </EmptyState>
    );
  }

  const verifiedLabel = scheme.lastVerifiedAt ? formatDate(scheme.lastVerifiedAt) : null;

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" asChild>
        <Link to="/schemes" className="gap-1">
          <ArrowLeft className="h-4 w-4" />
          {t("schemes.backToSchemes")}
        </Link>
      </Button>

      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="secondary">{toLabel(scheme.category)}</Badge>
              <Badge variant="outline">{scheme.stateCode === "*" ? "Central" : scheme.stateCode}</Badge>
            </div>
            <SpeakerButton
              id="speak-overview"
              text={`${scheme.name.en}. ${scheme.summary.en}. ${scheme.benefits.join(". ")}`}
              language="en"
              label="chat.listen"
              size="icon"
            />
          </div>
          <CardTitle className="text-2xl">{scheme.name.en}</CardTitle>
          <p className="text-sm text-muted-foreground">{scheme.code}</p>
        </CardHeader>
        <CardContent className="space-y-4">
          <p>{scheme.summary.en}</p>
          {scheme.benefits.length > 0 ? (
            <ul className="space-y-1">
              {scheme.benefits.map((benefit) => (
                <li key={benefit} className="flex items-start gap-2 text-sm">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
                  {benefit}
                </li>
              ))}
            </ul>
          ) : null}
          {verifiedLabel ? (
            <p className="text-xs text-muted-foreground">
              {t("schemes.lastVerified")}: {verifiedLabel}
            </p>
          ) : null}
        </CardContent>
      </Card>

      <EligibilityView rules={scheme.eligibilityRules} />
      <DocumentsView documents={scheme.requiredDocuments} />
      <ApplicationLinksView links={scheme.applicationLinks} />
    </div>
  );
}