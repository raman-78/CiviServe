/**
 * Admin dashboard types (Prompt 13/15). The wire DTOs are camelCase
 * (APIModel alias generation); these interfaces mirror the server responses
 * exactly so the dashboard renders without further reshaping.
 */
import type { LocalizedText, SchemeStatus, UserRole } from "@/types";

export interface AdminStats {
  schemeTotal: number;
  schemePublished: number;
  schemeDraft: number;
  schemePendingReview: number;
  schemeVerified: number;
  schemeArchived: number;
  expired: number;
  temporarilyUnavailable: number;
  userTotal: number;
  usersLast30d: number;
  publishedPercent: number;
  pendingApprovals: number;
  newFeedback: number;
  schemeVersionsCount: number;
  lastVerifiedAt: string | null;
}

export interface SchemeStatusCount {
  status: string;
  count: number;
}

export interface AdminOverview {
  stats: AdminStats;
  byStatus: SchemeStatusCount[];
  pendingReview: { id: string; schemeCode: string; requesterId: string | null; createdAt: string } | null;
  publishedCategories: { category: string; count: number }[];
}

export interface AdminScheme {
  id: string;
  code: string;
  shortName?: string;
  nameEn: string;
  nameNative: string;
  category: string;
  subCategory?: string;
  ministry: string;
  department?: string;
  scope: string;
  stateCode: string;
  schemeStatus: SchemeStatus;
  verificationStatus: string;
  sourceName?: string;
  sourceUrl?: string;
  sourceType?: string;
  reviewNote?: string;
  lastVerifiedAt: string | null;
  createdAt: string | null;
  updatedAt: string | null;
  popularity: number;
  viewCount: number;
  bookmarkCount: number;
  versionNumber: number | null;
  duplicateNames: string[];
  /** Content blocks re-added by the admin serializer (en/native pairs). */
  name?: LocalizedText;
  summary?: LocalizedText;
  description?: LocalizedText;
  tags: string[];
}

export interface AdminSchemePage {
  items: AdminScheme[];
  page: number;
  pageSize: number;
  total: number;
}

export interface SchemeAdminDetail {
  scheme: AdminScheme;
  duplicateIds: string[];
}

export interface SchemeVersion {
  id: string;
  schemeId: string;
  schemeCode: string;
  versionNumber: number;
  changes: { field: string; before: unknown; after: unknown }[];
  reason: string | null;
  author: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ReviewQueueItem {
  id: string;
  schemeId: string;
  schemeCode: string;
  status: string;
  fromStatus: string | null;
  requestNote: string | null;
  note: string | null;
  requesterId: string | null;
  reviewerId: string | null;
  createdAt: string;
}

export interface AdminUser {
  id: string;
  firebaseUid?: string;
  role: UserRole;
  status: "active" | "suspended" | "deleted";
  email?: string;
  displayName?: string;
  preferredLanguage: string;
  isGuest: boolean;
  createdAt: string | null;
  lastLoginAt: string | null;
}

export interface AdminUsersPage {
  items: AdminUser[];
  page: number;
  pageSize: number;
  total: number;
}

export interface AuditLog {
  id: string;
  actorId: string | null;
  actorRole: string | null;
  action: string;
  entityType: string;
  entityId: string | null;
  entityCode: string | null;
  summary: string | null;
  diff: Record<string, unknown> | null;
  createdAt: string;
}

export interface FeedbackItem {
  id: string;
  userId: string | null;
  schemeCode: string | null;
  rating: number | null;
  category: string | null;
  comment: string | null;
  language: string | null;
  status: "new" | "acknowledged" | "resolved" | "archived";
  createdAt: string;
}

export interface FeedbackPage {
  items: FeedbackItem[];
  page: number;
  pageSize: number;
  total: number;
  byStatus: Record<string, number>;
}

export interface ImportPreviewRow {
  row: number;
  code: string | null;
  name: string | null;
  error: string | null;
  willCreate: boolean;
  willUpdate: boolean;
}

export interface ImportPreview {
  kind: string;
  totalRows: number;
  validRows: number;
  invalidRows: number;
  rows: ImportPreviewRow[];
}

export interface ImportJob {
  id: string;
  kind: string;
  filename: string | null;
  status: string;
  totalRows: number;
  importedRows: number;
  failedRows: number;
  errors: { row: number; error: string }[];
  createdAt: string;
}

export interface ImportJobsPage {
  items: ImportJob[];
  page: number;
  pageSize: number;
  total: number;
}

export interface HealthCheck {
  component: string;
  status: "ok" | "down";
  latencyMs: number | null;
  message: string | null;
}

export interface HealthReport {
  checks: HealthCheck[];
  overall: "ok" | "degraded";
}

export interface Paged<T> {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
}