/**
 * Client state for one eligibility evaluation (Prompt 10).
 *
 * Reads the stored profile (via `useAuth`), maps it to a
 * `RecommendationRequest`, evaluates on mount, and exposes a manual refresh.
 */
import { useEffect, useMemo, useState } from "react";
import type { RecommendationResponse } from "@/types";
import { fetchEligibility } from "@/features/eligibility/api";
import {
  hasEligibilityInputs,
  profileToEligibilityRequest,
} from "@/features/eligibility/request";
import type { UserProfile } from "@/types";

export interface EligibilityState {
  /** Latest verdicts (null until the first run ends). */
  data: RecommendationResponse | null;
  running: boolean;
  error: boolean;
  /** True when the profile has enough detail to bother asking the engine. */
  ready: boolean;
  /** Re-run with the current profile. */
  refresh: () => void;
}

export function useEligibility(profile: UserProfile | null): EligibilityState {
  const request = useMemo(() => profileToEligibilityRequest(profile), [profile]);
  const ready = useMemo(() => hasEligibilityInputs(profile), [profile]);
  const [runId, setRunId] = useState(0);
  const [data, setData] = useState<RecommendationResponse | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!ready) {
      setData(null);
      setRunning(false);
      setError(false);
      return;
    }
    let active = true;
    setRunning(true);
    setError(false);
    fetchEligibility(request)
      .then((response) => {
        if (!active) return;
        setData(response);
        setRunning(false);
      })
      .catch(() => {
        if (!active) return;
        setError(true);
        setRunning(false);
      });
    return () => {
      active = false;
    };
  }, [ready, request, runId]);

  return {
    data,
    running,
    error,
    ready,
    refresh: () => setRunId((id) => id + 1),
  };
}