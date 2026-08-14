import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/shared/PageHeader";
import { ProfileCompletionCard } from "@/features/profile/components/ProfileCompletionCard";
import { ProfileSummaryCard } from "@/features/profile/components/ProfileSummaryCard";
import { ConsentBanner } from "@/features/profile/components/ConsentBanner";
import { LanguagePreference } from "@/features/profile/components/LanguagePreference";

/** Profile page: completion indicator + summary + privacy preferences. */
export function ProfilePage() {
  const { t } = useTranslation();

  return (
    <div className="space-y-8">
      <PageHeader title={t("profile.title")} subtitle={t("profile.subtitle")} />
      <ProfileCompletionCard />
      <ProfileSummaryCard />
      <LanguagePreference />
      <ConsentBanner />
    </div>
  );
}
