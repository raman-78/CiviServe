import { useTranslation } from "react-i18next";
import { useSettingsStore } from "@/store/settingsSlice";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";

/** Consent + privacy toggles bound to the persisted settings store. */
export function ConsentBanner() {
  const { t } = useTranslation();
  const consent = useSettingsStore((s) => s.consent);
  const setConsent = useSettingsStore((s) => s.setConsent);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{t("profile.consent")}</CardTitle>
        <CardDescription>{t("profile.consentDesc")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between gap-4">
          <div className="space-y-0.5">
            <Label htmlFor="consent-data">{t("settings.dataProcessing")}</Label>
          </div>
          <Switch
            id="consent-data"
            checked={consent.dataProcessing}
            onCheckedChange={(checked) => setConsent({ dataProcessing: checked })}
          />
        </div>
        <Separator />
        <div className="flex items-center justify-between gap-4">
          <div className="space-y-0.5">
            <Label htmlFor="consent-voice">{t("settings.voiceProcessing")}</Label>
          </div>
          <Switch
            id="consent-voice"
            checked={consent.voiceProcessing}
            onCheckedChange={(checked) => setConsent({ voiceProcessing: checked })}
          />
        </div>
        <Separator />
        <div className="flex items-center justify-between gap-4">
          <div className="space-y-0.5">
            <Label htmlFor="consent-location">{t("settings.locationAccess")}</Label>
          </div>
          <Switch
            id="consent-location"
            checked={consent.locationAccess}
            onCheckedChange={(checked) => setConsent({ locationAccess: checked })}
          />
        </div>
      </CardContent>
    </Card>
  );
}
