/**
 * Profile → eligibility-request mapping (Prompt 10).
 *
 * Pure functions: server rule fields are driven by the shared
 * `RecommendationRequest` contract (camelCase over the wire). No i18n/UI here
 * so they stay trivially unit-testable.
 */
import type {
  RecommendationRequest,
  UserProfile,
  EligibilityStatus,
} from "@civiserve/shared";

/** True when the profile has enough detail for a meaningful evaluation. */
export function hasEligibilityInputs(profile: UserProfile | null): boolean {
  if (!profile) return false;
  return Boolean(
    profile.stateCode ||
      profile.age !== undefined ||
      profile.incomeBand ||
      profile.isFarmer ||
      profile.isStudent ||
      profile.isDisabled ||
      profile.isMinority,
  );
}

/**
 * Flatten the stored citizen profile into the recommendation API payload.
 * Undefined/absent values are omitted so the server reports exactly the
 * fields it still needs.
 */
export function profileToEligibilityRequest(
  profile: UserProfile | null,
): RecommendationRequest {
  if (!profile) return {};

  const request: RecommendationRequest = {
    stateCode: profile.stateCode ?? undefined,
    district: profile.district ?? undefined,
    age: profile.age,
    gender: profile.gender,
    incomeBand: profile.incomeBand,
    education: profile.education,
    occupation: profile.occupation,
    casteCategory: profile.casteCategory,
    isStudent: profile.isStudent,
    isFarmer: profile.isFarmer,
    isDisabled: profile.isDisabled,
    isMinority: profile.isMinority,
    isWidow: profile.maritalStatus === "widowed" ? true : undefined,
    isWomen: profile.gender === "female" ? true : undefined,
    isSeniorCitizen:
      profile.age !== undefined && profile.age >= 60 ? true : undefined,
  };

  return Object.fromEntries(
    Object.entries(request).filter(([, value]) => value !== undefined),
  ) as RecommendationRequest;
}

/** Dot-path i18n keys for engine field names (missing-fields chips, rules). */
const FIELD_LABEL_KEYS: Record<string, string> = {
  age: "eligibility.fields.age",
  gender: "eligibility.fields.gender",
  income_band: "eligibility.fields.incomeBand",
  education: "eligibility.fields.education",
  occupation: "eligibility.fields.occupation",
  state: "eligibility.fields.stateCode",
  state_code: "eligibility.fields.stateCode",
  district: "eligibility.fields.district",
  annual_income: "eligibility.fields.annualIncome",
  community: "eligibility.fields.community",
  caste_category: "eligibility.fields.community",
  is_farmer: "eligibility.fields.isFarmer",
  is_student: "eligibility.fields.isStudent",
  is_disabled: "eligibility.fields.isDisabled",
  is_minority: "eligibility.fields.isMinority",
  is_senior_citizen: "eligibility.fields.isSeniorCitizen",
  is_self_employed: "eligibility.fields.isSelfEmployed",
  is_women: "eligibility.fields.isWomen",
  is_widow: "eligibility.fields.isWidow",
  is_bpl: "eligibility.fields.isBpl",
};

export function fieldLabelKey(field: string): string {
  return FIELD_LABEL_KEYS[field] ?? `eligibility.fields.${field}`;
}

/** Dot-path i18n key for a verdict's status badge label. */
export function statusLabelKey(status: EligibilityStatus): string {
  switch (status) {
    case "eligible":
      return "eligibility.status.eligible";
    case "likely":
      return "eligibility.status.likely";
    case "needs_more_info":
      return "eligibility.status.needsMoreInfo";
    case "not_eligible":
      return "eligibility.status.notEligible";
    default:
      return "eligibility.status.needsMoreInfo";
  }
}

/** Badge variant (bits reserved for the card). */
export type StatusTone = "success" | "warning" | "muted" | "destructive";

export function statusTone(status: EligibilityStatus): StatusTone {
  switch (status) {
    case "eligible":
      return "success";
    case "likely":
      return "warning";
    case "not_eligible":
      return "destructive";
    default:
      return "muted";
  }
}