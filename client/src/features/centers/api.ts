/**
 * Typed API for the service-centre endpoints (maps/locator prompt).
 *
 * All three rails are public and rate-limited server-side; no auth needed to
 * find a CSC. GPS anchors are sent once, per scan, and never persisted.
 */
import { get } from "@/lib/api-client";
import type {
  CenterManualSearchParams,
  CenterType,
  NearbyCentersRequest,
  NearbyCentersResponse,
  ServiceCenter,
} from "@/types";

export interface CentreDetail {
  centre: ServiceCenter;
  directionsUrl: string | null;
}

function toQuery(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

/** Nearby centres for live GPS coordinates (nearest first). */
export async function fetchNearbyCenters(
  params: NearbyCentersRequest,
): Promise<NearbyCentersResponse> {
  const query = toQuery({
    lat: params.lat,
    lng: params.lng,
    radiusKm: params.radiusKm,
    type: params.type,
    limit: params.limit,
  });
  return (await get<NearbyCentersResponse>(`/api/v1/centers/nearby${query}`)).data;
}

/** Manual-location search by state / district / city / PIN. */
export async function searchCentersManually(
  params: CenterManualSearchParams,
): Promise<NearbyCentersResponse> {
  const query = toQuery({
    stateCode: params.stateCode,
    district: params.district,
    city: params.city,
    pincode: params.pincode,
    type: params.type,
    limit: params.limit,
  });
  return (await get<NearbyCentersResponse>(`/api/v1/centers/manual${query}`)).data;
}

/** One centre's detail, plus an optional directions link from an origin. */
export async function fetchCentreDetail(
  centreId: string,
  origin?: { lat: number; lng: number } | null,
): Promise<CentreDetail> {
  const query = origin
    ? toQuery({ originLat: origin.lat, originLng: origin.lng })
    : "";
  return (await get<CentreDetail>(`/api/v1/centers/${encodeURIComponent(centreId)}${query}`)).data;
}

/** All supported centre types (drives the filter control). */
export const CENTER_TYPES: CenterType[] = [
  "csc",
  "esevai",
  "seva-kendra",
  "tehsil",
  "post_office",
  "bank",
];

/** Short English labels (centre names stay as-is; only the chip gets a label). */
export const CENTER_TYPE_OPTIONS: Record<CenterType, string> = {
  csc: "CSC",
  esevai: "e-Sevai",
  "seva-kendra": "Seva Kendra",
  tehsil: "Tehsil",
  post_office: "Post Office",
  bank: "Bank",
};