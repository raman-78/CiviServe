import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/shared/PageHeader";
import { AccountSettings } from "@/features/settings/components/AccountSettings";
import { AccessibilitySettings } from "@/features/settings/components/AccessibilitySettings";
import { VoiceSettings } from "@/features/settings/components/VoiceSettings";
import { NotificationSettings } from "@/features/settings/components/NotificationSettings";

/** Settings page: account, accessibility, voice and notification preferences. */
export function SettingsPage() {
  const { t } = useTranslation();

  return (
    <div className="space-y-8">
      <PageHeader title={t("settings.title")} subtitle={t("settings.subtitle")} />
      <AccountSettings />
      <AccessibilitySettings />
      <VoiceSettings />
      <NotificationSettings />
    </div>
  );
}
