import { Check, ChevronsUpDown, Languages } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useSettingsStore } from "@/store/settingsSlice";
import { applyUILanguage } from "@/i18n";
import { SUPPORTED_UI_LANGUAGES } from "@/lib/constants";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

/** Global language switcher. Persists the preference via the settings store. */
export function LanguageSwitcher() {
  const { t } = useTranslation();
  const language = useSettingsStore((s) => s.language);
  const setLanguage = useSettingsStore((s) => s.setLanguage);

  const current = SUPPORTED_UI_LANGUAGES.find((l) => l.code === language);

  const handleSelect = (code: string) => {
    const next = SUPPORTED_UI_LANGUAGES.find((l) => l.code === code);
    if (!next) return;
    setLanguage(next.code);
    void applyUILanguage(next.code);
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="gap-1.5">
          <Languages className="h-4 w-4" />
          <span>{current?.native ?? "English"}</span>
          <ChevronsUpDown className="h-3 w-3 opacity-60" aria-hidden />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>{t("language.choose")}</DropdownMenuLabel>
        <DropdownMenuRadioGroup value={language} onValueChange={handleSelect}>
          {SUPPORTED_UI_LANGUAGES.map((lang) => (
            <DropdownMenuRadioItem key={lang.code} value={lang.code}>
              <span className="flex-1">{lang.native}</span>
              <span className="text-xs text-muted-foreground">{lang.label}</span>
              {lang.code === language && <Check className="h-4 w-4" />}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
