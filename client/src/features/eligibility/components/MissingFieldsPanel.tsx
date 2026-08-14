import { useTranslation } from "react-i18next";
import { PlusCircle, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { fieldLabelKey } from "@/features/eligibility/request";

interface MissingFieldsPanelProps {
  fields: string[];
  onEdit: () => void;
}

/**
 * Progressive-questioning panel: the fields that would sharpen the verdicts,
 * each with a jump into profile edit.
 */
export function MissingFieldsPanel({ fields, onEdit }: MissingFieldsPanelProps) {
  const { t } = useTranslation();
  if (fields.length === 0) return null;

  return (
    <Card className="border-dashed">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Sparkles className="h-4 w-4 text-primary" aria-hidden />
          {t("eligibility.missingTitle")}
        </CardTitle>
        <CardDescription>{t("eligibility.missingDesc")}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap items-center gap-2">
        {fields.map((field) => (
          <Button
            key={field}
            type="button"
            variant="outline"
            size="sm"
            onClick={onEdit}
            className="h-7 gap-1 px-2 text-xs"
          >
            <PlusCircle className="h-3.5 w-3.5" aria-hidden />
            {t(fieldLabelKey(field), { defaultValue: field })}
          </Button>
        ))}
      </CardContent>
    </Card>
  );
}