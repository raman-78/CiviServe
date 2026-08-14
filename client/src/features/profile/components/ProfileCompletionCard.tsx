import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAuth } from "@/features/auth/AuthContext";

/** Profile completion progress + missing-field checklist. */
export function ProfileCompletionCard() {
  const { t } = useTranslation();
  const { completion, profileLoading } = useAuth();

  if (profileLoading || !completion) return null;

  const complete = completion.isComplete;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{t("profile.completionTitle")}</CardTitle>
        <CardDescription>{t("profile.completionDesc")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <div className="mb-1.5 flex justify-between text-sm">
            <span className="text-muted-foreground">{t("profile.completion")}</span>
            <span className="font-medium">{completion.percent}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{ width: `${completion.percent}%` }}
            />
          </div>
        </div>

        {complete ? (
          <p className="text-sm text-muted-foreground">{t("profile.completionDone")}</p>
        ) : (
          <div className="space-y-2">
            <p className="text-sm font-medium">{t("profile.stillNeeded")}</p>
            <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
              {completion.missingFields.map((field) => (
                <li key={field}>{t(`profile.fields.${field}`)}</li>
              ))}
            </ul>
            <Button asChild className="mt-2">
              <Link to="/profile/setup">{t("profile.completeNow")}</Link>
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
