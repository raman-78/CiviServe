import { Search, X } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { SchemeCategory, StateCode } from "@/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { INDIAN_STATES } from "@/lib/constants";
import { toLabel } from "@/lib/utils";

const CATEGORIES: readonly SchemeCategory[] = [
  "education",
  "health",
  "housing",
  "employment",
  "agriculture",
  "pension",
  "women",
  "disability",
  "food-security",
  "financial-inclusion",
  "other",
];

export interface SchemeFilterState {
  query: string;
  category: SchemeCategory | "all";
  state: StateCode | "all";
}

interface SchemeFiltersProps {
  filters: SchemeFilterState;
  onChange: (filters: SchemeFilterState) => void;
  onClear: () => void;
}

/** Filters for the schemes catalog: free-text, category and state. */
export function SchemeFilters({ filters, onChange, onClear }: SchemeFiltersProps) {
  const { t } = useTranslation();
  const hasFilters =
    filters.query.trim() !== "" || filters.category !== "all" || filters.state !== "all";

  return (
    <div className="space-y-4">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={filters.query}
          onChange={(e) => onChange({ ...filters, query: e.target.value })}
          placeholder={t("schemes.searchPlaceholder")}
          className="pl-9"
          aria-label={t("common.search")}
        />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="scheme-category">{t("schemes.category")}</Label>
          <Select
            value={filters.category}
            onValueChange={(value) =>
              onChange({ ...filters, category: value as SchemeCategory | "all" })
            }
          >
            <SelectTrigger id="scheme-category">
              <SelectValue placeholder={t("schemes.allCategories")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t("schemes.allCategories")}</SelectItem>
              {CATEGORIES.map((category) => (
                <SelectItem key={category} value={category}>
                  {toLabel(category)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="scheme-state">{t("schemes.state")}</Label>
          <Select
            value={filters.state}
            onValueChange={(value) => onChange({ ...filters, state: value })}
          >
            <SelectTrigger id="scheme-state">
              <SelectValue placeholder={t("schemes.allStates")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t("schemes.allStates")}</SelectItem>
              {INDIAN_STATES.map((state) => (
                <SelectItem key={state.code} value={state.code}>
                  {state.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      {hasFilters ? (
        <Button variant="ghost" size="sm" onClick={onClear}>
          <X className="h-4 w-4" />
          {t("schemes.clearFilters")}
        </Button>
      ) : null}
    </div>
  );
}
