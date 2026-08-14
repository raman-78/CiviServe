/**
 * Nearby centres page (maps/locator prompt).
 *
 * Two searches: GPS ("Use my location") and a manual fallback (state / district
 * / city / PIN). Results render as a list or a Leaflet map; each centre offers
 * an external "Get directions" link — the app never navigates in-app.
 *
 * Privacy: the GPS anchor is used for one scan only and stays in component
 * state (nothing is stored or uploaded beyond the query the user triggered).
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  List,
  LoaderCircle,
  Map as MapIcon,
  MapPinOff,
  Navigation,
} from "lucide-react";
import { CENTER_RADIUS_PRESETS } from "@civiserve/shared";

import { EmptyState } from "@/components/shared/EmptyState";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  CENTER_TYPES,
  CENTER_TYPE_OPTIONS,
  fetchCentreDetail,
} from "@/features/centers/api";
import { CenterList } from "@/features/centers/components/CenterList";
import { CenterMap } from "@/features/centers/components/CenterMap";
import { LocationBanner } from "@/features/centers/components/LocationBanner";
import { ManualSearchForm } from "@/features/centers/components/ManualSearchForm";
import { useCentersSearch } from "@/features/centers/useCentersSearch";
import type { CenterType, ServiceCenter } from "@/types";

export function CentersPage() {
  const { t } = useTranslation();
  const {
    status,
    anchor,
    viewAnchor,
    manual,
    radius,
    type,
    loading,
    result,
    hasManualFilter,
    setManualField,
    locate,
    searchManual,
    rescale,
  } = useCentersSearch();
  const [view, setView] = useState<"list" | "map">("list");

  const centers = result?.centers ?? [];
  const markers = centers.map((center) => ({
    id: center.id,
    lat: center.lat,
    lng: center.lng,
    type: center.type,
    name: center.name,
    verified: center.verified,
    distanceKm: center.distanceKm,
  }));

  const openDirections = async (center: ServiceCenter) => {
    const detail = await fetchCentreDetail(center.id, anchor);
    if (detail.directionsUrl) window.open(detail.directionsUrl, "_blank", "noopener");
  };

  const radiusKm = radius as number;

  return (
    <div className="space-y-6">
      <PageHeader title={t("centers.title")} subtitle={t("centers.subtitle")} />

      <LocationBanner
        state={status === "locating" ? "locating" : status === "denied" ? "denied" : "granted"}
        onRequestLocation={locate}
        loading={loading}
      />

      <div className="flex flex-wrap items-center gap-3">
        <RadiusControl
          value={radiusKm}
          options={[...CENTER_RADIUS_PRESETS]}
          onChange={(km) => rescale(km as (typeof CENTER_RADIUS_PRESETS)[number], type)}
        />
        <TypeControl value={type} onChange={(next) => rescale(radius, next)} />
      </div>

      {(status === "denied" || status === "idle") && !result ? (
        <ManualSearchForm
          value={manual}
          onChange={setManualField}
          onSubmit={searchManual}
          disabled={loading || !hasManualFilter}
        />
      ) : null}

      {!result && (status === "idle" || status === "granted") ? (
        <div className="flex flex-col items-center gap-3 py-10 text-center">
          <Navigation className="h-8 w-8 text-muted-foreground" />
          <p className="max-w-sm text-sm text-muted-foreground">{t("centers.prompt")}</p>
          <Button onClick={locate} disabled={loading}>
            {loading ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Navigation className="h-4 w-4" />}
            {t("centers.useMyLocation")}
          </Button>
        </div>
      ) : null}

      {result ? (
        <Tabs value={view} onValueChange={(v) => setView(v as "list" | "map")}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-muted-foreground">
              {t("centers.resultsCount", { count: centers.length })}
            </p>
            <TabsList>
              <TabsTrigger value="list">
                <List className="h-4 w-4" />
                {t("centers.list")}
              </TabsTrigger>
              <TabsTrigger value="map">
                <MapIcon className="h-4 w-4" />
                {t("centers.map")}
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="list">
            {centers.length === 0 ? (
              <EmptyState
                icon={MapPinOff}
                title={t("centers.noCenters")}
                description={t("centers.noCentersDesc")}
              />
            ) : (
              <CenterList centers={centers} onDirections={openDirections} />
            )}
          </TabsContent>

          <TabsContent value="map">
            <CenterMap
              centers={markers}
              anchor={viewAnchor}
              radiusKm={radiusKm}
              onSelect={(id) => {
                const center = centers.find((c) => c.id === id);
                if (center) void openDirections(center);
              }}
            />
            {result.attributionNote ? (
              <p className="mt-2 text-xs text-muted-foreground">{result.attributionNote}</p>
            ) : null}
          </TabsContent>
        </Tabs>
      ) : null}
    </div>
  );
}

function RadiusControl({
  value,
  options,
  onChange,
}: {
  value: number;
  options: readonly number[];
  onChange: (value: number) => void;
}) {
  const { t } = useTranslation();
  return (
    <Select value={String(value)} onValueChange={(v) => onChange(Number(v))}>
      <SelectTrigger className="w-28" aria-label={t("centers.radius")}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {options.map((km) => (
          <SelectItem key={km} value={String(km)}>
            {t("centers.radiusKm", { km })}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

function TypeControl({
  value,
  onChange,
}: {
  value: CenterType | "";
  onChange: (value: CenterType | "") => void;
}) {
  const { t } = useTranslation();
  return (
    <Select value={value || "all"} onValueChange={(v) => onChange(v as CenterType | "")}>
      <SelectTrigger className="w-44" aria-label={t("centers.type")}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">{t("centers.allTypes")}</SelectItem>
        {CENTER_TYPES.map((ct) => (
          <SelectItem key={ct} value={ct}>
            {CENTER_TYPE_OPTIONS[ct]}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}