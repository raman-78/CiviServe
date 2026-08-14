import { Navigation, LoaderCircle, CheckCircle2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert";

interface LocationBannerProps {
  state: "idle" | "locating" | "granted" | "denied";
  loading?: boolean;
  onRequestLocation: () => void;
}

/** Geolocation consent banner + scan status (maps/locator prompt). */
export function LocationBanner({ state, loading, onRequestLocation }: LocationBannerProps) {
  const { t } = useTranslation();

  if (state === "denied") {
    return (
      <Alert variant="destructive">
        <AlertTitle>{t("centers.locationDenied")}</AlertTitle>
        <AlertDescription>{t("centers.manualSearchHint")}</AlertDescription>
      </Alert>
    );
  }

  const isGranted = state === "granted";
  const isLocating = state === "locating" || loading;

  return (
    <Alert variant={isGranted ? "default" : undefined}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <AlertTitle>{isGranted ? t("centers.grantedTitle") : t("centers.title")}</AlertTitle>
          <AlertDescription>
            {isGranted ? t("centers.grantedDesc") : t("centers.subtitle")}
          </AlertDescription>
        </div>
        <Button size="sm" onClick={onRequestLocation} disabled={isLocating}>
          {isLocating ? (
            <LoaderCircle className="h-4 w-4 animate-spin" />
          ) : isGranted ? (
            <CheckCircle2 className="h-4 w-4" />
          ) : (
            <Navigation className="h-4 w-4" />
          )}
          {isLocating
            ? t("centers.locating")
            : isGranted
              ? t("centers.located")
              : t("centers.useMyLocation")}
        </Button>
      </div>
    </Alert>
  );
}
