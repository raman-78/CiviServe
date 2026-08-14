/**
 * Public scheme catalog API (Prompt 6/15). Thin typed wrappers over the FastAPI
 * `/api/v1/schemes` routes. Read-only; the catalog pages fetch live, published
 * schemes instead of static mock data.
 */
import { get } from "@/lib/api-client";
import type { Paginated, Scheme, SchemeSummary } from "@/types";

const BASE = "/api/v1/schemes";

function toQuery(params: Record<string, string | number | boolean | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export interface SchemeListQuery {
  page?: number;
  pageSize?: number;
  query?: string;
  category?: string;
  state?: string;
  sort?: string;
}

/**
 * List/browse summaries. A non-empty query routes to the relevance search,
 * otherwise the catalog browse endpoint is used.
 */
export async function fetchSchemeSummaries(
  params: SchemeListQuery = {},
): Promise<Paginated<SchemeSummary>> {
  const { query, page, pageSize, category, state, sort } = params;
  const q = query?.trim();
  const endpoint = q ? `${BASE}/search` : BASE;
  return (
    await get<Paginated<SchemeSummary>>(
      `${endpoint}${toQuery({ page, pageSize, category, state, q, sort: sort ?? (q ? "relevance" : "popular") })}`,
    )
  ).data;
}

export async function fetchSchemeByCode(code: string): Promise<Scheme> {
  return (await get<Scheme>(`${BASE}/${encodeURIComponent(code)}`)).data;
}

export async function fetchRelatedSchemes(code: string, limit = 6): Promise<SchemeSummary[]> {
  return (
    await get<SchemeSummary[]>(`${BASE}/${encodeURIComponent(code)}/related${toQuery({ limit })}`)
  ).data;
}