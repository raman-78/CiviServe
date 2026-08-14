import type { DocumentKind, RequiredDocument } from "./scheme";
import type { ISODateString, LanguageCode, UUID } from "./common";

/**
 * Canonical codes used by the document catalog (`document_types`) and the OCR
 * detector. Scheme requirements reference these by `name`; OCR maps the
 * recognized text to one of these codes.
 */
export type DocumentCode =
  | "AADHAAR"
  | "PAN_CARD"
  | "RATION_CARD"
  | "BANK_PASSBOOK"
  | "BANK_ACCOUNT"
  | "INCOME_CERTIFICATE"
  | "COMMUNITY_CERTIFICATE"
  | "CASTE_CERTIFICATE"
  | "RESIDENCE_CERTIFICATE"
  | "DISABILITY_CERTIFICATE"
  | "BIRTH_CERTIFICATE"
  | "MARK_SHEET"
  | "VOTER_ID"
  | "PASSPORT"
  | "LAND_RECORD"
  | "PHOTOGRAPH"
  | "MARRIAGE_CERTIFICATE"
  | "APPLICATION_FORM"
  | "OTHER";

/**
 * Lifecycle of a user's document through upload → OCR → review.
 * `missing` is a derived state only (no DB row exists yet).
 */
export type DocumentStatus =
  | "missing"
  | "uploaded"
  | "processing"
  | "processed"
  | "needs_review"
  | "matches"
  | "mismatch"
  | "unsupported"
  | "ocr_failed"
  | "user_confirmed";

/** Simplified OCR quality indicator — never proof of genuineness. */
export type OcrConfidence = "high" | "needs_review" | "low";

/** One extracted field with a masked display form for sensitive values. */
export interface ExtractedField {
  key: string;
  label: string;
  value: string;
  /** Masked copy safe to show the user (e.g. "XXXX XXXX 1234"). */
  masked?: string;
  /** True when the detector was reasonably sure of this field. */
  reliable?: boolean;
}

/** Catalog entry for one recognisable document type (server `document_types`). */
export interface DocumentTypeInfo {
  code: DocumentCode;
  kind: DocumentKind;
  nameEn: string;
  localizedNames: Partial<Record<LanguageCode, string>>;
  ocrSupported: boolean;
  acceptedFormats: string[];
  /** View box for the "How to obtain it" guidance links. */
  guidance?: DocumentGuidance;
}

/** Guidance copy shown for a missing document type. */
export interface DocumentGuidance {
  summaryEn: string;
  officialSourceUrl?: string;
}

/** A citizen's uploaded document (server `user_documents`, + extraction/review). */
export interface UserDocument {
  id: UUID;
  userId: UUID;
  schemeCode?: string;
  /** The scheme requirement this upload targets (RequiredDocument.name). */
  requiredName?: string;
  fileName: string;
  fileExtension: string;
  fileSizeBytes: number;
  mimeType: string;
  status: DocumentStatus;
  ocrConfidence: OcrConfidence | null;
  detectedType: DocumentCode | null;
  detectionConfidence: number | null;
  /**
   * True when the detected type matches the scheme's required document.
   * `null` when there is nothing to match against yet.
   */
  typeMatches: boolean | null;
  /** Detected/extracted fields after OCR + user correction. */
  extractedFields: ExtractedField[];
  required?: RequiredDocument;
  createdAt: ISODateString;
  updatedAt: ISODateString;
  processedAt?: ISODateString;
  reviewedAt?: ISODateString;
}

/** Result of the OCR + document-type-detection pass for one upload. */
export interface OcrResult {
  documentId: UUID;
  detectedType: DocumentCode | null;
  typeName: string;
  confidence: number;
  ocrConfidence: OcrConfidence;
  /** Machine-readable reason for the verdict ("matched"/"unrecognised"/...). */
  detectionCode: "matched" | "partial" | "unrecognised" | "mismatch";
  extractedFields: ExtractedField[];
  /** True so the UI can hand off to manual type selection. */
  needsManualSelection: boolean;
}

/** Manual confirmation/correction of the document type by the user. */
export interface DocumentTypeConfirmRequest {
  documentType: DocumentCode;
}

/** Review submission: user confirms or corrects the extracted information. */
export interface DocumentReviewRequest {
  /** Corrected field values the user verified (all fields incl. corrections). */
  fields?: ExtractedField[];
}

/** One row in a scheme's document checklist. */
export interface ChecklistItem {
  required: RequiredDocument;
  status: DocumentStatus;
  /** Already-uploaded document for this requirement (when one exists). */
  userDocument?: UserDocument | null;
  /** True when this claim still needs a document to be "complete". */
  isMissing: boolean;
  /** Citizen-friendly guidance when missing / needs attention. */
  guidance?: string;
  officialSourceUrl?: string;
}

/** Per-scheme readiness summary (CiviServe pre-check only). */
export interface DocumentReadiness {
  schemeCode: string;
  requiredCount: number;
  uploadedCount: number;
  missingCount: number;
  needsReviewCount: number;
  /** 0..100 — NOT an official approval score. */
  percent: number;
  items: ChecklistItem[];
  /**
   * Fixed disclaimer copy: pre-check only, final acceptance is decided by the
   * relevant government authority.
   */
  disclaimer: string;
}

export interface UserDocumentListResponse {
  items: UserDocument[];
  total: number;
}