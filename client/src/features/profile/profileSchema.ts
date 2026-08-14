/**
 * Zod schema + value mappers for the citizen profile form.
 *
 * The form keeps raw string/select values (age as text, tri-state selects for
 * boolean attributes) so empty selections are distinguishable from "no"; the
 * mapper converts to the canonical `ProfileUpdate` contract on submit.
 */
import { z } from "zod";
import type {
  AccessibilityPreferences,
  CasteCategory,
  ConsentFlags,
  EducationLevel,
  Gender,
  IncomeBand,
  LanguageCode,
  MaritalStatus,
  NotificationPreference,
  PreferredInputMethod,
  PreferredOutputMethod,
  ProfileUpdate,
  UserProfile,
} from "@civiserve/shared";

export const GENDERS = ["male", "female", "transgender", "prefer-not-to-say"] as const;
export const INCOME_BANDS = ["below-poverty", "low", "middle", "upper"] as const;
export const CASTE_CATEGORIES = ["general", "sc", "st", "obc", "ews"] as const;
export const EDUCATION_LEVELS = [
  "none",
  "primary",
  "secondary",
  "higher-secondary",
  "diploma",
  "graduate",
  "postgraduate",
  "professional",
  "other",
] as const;
export const MARITAL_STATUSES = [
  "unmarried",
  "married",
  "widowed",
  "divorced",
  "prefer-not-to-say",
] as const;
export const INPUT_OUTPUT_METHODS = ["text", "voice", "both"] as const;
export const NOTIFICATION_PREFERENCES = ["all", "essential", "none"] as const;
export const YES_NO_UNSURE = ["yes", "no", "not-sure"] as const;

export type TriState = (typeof YES_NO_UNSURE)[number] | "";

export const profileSchema = z.object({
  name: z.string().trim().min(1, "Please enter your name."),
  phone: z
    .string()
    .trim()
    .optional()
    .refine((v) => !v || /^[+0-9][0-9 .-]{6,19}$/.test(v), "Enter a valid phone number."),
  age: z
    .string()
    .refine(
      (v) => v === "" || (Number.isInteger(Number(v)) && Number(v) >= 0 && Number(v) <= 130),
      "Enter a valid age (0–130).",
    ),
  gender: z.enum([...GENDERS, ""] as const),
  stateCode: z.string().trim().min(1, "Select your state."),
  district: z.string().trim().min(1, "Please enter your district."),
  incomeBand: z.enum([...INCOME_BANDS, ""] as const),
  casteCategory: z.enum([...CASTE_CATEGORIES, ""] as const),
  education: z.enum([...EDUCATION_LEVELS, ""] as const),
  occupation: z.string().trim().optional(),
  maritalStatus: z.enum([...MARITAL_STATUSES, ""] as const),
  isStudent: z.enum([...YES_NO_UNSURE, ""] as const),
  isFarmer: z.enum([...YES_NO_UNSURE, ""] as const),
  isMinority: z.enum([...YES_NO_UNSURE, ""] as const),
  isDisabled: z.enum([...YES_NO_UNSURE, ""] as const),
  disabilityType: z.string().trim().max(60).optional(),
  preferredLanguage: z.string().trim(),
  preferredInputMethod: z.enum([...INPUT_OUTPUT_METHODS, ""] as const),
  preferredOutputMethod: z.enum([...INPUT_OUTPUT_METHODS, ""] as const),
  notificationPreference: z.enum([...NOTIFICATION_PREFERENCES, ""] as const),
  languages: z.array(z.string().trim().min(1)).min(1, "Choose at least one language."),
});

export type ProfileFormValues = z.infer<typeof profileSchema>;

function triToBool(value: ProfileFormValues["isStudent"]): boolean | undefined {
  if (value === "yes") return true;
  if (value === "no") return false;
  return undefined;
}

function boolToTri(value: boolean | undefined): TriState {
  if (value === true) return "yes";
  if (value === false) return "no";
  return "";
}

/** Hydrate form values from a stored profile (or a fresh shell). */
export function fromProfile(profile: Partial<UserProfile>): ProfileFormValues {
  return {
    name: profile.name ?? "",
    phone: profile.phone ?? "",
    age: profile.age === undefined ? "" : String(profile.age),
    gender: profile.gender ?? "",
    stateCode: profile.stateCode ?? "",
    district: profile.district ?? "",
    incomeBand: profile.incomeBand ?? "",
    casteCategory: profile.casteCategory ?? "",
    education: profile.education ?? "",
    occupation: profile.occupation ?? "",
    maritalStatus: profile.maritalStatus ?? "",
    isStudent: boolToTri(profile.isStudent),
    isFarmer: boolToTri(profile.isFarmer),
    isMinority: boolToTri(profile.isMinority),
    isDisabled: boolToTri(profile.isDisabled),
    disabilityType: profile.disabilityType ?? "",
    preferredLanguage: profile.preferredLanguage ?? "",
    preferredInputMethod: profile.preferredInputMethod ?? "",
    preferredOutputMethod: profile.preferredOutputMethod ?? "",
    notificationPreference: profile.notificationPreference ?? "",
    languages: profile.languages ?? [],
  };
}

/** Convert validated form values + consent into the canonical update payload. */
export function toProfileUpdate(
  values: ProfileFormValues,
  extras: { consent: ConsentFlags; accessibility: AccessibilityPreferences },
): ProfileUpdate {
  return {
    name: values.name || undefined,
    phone: values.phone || undefined,
    stateCode: values.stateCode || undefined,
    district: values.district || undefined,
    age: values.age ? Number(values.age) : undefined,
    gender: (values.gender || undefined) as Gender | undefined,
    incomeBand: (values.incomeBand || undefined) as IncomeBand | undefined,
    casteCategory: (values.casteCategory || undefined) as CasteCategory | undefined,
    education: (values.education || undefined) as EducationLevel | undefined,
    occupation: values.occupation || undefined,
    maritalStatus: (values.maritalStatus || undefined) as MaritalStatus | undefined,
    isStudent: triToBool(values.isStudent),
    isFarmer: triToBool(values.isFarmer),
    isMinority: triToBool(values.isMinority),
    isDisabled: triToBool(values.isDisabled),
    disabilityType: values.disabilityType || undefined,
    preferredLanguage: (values.preferredLanguage || undefined) as LanguageCode | undefined,
    preferredInputMethod: (values.preferredInputMethod ||
      undefined) as PreferredInputMethod | undefined,
    preferredOutputMethod: (values.preferredOutputMethod ||
      undefined) as PreferredOutputMethod | undefined,
    notificationPreference: (values.notificationPreference ||
      undefined) as NotificationPreference | undefined,
    languages: values.languages as LanguageCode[],
    consent: extras.consent,
    accessibilityPreferences: extras.accessibility,
  };
}
