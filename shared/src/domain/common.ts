/**
 * Common primitives shared by all domain models.
 * These are canonical contracts — the backend exposes the same shape as JSON
 * and Pydantic models must serialize to these exact field names.
 */

/** ISO 8601 timestamp, UTC. */
export type ISODateString = string;

/** Basic unique identifiers. Server uses UUIDv7 by default. */
export type UUID = string;

/** Currency amounts in INR. */
export type INR = number;

/** A short machine + human readable code, e.g. "PM-KISAN". */
export type SchemeCode = string;

/** Canonical two-letter language code per BCP-47 subset used by IndicTrans2. */
export type LanguageCode =
  | "as"
  | "bn"
  | "en"
  | "gu"
  | "hi"
  | "kn"
  | "ml"
  | "mr"
  | "or"
  | "pa"
  | "ta"
  | "te"
  | "ur";

/** Two-letter ISO 3166-1 alpha-2 state code; "*" means central/pan-India. */
export type StateCode = string | "*";

/** Generic key/value map for flexible payloads (message cards, scheme extras). */
export type JsonObject = Record<string, unknown>;
