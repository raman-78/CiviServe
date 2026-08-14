import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { ChevronDown, ChevronUp, CircleAlert } from "lucide-react";
import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { SpeakerButton } from "@/components/shared/SpeakerButton";
import type { Recommendation } from "@/types";
import type { RecommendationRequest } from "@/types";
import {
  fieldLabelKey,
  statusLabelKey,
  statusTone,
} from "@/features/eligibility/request";
import { fetchAlternatives } from "@/features/eligibility/api";

interface SchemeResultCardProps {
  recommendation: Recommendation;
  request: RecommendationRequest;
}

/** One scheme verdict: status badge, reasons, unmet rules, and alternatives. */
export function SchemeResultCard({ recommendation, request }: SchemeResultCardProps) {
  const { t } = useTranslation();
  const scheme = recommendation.scheme;
  const short = `${scheme.code}: ${scheme.name.en}. ${t(statusLabelKey(recommendation.status))}.`;

  const [showAlternatives, setShowAlternatives] = useState(false);
  const [alternatives, setAlternatives] = useState<Recommendation[]>([]);
  const [alternativesLoading, setAlternativesLoading] = useState(false);
  const [alternativesError, setAlternativesError] = useState(false);

  const toggleAlternatives = useCallback(async () => {
    if (showAlternatives) {
      setShowAlternatives(false);
      return;
    }
    setShowAlternatives(true);
    if (alternatives.length > 0 || alternativesError) return;
    setAlternativesLoading(true);
    setAlternativesError(false);
    try {
      setAlternatives(await fetchAlternatives(scheme.code, request));
    } catch {
      setAlternativesError(true);
    } finally {
      setAlternativesLoading(false);
    }
  }, [showAlternatives, alternatives.length, alternativesError, scheme.code, request]);

  const canOfferAlternatives = recommendation.status === "not_eligible";

  return (
    <Card>
      <CardContent className="space-y-3 pt-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {scheme.code}
            </p>
            <h3 className="text-base font-semibold leading-snug">
              <Link
                to={`/schemes/${scheme.code}`}
                className="hover:underline"
              >
                {scheme.name.en}
              </Link>
            </h3>
          </div>
          <div className="flex shrink-0 flex-col items-end gap-1">
            <Badge variant={statusTone(recommendation.status)}>
              {t(statusLabelKey(recommendation.status))}
            </Badge>
            <span className="text-xs font-medium text-muted-foreground">
              {t("eligibility.matchScore", { count: Math.round(recommendation.matchScore) })}
            </span>
          </div>
        </div>

        {recommendation.reasons.length > 0 ? (
          <>
            <Separator />
            <div className="space-y-1.5">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {t("eligibility.reasonsTitle")}
              </p>
              <ul className="space-y-1 text-sm text-muted-foreground">
                {recommendation.reasons.map((reason, index) => (
                  <li key={index} className="flex gap-2">
                    <span aria-hidden>•</span>
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>
            </div>
          </>
        ) : null}

        {recommendation.brokenRules && recommendation.brokenRules.length > 0 ? (
          <div className="space-y-1.5">
            <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-destructive">
              <CircleAlert className="h-3.5 w-3.5" aria-hidden />
              {t("eligibility.brokenTitle")}
            </p>
            <ul className="space-y-1 text-sm text-muted-foreground">
              {recommendation.brokenRules.map((rule, index) => (
                <li key={index}>
                  <span className="font-medium text-foreground">
                    {t(fieldLabelKey(rule.field), { defaultValue: rule.field })}:
                  </span>{" "}
                  {rule.description}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {canOfferAlternatives ? (
          <div className="pt-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="gap-1 -ml-2 text-xs text-muted-foreground"
              onClick={toggleAlternatives}
              disabled={alternativesLoading}
            >
              {showAlternatives ? (
                <ChevronUp className="h-3.5 w-3.5" aria-hidden />
              ) : (
                <ChevronDown className="h-3.5 w-3.5" aria-hidden />
              )}
              {showAlternatives
                ? t("eligibility.alternativesHide")
                : t("eligibility.alternativesCta")}
            </Button>

            {showAlternatives ? (
              <div className="mt-2 space-y-2 rounded-md border bg-muted/30 p-3">
                {alternativesLoading ? (
                  <p className="text-xs text-muted-foreground">{t("common.loading")}</p>
                ) : null}
                {alternativesError ? (
                  <p className="text-xs text-destructive">{t("eligibility.alternativesError")}</p>
                ) : null}
                {!alternativesLoading && !alternativesError && alternatives.length === 0 ? (
                  <p className="text-xs text-muted-foreground">{t("eligibility.alternativesEmpty")}</p>
                ) : null}
                {alternatives.map((item) => (
                  <div key={item.schemeId}>
                    <Link
                      to={`/schemes/${item.scheme.code}`}
                      className="group flex items-start justify-between gap-2"
                    >
                      <span className="text-sm font-medium group-hover:underline">
                        {item.scheme.name.en}
                      </span>
                      <Badge variant={statusTone(item.status)} className="ml-auto shrink-0">
                        {t(statusLabelKey(item.status))}
                      </Badge>
                    </Link>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        <div className="flex justify-end">
          <SpeakerButton
            id={`eligibility-${recommendation.schemeId}`}
            text={short}
            language="en"
            label="chat.listen"
            size="sm"
            withText={false}
          />
        </div>
      </CardContent>
    </Card>
  );
}