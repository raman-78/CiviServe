/**
 * Manual-location form for the locator — state / district / city / PIN code.
 * Empty inputs are omitted; the server scopes the catalogue search. Anchors
 * resolved this way are always labelled approximate.
 */
import { Search } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { ReactNode } from "react";

import type { ManualSearchInput } from "@/features/centers/useCentersSearch";
import { INDIAN_STATES } from "@/lib/constants";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface ManualSearchFormProps {
  value: ManualSearchInput;
  onChange: (key: keyof ManualSearchInput, value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium text-muted-foreground">{label}</label>
      {children}
    </div>
  );
}

export function ManualSearchForm({ value, onChange, onSubmit, disabled }: ManualSearchFormProps) {
  const { t } = useTranslation();

  return (
    <div className="rounded-xl border bg-card p-4">
      <p className="mb-3 text-sm font-medium">{t("centers.manualSearch")}</p>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label={t("centers.state")}>
          <Select value={value.stateCode || "any"} onValueChange={(v) => onChange("stateCode", v === "any" ? "" : v)}>
            <SelectTrigger aria-label={t("centers.state")}>
              <SelectValue placeholder={t("centers.selectState")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="any">{t("schemes.allStates")}</SelectItem>
              {INDIAN_STATES.map((state) => (
                <SelectItem key={state.code} value={state.code}>
                  {state.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
        <Field label={t("centers.district")}>
          <Input
            value={value.district}
            onChange={(e) => onChange("district", e.target.value)}
            placeholder={t("centers.districtPlaceholder")}
          />
        </Field>
        <Field label={t("centers.city")}>
          <Input
            value={value.city}
            onChange={(e) => onChange("city", e.target.value)}
            placeholder={t("centers.cityPlaceholder")}
          />
        </Field>
        <Field label={t("centers.pin")}>
          <Input
            value={value.pincode}
            inputMode="numeric"
            maxLength={6}
            onChange={(e) => onChange("pincode", e.target.value.replace(/\D/g, ""))}
            placeholder={t("centers.pinPlaceholder")}
          />
        </Field>
      </div>
      <Button className="mt-4 w-full sm:w-auto" onClick={onSubmit} disabled={disabled}>
        <Search className="h-4 w-4" />
        {t("centers.search")}
      </Button>
    </div>
  );
}