/**
 * Speech-to-Text adapter (docs/architecture/17 swap point).
 *
 * Feature code depends on the `SpeechToTextAdapter` interface only. The concrete
 * browser implementation is a new class + a config value (`VITE_STT_ENGINE`);
 * swapping to a cloud engine is zero change in the feature layer.
 */

export type SpeechRecognitionError =
  | "not-allowed"
  | "no-speech"
  | "audio-capture"
  | "network"
  | "aborted"
  | "service-not-allowed"
  | "other";

export interface SpeechResult {
  /** Best-guess final or interim transcript so far. */
  transcript: string;
  /** True only for a settled, final result chunk. */
  isFinal: boolean;
}

export type SpeechStatus = "idle" | "listening" | "processing";

export interface SpeechToTextAdapter {
  /** True when the engine (e.g. browser SpeechRecognition) is available. */
  readonly isSupported: boolean;
  /**
   * Start listening. Resolves to a `denied` status via callback if the user
   * blocks microphone access.
   */
  start(lang: string): void;
  stop(): void;
  onStatusChange(cb: (status: SpeechStatus) => void): () => void;
  onResult(cb: (result: SpeechResult) => void): () => void;
  onError(cb: (code: SpeechRecognitionError) => void): () => void;
}

/** Factory behind `VITE_STT_ENGINE`. Unknown engines fall back to the browser adapter. */
export function createSpeechToTextAdapter(): SpeechToTextAdapter {
  const engine = import.meta.env.VITE_STT_ENGINE ?? "browser";
  if (engine === "google" || engine === "azure") {
    // Cloud engines are declared swap points (docs/architecture/17, doc 10).
    // No cloud SDK is wired yet, so fall back to the browser engine.
    return new BrowserSpeechAdapter();
  }
  return new BrowserSpeechAdapter();
}

/** Minimal typing for the Web Speech API (not in standard lib.dom). */
interface SpeechRecognitionEl {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  start(): void;
  stop(): void;
  abort(): void;
  onstart: (() => void) | null;
  onend: (() => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onresult: ((e: SpeechRecognitionEventEl) => void) | null;
}

interface SpeechRecognitionEventEl {
  resultIndex: number;
  results: {
    length: number;
    [index: number]: {
      isFinal: boolean;
      length: number;
      [index: number]: { transcript: string };
    };
  };
}

type SpeechRecognitionCtor = new () => SpeechRecognitionEl;

/**
 * Browser Web Speech implementation. Keeps the recognition instance in
 * module scope so a long-lived chat page reuses one engine.
 */
export class BrowserSpeechAdapter implements SpeechToTextAdapter {
  private recognition: SpeechRecognitionEl | null = null;
  private statusCbs: ((s: SpeechStatus) => void)[] = [];
  private resultCbs: ((r: SpeechResult) => void)[] = [];
  private errorCbs: ((c: SpeechRecognitionError) => void)[] = [];
  private finalTranscript = "";

  readonly isSupported: boolean;

  constructor() {
    this.isSupported = resolveSpeechRecognition() !== null;
  }

  start(lang: string) {
    if (!this.isSupported) return;
    const Recognition = resolveSpeechRecognition();
    if (!Recognition) return;

    if (!this.recognition) {
      const rec = new Recognition();
      rec.interimResults = true;
      rec.maxAlternatives = 1;

      rec.onstart = () => this.setStatus("listening");
      rec.onend = () => this.setStatus("idle");
      rec.onerror = (e) => {
        this.setStatus("idle");
        this.errorCbs.forEach((cb) => cb(normalizeError(e.error)));
      };
      rec.onresult = (e) => {
        let interim = "";
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const chunk = e.results[i];
          const text = chunk[0]?.transcript ?? "";
          if (chunk.isFinal) {
            this.finalTranscript += text;
            this.resultCbs.forEach((cb) => cb({ transcript: this.finalTranscript, isFinal: true }));
          } else {
            interim += text;
          }
        }
        if (interim) {
          this.resultCbs.forEach((cb) =>
            cb({ transcript: this.finalTranscript + interim, isFinal: false }),
          );
        }
      };
      this.recognition = rec;
    }

    this.finalTranscript = "";
    this.recognition.lang = lang;
    this.setStatus("processing");
    try {
      this.recognition.start();
    } catch {
      // start() while already started throws; treat as already listening.
      this.setStatus("listening");
    }
  }

  stop(): void {
    if (!this.recognition) return;
    this.recognition.stop();
    this.recognition.abort();
    this.setStatus("idle");
  }

  onStatusChange(cb: (s: SpeechStatus) => void): () => void {
    this.statusCbs.push(cb);
    return () => {
      this.statusCbs = this.statusCbs.filter((f) => f !== cb);
    };
  }

  onResult(cb: (r: SpeechResult) => void): () => void {
    this.resultCbs.push(cb);
    return () => {
      this.resultCbs = this.resultCbs.filter((f) => f !== cb);
    };
  }

  onError(cb: (c: SpeechRecognitionError) => void): () => void {
    this.errorCbs.push(cb);
    return () => {
      this.errorCbs = this.errorCbs.filter((f) => f !== cb);
    };
  }

  private setStatus(status: SpeechStatus) {
    this.statusCbs.forEach((cb) => cb(status));
  }
}

function normalizeError(raw: string): SpeechRecognitionError {
  switch (raw) {
    case "not-allowed":
    case "service-not-allowed":
      return "not-allowed";
    case "no-speech":
      return "no-speech";
    case "audio-capture":
      return "audio-capture";
    case "network":
      return "network";
    case "aborted":
      return "aborted";
    default:
      return "other";
  }
}

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionCtor;
    webkitSpeechRecognition?: SpeechRecognitionCtor;
  }
}

function resolveSpeechRecognition(): SpeechRecognitionCtor | null {
  if (typeof window === "undefined") return null;
  return window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null;
}

/** Shared long-lived instance so listeners are registered once. */
export const sttAdapter = createSpeechToTextAdapter();