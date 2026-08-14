/**
 * Admin dashboard state hook (Prompt 13/15). Loads overview + list pages and
 * exposes mutations with toast feedback. Kept local to the feature (no global
 * store) — the dashboard refreshes its own data after each mutation.
 */
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { useTranslation } from "react-i18next";
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
import {
  applyImport,
  changeSchemeStatus,
  createScheme,
  decideReview,
  deleteScheme,
  fetchAdminOverview,
  fetchAdminSchemes,
  fetchAdminSchemeDetail,
  fetchAdminUsers,
  fetchAuditLogs,
  fetchFeedback,
  fetchImportJobs,
  fetchReviewQueue,
  fetchSchemeVersions,
  fetchSystemHealth,
  previewImport,
  setUserRole,
  setUserStatus,
  submitSchemeForReview,
  updateFeedback,
  updateScheme,
} from "@/features/admin/api";
import { errorMessage } from "@/lib/errors";

export interface AdminSchemeQuery {
  page?: number;
  pageSize?: number;
  q?: string;
  status?: string;
  category?: string;
  verificationStatus?: string;
  scope?: string;
}

export interface UseAdminResult {
  overview: AdminOverview | null;
  overviewLoading: boolean;
  schemes: AdminSchemePage | null;
  schemesLoading: boolean;
  schemeQuery: AdminSchemeQuery;
  setSchemeQuery: (query: AdminSchemeQuery) => void;
  schemeDetail: (code: string) => Promise<SchemeAdminDetail>;
  schemeVersions: (code: string) => Promise<SchemeVersion[]>;
  createScheme: (payload: Record<string, unknown>) => Promise<void>;
  updateScheme: (code: string, payload: Record<string, unknown>) => Promise<void>;
  changeStatus: (code: string, status: string, note?: string) => Promise<void>;
  submitForReview: (code: string, note?: string) => Promise<void>;
  removeScheme: (code: string) => Promise<void>;
  reviews: Paged<ReviewQueueItem> | null;
  reviewsLoading: boolean;
  reviewsRefresh: () => void;
  decide: (reviewId: string, opts: { approve: boolean; publish?: boolean; note?: string }) => Promise<void>;
  users: AdminUsersPage | null;
  usersLoading: boolean;
  usersRefresh: () => void;
  updateUserRole: (userId: string, role: string) => Promise<void>;
  updateUserStatus: (userId: string, status: string) => Promise<void>;
  auditLogs: Paged<AuditLog> | null;
  auditLoading: boolean;
  auditRefresh: () => void;
  feedback: FeedbackPage | null;
  feedbackLoading: boolean;
  feedbackRefresh: () => void;
  updateFeedbackStatus: (feedbackId: string, status: string) => Promise<void>;
  importJobs: ImportJobsPage | null;
  importJobsLoading: boolean;
  importJobsRefresh: () => void;
  previewRows: (rows: Record<string, unknown>[]) => Promise<ImportPreview>;
  importRows: (rows: Record<string, unknown>[]) => Promise<void>;
  health: HealthReport | null;
  healthLoading: boolean;
  runHealthCheck: () => Promise<void>;
}

interface PageState<T> {
  data: T | null;
  loading: boolean;
  page: number;
}

export function useAdmin(): UseAdminResult {
  const { t } = useTranslation();
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(true);
  const [schemes, setSchemes] = useState<AdminSchemePage | null>(null);
  const [schemesLoading, setSchemesLoading] = useState(true);
  const [schemeQuery, setSchemeQueryState] = useState<AdminSchemeQuery>({ page: 1, pageSize: 20 });
  const [reviews, setReviews] = useState<PageState<Paged<ReviewQueueItem>>>({
    data: null,
    loading: true,
    page: 1,
  });
  const [users, setUsers] = useState<PageState<AdminUsersPage>>({ data: null, loading: true, page: 1 });
  const [audit, setAudit] = useState<PageState<Paged<AuditLog>>>({ data: null, loading: true, page: 1 });
  const [feedback, setFeedback] = useState<PageState<FeedbackPage>>({ data: null, loading: true, page: 1 });
  const [importJobs, setImportJobs] = useState<PageState<ImportJobsPage>>({
    data: null,
    loading: true,
    page: 1,
  });
  const [health, setHealth] = useState<HealthReport | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);

  const run = useCallback(
    async <T,>(fn: () => Promise<T>, onOk: (data: T) => void, onError?: () => void) => {
      try {
        onOk(await fn());
      } catch (error) {
        toast.error(errorMessage(error));
        onError?.();
      }
    },
    [],
  );

  /** Runs a mutation, toasting failures (the page never sees a rejection). */
  const mutate = useCallback(
    async (fn: () => Promise<void>) => {
      try {
        await fn();
      } catch (error) {
        toast.error(errorMessage(error));
      }
    },
    [],
  );

  const refreshOverview = useCallback(() => {
    setOverviewLoading(true);
    void run(
      fetchAdminOverview,
      (data) => {
        setOverview(data);
        setOverviewLoading(false);
      },
      () => setOverviewLoading(false),
    );
  }, [run]);

  const refreshSchemes = useCallback(
    (query: AdminSchemeQuery) => {
      setSchemesLoading(true);
      void run(
        () => fetchAdminSchemes(query),
        (data) => {
          setSchemes(data);
          setSchemesLoading(false);
        },
        () => setSchemesLoading(false),
      );
    },
    [run],
  );

  useEffect(() => {
    refreshOverview();
  }, [refreshOverview]);

  useEffect(() => {
    refreshSchemes(schemeQuery);
  }, [schemeQuery, refreshSchemes]);

  const setSchemeQuery = useCallback((query: AdminSchemeQuery) => setSchemeQueryState(query), []);

  const loadReviews = useCallback(
    (page: number) => {
      setReviews((s) => ({ ...s, loading: true }));
      void run(
        () => fetchReviewQueue(page),
        (data) => setReviews({ data, loading: false, page }),
        () => setReviews((s) => ({ ...s, loading: false })),
      );
    },
    [run],
  );

  const loadUsers = useCallback(
    (page: number) => {
      setUsers((s) => ({ ...s, loading: true }));
      void run(
        () => fetchAdminUsers({ page, pageSize: 20 }),
        (data) => setUsers({ data, loading: false, page }),
        () => setUsers((s) => ({ ...s, loading: false })),
      );
    },
    [run],
  );

  const loadAudit = useCallback(
    (page: number) => {
      setAudit((s) => ({ ...s, loading: true }));
      void run(
        () => fetchAuditLogs({ page, pageSize: 30 }),
        (data) => setAudit({ data, loading: false, page }),
        () => setAudit((s) => ({ ...s, loading: false })),
      );
    },
    [run],
  );

  const loadFeedback = useCallback(
    (page: number, status?: string) => {
      setFeedback((s) => ({ ...s, loading: true }));
      void run(
        () => fetchFeedback({ page, pageSize: 20, status }),
        (data) => setFeedback({ data, loading: false, page }),
        () => setFeedback((s) => ({ ...s, loading: false })),
      );
    },
    [run],
  );

  const loadImports = useCallback(
    (page: number) => {
      setImportJobs((s) => ({ ...s, loading: true }));
      void run(
        () => fetchImportJobs(page, 20),
        (data) => setImportJobs({ data, loading: false, page }),
        () => setImportJobs((s) => ({ ...s, loading: false })),
      );
    },
    [run],
  );

  useEffect(() => {
    loadReviews(1);
    loadUsers(1);
    loadAudit(1);
    loadFeedback(1);
    loadImports(1);
  }, [loadReviews, loadUsers, loadAudit, loadFeedback, loadImports]);

  const schemeDetail = useCallback((code: string) => fetchAdminSchemeDetail(code), []);
  const schemeVersions = useCallback((code: string) => fetchSchemeVersions(code), []);

  const createSchemeCb = useCallback(
    async (payload: Record<string, unknown>) => {
      await mutate(async () => {
        await createScheme(payload);
        toast.success(t("admin.schemeCreated"));
        refreshSchemes(schemeQuery);
        refreshOverview();
      });
    },
    [mutate, refreshSchemes, refreshOverview, schemeQuery, t],
  );

  const updateSchemeCb = useCallback(
    async (code: string, payload: Record<string, unknown>) => {
      await mutate(async () => {
        await updateScheme(code, payload);
        toast.success(t("admin.schemeUpdated"));
        refreshSchemes(schemeQuery);
        refreshOverview();
      });
    },
    [mutate, refreshSchemes, refreshOverview, schemeQuery, t],
  );

  const changeStatus = useCallback(
    async (code: string, status: string, note?: string) => {
      await mutate(async () => {
        await changeSchemeStatus(code, status, note);
        toast.success(t("admin.statusChanged"));
        refreshSchemes(schemeQuery);
        refreshOverview();
        loadReviews(1);
      });
    },
    [mutate, refreshSchemes, refreshOverview, schemeQuery, t, loadReviews],
  );

  const submitForReview = useCallback(
    async (code: string, note?: string) => {
      await mutate(async () => {
        await submitSchemeForReview(code, note);
        toast.success(t("admin.reviewSubmitted"));
        refreshSchemes(schemeQuery);
      });
    },
    [mutate, refreshSchemes, schemeQuery, t],
  );

  const removeScheme = useCallback(
    async (code: string) => {
      await mutate(async () => {
        await deleteScheme(code);
        toast.success(t("admin.schemeDeleted"));
        refreshSchemes(schemeQuery);
        refreshOverview();
      });
    },
    [mutate, refreshSchemes, refreshOverview, schemeQuery, t],
  );

  const reviewsRefresh = useCallback(() => loadReviews(reviews.page), [loadReviews, reviews.page]);

  const decide = useCallback(
    async (reviewId: string, opts: { approve: boolean; publish?: boolean; note?: string }) => {
      await mutate(async () => {
        await decideReview(reviewId, opts);
        loadReviews(reviews.page);
        refreshOverview();
        refreshSchemes(schemeQuery);
      });
    },
    [mutate, loadReviews, refreshOverview, refreshSchemes, reviews.page, schemeQuery],
  );

  const usersRefresh = useCallback(() => loadUsers(users.page), [loadUsers, users.page]);
  const updateUserRole = useCallback(
    async (userId: string, role: string) => {
      await mutate(async () => {
        await setUserRole(userId, role);
        toast.success(t("admin.userUpdated"));
        loadUsers(users.page);
      });
    },
    [mutate, loadUsers, users.page, t],
  );
  const updateUserStatus = useCallback(
    async (userId: string, status: string) => {
      await mutate(async () => {
        await setUserStatus(userId, status);
        toast.success(t("admin.userUpdated"));
        loadUsers(users.page);
      });
    },
    [mutate, loadUsers, users.page, t],
  );

  const auditRefresh = useCallback(() => loadAudit(audit.page), [loadAudit, audit.page]);
  const feedbackRefresh = useCallback(() => loadFeedback(feedback.page), [loadFeedback, feedback.page]);

  const updateFeedbackStatus = useCallback(
    async (feedbackId: string, status: string) => {
      await mutate(async () => {
        await updateFeedback(feedbackId, status);
        toast.success(t("admin.feedbackUpdated"));
        loadFeedback(feedback.page);
        refreshOverview();
      });
    },
    [mutate, loadFeedback, feedback.page, refreshOverview, t],
  );

  const importJobsRefresh = useCallback(() => loadImports(importJobs.page), [loadImports, importJobs.page]);

  const previewRows = useCallback((rows: Record<string, unknown>[]) => previewImport(rows), []);

  const importRows = useCallback(
    async (rows: Record<string, unknown>[]) => {
      await mutate(async () => {
        const result = await applyImport(rows);
        toast.success(
          `${t("admin.importDone")} ${result.importedRows}${result.failedRows ? ` / ${result.failedRows} ${t("admin.importFailed")}` : ""}`,
        );
        loadImports(1);
        refreshOverview();
        refreshSchemes(schemeQuery);
      });
    },
    [mutate, loadImports, refreshOverview, refreshSchemes, schemeQuery, t],
  );

  const runHealthCheck = useCallback(async () => {
    setHealthLoading(true);
    try {
      setHealth(await fetchSystemHealth());
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setHealthLoading(false);
    }
  }, []);

  return {
    overview,
    overviewLoading,
    schemes,
    schemesLoading,
    schemeQuery,
    setSchemeQuery,
    schemeDetail,
    schemeVersions,
    createScheme: createSchemeCb,
    updateScheme: updateSchemeCb,
    changeStatus,
    submitForReview,
    removeScheme,
    reviews: reviews.data,
    reviewsLoading: reviews.loading,
    reviewsRefresh,
    decide,
    users: users.data,
    usersLoading: users.loading,
    usersRefresh,
    updateUserRole,
    updateUserStatus,
    auditLogs: audit.data,
    auditLoading: audit.loading,
    auditRefresh,
    feedback: feedback.data,
    feedbackLoading: feedback.loading,
    feedbackRefresh,
    updateFeedbackStatus,
    importJobs: importJobs.data,
    importJobsLoading: importJobs.loading,
    importJobsRefresh,
    previewRows,
    importRows,
    health,
    healthLoading,
    runHealthCheck,
  };
}