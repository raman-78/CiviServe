import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { BadgeCheck, RefreshCw } from "lucide-react";
import { useAuth } from "@/features/auth/AuthContext";
import { PageHeader } from "@/components/shared/PageHeader";
import { LoadingState } from "@/components/shared/LoadingState";
import { EmptyState } from "@/components/shared/EmptyState";
import { SectionSpeakerRow } from "@/components/shared/SectionSpeakerRow";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useEligibility } from "@/features/eligibility/useEligibility";
import { profileToEligibilityRequest } from "@/features/eligibility/request";
import { MissingFieldsPanel } from "@/features/eligibility/components/MissingFieldsPanel";
import { SchemeResultCard } from "@/features/eligibility/components/SchemeResultCard";
import { cn } from "@/lib/utils";

/** Personal eligibility check page (Prompt 10). */
export function EligibilityPage() {
  const { t } = useTranslation();
  const { profile, profileLoading } = useAuth();
  const navigate = useNavigate();
  const request = useMemo(() => profileToEligibilityRequest(profile), [profile]);
  const { data, running, error, ready, refresh } = useEligibility(profile);

  const speechText = useMemo(() => {
    if (!data) return t("eligibility.resultsTitle");
    const parts = data.recommendations.map((rec) => {
      const reasons = rec.reasons.length > 0 ? `: ${rec.reasons.join(". ")}` : "";
      return `${rec.scheme.name.en} — ${Math.round(rec.matchScore)}%.${reasons}`;
    });
    return parts.join(". ");
  }, [data, t]);

  return (
    <div className="space-y-6">
      <PageHeader title={t("eligibility.title")} subtitle={t("eligibility.subtitle")} />

      {profileLoading ? (
        <LoadingState />
      ) : !ready ? (
        <EmptyState
          icon={BadgeCheck}
          title={t("eligibility.emptyTitle")}
          description={t("eligibility.emptyDesc")}
        >
          <Button onClick={() => navigate("/profile/edit")}>
            {t("eligibility.openProfile")}
          </Button>
        </EmptyState>
      ) : (
        <div className="space-y-4">
          <SectionSpeakerRow
            id="eligibility-page"
            title={t("eligibility.resultsTitle")}
            text={speechText}
            language="en"
          />

          <div className="flex items-center justify-between gap-2">
            <p className="text-sm text-muted-foreground">{t("eligibility.resultsHint")}</p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={refresh}
              disabled={running}
            >
              <RefreshCw
                className={cn("h-4 w-4", running && "animate-spin")}
                aria-hidden
              />
              {t("eligibility.checkAgain")}
            </Button>
          </div>

          {running && !data ? <LoadingState label={t("eligibility.loading")} /> : null}

          {error ? (
            <Alert variant="destructive">
              <AlertTitle>{t("eligibility.errorTitle")}</AlertTitle>
              <AlertDescription>{t("eligibility.errorDesc")}</AlertDescription>
            </Alert>
          ) : null}

          {data ? (
            <>
              <MissingFieldsPanel
                fields={data.missingFields}
                onEdit={() => navigate("/profile/edit")}
              />

              {data.recommendations.length === 0 ? (
                <EmptyState
                  title={t("eligibility.noResults")}
                  description={t("eligibility.noResultsDesc")}
                />
              ) : (
                <ul className="space-y-4">
                  {data.recommendations.map((rec) => (
                    <li key={rec.schemeId}>
                      <SchemeResultCard recommendation={rec} request={request} />
                    </li>
                  ))}
                </ul>
              )}
            </>
          ) : null}
        </div>
      )}
    </div>
  );
}