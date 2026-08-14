import type { ISODateString, JsonObject, LanguageCode, UUID } from "./common";

export type MessageRole = "user" | "assistant" | "system";
export type MessageStatus = "queued" | "processing" | "complete" | "failed";

export type MessageContentType =
  | "text"
  | "scheme-card"
  | "scheme-list"
  | "eligibility-result"
  | "document-list"
  | "location-card"
  | "center-list"
  | "application-link"
  | "quick-replies"
  | "image"
  | "error";

export type IntentType =
  | "scheme_discovery"
  | "eligibility_check"
  | "document_guidance"
  | "application_help"
  | "center_locator"
  | "greeting"
  | "feedback"
  | "general";

/**
 * A single turn in the conversation. The canonical language (`content`/`language`)
 * is what the AI produced; `renderedText` is the user-facing translated text so
 * clients can re-render in another language without re-calling the backend.
 */
export interface ChatMessage {
  id: UUID;
  sessionId: UUID;
  role: MessageRole;
  contentType: MessageContentType;
  /** Canonical-language text (language of the AI response). */
  content: string;
  language: LanguageCode;
  /** Translated rendering for the current UI language. */
  renderedText?: string;
  intent?: IntentType;
  /** Structured payload for rich cards (scheme, centers, documents, ...). */
  payload?: JsonObject;
  status: MessageStatus;
  createdAt: ISODateString;
}

export type ChatSessionStatus = "active" | "closed";

/** A conversation anchored to a user; the unit of history/context. */
export interface ChatSession {
  id: UUID;
  userId: UUID;
  /** Language the user started the session in. */
  language: LanguageCode;
  channel: string;
  status: ChatSessionStatus | "archived";
  /** Human-readable auto-title (first user message) or the user's own rename. */
  title?: string | null;
  messageCount: number;
  createdAt: ISODateString;
  updatedAt: ISODateString;
  lastMessageAt?: ISODateString;
}

/** Compact scheme card referenced by an assistant answer (grounded in catalog). */
export interface SchemeReference {
  id: string;
  code: string;
  name: string;
  category: string;
  subCategory?: string | null;
  summary: string;
  officialWebsite?: string | null;
  lastVerifiedAt?: string | null;
}

/** Rule-based "eligible or not-excluded" suggestion next to the answer. */
export interface SchemeRecommendation {
  code: string;
  name?: string;
  category?: string;
  reason?: string;
}

/** Grounding claim for the message: verified catalog facts vs. "could not be verified". */
export interface ChatGrounding {
  verified: boolean;
  note: string;
  sources: Array<{ code: string }>;
}

/** Structured payload of an assistant reply (contentType === "text"). */
export interface AssistantChatPayload {
  intent: IntentType;
  needsMoreInfo: boolean;
  answer: string;
  followUpQuestions?: string[];
  referencedSchemes?: SchemeReference[];
  recommendations?: SchemeRecommendation[];
  recommendationFallbacks?: SchemeRecommendation[];
  grounding: ChatGrounding;
}

/** Request contract for sending a chat message. */
export interface ChatRequest {
  sessionId?: UUID;
  /** Text after STT. If absent, client must send `audioRef` for server STT. */
  text?: string;
  audioRef?: string;
  language: LanguageCode;
  /** Optional overrides pulled from the profile; sent explicitly for anonymous. */
  context?: Partial<Pick<UserProfileFields, "stateCode" | "age" | "incomeBand" | "casteCategory" | "gender">>;
}

type UserProfileFields = import("./user").UserProfile;

/** Suggested reply chips shown under an assistant message. */
export interface QuickReply {
  label: string;
  payload?: string;
}
