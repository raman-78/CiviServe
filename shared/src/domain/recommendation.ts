import type { EligibilityRule, SchemeSummary } from "./scheme";
import type { UUID } from "./common";

/**
 * Ladder used when we cannot give a definitive yes/no.
 * - `eligible`       → all hard rules satisfied.
 * - `likely`         → hard rules met, soft signals uncertain.
 * - `needs_more_info`→ not enough profile data (drives the chat to ask follow-ups).
 * - `not_eligible`   → a hard rule is conclusively violated.
 */
export type EligibilityStatus = "eligible" | "likely" | "needs_more_info" | "not_eligible";

/**
 * Result of the eligibility engine for one scheme against a profile.
 * `matchScore` in [0,100]; `matchedRules` are the satisfied rules used to
 * compute it; `reasons` are human-readable explanations for the user.
 */
export interface Recommendation {
  schemeId: UUID;
  scheme: SchemeSummary;
  status: EligibilityStatus;
  matchScore: number;
  matchedRules: EligibilityRule[];
  /** Conclusively-broken rules driving `not_eligible`. */
  brokenRules?: EligibilityRule[];
  /** Fields needed to turn an uncertain verdict into yes/no. */
  missingFields: string[];
  /** Short reasons like "Age ≥ 18 matches", "State = Tamil Nadu matches". */
  reasons: string[];
  /** Backward-compat convenience: status === "eligible". */
  fullyEligible: boolean;
}

export interface RecommendationRequest {
  stateCode?: string;
  district?: string;
  age?: number;
  gender?: string;
  incomeBand?: string;
  annualIncomeInr?: number;
  education?: string;
  occupation?: string;
  casteCategory?: string;
  isFarmer?: boolean;
  isStudent?: boolean;
  isDisabled?: boolean;
  isMinority?: boolean;
  isSeniorCitizen?: boolean;
  isSelfEmployed?: boolean;
  isWidow?: boolean;
  isWomen?: boolean;
  /** Cap the number of recommendations. */
  limit?: number;
}

export interface RecommendationResponse {
  recommendations: Recommendation[];
  /** Summary of missing data that would improve accuracy. */
  missingFields: string[];
}
