/**
 * Admin dashboard (Prompt 13/15 completion). Tabs for overview, scheme
 * management, review queue, users, audit, feedback, bulk import and system
 * health. Everything reads/writes through `useAdmin`, which mirrors the
 * FastAPI admin router 1:1.
 */
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Activity,
  Archive,
  CheckCircle2,
  CircleDollarSign,
  Clock,
  Eye,
  FileInput,
  FilePlus2,
  LayoutDashboard,
  ListChecks,
  RefreshCw,
  Search,
  Star,
  Trash2,
  UserRound,
  Users,
  XCircle,
} from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingState } from "@/components/shared/LoadingState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAdmin } from "@/features/admin/useAdmin";

/** Map a verbose Dashboard piece (?) — no-op mapping helpers for status labels. */
function StatusBadge({ status }: { status: string }) {
  const variant =
    status === "published"
      ? "success"
      : status === "draft" || status === "pending_review"
        ? "warning"
        : status === "archived" || status === "expired"
          ? "muted"
          : "secondary";
  return <Badge variant={variant}>{status}</Badge>;
}

function StatCard({
  label,
  value,
  icon: Icon,
  hint,
}: {
  label: string;
  value: number | string;
  icon: typeof Activity;
  hint?: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-start justify-between gap-3 p-5">
        <div className="space-y-1">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {label}
          </p>
          <p className="text-2xl font-semibold tabular-nums">{value}</p>
          {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
        </div>
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-muted">
          <Icon className="h-4 w-4 text-muted-foreground" />
        </span>
      </CardContent>
    </Card>
  );
}

function Pager({
  page,
  total,
  pageSize,
  onPage,
}: {
  page: number;
  total: number;
  pageSize: number;
  onPage: (page: number) => void;
}) {
  const { t } = useTranslation();
  const pages = total === 0 ? 1 : Math.ceil(total / pageSize);
  return (
    <div className="flex items-center justify-between gap-2 pt-2">
      <p className="text-xs text-muted-foreground">
        {t("admin.page")} {page} / {pages} · {t("admin.totalRows", { count: total })}
      </p>
      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="sm"
          disabled={page <= 1}
          onClick={() => onPage(page - 1)}
        >
          {t("admin.previous")}
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={page >= pages}
          onClick={() => onPage(page + 1)}
        >
          {t("admin.next")}
        </Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tabs
// ---------------------------------------------------------------------------

function OverviewTab() {
  const { t } = useTranslation();
  const { overview, overviewLoading, runHealthCheck, health, healthLoading } = useAdmin();

  if (overviewLoading || !overview) return <LoadingState />;
  const s = overview.stats;
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={LayoutDashboard} label={t("admin.statTotal")} value={s.schemeTotal} />
        <StatCard icon={CheckCircle2} label={t("admin.statPublished")} value={s.schemePublished} />
        <StatCard
          icon={Clock}
          label={t("admin.statPendingApprovals")}
          value={s.pendingApprovals}
          hint={s.lastVerifiedAt ? new Date(s.lastVerifiedAt).toLocaleString() : t("admin.never")}
        />
        <StatCard icon={Users} label={t("admin.statUsers")} value={s.userTotal} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">{t("admin.statusBreakdown")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {overview.byStatus.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t("admin.emptyStatus")}</p>
            ) : (
              overview.byStatus.map(({ status, count }) => (
                <div key={status} className="flex items-center justify-between gap-2 text-sm">
                  <StatusBadge status={status} />
                  <span className="tabular-nums text-muted-foreground">{count}</span>
                </div>
              ))
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">{t("admin.publishedCategories")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {overview.publishedCategories.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t("admin.emptyCategories")}</p>
            ) : (
              overview.publishedCategories.map(({ category, count }) => (
                <div key={category} className="flex items-center justify-between gap-2 text-sm">
                  <span className="capitalize">{category}</span>
                  <span className="tabular-nums text-muted-foreground">{count}</span>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">{t("admin.pendingReview")}</CardTitle>
          <CardDescription>{t("admin.pendingReviewDesc")}</CardDescription>
        </CardHeader>
        <CardContent>
          {overview.pendingReview ? (
            <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <span className="font-mono text-muted-foreground">
                {overview.pendingReview.schemeCode}
              </span>
              <span>{new Date(overview.pendingReview.createdAt).toLocaleString()}</span>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">{t("admin.noPendingReview")}</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">{t("admin.healthTitle")}</CardTitle>
          <CardDescription>{t("admin.healthDesc")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between gap-2">
            <Button variant="outline" size="sm" onClick={runHealthCheck} disabled={healthLoading}>
              <RefreshCw className={healthLoading ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
              {t("admin.runHealth")}
            </Button>
            {health ? (
              <Badge variant={health.overall === "ok" ? "success" : "destructive"}>
                {health.overall}
              </Badge>
            ) : null}
          </div>
          {health ? (
            <div className="space-y-1">
              {health.checks.map((c) => (
                <div key={c.component} className="flex items-center justify-between gap-2 text-sm">
                  <span className="capitalize">{c.component}</span>
                  <div className="flex items-center gap-2">
                    {c.message ? (
                      <span className="text-xs text-muted-foreground">{c.message}</span>
                    ) : null}
                    <Badge variant={c.status === "ok" ? "success" : "destructive"}>
                      {c.status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}

const SCHEME_STATUSES = [
  "draft",
  "pending_review",
  "verified",
  "published",
  "temporarily_unavailable",
  "archived",
  "expired",
] as const;

function SchemesTab() {
  const { t } = useTranslation();
  const {
    schemes,
    schemesLoading,
    schemeQuery,
    setSchemeQuery,
    changeStatus,
    removeScheme,
    submitForReview,
  } = useAdmin();
  const [busyCode, setBusyCode] = useState<string | null>(null);

  const runAction = async (fn: () => Promise<void>, code: string) => {
    setBusyCode(code);
    try {
      await fn();
    } finally {
      setBusyCode(null);
    }
  };

  if (schemesLoading && !schemes) return <LoadingState />;
  const items = schemes?.items ?? [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-56 flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder={t("admin.searchSchemes")}
            defaultValue={schemeQuery.q ?? ""}
            onChange={(e) => setSchemeQuery({ ...schemeQuery, q: e.target.value, page: 1 })}
            className="pl-9"
          />
        </div>
        <Select
          value={schemeQuery.status ?? "all"}
          onValueChange={(value) =>
            setSchemeQuery({ ...schemeQuery, status: value === "all" ? undefined : value, page: 1 })
          }
        >
          <SelectTrigger className="w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t("admin.allStatuses")}</SelectItem>
            {SCHEME_STATUSES.map((status) => (
              <SelectItem key={status} value={status}>
                {status}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={schemeQuery.verificationStatus ?? "all"}
          onValueChange={(value) =>
            setSchemeQuery({
              ...schemeQuery,
              verificationStatus: value === "all" ? undefined : value,
              page: 1,
            })
          }
        >
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t("admin.allVerification")}</SelectItem>
            {["unverified", "pending", "verified", "failed", "stale"].map((v) => (
              <SelectItem key={v} value={v}>
                {v}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {items.length === 0 ? (
        <EmptyState icon={FilePlus2} title={t("admin.noSchemes")} />
      ) : (
        <div className="space-y-3">
          {items.map((scheme) => (
            <Card key={scheme.id}>
              <CardContent className="flex flex-wrap items-center gap-4 p-4">
                <div className="min-w-40 flex-1 space-y-1">
                  <p className="font-medium">{scheme.nameEn}</p>
                  <p className="font-mono text-xs text-muted-foreground">
                    {scheme.code} · {scheme.category}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <StatusBadge status={scheme.schemeStatus} />
                  <Badge variant="outline">{scheme.verificationStatus}</Badge>
                </div>
                <div className="flex items-center gap-1.5">
                  {(scheme.schemeStatus === "draft" || scheme.schemeStatus === "verified") && (
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={busyCode === scheme.code}
                      onClick={() =>
                        runAction(() => submitForReview(scheme.code), scheme.code)
                      }
                    >
                      <ListChecks className="h-4 w-4" />
                      {t("admin.submitReview")}
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={busyCode === scheme.code}
                    onClick={() => {
                      const next =
                        scheme.schemeStatus === "published" ? "temporarily_unavailable" : "published";
                      runAction(
                        () => changeStatus(scheme.code, next),
                        scheme.code,
                      );
                    }}
                  >
                    {scheme.schemeStatus === "published" ? (
                      <>
                        <Archive className="h-4 w-4" />
                        {t("admin.unpublish")}
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="h-4 w-4" />
                        {t("admin.publish")}
                      </>
                    )}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={busyCode === scheme.code}
                    onClick={() =>
                      runAction(() => changeStatus(scheme.code, "archived"), scheme.code)
                    }
                  >
                    <Archive className="h-4 w-4" />
                    {t("admin.archive")}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={busyCode === scheme.code}
                    onClick={() => runAction(() => removeScheme(scheme.code), scheme.code)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
          <Pager
            page={schemes?.page ?? 1}
            total={schemes?.total ?? 0}
            pageSize={schemes?.pageSize ?? 20}
            onPage={(page) => setSchemeQuery({ ...schemeQuery, page })}
          />
        </div>
      )}
    </div>
  );
}

function ReviewsTab() {
  const { t } = useTranslation();
  const { reviews, reviewsLoading, decide, reviewsRefresh } = useAdmin();
  const [busyId, setBusyId] = useState<string | null>(null);

  if (reviewsLoading && !reviews) return <LoadingState />;
  const items = reviews?.items ?? [];

  const runDecision = async (id: string, opts: { approve: boolean; publish?: boolean }) => {
    setBusyId(id);
    try {
      await decide(id, opts);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button variant="outline" size="sm" onClick={reviewsRefresh}>
          <RefreshCw className="h-4 w-4" />
          {t("admin.refresh")}
        </Button>
      </div>
      {items.length === 0 ? (
        <EmptyState icon={ListChecks} title={t("admin.noReviews")} />
      ) : (
        <div className="space-y-3">
          {items.map((r) => (
            <Card key={r.id}>
              <CardContent className="flex flex-wrap items-center gap-4 p-4">
                <div className="min-w-40 flex-1 space-y-1">
                  <p className="font-mono text-xs text-muted-foreground">{r.schemeCode}</p>
                  <p className="text-sm">
                    {t("admin.fromStatus")} <Badge variant="outline">{r.fromStatus}</Badge>
                  </p>
                  {r.requestNote ? (
                    <p className="text-sm text-muted-foreground">{r.requestNote}</p>
                  ) : null}
                  <p className="text-xs text-muted-foreground">
                    {new Date(r.createdAt).toLocaleString()}
                  </p>
                </div>
                <div className="flex items-center gap-1.5">
                  <Button
                    size="sm"
                    disabled={busyId === r.id}
                    onClick={() => runDecision(r.id, { approve: false })}
                  >
                    <XCircle className="h-4 w-4" />
                    {t("admin.reject")}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={busyId === r.id}
                    onClick={() => runDecision(r.id, { approve: true })}
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    {t("admin.approve")}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={busyId === r.id}
                    onClick={() => runDecision(r.id, { approve: true, publish: true })}
                  >
                    <CircleDollarSign className="h-4 w-4" />
                    {t("admin.approvePublish")}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

const USER_ROLES = ["citizen", "content_editor", "admin"] as const;

function UsersTab() {
  const { t } = useTranslation();
  const { users, usersLoading, updateUserRole, updateUserStatus, usersRefresh } = useAdmin();
  const [busyId, setBusyId] = useState<string | null>(null);

  if (usersLoading && !users) return <LoadingState />;
  const items = users?.items ?? [];

  const run = async (id: string, fn: () => Promise<void>) => {
    setBusyId(id);
    try {
      await fn();
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button variant="outline" size="sm" onClick={usersRefresh}>
          <RefreshCw className="h-4 w-4" />
          {t("admin.refresh")}
        </Button>
      </div>
      {items.length === 0 ? (
        <EmptyState icon={Users} title={t("admin.noUsers")} />
      ) : (
        <div className="space-y-3">
          {items.map((u) => (
            <Card key={u.id}>
              <CardContent className="flex flex-wrap items-center gap-4 p-4">
                <div className="min-w-40 flex-1 space-y-1">
                  <p className="font-medium">{u.displayName || u.email || u.id}</p>
                  <p className="font-mono text-xs text-muted-foreground">{u.preferredLanguage}</p>
                </div>
                <Badge variant="outline">{u.role}</Badge>
                <Badge
                  variant={u.status === "active" ? "success" : u.status === "suspended" ? "destructive" : "muted"}
                >
                  {u.status}
                </Badge>
                <div className="flex items-center gap-1.5">
                  <Select
                    value={u.role}
                    onValueChange={(role) => run(u.id, () => updateUserRole(u.id, role))}
                  >
                    <SelectTrigger className="h-8 w-36">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {USER_ROLES.map((role) => (
                        <SelectItem key={role} value={role}>
                          {role}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={busyId === u.id}
                    onClick={() =>
                      run(u.id, () =>
                        updateUserStatus(u.id, u.status === "active" ? "suspended" : "active"),
                      )
                    }
                  >
                    <UserRound className="h-4 w-4" />
                    {u.status === "active" ? t("admin.suspend") : t("admin.activate")}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function AuditTab() {
  const { t } = useTranslation();
  const { auditLogs, auditLoading, auditRefresh } = useAdmin();

  if (auditLoading && !auditLogs) return <LoadingState />;
  const items = auditLogs?.items ?? [];

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button variant="outline" size="sm" onClick={auditRefresh}>
          <RefreshCw className="h-4 w-4" />
          {t("admin.refresh")}
        </Button>
      </div>
      {items.length === 0 ? (
        <EmptyState icon={Activity} title={t("admin.noAudit")} />
      ) : (
        <div className="space-y-1.5">
          {items.map((entry) => (
            <div
              key={entry.id}
              className="flex flex-wrap items-baseline justify-between gap-2 rounded-md border px-3 py-2 text-sm"
            >
              <div className="flex items-baseline gap-2">
                <Badge variant="outline">{entry.action}</Badge>
                <span className="font-mono text-xs text-muted-foreground">
                  {entry.entityType}/{entry.entityCode ?? entry.entityId ?? "-"}
                </span>
              </div>
              <span className="text-xs text-muted-foreground">
                {entry.actorRole ?? "-"} · {new Date(entry.createdAt).toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const FEEDBACK_STATUSES = ["new", "acknowledged", "resolved", "archived"] as const;

function FeedbackTab() {
  const { t } = useTranslation();
  const { feedback, feedbackLoading, updateFeedbackStatus, feedbackRefresh } = useAdmin();

  if (feedbackLoading && !feedback) return <LoadingState />;
  const items = feedback?.items ?? [];

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button variant="outline" size="sm" onClick={feedbackRefresh}>
          <RefreshCw className="h-4 w-4" />
          {t("admin.refresh")}
        </Button>
      </div>
      {items.length === 0 ? (
        <EmptyState icon={Star} title={t("admin.noFeedback")} />
      ) : (
        <div className="space-y-3">
          {items.map((f) => (
            <Card key={f.id}>
              <CardContent className="space-y-2 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                  <div className="flex items-center gap-2">
                    {f.rating ? (
                      <span className="text-amber-500">
                        {"★".repeat(f.rating)}
                        <span className="text-muted-foreground">{"★".repeat(5 - f.rating)}</span>
                      </span>
                    ) : null}
                    {f.category ? <Badge variant="outline">{f.category}</Badge> : null}
                    <Badge variant="outline">{f.status}</Badge>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {f.language} · {new Date(f.createdAt).toLocaleString()}
                  </span>
                </div>
                {f.comment ? <p className="text-sm text-muted-foreground">{f.comment}</p> : null}
                <div className="flex items-center gap-1.5">
                  <Select
                    value={f.status}
                    onValueChange={(status) => {
                      void updateFeedbackStatus(f.id, status);
                    }}
                  >
                    <SelectTrigger className="h-8 w-40">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {FEEDBACK_STATUSES.map((status) => (
                        <SelectItem key={status} value={status}>
                          {status}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function ImportTab() {
  const { t } = useTranslation();
  const {
    importJobs,
    importJobsLoading,
    importJobsRefresh,
    previewRows,
    importRows,
  } = useAdmin();
  const [csv, setCsv] = useState("");
  const [preview, setPreview] = useState<Awaited<ReturnType<typeof previewRows>> | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const parseCsv = (text: string): Record<string, string>[] => {
    const lines = text
      .trim()
      .split(/\r?\n/)
      .filter((line) => line.trim() !== "");
    if (lines.length === 0) return [];
    const header = lines[0].split(",").map((h) => h.trim());
    return lines.slice(1).map((line) => {
      const cells = line.split(",").map((c) => c.trim());
      const row: Record<string, string> = {};
      header.forEach((h, i) => {
        if (h) row[h] = cells[i] ?? "";
      });
      return row;
    });
  };

  const onPreview = async () => {
    setBusy("preview");
    try {
      setPreview(await previewRows(parseCsv(csv)));
    } finally {
      setBusy(null);
    }
  };

  const onApply = async () => {
    setBusy("apply");
    try {
      await importRows(parseCsv(csv));
      setPreview(null);
      setCsv("");
      await importJobsRefresh();
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">{t("admin.importTitle")}</CardTitle>
          <CardDescription>{t("admin.importDesc")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Textarea
            value={csv}
            onChange={(e) => setCsv(e.target.value)}
            placeholder={t("admin.importPlaceholder")}
            rows={8}
          />
          <div className="flex flex-wrap gap-2">
            <Button size="sm" onClick={onPreview} disabled={busy !== null || !csv.trim()}>
              <Eye className="h-4 w-4" />
              {t("admin.previewImport")}
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={onApply}
              disabled={busy !== null || !csv.trim()}
            >
              <FileInput className="h-4 w-4" />
              {t("admin.applyImport")}
            </Button>
          </div>
          {preview ? (
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">
                {t("admin.importValid", { count: preview.validRows })} ·{" "}
                {t("admin.importInvalid", { count: preview.invalidRows })} ·{" "}
                {t("admin.importTotal", { count: preview.totalRows })}
              </p>
              <ScrollPreview rows={preview.rows} />
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">{t("admin.importJobs")}</CardTitle>
        </CardHeader>
        <CardContent>
          {importJobsLoading && !importJobs ? (
            <LoadingState />
          ) : (importJobs?.items ?? []).length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("admin.noJobs")}</p>
          ) : (
            <div className="space-y-1.5">
              {(importJobs?.items ?? []).map((job) => (
                <div
                  key={job.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-md border px-3 py-2 text-sm"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-muted-foreground">
                      {job.filename ?? job.id}
                    </span>
                    <Badge variant={job.status === "processed" ? "success" : "warning"}>
                      {job.status}
                    </Badge>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {job.importedRows} {t("admin.imported")} · {job.failedRows} {t("admin.failed")}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function ScrollPreview({ rows }: { rows: { row: number; code: string | null; name: string | null; error: string | null; willCreate: boolean; willUpdate: boolean }[] }) {
  const { t } = useTranslation();
  return (
    <div className="max-h-72 space-y-1 overflow-auto rounded-md border p-2">
      {rows.map((r) => (
        <div key={r.row} className="flex items-center justify-between gap-2 text-sm">
          <span className="font-mono text-xs tabular-nums text-muted-foreground">#{r.row}</span>
          <span className="min-w-0 flex-1 truncate">{r.name ?? r.code ?? "-"}</span>
          {r.error ? (
            <span className="text-xs text-destructive">{r.error}</span>
          ) : (
            <span className="text-xs text-muted-foreground">
              {r.willCreate ? t("admin.willCreate") : r.willUpdate ? t("admin.willUpdate") : ""}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export function AdminDashboardPage() {
  const { t } = useTranslation();
  const { overview } = useAdmin();
  const pendingCount = overview?.stats.pendingApprovals ?? 0;

  const tabs = useMemo(
    () => [
      { value: "overview", key: "admin.tabOverview" },
      { value: "schemes", key: "admin.tabSchemes" },
      { value: "reviews", key: "admin.tabReviews" },
      { value: "users", key: "admin.tabUsers" },
      { value: "audit", key: "admin.tabAudit" },
      { value: "feedback", key: "admin.tabFeedback" },
      { value: "import", key: "admin.tabImport" },
    ],
    [],
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("admin.title")}
        description={t("admin.description")}
        actions={
          pendingCount > 0 ? (
            <Badge variant="warning">
              <ListChecks className="mr-1 h-3.5 w-3.5" />
              {t("admin.pendingApprovalsBadge", { count: pendingCount })}
            </Badge>
          ) : undefined
        }
      />

      <Tabs defaultValue="overview">
        <TabsList className="flex h-auto flex-wrap">
          {tabs.map(({ value, key }) => (
            <TabsTrigger key={value} value={value}>
              {t(key)}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="overview">
          <OverviewTab />
        </TabsContent>
        <TabsContent value="schemes">
          <SchemesTab />
        </TabsContent>
        <TabsContent value="reviews">
          <ReviewsTab />
        </TabsContent>
        <TabsContent value="users">
          <UsersTab />
        </TabsContent>
        <TabsContent value="audit">
          <AuditTab />
        </TabsContent>
        <TabsContent value="feedback">
          <FeedbackTab />
        </TabsContent>
        <TabsContent value="import">
          <ImportTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}