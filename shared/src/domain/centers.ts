import type { LanguageCode, StateCode, UUID } from "./common";

/** Physical service-center types. Coverage is extensible (tehsil, post office, bank). */
export type CenterType = "csc" | "esevai" | "seva-kendra" | "tehsil" | "post_office" | "bank";

/** Manual-location collection families the locator supports. */
export type ManualLocationKind = "state" | "district" | "city" | "pin_code" | "address";

/** Radius presets offered by the UI (km). */
export const CENTER_RADIUS_PRESETS = [5, 10, 25, 50] as const;
export type CenterRadiusKm = (typeof CENTER_RADIUS_PRESETS)[number];

/** How a centre's catalogue entry was produced (docs/database/04 §Ingestion). */
export type CenterSource = "manual" | "import" | "api";

/**
 * Provenance of a centre record: where the data came from and when, so the UI
 * can separate map/location detail from official information (maps prompt).
 */
export interface CenterAttribution {
  sourceName?: string;
  sourceUrl?: string;
  lastUpdatedAt?: string;
}

/** A physical service center (Common Service Centre, e-Sevai, Seva Kendra). */
export interface ServiceCenter {
  id: UUID;
  type: CenterType;
  name: string;
  stateCode: StateCode;
  district?: string;
  /** Postal code when known (used for manual PIN-based location search). */
  pincode?: string;
  address: string;
  /** WGS84 latitude/longitude for PostGIS `ST_DWithin` queries. */
  lat: number;
  lng: number;
  services: string[];
  timings?: string;
  phone?: string;
  verified: boolean;
  /** Computed client-side or server-side distance in km. */
  distanceKm?: number;
  /** Languages offered at the center (agent proficiency), when known. */
  languages?: LanguageCode[];
  attribution?: CenterAttribution;
}

/** Request for the "nearby centers" endpoint (WGS84). */
export interface NearbyCentersRequest {
  lat: number;
  lng: number;
  radiusKm?: CenterRadiusKm;
  type?: CenterType;
  limit?: number;
}

/** Where the user says they are: live coordinates or a manual anchor. */
export type LocationAnchor =
  | { kind: "gps"; lat: number; lng: number; accuracyMeters?: number }
  | { kind: "state"; stateCode: StateCode }
  | { kind: "district"; stateCode: StateCode; district: string }
  | { kind: "city"; city: string }
  | { kind: "pin_code"; pincode: string };

/** Query for a manual-location search against the centre catalog. */
export interface CenterManualSearchParams {
  stateCode?: StateCode;
  district?: string;
  city?: string;
  pincode?: string;
  type?: CenterType;
  radiusKm?: CenterRadiusKm;
  limit?: number;
}

export interface GeoPoint {
  lat: number;
  lng: number;
  accuracyMeters?: number;
  placeName?: string;
}

/** Manual-location resolve result (geocoding service output). */
export interface GeoPlace {
  placeName: string;
  kind: ManualLocationKind;
  stateCode?: StateCode;
  district?: string;
  lat?: number;
  lng?: number;
  /** True when coordinates were derived as an approximation, not a verified point. */
  approximate: boolean;
}

/** Directions link handed to the client (never in-app navigation). */
export interface DirectionsLink {
  provider: string;
  url: string;
  text: string;
}

/** Full response envelope of the nearby/search endpoints. */
export interface NearbyCentersResponse {
  anchor: GeoPoint;
  radiusKm: CenterRadiusKm;
  centers: ServiceCenter[];
  attributionNote: string;
}

/** Marker data for the Leaflet map (client-local). */
export interface CenterMarker extends GeoPoint {
  id: UUID;
  type: CenterType;
  name: string;
  verified: boolean;
  distanceKm?: number;
}