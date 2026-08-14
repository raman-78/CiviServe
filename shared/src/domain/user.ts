import type { ISODateString, LanguageCode, UUID } from "./common";

export type Gender = "male" | "female" | "transgender" | "prefer-not-to-say";
export type IncomeBand = "below-poverty" | "low" | "middle" | "upper";
export type CasteCategory = "general" | "sc" | "st" | "obc" | "ews";

/** Highest level of education attained (mirrors `user_profiles.education_level`). */
export type EducationLevel =
  | "none"
  | "primary"
  | "secondary"
  | "higher-secondary"
  | "diploma"
  | "graduate"
  | "postgraduate"
  | "professional"
  | "other";

export type MaritalStatus = "unmarried" | "married" | "widowed" | "divorced" | "prefer-not-to-say";

/** How the citizen prefers to interact with the assistant. */
export type PreferredInputMethod = "text" | "voice" | "both";
export type PreferredOutputMethod = "text" | "voice" | "both";

export type NotificationPreference = "all" | "essential" | "none";

export interface ConsentFlags {
  /** Allow storing a minimal profile used to recommend schemes. */
  dataProcessing: boolean;
  /** Allow capturing voice for STT (transcripts are not retained by default). */
  voiceProcessing: boolean;
  /** Allow using precise location for nearby centers. */
  locationAccess?: boolean;
}

export interface AccessibilityPreferences {
  /** Prefer text-only replies (no auto TTS). */
  textOnly?: boolean;
  highContrast?: boolean;
  /** Slow down speech synthesis. */
  slowSpeech?: boolean;
}

/**
 * Minimal citizen profile. The chatbot collects only the attributes needed to
 * evaluate eligibility rules — nothing more. Stored server-side keyed by the
 * Firebase UID; PII is minimized per DPDP/security guidance.
 */
export interface UserProfile {
  id: UUID;
  /** Firebase Authentication UID (null for guests). */
  firebaseUid?: string;
  name?: string;
  phone?: string;
  stateCode?: string;
  district?: string;
  age?: number;
  gender?: Gender;
  incomeBand?: IncomeBand;
  casteCategory?: CasteCategory;
  education?: EducationLevel;
  occupation?: string;
  isStudent?: boolean;
  isFarmer?: boolean;
  isMinority?: boolean;
  isDisabled?: boolean;
  disabilityType?: string;
  maritalStatus?: MaritalStatus;
  /** Preferred UI/chat language, mirrored to `users.preferred_language`. */
  preferredLanguage?: LanguageCode;
  preferredInputMethod?: PreferredInputMethod;
  preferredOutputMethod?: PreferredOutputMethod;
  notificationPreference?: NotificationPreference;
  languages: LanguageCode[];
  accessibilityPreferences?: AccessibilityPreferences;
  consent: ConsentFlags;
  createdAt: ISODateString;
  updatedAt: ISODateString;
}

/**
 * Writable profile subset (PUT /users/me/profile). Field names exactly match
 * `UserProfile`; omitted fields are left unchanged by the server.
 */
export interface ProfileUpdate {
  name?: string;
  phone?: string;
  stateCode?: string;
  district?: string;
  age?: number;
  gender?: Gender;
  incomeBand?: IncomeBand;
  casteCategory?: CasteCategory;
  education?: EducationLevel;
  occupation?: string;
  isStudent?: boolean;
  isFarmer?: boolean;
  isMinority?: boolean;
  isDisabled?: boolean;
  disabilityType?: string;
  maritalStatus?: MaritalStatus;
  preferredLanguage?: LanguageCode;
  preferredInputMethod?: PreferredInputMethod;
  preferredOutputMethod?: PreferredOutputMethod;
  notificationPreference?: NotificationPreference;
  languages?: LanguageCode[];
  accessibilityPreferences?: AccessibilityPreferences;
  consent?: ConsentFlags;
}

/**
 * Profile completion indicator (GET /users/me/profile/completion). Computed
 * server-side so the required-field list has a single source of truth.
 */
export interface ProfileCompletion {
  percent: number;
  isComplete: boolean;
  completedFields: string[];
  missingFields: string[];
}

export type UserRole = "citizen" | "admin" | "content_editor";
export type AuthMethod = "email" | "phone" | "google" | "guest";

/** Server view of the authenticated account (GET /auth/me). */
export interface CurrentUser {
  userId: string;
  firebaseUid?: string;
  email?: string;
  displayName?: string;
  role: UserRole;
  isGuest: boolean;
  authMethod: AuthMethod;
  emailVerified: boolean;
  preferredLanguage: LanguageCode;
  createdAt?: ISODateString;
}
