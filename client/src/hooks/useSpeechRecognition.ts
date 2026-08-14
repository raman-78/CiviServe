import { useCallback, useEffect, useRef, useState } from "react";
import {
  sttAdapter,
  type SpeechRecognitionError,
  type SpeechStatus,
  type SpeechToTextAdapter,
} from "@/services/stt";

export type { SpeechRecognitionError, SpeechStatus };

export interface UseSpeechRecognitionOptions {
  /** Language code used to pick the SpeechRecognition locale. */
  lang: string;
  onTranscript?: (transcript: string, isFinal: boolean) => void;
}

export interface UseSpeechRecognitionResult {
  /** Whether the current environment can transcribe at all. */
  supported: boolean;
  status: SpeechStatus;
  error: SpeechRecognitionError | null;
  finalTranscript: string;
  interimTranscript: string;
  transcript: string;
  start: () => void;
  stop: () => void;
  /** Bring the mic back to idle and clear partial results. */
  reset: () => void;
}

/**
 * React binding around the STT adapter. Transcripts stream through
 * `onTranscript` (pair with the chat slice `setDraftInput`); final results are
 * offered to the user for editing before sending (no auto-submit).
 */
export function useSpeechRecognition(options: UseSpeechRecognitionOptions): UseSpeechRecognitionResult {
  const { lang, onTranscript } = options;
  const [status, setStatus] = useState<SpeechStatus>("idle");
  const [error, setError] = useState<SpeechRecognitionError | null>(null);
  const [finalTranscript, setFinalTranscript] = useState("");
  const [interimTranscript, setInterimTranscript] = useState("");

  const adapterRef = useRef<SpeechToTextAdapter>(sttAdapter);
  const onTranscriptRef = useRef(onTranscript);
  onTranscriptRef.current = onTranscript;

  useEffect(() => {
    const adapter = adapterRef.current;
    const unsubStatus = adapter.onStatusChange(setStatus);
    const unsubError = adapter.onError((code: SpeechRecognitionError) => {
      setError(code);
      if (code === "not-allowed" || code === "no-speech") {
        setStatus("idle");
        setFinalTranscript("");
        setInterimTranscript("");
      }
    });
    const unsubResult = adapter.onResult((result) => {
      if (result.isFinal) {
        setFinalTranscript(result.transcript);
        setInterimTranscript("");
        onTranscriptRef.current?.(result.transcript, true);
      } else {
        setInterimTranscript(result.transcript);
        onTranscriptRef.current?.(result.transcript, false);
      }
    });
    setError(null);
    return () => {
      unsubStatus();
      unsubError();
      unsubResult();
      adapter.stop();
    };
  }, []);

  const start = useCallback(() => {
    if (!adapterRef.current.isSupported) return;
    setError(null);
    setInterimTranscript("");
    adapterRef.current.start(lang);
  }, [lang]);

  const stop = useCallback(() => {
    adapterRef.current.stop();
    setStatus("idle");
  }, []);

  const reset = useCallback(() => {
    adapterRef.current.stop();
    setFinalTranscript("");
    setInterimTranscript("");
    setError(null);
    setStatus("idle");
  }, []);

  return {
    supported: adapterRef.current.isSupported,
    status,
    error,
    finalTranscript,
    interimTranscript,
    transcript: (finalTranscript + (interimTranscript ? ` ${interimTranscript}` : "")).trim(),
    start,
    stop,
    reset,
  };
}