import type { LanguageCode } from "./common";

/** Supported language capabilities surfaced to the UI. */
export interface LanguageInfo {
  code: LanguageCode;
  /** Native name, e.g. "हिन्दी" for hi. */
  nativeName: string;
  /** English name, e.g. "Hindi". */
  englishName: string;
  /** Script direction. */
  rtl: boolean;
  stt: boolean;
  tts: boolean;
  /** IndicTrans2 coverage (else Google fallback is used). */
  indicTrans: boolean;
}

/** Canonical catalog of supported languages (source of truth, mirrored server-side). */
export const SUPPORTED_LANGUAGES: readonly LanguageInfo[] = [
  { code: "hi", nativeName: "हिन्दी", englishName: "Hindi", rtl: false, stt: true, tts: true, indicTrans: true },
  { code: "bn", nativeName: "বাংলা", englishName: "Bengali", rtl: false, stt: true, tts: true, indicTrans: true },
  { code: "ta", nativeName: "தமிழ்", englishName: "Tamil", rtl: false, stt: true, tts: true, indicTrans: true },
  { code: "te", nativeName: "తెలుగు", englishName: "Telugu", rtl: false, stt: true, tts: true, indicTrans: true },
  { code: "kn", nativeName: "ಕನ್ನಡ", englishName: "Kannada", rtl: false, stt: true, tts: true, indicTrans: true },
  { code: "ml", nativeName: "മലയാളം", englishName: "Malayalam", rtl: false, stt: true, tts: true, indicTrans: true },
  { code: "gu", nativeName: "ગુજરાતી", englishName: "Gujarati", rtl: false, stt: true, tts: true, indicTrans: true },
  { code: "mr", nativeName: "मराठी", englishName: "Marathi", rtl: false, stt: true, tts: true, indicTrans: true },
  { code: "pa", nativeName: "ਪੰਜਾਬੀ", englishName: "Punjabi", rtl: false, stt: true, tts: true, indicTrans: true },
  { code: "or", nativeName: "ଓଡ଼ିଆ", englishName: "Odia", rtl: false, stt: true, tts: true, indicTrans: true },
  { code: "as", nativeName: "অসমীয়া", englishName: "Assamese", rtl: false, stt: true, tts: true, indicTrans: true },
  { code: "ur", nativeName: "اردو", englishName: "Urdu", rtl: true, stt: true, tts: true, indicTrans: true },
  { code: "en", nativeName: "English", englishName: "English", rtl: false, stt: true, tts: true, indicTrans: true },
];

/** Default fallback language when the user's choice is not supported. */
export const FALLBACK_LANGUAGE: LanguageCode = "en";

/**
 * BCP-47 speech locales for the on-device/web speech adapters. Indian-English
 * (`*-IN`) voices are preferred so regional accents are recognised/spoken.
 * The browser falls back to any voice it has for the primary subtag when an
 * exact `-IN` voice does not exist.
 */
export const SPEECH_LOCALES: Readonly<Record<LanguageCode, string>> = {
  as: "as-IN",
  bn: "bn-IN",
  en: "en-IN",
  gu: "gu-IN",
  hi: "hi-IN",
  kn: "kn-IN",
  ml: "ml-IN",
  mr: "mr-IN",
  or: "or-IN",
  pa: "pa-IN",
  ta: "ta-IN",
  te: "te-IN",
  ur: "ur-IN",
};

/** Speech playback rate presets shown in the voice settings. */
export const SPEECH_RATES: Readonly<Record<SpeechSpeed, number>> = {
  slow: 0.8,
  normal: 1,
  fast: 1.25,
};

/** User-selectable read-aloud pace. */
export type SpeechSpeed = "slow" | "normal" | "fast";
