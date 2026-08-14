/**
 * i18next bootstrap. Language preference is persisted and applied to the
 * document; all 13 locales ship UI copy, and RTL layout is applied for Urdu.
 */
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import type { LanguageCode } from "@civiserve/shared";
import { en } from "./resources/en";
import { hi } from "./resources/hi";
import { ta } from "./resources/ta";
import { te } from "./resources/te";
import { bn } from "./resources/bn";
import { kn } from "./resources/kn";
import { ml } from "./resources/ml";
import { gu } from "./resources/gu";
import { mr } from "./resources/mr";
import { pa } from "./resources/pa";
import { or } from "./resources/or";
import { as } from "./resources/as";
import { ur } from "./resources/ur";

export const I18N_RESOURCES = {
  en: { translation: en },
  hi: { translation: hi },
  ta: { translation: ta },
  te: { translation: te },
  bn: { translation: bn },
  kn: { translation: kn },
  ml: { translation: ml },
  gu: { translation: gu },
  mr: { translation: mr },
  pa: { translation: pa },
  or: { translation: or },
  as: { translation: as },
  ur: { translation: ur },
} as const;

export type SupportedLocale = keyof typeof I18N_RESOURCES;

/** Languages rendered right-to-left. */
export const RTL_LOCALES: ReadonlySet<SupportedLocale> = new Set(["ur"]);

const storedLanguage = (): SupportedLocale => {
  try {
    const raw = window.localStorage.getItem("civiserve-settings");
    if (!raw) return "en";
    const parsed = JSON.parse(raw) as { state?: { language?: string } };
    const lang = parsed.state?.language;
    return lang && lang in I18N_RESOURCES ? (lang as SupportedLocale) : "en";
  } catch {
    return "en";
  }
};

const initialLocale = storedLanguage();

// Apply RTL/LTR direction for the persisted language before first paint so
// Urdu is laid out correctly even before any language switch happens.
if (typeof document !== "undefined") {
  document.documentElement.dir = RTL_LOCALES.has(initialLocale) ? "rtl" : "ltr";
}

void i18n.use(initReactI18next).init({
  resources: I18N_RESOURCES,
  lng: initialLocale,
  fallbackLng: "en",
  interpolation: { escapeValue: false },
  returnEmptyString: false,
});

/**
 * Apply the chosen UI language to the document. Accepts the full BCP-47 subset
 * used by the app; resources not yet shipped fall back to English. RTL layout
 * is toggled on `documentElement.dir` for right-to-left locales (Urdu).
 */
export async function applyUILanguage(language: LanguageCode): Promise<void> {
  const locale = language in I18N_RESOURCES ? language : "en";
  document.documentElement.lang = language;
  document.documentElement.dir = RTL_LOCALES.has(locale) ? "rtl" : "ltr";
  await i18n.changeLanguage(locale);
}

export default i18n;
