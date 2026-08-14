/**
 * Locator state machine for the nearby-centres page (maps/locator prompt).
 *
 * Owns the "consent → scan" flow and the manual-location fallback. Privacy
 * contract: the GPS point is used for a single scan and kept only for the
 * current render; nothing is stored, logged, or forwarded to a third party.
 */
import { useCallback, useState } from "react";
import { fetchNearbyCenters, searchCentersManually } from "@/features/centers/api";
import type {
  CenterRadiusKm,
  CenterType,
  GeoPoint,
  NearbyCentersResponse,
} from "@/types";

export type LocatorStatus = "idle" | "locating" | "granted" | "denied" | "error";

export interface ManualSearchInput {
  stateCode: string;
  district: string;
  city: string;
  pincode: string;
}

const EMPTY_MANUAL: ManualSearchInput = { stateCode: "", district: "", city: "", pincode: "" };

const INDIA_DEFAULT: GeoPoint = { lat: 22.85, lng: 77.6569 };

export function useCentersSearch() {
  const [status, setStatus] = useState<LocatorStatus>("idle");
  const [anchor, setAnchor] = useState<GeoPoint | null>(null);
  const [manual, setManual] = useState<ManualSearchInput>(EMPTY_MANUAL);
  const [radius, setRadius] = useState<CenterRadiusKm>(10);
  const [type, setType] = useState<CenterType | "">("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<NearbyCentersResponse | null>(null);

  const locate = useCallback(() => {
    setError(null);
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      setStatus("denied");
      return;
    }
    setStatus("locating");
    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const point = { lat: position.coords.latitude, lng: position.coords.longitude };
        setAnchor(point);
        setStatus("granted");
        try {
          const data = await fetchNearbyCenters({
            lat: point.lat,
            lng: point.lng,
            radiusKm: radius,
            type: type || undefined,
          });
          setResult(data);
        } catch {
          setStatus("error");
        } finally {
          setLoading(false);
        }
      },
      () => {
        setStatus("denied");
        setLoading(false);
      },
      { enableHighAccuracy: true, timeout: 10_000, maximumAge: 0 },
    );
  }, [radius, type]);

  const searchManual = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const data = await searchCentersManually({
        stateCode: manual.stateCode || undefined,
        district: manual.district || undefined,
        city: manual.city || undefined,
        pincode: manual.pincode || undefined,
        type: type || undefined,
      });
      setResult(data);
      if (data.anchor?.lat !== undefined && data.anchor?.lng !== undefined) {
        setAnchor({ lat: data.anchor.lat, lng: data.anchor.lng });
        setStatus("granted");
      } else {
        setStatus("idle");
      }
    } catch {
      setError("manual_failed");
    } finally {
      setLoading(false);
    }
  }, [manual, type]);

  const rescale = useCallback(
    async (nextRadius: CenterRadiusKm, nextType: CenterType | "") => {
      setRadius(nextRadius);
      setType(nextType);
      if (!anchor) return;
      setLoading(true);
      setError(null);
      try {
        const data = await fetchNearbyCenters({
          lat: anchor.lat,
          lng: anchor.lng,
          radiusKm: nextRadius,
          type: nextType || undefined,
        });
        setResult(data);
      } catch {
        setError("rescale_failed");
      } finally {
        setLoading(false);
      }
    },
    [anchor],
  );

  const setManualField = useCallback((key: keyof ManualSearchInput, value: string) => {
    setManual((prev) => ({ ...prev, [key]: value }));
  }, []);

  const hasManualFilter = Boolean(
    manual.stateCode || manual.district || manual.city || manual.pincode,
  );

  return {
    status,
    anchor,
    viewAnchor: anchor ?? INDIA_DEFAULT,
    manual,
    radius,
    type,
    loading,
    error,
    result,
    hasManualFilter,
    setManualField,
    locate,
    searchManual,
    rescale,
  };
}