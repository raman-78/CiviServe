import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/shared/PageHeader";
import { LoadingState } from "@/components/shared/LoadingState";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/features/auth/AuthContext";
import { ProfileForm } from "@/features/profile/components/ProfileForm";
import { fromProfile } from "@/features/profile/profileSchema";

/** Edit existing profile (single full form). */
export function EditProfilePage() {
  const { t } = useTranslation();
  const { profile, profileLoading, refreshProfile } = useAuth();

  if (profileLoading) return <LoadingState />;

  return (
    <div className="space-y-8">
      <PageHeader title={t("profile.editTitle")} subtitle={t("profile.editSubtitle")} />
      <Card>
        <CardContent className="pt-6">
          <ProfileForm
            defaultValues={fromProfile(profile ?? {})}
            onSaved={() => void refreshProfile()}
          />
        </CardContent>
      </Card>
    </div>
  );
}
