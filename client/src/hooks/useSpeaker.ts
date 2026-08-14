import { useCallback, useEffect, useRef, useState } from "react";
import { ttsAdapter } from "@/services/tts";

/**
 * Tracks the single speaker instance (by stable `id`) currently playing.
 * `ttsAdapter` is a shared singleton so at most one voice plays at a time —
 * starting any speaker cancels the previous one app-wide.
 */
let activeSpeakerId: string | null = null;
const activeListeners = new Set<(id: string | null) => void>();

function setActiveSpeaker(id: string | null) {
  activeSpeakerId = id;
  activeListeners.forEach((cb) => cb(id));
}

function subscribeActive(cb: (id: string | null) => void): () => void {
  activeListeners.add(cb);
  return () => {
    activeListeners.delete(cb);
  };
}

export interface UseSpeakerResult {
  /** True while THIS speaker is the one playing. */
  speaking: boolean;
  /** Start reading (cancels any other active speaker). */
  speak: (
    text: string,
    opts?: { lang?: string; rate?: number; voiceId?: string },
  ) => void;
  /** Stop speech from this speaker, or globally. */
  stop: (scope?: "this" | "global") => void;
  supported: boolean;
}

/**
 * User-triggered read-aloud. Never invoked automatically — callers react only
 * to explicit clicks / explicit "Yes" confirmations (voice prompt spec).
 */
export function useSpeaker(id: string): UseSpeakerResult {
  const [speaking, setSpeaking] = useState(false);
  const idRef = useRef(id);
  idRef.current = id;

  const updateSpeaking = useCallback((activeId: string | null) => {
    setSpeaking(activeId === idRef.current && ttsAdapter.isSpeaking());
  }, []);

  useEffect(() => {
    const unsubStatus = ttsAdapter.onStatusChange(() => updateSpeaking(activeSpeakerId));
    const unsubActive = subscribeActive(updateSpeaking);
    updateSpeaking(activeSpeakerId);
    return () => {
      unsubStatus();
      unsubActive();
    };
  }, [updateSpeaking]);

  const speak = useCallback(
    (text: string, opts: { lang?: string; rate?: number; voiceId?: string } = {}) => {
      if (!ttsAdapter.isSupported || !text.trim()) return;
      setActiveSpeaker(idRef.current);
      ttsAdapter.speak(text, opts.lang ?? "en-IN", {
        rate: opts.rate,
        voiceId: opts.voiceId,
      });
    },
    [],
  );

  const stop = useCallback((scope: "this" | "global" = "this") => {
    if (scope === "this" && activeSpeakerId !== idRef.current) return;
    ttsAdapter.stop();
    setActiveSpeaker(null);
  }, []);

  return { speaking, speak, stop, supported: ttsAdapter.isSupported };
}

/** Silence any ongoing playback (navigation / unmount so speech never lingers). */
export function stopAllSpeech(): void {
  ttsAdapter.stop();
  setActiveSpeaker(null);
}