import { useTranslation } from "react-i18next";
import { useSettingsStore } from "@/store/settingsSlice";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";

/** Notification preference toggles bound to the persisted settings store. */
export function NotificationSettings() {
  const { t } = useTranslation();
  const notifications = useSettingsStore((s) => s.notifications);
  const toggleNotification = useSettingsStore((s) => s.toggleNotification);

  const rows = [
    { key: "schemeUpdates" as const, label: t("settings.schemeUpdates") },
    { key: "eligibilityMatches" as const, label: t("settings.eligibilityMatches") },
    { key: "renewalReminders" as const, label: t("settings.renewalReminders") },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{t("settings.notifications")}</CardTitle>
        <CardDescription>{t("settings.subtitle")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {rows.map((row, index) => (
          <div key={row.key}>
            {index > 0 ? <Separator className="mb-4" /> : null}
            <div className="flex items-center justify-between gap-4">
              <div className="space-y-0.5">
                <Label htmlFor={`notif-${row.key}`}>{row.label}</Label>
              </div>
              <Switch
                id={`notif-${row.key}`}
                checked={notifications[row.key]}
                onCheckedChange={() => toggleNotification(row.key)}
              />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
