import type { ISODateString, LanguageCode, SchemeCode, StateCode, UUID } from "./common";

export type SchemeCategory =
  | "education"
  | "health"
  | "housing"
  | "employment"
  | "agriculture"
  | "pension"
  | "women"
  | "disability"
  | "food-security"
  | "financial-inclusion"
  | "other";

/** Central = pan-India; state = a specific state's scheme. */
export type SchemeScope = "central" | "state";

/**
 * Publication lifecycle of a scheme (mirrors the `schemes.scheme_status` column).
 * Only `published` appears in the public catalog; the other statuses drive the
 * admin content+pipeline (draft → pending_review → verified → published).
 */
export type SchemeStatus =
  | "draft"
  | "pending_review"
  | "verified"
  | "published"
  | "temporarily_unavailable"
  | "archived"
  | "expired";

/** Content source/verification state shown to admins (Prompt 15). */
export type SchemeVerificationStatus =
  | "unverified"
  | "pending"
  | "verified"
  | "failed"
  | "stale";

/** Accepted sort keys for the schemes list endpoint. */
export type SchemeSort = "relevance" | "updated" | "popular";

/** A step in the application/renewal process. */
export interface SchemeApplicationStep {
  step: number;
  title: LocalizedText;
  description?: LocalizedText;
  /** Online / offline / both — which channel the step is done through. */
  mode?: "online" | "offline" | "both";
}

/** Frequently-asked question attached to a scheme. */
export interface SchemeFAQ {
  id: UUID;
  question: LocalizedText;
  answer: LocalizedText;
}

/** A saved (bookmarked) search the user wants to revisit. */
export interface SavedSearch {
  id: UUID;
  query: string;
  filters?: Record<string, string | boolean | number | undefined>;
  notifyOnUpdate: boolean;
  createdAt: ISODateString;
}

/** One entry in the user's recent-search history. */
export interface SearchHistoryItem {
  id: UUID;
  query: string;
  createdAt: ISODateString;
}

/** Autocomplete / popular-search suggestions for a partial query. */
export interface SearchSuggestions {
  query: string;
  /** Completion terms (words/tags/categories) for the prefix. */
  suggestions: string[];
  /** Closest known scheme/category name (for misspellings), if any. */
  corrected?: string;
}

/** Lightweight scheme in the trending/popular rails. */
export interface SchemeTrending {
  rank: number;
  scheme: SchemeSummary;
}

export interface SchemeSearchQuery {
  q?: string;
  category?: SchemeCategory;
  subCategory?: string;
  state?: StateCode;
  scope?: SchemeScope;
  ministry?: string;
  department?: string;
  /** Demographic filters evaluated against the scheme's eligibility rules. */
  gender?: string;
  occupation?: string;
  incomeBand?: string;
  education?: string;
  isFarmer?: boolean;
  isStudent?: boolean;
  isDisabled?: boolean;
  isMinority?: boolean;
  isSeniorCitizen?: boolean;
  isSelfEmployed?: boolean;
  isWomen?: boolean;
  page?: number;
  pageSize?: number;
  sort?: SchemeSort;
}

/** Field names the eligibility engine can evaluate against a UserProfile. */
export type EligibilityField =
  | "age"
  | "gender"
  | "state"
  | "district"
  | "income_band"
  | "caste_category"
  | "occupation"
  | "education"
  | "is_farmer"
  | "is_student"
  | "is_disabled"
  | "is_minority"
  | "is_senior_citizen"
  | "is_self_employed"
  | "is_widow"
  | "is_women";

export type EligibilityOperator = "eq" | "neq" | "gte" | "lte" | "in" | "between" | "exists";

export interface EligibilityRule {
  field: EligibilityField;
  operator: EligibilityOperator;
  value: string | number | [number, number] | string[];
  /** Human-readable explanation in English (translated on the client). */
  description: string;
}

/** Localized document with name/summary pair used across every scheme resource. */
export interface LocalizedText {
  en: string;
  native: string;
}

/** Canonical document category used for OCR + checklist grouping. */
export type DocumentKind =
  | "identity"
  | "address"
  | "income"
  | "age"
  | "caste"
  | "bank"
  | "land"
  | "disability"
  | "family"
  | "photo"
  | "other";

export interface RequiredDocument {
  id: UUID;
  /** Canonical document type, e.g. "AADHAAR", "RATION_CARD". */
  name: string;
  kind: DocumentKind;
  localizedNames: Partial<Record<LanguageCode, string>>;
  optional: boolean;
  /** Whether OCR (tesseract/PaddleOCR) can extract data from this doc. */
  ocrSupported: boolean;
  /** Localized guidance for obtaining/using this document. */
  verificationHint?: string;
  notes?: string;
}

export interface SchemeApplicationLinks {
  /** Official online application URL (post.onlinereg etc). */
  online?: string;
  /** Offline application description (CSC center, SDM office). */
  offline?: string;
  helpline?: string;
  /** Official portal source URL used for verification. */
  sourceUrl?: string;
}

/**
 * A government scheme (Prompt 6 schema). `scope: "central"` schemes apply to all
 * states (`applicableStates` empty means pan-India); `scope: "state"` schemes
 * must list their states. All rich text is bilingual (English + native) at
 * rest; other languages are translated on demand.
 */
export interface Scheme {
  id: UUID;
  code: SchemeCode;
  /** Compact display name, e.g. "PM-KISAN". */
  shortName?: string;
  name: LocalizedText;
  summary: LocalizedText;
  /** Full, structured description (covers Overview section). */
  description: LocalizedText;
  category: SchemeCategory;
  /** Optional sub-category, e.g. "scholarship" under "education". */
  subCategory?: string;
  ministry: string;
  /** Responsible department (for state schemes, the state department). */
  department?: string;
  scope: SchemeScope;
  /** Legacy single-state tag used by chat cards ("*" = central). */
  stateCode: StateCode;
  /** States the scheme applies to; empty array = all India. */
  applicableStates: StateCode[];
  /** Who the scheme is aimed at, e.g. ["landholding farmer families"]. */
  targetBeneficiaries: string[];
  benefits: string[];
  eligibilityRules: EligibilityRule[];
  requiredDocuments: RequiredDocument[];
  applicationSteps: SchemeApplicationStep[];
  /** How to renew (periodicity + process), if renewable. */
  renewalProcess?: LocalizedText;
  applicationLinks: SchemeApplicationLinks;
  officialWebsite?: string;
  officialApplicationLink?: string;
  helpline?: string;
  faqs: SchemeFAQ[];
  schemeStatus: SchemeStatus;
  /** Last time the content was verified against the official source. */
  lastVerifiedAt: string;
  /** Source provenance + verification state (Prompt 15 admin surface). */
  sourceName?: string;
  sourceUrl?: string;
  sourceType?: string;
  verificationStatus?: SchemeVerificationStatus;
  reviewNote?: string;
  /** Search keywords / synonyms beyond tags, e.g. ["kisan", "crop loan"]. */
  keywords: string[];
  /** Free-text tags for search, e.g. ["farmers", "KCC"]. */
  tags: string[];
  /** Global popularity index (used for trending/ordering). */
  popularity?: number;
  viewCount?: number;
  bookmarkCount?: number;
  validUntil?: string;
}

export interface SchemeSummary {
  id: UUID;
  code: SchemeCode;
  category: SchemeCategory;
  scope: SchemeScope;
  stateCode: StateCode;
  shortName?: string;
  name: LocalizedText;
  summary: LocalizedText;
  tags: string[];
  matchScore?: number;
  popularity?: number;
}

/** Paged list response envelope used by all list endpoints. */
export interface Paginated<T> {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
}
