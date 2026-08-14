import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { SearchX } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { LoadingState } from "@/components/shared/LoadingState";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import {
  SchemeFilters,
  type SchemeFilterState,
} from "@/features/schemes/components/SchemeFilters";
import { SchemeGrid } from "@/features/schemes/components/SchemeGrid";
import { fetchSchemeSummaries } from "@/features/schemes/api";
import type { Paginated, SchemeSummary } from "@/types";

const DEFAULT_FILTERS: SchemeFilterState = {
  query: "",
  category: "all",
  state: "all",
};

/** Schemes catalog page (live published data from the backend). */
export function SchemesPage() {
  const { t } = useTranslation();
  const [filters, setFilters] = useState<SchemeFilterState>(DEFAULT_FILTERS);
  const [data, setData] = useState<Paginated<SchemeSummary> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(false);
    fetchSchemeSummaries({
      page: 1,
      pageSize: 60,
      query: filters.query,
      category: filters.category === "all" ? undefined : filters.category,
      state: filters.state === "all" ? undefined : filters.state,
    })
      .then((result) => {
        if (active) setData(result);
      })
      .catch(() => {
        if (active) setError(true);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [filters, attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  const clearFilters = useCallback(() => setFilters(DEFAULT_FILTERS), []);

  if (error && !data) {
    return (
      <div className="space-y-6">
        <PageHeader title={t("schemes.title")} subtitle={t("schemes.subtitle")} />
        <ErrorState onRetry={retry} />
      </div>
    );
  }

  if (loading && !data) {
    return (
      <div className="space-y-6">
        <PageHeader title={t("schemes.title")} subtitle={t("schemes.subtitle")} />
        <LoadingState />
      </div>
    );
  }

  const schemes = data?.items ?? [];

  return (
    <div className="space-y-6">
      <PageHeader title={t("schemes.title")} subtitle={t("schemes.subtitle")} />
      <SchemeFilters filters={filters} onChange={setFilters} onClear={clearFilters} />
      <p className="text-sm text-muted-foreground">
        {t("schemes.results", { count: data?.total ?? schemes.length })}
      </p>
      {schemes.length === 0 ? (
        <EmptyState
          icon={SearchX}
          title={t("schemes.noResults")}
          description={t("schemes.noResultsDesc")}
        />
      ) : (
        <SchemeGrid schemes={schemes} />
      )}
    </div>
  );
}