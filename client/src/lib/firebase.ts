/**
 * Firebase app + auth singleton.
 *
 * The web config is public-by-design (docs/architecture/15 §1) and comes from
 * `VITE_FIREBASE_*` env vars. Initialization is lazy so modules that import this
 * never throw at load time when the project is unconfigured.
 */
import { initializeApp, type FirebaseApp } from "firebase/app";
import { getAuth, type Auth } from "firebase/auth";
import { firebaseConfig, isFirebaseConfigured } from "@/config/env";

let app: FirebaseApp | null = null;
let auth: Auth | null = null;

function ensureConfigured(): void {
  if (!isFirebaseConfigured) {
    throw new Error(
      "Firebase is not configured. Set the VITE_FIREBASE_* environment variables.",
    );
  }
}

export function getFirebaseApp(): FirebaseApp {
  if (!app) {
    ensureConfigured();
    app = initializeApp(firebaseConfig);
  }
  return app;
}

export function getFirebaseAuth(): Auth {
  if (!auth) {
    auth = getAuth(getFirebaseApp());
  }
  return auth;
}
