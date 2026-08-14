/** Local type re-exports of the canonical shared contracts plus small UI types. */
export type {
  AssistantChatPayload,
  ChatGrounding,
  ChatMessage,
  ChatRequest,
  ChatSession,
  ChatSessionStatus,
  IntentType,
  MessageContentType,
  MessageRole,
  MessageStatus,
  QuickReply,
  SchemeRecommendation,
  SchemeReference,
} from "@civiserve/shared";

export type {
  EligibilityField,
  EligibilityOperator,
  EligibilityRule,
  EligibilityStatus,
  LocalizedText,
  Paginated,
  Recommendation,
  RecommendationRequest,
  RecommendationResponse,
  RequiredDocument,
  Scheme,
  SchemeApplicationLinks,
  SchemeCategory,
  SchemeCode,
  SchemeStatus,
  SchemeSummary,
  SchemeVerificationStatus,
} from "@civiserve/shared";

export type {
  ChecklistItem,
  DocumentCode,
  DocumentGuidance,
  DocumentReadiness,
  DocumentStatus,
  DocumentTypeConfirmRequest,
  DocumentTypeInfo,
  DocumentReviewRequest,
  ExtractedField,
  OcrConfidence,
  OcrResult,
  UserDocument,
  UserDocumentListResponse,
} from "@civiserve/shared";

export type {
  CenterAttribution,
  CenterManualSearchParams,
  CenterMarker,
  CenterRadiusKm,
  CenterSource,
  CenterType,
  DirectionsLink,
  GeoPlace,
  GeoPoint,
  LocationAnchor,
  ManualLocationKind,
  NearbyCentersRequest,
  NearbyCentersResponse,
  ServiceCenter,
} from "@civiserve/shared";

export type {
  AccessibilityPreferences,
  AuthMethod,
  ConsentFlags,
  CurrentUser,
  EducationLevel,
  Gender,
  IncomeBand,
  MaritalStatus,
  NotificationPreference,
  PreferredInputMethod,
  PreferredOutputMethod,
  ProfileCompletion,
  ProfileUpdate,
  UserProfile,
  UserRole,
} from "@civiserve/shared";

export type { LanguageCode, StateCode, UUID } from "@civiserve/shared";

export type { LanguageInfo } from "@civiserve/shared";

/** A single item in the notification inbox (UI placeholder). */
export interface AppNotification {
  id: string;
  type: "scheme_update" | "eligibility_match" | "renewal_reminder" | "announcement";
  title: string;
  body: string;
  createdAt: string;
  read: boolean;
}
