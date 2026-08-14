import { useTranslation } from "react-i18next";
import { useSettingsStore } from "@/store/settingsSlice";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";

/** Accessibility toggles bound to the persisted settings store. */
export function AccessibilitySettings() {
  const { t } = useTranslation();
  const textOnly = useSettingsStore((s) => s.textOnly);
  const highContrast = useSettingsStore((s) => s.highContrast);
  const slowSpeech = useSettingsStore((s) => s.slowSpeech);
  const setTextOnly = useSettingsStore((s) => s.setTextOnly);
  const setHighContrast = useSettingsStore((s) => s.setHighContrast);
  const setSlowSpeech = useSettingsStore((s) => s.setSlowSpeech);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{t("settings.accessibility")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between gap-4">
          <div className="space-y-0.5">
            <Label htmlFor="acc-textonly">{t("settings.textOnly")}</Label>
            <p className="text-sm text-muted-foreground">{t("settings.textOnlyDesc")}</p>
          </div>
          <Switch
            id="acc-textonly"
            checked={textOnly}
            onCheckedChange={setTextOnly}
          />
        </div>
        <Separator />
        <div className="flex items-center justify-between gap-4">
          <div className="space-y-0.5">
            <Label htmlFor="acc-contrast">{t("settings.highContrast")}</Label>
            <p className="text-sm text-muted-foreground">{t("settings.highContrastDesc")}</p>
          </div>
          <Switch
            id="acc-contrast"
            checked={highContrast}
            onCheckedChange={setHighContrast}
          />
        </div>
        <Separator />
        <div className="flex items-center justify-between gap-4">
          <div className="space-y-0.5">
            <Label htmlFor="acc-slow">{t("settings.slowSpeech")}</Label>
            <p className="text-sm text-muted-foreground">{t("settings.slowSpeechDesc")}</p>
          </div>
          <Switch
            id="acc-slow"
            checked={slowSpeech}
            onCheckedChange={setSlowSpeech}
          />
        </div>
      </CardContent>
    </Card>
  );
}
