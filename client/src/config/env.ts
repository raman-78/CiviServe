/**
 * Typed access to client environment variables and derived feature flags.
 * All values are public-by-design (Vite inlines only `VITE_*`).
 */
const env = import.meta.env;

const bool = (value: string | undefined, fallback: boolean): boolean => {
  if (value === undefined) return fallback;
  return value === "true" || value === "1";
};

export const appConfig = {
  name: env.VITE_APP_NAME ?? "CiviServe",
  env: (env.VITE_APP_ENV ?? "development") as "development" | "staging" | "production",
  version: env.VITE_APP_VERSION ?? "0.1.0",
  defaultLanguage: env.VITE_DEFAULT_LANGUAGE ?? "en",
  apiBaseUrl: env.VITE_API_BASE_URL ?? "",
} as const;

/** Public Firebase web config (not a secret — docs/architecture/15 §1). */
export const firebaseConfig = {
  apiKey: env.VITE_FIREBASE_API_KEY ?? "",
  authDomain: env.VITE_FIREBASE_AUTH_DOMAIN ?? "",
  projectId: env.VITE_FIREBASE_PROJECT_ID ?? "",
  storageBucket: env.VITE_FIREBASE_STORAGE_BUCKET ?? "",
  messagingSenderId: env.VITE_FIREBASE_MESSAGING_SENDER_ID ?? "",
  appId: env.VITE_FIREBASE_APP_ID ?? "",
} as const;

/** True when a Firebase web project has been configured via env vars. */
export const isFirebaseConfigured = Boolean(
  firebaseConfig.apiKey && firebaseConfig.projectId,
);

export const featureFlags = {
  voice: bool(env.VITE_ENABLE_VOICE, true),
  ocr: bool(env.VITE_ENABLE_OCR, false),
  geolocation: bool(env.VITE_GEOLOCATION_ENABLED, true),
  history: bool(env.VITE_ENABLE_HISTORY, true),
  translationFallback: bool(env.VITE_TRANSLATION_FALLBACK_ENABLED, true),
  mapsProvider: (env.VITE_MAPS_PROVIDER ?? "osm") as "osm" | "google",
  /** Adapter selector used by services/stt (docs/architecture/10). */
  sttEngine: (env.VITE_STT_ENGINE ?? "browser") as "browser" | "google" | "azure",
  /** Adapter selector used by services/tts (docs/architecture/10). */
  ttsEngine: (env.VITE_TTS_ENGINE ?? "browser") as "browser" | "google" | "azure",
} as const;
