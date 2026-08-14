/**
 * Admin dashboard API (Prompt 13/15). Thin typed wrappers over the FastAPI
 * admin router under `/api/v1/admin`. All endpoints 401/403 server-side.
 */
import { apiRequest, del, get, patch, post, put } from "@/lib/api-client";
import type {
  AdminOverview,
  AdminSchemePage,
  AdminUsersPage,
  AuditLog,
  FeedbackPage,
  HealthReport,
  ImportJobsPage,
  ImportPreview,
  Paged,
  ReviewQueueItem,
  SchemeAdminDetail,
  SchemeVersion,
} from "@/features/admin/types";

const BASE = "/api/v1/admin";

function toQuery(params: Record<string, string | number | boolean | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

// -- Overview -----------------------------------------------------------------

export async function fetchAdminOverview(): Promise<AdminOverview> {
  return (await get<AdminOverview>(`${BASE}/overview`)).data;
}

// -- Schemes ------------------------------------------------------------------

export interface AdminSchemeQuery {
  page?: number;
  pageSize?: number;
  q?: string;
  status?: string;
  category?: string;
  verificationStatus?: string;
  ministry?: string;
  scope?: string;
  sort?: string;
}

export async function fetchAdminSchemes(query: AdminSchemeQuery = {}): Promise<AdminSchemePage> {
  return (
    await get<AdminSchemePage>(
      `${BASE}/schemes${toQuery({ ...query, verificationStatus: query.verificationStatus ?? "" })}`,
    )
  ).data;
}

export async function fetchAdminSchemeDetail(code: string): Promise<SchemeAdminDetail> {
  return (await get<SchemeAdminDetail>(`${BASE}/schemes/${encodeURIComponent(code)}/detail`)).data;
}

export async function fetchSchemeVersions(code: string): Promise<SchemeVersion[]> {
  return (await get<SchemeVersion[]>(`${BASE}/schemes/${encodeURIComponent(code)}/versions`)).data;
}

export async function createScheme(payload: Record<string, unknown>): Promise<unknown> {
  return (await post(`${BASE}/schemes`, payload)).data;
}

export async function updateScheme(code: string, payload: Record<string, unknown>): Promise<unknown> {
  return (await put(`${BASE}/schemes/${encodeURIComponent(code)}`, payload)).data;
}

export async function changeSchemeStatus(
  code: string,
  status: string,
  note?: string,
): Promise<unknown> {
  return (
    await patch(
      `${BASE}/schemes/${encodeURIComponent(code)}/status${toQuery({ status, note })}`,
    )
  ).data;
}

export async function submitSchemeForReview(code: string, note?: string): Promise<unknown> {
  return (
    await post(
      `${BASE}/schemes/${encodeURIComponent(code)}/submit-for-review${toQuery({ note })}`,
    )
  ).data;
}

export async function deleteScheme(code: string): Promise<void> {
  await del(`${BASE}/schemes/${encodeURIComponent(code)}`);
}

// -- Reviews -------------------------------------------------------------------

export async function fetchReviewQueue(page = 1, pageSize = 50): Promise<Paged<ReviewQueueItem>> {
  return (await get<Paged<ReviewQueueItem>>(`${BASE}/reviews${toQuery({ page, pageSize })}`)).data;
}

export async function decideReview(
  reviewId: string,
  opts: { approve: boolean; publish?: boolean; note?: string },
): Promise<unknown> {
  return (
    await post(
      `${BASE}/reviews/${encodeURIComponent(reviewId)}/decision${toQuery({
        approve: opts.approve,
        publish: opts.publish,
        note: opts.note,
      })}`,
    )
  ).data;
}

// -- Users ---------------------------------------------------------------------

export async function fetchAdminUsers(
  query: { page?: number; pageSize?: number; q?: string; role?: string; status?: string } = {},
): Promise<AdminUsersPage> {
  return (await get<AdminUsersPage>(`${BASE}/users${toQuery(query)}`)).data;
}

export async function setUserRole(userId: string, role: string): Promise<unknown> {
  return (await put(`${BASE}/users/${encodeURIComponent(userId)}/role${toQuery({ role })}`)).data;
}

export async function setUserStatus(userId: string, status: string): Promise<unknown> {
  return (
    await put(`${BASE}/users/${encodeURIComponent(userId)}/status${toQuery({ status })}`)
  ).data;
}

// -- Audit logs ------------------------------------------------------------------

export async function fetchAuditLogs(
  query: { page?: number; pageSize?: number; entityType?: string; action?: string } = {},
): Promise<Paged<AuditLog>> {
  return (await get<Paged<AuditLog>>(`${BASE}/audit-logs${toQuery(query)}`)).data;
}

// -- Feedback ------------------------------------------------------------------

export async function fetchFeedback(
  query: { page?: number; pageSize?: number; status?: string } = {},
): Promise<FeedbackPage> {
  return (await get<FeedbackPage>(`${BASE}/feedback${toQuery(query)}`)).data;
}

export async function updateFeedback(
  feedbackId: string,
  status: string,
  note?: string,
): Promise<unknown> {
  return (
    await patch(`${BASE}/feedback/${encodeURIComponent(feedbackId)}${toQuery({ status, note })}`)
  ).data;
}

// -- Import ---------------------------------------------------------------------

/** Serialize an array of row objects to a CSV string (matches server import). */
function rowsToCsv(rows: Record<string, unknown>[]): string {
  if (rows.length === 0) return "";
  const headers = Array.from(
    new Set(rows.flatMap((row) => Object.keys(row))),
  );
  const escape = (value: unknown): string => {
    const text = value == null ? "" : String(value);
    return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  };
  const lines = [headers.join(",")];
  for (const row of rows) {
    lines.push(headers.map((header) => escape(row[header])).join(","));
  }
  return lines.join("\n");
}

async function uploadImport(
  path: string,
  rows: Record<string, unknown>[],
  kind = "scheme",
): Promise<unknown> {
  const form = new FormData();
  form.set("file", new Blob([rowsToCsv(rows)], { type: "text/csv" }), "schemes.csv");
  return (
    await apiRequest(`${BASE}${path}?kind=${kind}`, { method: "POST", body: form }, { multipart: true })
  ).data;
}

export async function previewImport(
  rows: Record<string, unknown>[],
  kind = "scheme",
): Promise<ImportPreview> {
  return (await uploadImport("/import/preview", rows, kind)) as unknown as ImportPreview;
}

export interface ImportApplyResult {
  jobId: string;
  kind: string;
  importedRows: number;
  failedRows: number;
  errors: { row: number; error: string }[];
}

export async function applyImport(
  rows: Record<string, unknown>[],
  kind = "scheme",
): Promise<ImportApplyResult> {
  return (await uploadImport("/import/apply", rows, kind)) as unknown as ImportApplyResult;
}

export async function fetchImportJobs(page = 1, pageSize = 20): Promise<ImportJobsPage> {
  return (await get<ImportJobsPage>(`${BASE}/import/jobs${toQuery({ page, pageSize })}`)).data;
}

// -- Health ----------------------------------------------------------------------

export async function fetchSystemHealth(): Promise<HealthReport> {
  return (await get<HealthReport>(`${BASE}/health`)).data;
}