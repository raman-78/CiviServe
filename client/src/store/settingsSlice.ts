import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { LanguageCode, SpeechSpeed } from "@civiserve/shared";

export interface ConsentDraft {
  dataProcessing: boolean;
  voiceProcessing: boolean;
  locationAccess: boolean;
}

interface SettingsState {
  /** Preferred UI language (persisted). */
  language: LanguageCode;
/** Text-only mode: no auto-TTS (docs/architecture/15). */
  textOnly: boolean;
  highContrast: boolean;
  slowSpeech: boolean;
  /**
   * Voice Assistance master (persisted, default OFF). While OFF, CiviServe never
   * offers to read replies aloud and repeat confirmations stay hidden. This is
   * the toggle surfaced by `VoiceToggle` in the header.
   */
  voiceAssistance: boolean;
  /** Preferred read-aloud pace (persisted). */
  speechSpeed: SpeechSpeed;
  /**
   * Ask before reading a reply aloud (default ON). Only reachable while
   * `voiceAssistance` is ON; replies are never read automatically.
   */
  repeatConfirmation: boolean;
  /** Preferred TTS voice id, or "" = automatic match to the UI language. */
  preferredVoice: string;
  notifications: {
    schemeUpdates: boolean;
    eligibilityMatches: boolean;
    renewalReminders: boolean;
  };
  consent: ConsentDraft;
  setLanguage: (language: LanguageCode) => void;
  setTextOnly: (enabled: boolean) => void;
  setHighContrast: (enabled: boolean) => void;
  setSlowSpeech: (enabled: boolean) => void;
  setVoiceAssistance: (enabled: boolean) => void;
  setSpeechSpeed: (speed: SpeechSpeed) => void;
  setRepeatConfirmation: (enabled: boolean) => void;
  setPreferredVoice: (id: string) => void;
  toggleNotification: (key: keyof SettingsState["notifications"]) => void;
  setConsent: (patch: Partial<ConsentDraft>) => void;
}

const defaultLanguage = (import.meta.env.VITE_DEFAULT_LANGUAGE as LanguageCode | undefined) ?? "en";

/**
 * Language / voice / accessibility preferences — the only slice that persists
 * (docs/architecture/09), because it must survive reload.
 */
export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      language: defaultLanguage,
      textOnly: false,
      highContrast: false,
      slowSpeech: false,
      voiceAssistance: false,
      speechSpeed: "normal",
      repeatConfirmation: true,
      preferredVoice: "",
      notifications: {
        schemeUpdates: true,
        eligibilityMatches: true,
        renewalReminders: false,
      },
      consent: {
        dataProcessing: false,
        voiceProcessing: false,
        locationAccess: false,
      },
      setLanguage: (language) => set({ language }),
      setTextOnly: (textOnly) => set({ textOnly }),
      setHighContrast: (highContrast) => set({ highContrast }),
      setSlowSpeech: (slowSpeech) => set({ slowSpeech }),
      setVoiceAssistance: (voiceAssistance) => set({ voiceAssistance }),
      setSpeechSpeed: (speechSpeed) => set({ speechSpeed }),
      setRepeatConfirmation: (repeatConfirmation) => set({ repeatConfirmation }),
      setPreferredVoice: (preferredVoice) => set({ preferredVoice }),
      toggleNotification: (key) =>
        set((s) => ({
          notifications: { ...s.notifications, [key]: !s.notifications[key] },
        })),
      setConsent: (patch) =>
        set((s) => ({ consent: { ...s.consent, ...patch } })),
    }),
    { name: "civiserve-settings" },
  ),
);
