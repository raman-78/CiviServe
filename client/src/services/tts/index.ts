/**
 * Text-to-Speech adapter (docs/architecture/17 swap point).
 *
 * Feature code depends on the `TextToSpeechAdapter` interface only. The concrete
 * browser implementation is swappable via `VITE_TTS_ENGINE` (e.g. Google/Azure
 * cloud TTS without touching chat/scheme/center features).
 */

export interface SpeechVoice {
  name: string;
  /** BCP-47 language tag of the voice, e.g. "hi-IN". */
  lang: string;
  /** Stable identifier the platform gives the voice (browser: voiceURI). */
  id: string;
  default?: boolean;
}

export type SpeechStatus =
  | "idle"
  | "speaking"
  | "paused";

export interface TextToSpeechAdapter {
  readonly isSupported: boolean;
  /** All voices the engine can currently offer, filtered + deduped. */
  getVoices(): SpeechVoice[];
  /**
   * Speak text aloud. A previous utterance on this adapter is cancelled first,
   * so only one voice plays at a time (docs: single-speaker-at-a-time).
   */
  speak(text: string, lang: string, opts?: { rate?: number; voiceId?: string }): void;
  stop(): void;
  /** True while something is being spoken. */
  isSpeaking(): boolean;
  onStatusChange(cb: (status: SpeechStatus) => void): () => void;
  /** Subscribe to voice-list availability changes (browser loads voices async). */
  onVoicesChanged(cb: () => void): () => void;
}

/** Factory behind `VITE_TTS_ENGINE`. Unknown engines fall back to the browser adapter. */
export function createTextToSpeechAdapter(): TextToSpeechAdapter {
  const engine = import.meta.env.VITE_TTS_ENGINE ?? "browser";
  if (engine === "google" || engine === "azure") {
    // Declared swap point (docs/architecture/17); no cloud SDK wired yet.
    return new BrowserSynthesisAdapter();
  }
  return new BrowserSynthesisAdapter();
}

/**
 * Browser `speechSynthesis` implementation. A single shared instance enforces
 * one-at-a-time playback across every speaker button in the app.
 */
export class BrowserSynthesisAdapter implements TextToSpeechAdapter {
  private voiceCache: SpeechVoice[] = [];
  private statusCbs: ((s: SpeechStatus) => void)[] = [];
  private voiceCbs: (() => void)[] = [];

  readonly isSupported: boolean;

  constructor() {
    this.isSupported =
      typeof window !== "undefined" &&
      typeof window.speechSynthesis !== "undefined";
    if (this.isSupported) {
      window.speechSynthesis.onvoiceschanged = () => {
        this.refreshVoices();
        this.voiceCbs.forEach((cb) => cb());
      };
      this.refreshVoices();
    }
  }

  getVoices(): SpeechVoice[] {
    if (!this.isSupported) return [];
    if (this.voiceCache.length === 0) this.refreshVoices();
    return this.voiceCache;
  }

  speak(
    text: string,
    lang: string,
    opts: { rate?: number; voiceId?: string } = {},
  ): void {
    if (!this.isSupported || !text.trim()) return;
    this.stop();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = pickVoice(lang, this.getVoices(), opts.voiceId)?.lang ?? lang;
    utterance.rate = opts.rate ?? 1;
    const voice = pickVoice(lang, this.getVoices(), opts.voiceId);
    if (voice) utterance.voice = voice as unknown as SpeechSynthesisVoice;

    utterance.onstart = () => this.setStatus("speaking");
    utterance.onend = () => {
      this.setStatus("idle");
    };
    utterance.onerror = () => {
      this.setStatus("idle");
    };
    utterance.onpause = () => this.setStatus("paused");
    utterance.onresume = () => this.setStatus("speaking");

    window.speechSynthesis.speak(utterance);
    this.setStatus("speaking");
  }

  stop(): void {
    if (!this.isSupported) return;
    window.speechSynthesis.cancel();
    this.setStatus("idle");
  }

  isSpeaking(): boolean {
    return this.status === "speaking";
  }

  onStatusChange(cb: (s: SpeechStatus) => void): () => void {
    this.statusCbs.push(cb);
    return () => {
      this.statusCbs = this.statusCbs.filter((f) => f !== cb);
    };
  }

  onVoicesChanged(cb: () => void): () => void {
    this.voiceCbs.push(cb);
    return () => {
      this.voiceCbs = this.voiceCbs.filter((f) => f !== cb);
    };
  }

  private status: SpeechStatus = "idle";

  private refreshVoices() {
    if (!this.isSupported) return;
    const seen = new Set<string>();
    const voices: SpeechVoice[] = [];
    for (const v of window.speechSynthesis.getVoices()) {
      if (seen.has(v.voiceURI)) continue;
      seen.add(v.voiceURI);
      voices.push({
        name: v.name,
        lang: v.lang,
        id: v.voiceURI,
        default: v.default,
      });
    }
    this.voiceCache = voices;
  }

  private setStatus(status: SpeechStatus) {
    this.status = status;
    this.statusCbs.forEach((cb) => cb(status));
  }
}

/**
 * Pick the most suitable voice for a target locale. Prefers an exact BCP-47
 * match (`hi-IN`) at the moment the voice list is queried, else the language
 * subtag, else the explicitly chosen voiceId, else null (browser default).
 */
function pickVoice(
  lang: string,
  voices: SpeechVoice[],
  voiceId?: string,
): SpeechVoice | undefined {
  const requested = voiceId ? voices.find((v) => v.id === voiceId) : undefined;
  if (requested) return requested;

  const langSubt = lang.split("-")[0];
  return (
    voices.find((v) => v.lang.toLowerCase() === lang.toLowerCase()) ??
    voices.find((v) => v.lang.toLowerCase().startsWith(`${langSubt.toLowerCase()}-`)) ??
    voices.find((v) => v.lang.toLowerCase() === langSubt.toLowerCase()) ??
    undefined
  );
}

/** Shared single-instance used across the app so one voice plays at a time. */
export const ttsAdapter = createTextToSpeechAdapter();