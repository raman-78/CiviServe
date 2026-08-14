/**
 * Typed API for the eligibility endpoints (Prompt 10).
 *
 * Mirrors `features/chat/api.ts` / `features/profile/api.ts`: thin wrappers
 * over the shared HTTP client for `POST /api/v1/recommendations/*`.
 */
import { post } from "@/lib/api-client";
import type {
  Recommendation,
  RecommendationRequest,
  RecommendationResponse,
} from "@/types";

/** Rank schemes for the stored profile. */
export async function fetchEligibility(
  request: RecommendationRequest,
): Promise<RecommendationResponse> {
  return (await post<RecommendationResponse>(
    "/api/v1/recommendations/evaluate",
    request,
  )).data;
}

/** Fields the candidate schemes still need. */
export async function fetchMissingFields(
  request: RecommendationRequest,
): Promise<string[]> {
  const { data } = await post<{ missingFields: string[] }>(
    "/api/v1/recommendations/missing-fields",
    request,
  );
  return data.missingFields;
}

/** Schemes a not-eligible scheme's blocking rule doesn't constrain. */
export async function fetchAlternatives(
  code: string,
  request: RecommendationRequest,
): Promise<Recommendation[]> {
  return (await post<Recommendation[]>(
    `/api/v1/recommendations/${encodeURIComponent(code)}/alternatives`,
    { ...request, limit: 3 },
  )).data;
}