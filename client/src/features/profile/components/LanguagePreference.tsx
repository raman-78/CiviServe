import { useTranslation } from "react-i18next";
import { useSettingsStore } from "@/store/settingsSlice";
import { applyUILanguage } from "@/i18n";
import { SUPPORTED_UI_LANGUAGES } from "@/lib/constants";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/** Language preference control for the profile page. */
export function LanguagePreference() {
  const { t } = useTranslation();
  const language = useSettingsStore((s) => s.language);
  const setLanguage = useSettingsStore((s) => s.setLanguage);

  const handleChange = (code: string) => {
    const next = SUPPORTED_UI_LANGUAGES.find((l) => l.code === code);
    if (!next) return;
    setLanguage(next.code);
    void applyUILanguage(next.code);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{t("language.choose")}</CardTitle>
        <CardDescription>{t("profile.subtitle")}</CardDescription>
      </CardHeader>
      <CardContent>
        <Label htmlFor="profile-language">{t("language.choose")}</Label>
        <Select value={language} onValueChange={handleChange}>
          <SelectTrigger id="profile-language" className="mt-1.5">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {SUPPORTED_UI_LANGUAGES.map((lang) => (
              <SelectItem key={lang.code} value={lang.code}>
                {lang.native}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </CardContent>
    </Card>
  );
}
