import { useTranslation } from "react-i18next";
import type { EligibilityRule } from "@/types";
import { toLabel } from "@/lib/utils";
import { SectionSpeakerRow } from "@/components/shared/SectionSpeakerRow";

interface EligibilityViewProps {
  rules: EligibilityRule[];
}

/**
 * Rule-by-rule eligibility breakdown (static until the engine lands). The
 * heading carries a read-aloud speaker for the whole section.
 */
export function EligibilityView({ rules }: EligibilityViewProps) {
  const { t } = useTranslation();

  const speechText = rules
    .map((rule) => `${toLabel(rule.field)}: ${rule.description}`)
    .join(". ");

  return (
    <div className="space-y-3">
      <SectionSpeakerRow id="eligibility" title={t("schemes.minEligibility")} text={speechText} language="en" />
      {rules.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("schemes.noResults")}</p>
      ) : (
        <ul className="space-y-2">
          {rules.map((rule, index) => (
            <li key={index} className="flex items-start gap-2 text-sm">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
              <div>
                <span className="font-medium">{toLabel(rule.field)}:</span>{" "}
                <span className="text-muted-foreground">{rule.description}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}