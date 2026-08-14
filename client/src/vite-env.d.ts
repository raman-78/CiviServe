/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_APP_NAME?: string;
  readonly VITE_APP_ENV?: "development" | "staging" | "production";
  readonly VITE_APP_VERSION?: string;
  readonly VITE_DEFAULT_LANGUAGE?: string;
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_FIREBASE_API_KEY?: string;
  readonly VITE_FIREBASE_AUTH_DOMAIN?: string;
  readonly VITE_FIREBASE_PROJECT_ID?: string;
  readonly VITE_FIREBASE_STORAGE_BUCKET?: string;
  readonly VITE_FIREBASE_MESSAGING_SENDER_ID?: string;
  readonly VITE_FIREBASE_APP_ID?: string;
  readonly VITE_MAPS_PROVIDER?: "osm" | "google";
  readonly VITE_MAPS_API_KEY?: string;
  readonly VITE_STT_ENGINE?: "browser" | "google" | "azure";
  readonly VITE_TTS_ENGINE?: "browser" | "google" | "azure";
  readonly VITE_ENABLE_VOICE?: string;
  readonly VITE_TRANSLATION_FALLBACK_ENABLED?: string;
  readonly VITE_OCR_ENGINE?: "tesseract" | "paddle";
  readonly VITE_ENABLE_OCR?: string;
  readonly VITE_GEOLOCATION_ENABLED?: string;
  readonly VITE_ENABLE_HISTORY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
