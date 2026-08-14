import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Pencil } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/features/auth/AuthContext";

/** Read-only summary of the stored profile with an edit link. */
export function ProfileSummaryCard() {
  const { t } = useTranslation();
  const { profile, me, profileLoading, user } = useAuth();

  if (profileLoading || !profile) {
    return (
      <Card>
        <CardContent className="space-y-3 pt-6">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-4 w-2/3" />
        </CardContent>
      </Card>
    );
  }

  const email = me?.email ?? user?.email ?? "";
  const rows: { label: string; value: string }[] = [
    { label: t("profile.name"), value: profile.name ?? "" },
    { label: t("auth.email"), value: email },
    { label: t("profile.phone"), value: profile.phone ?? "" },
    { label: t("profile.age"), value: profile.age !== undefined ? String(profile.age) : "" },
    {
      label: t("profile.state"),
      value: profile.stateCode ? `${profile.stateCode}${profile.district ? ` · ${profile.district}` : ""}` : "",
    },
    { label: t("profile.incomeBand"), value: profile.incomeBand ? profile.incomeBand.replace(/-/g, " ") : "" },
    {
      label: t("profile.education"),
      value: profile.education ? profile.education.replace(/-/g, " ") : "",
    },
    { label: t("profile.occupation"), value: profile.occupation ?? "" },
    {
      label: t("profile.languages"),
      value: (profile.languages ?? []).join(", "),
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{t("profile.summaryTitle")}</CardTitle>
        <CardDescription>{t("profile.summaryDesc")}</CardDescription>
      </CardHeader>
      <CardContent>
        <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
          {rows
            .filter((row) => row.value)
            .map((row) => (
              <div key={row.label} className="flex flex-col">
                <dt className="text-xs uppercase tracking-wide text-muted-foreground">{row.label}</dt>
                <dd className="text-sm font-medium">{row.value}</dd>
              </div>
            ))}
        </dl>
        {rows.every((row) => !row.value) ? (
          <p className="text-sm text-muted-foreground">{t("profile.empty")}</p>
        ) : null}
      </CardContent>
      <CardFooter>
        <Button asChild variant="outline">
          <Link to="/profile/edit">
            <Pencil className="h-4 w-4" />
            {t("profile.edit")}
          </Link>
        </Button>
      </CardFooter>
    </Card>
  );
}
