import { describe, expect, it } from "vitest";
import { SPEECH_LOCALES, SPEECH_RATES } from "@civiserve/shared";
import { BrowserSpeechAdapter, createSpeechToTextAdapter } from "@/services/stt";
import { BrowserSynthesisAdapter, createTextToSpeechAdapter } from "@/services/tts";

describe("speech locale map (shared)", () => {
  it("covers all 13 supported languages with -IN voices", () => {
    const langs = Object.keys(SPEECH_LOCALES).sort();
    expect(langs).toEqual([
      "as", "bn", "en", "gu", "hi", "kn", "ml", "mr", "or", "pa", "ta", "te", "ur",
    ]);
    for (const locale of Object.values(SPEECH_LOCALES)) {
      expect(locale).toMatch(/^[a-z]{2}-IN$/i);
    }
    expect(SPEECH_LOCALES.en).toBe("en-IN");
    expect(SPEECH_LOCALES.hi).toBe("hi-IN");
    expect(SPEECH_LOCALES.ur).toBe("ur-IN");
  });

  it("defines slow/normal/fast rates", () => {
    expect(SPEECH_RATES.slow).toBeLessThan(SPEECH_RATES.normal);
    expect(SPEECH_RATES.normal).toBeLessThan(SPEECH_RATES.fast);
    expect(SPEECH_RATES.normal).toBe(1);
  });
});

describe("STT adapter", () => {
  it("reports unsupported when the Web Speech API is absent (jsdom)", () => {
    expect(new BrowserSpeechAdapter().isSupported).toBe(false);
  });

  it("factory does not throw and returns a browser adapter", () => {
    expect(() => createSpeechToTextAdapter()).not.toThrow();
  });
});

describe("TTS adapter", () => {
  it("exposes no voices and unsupported flag without speechSynthesis (jsdom)", () => {
    const adapter = new BrowserSynthesisAdapter();
    expect(adapter.isSupported).toBe(false);
    expect(adapter.getVoices()).toEqual([]);
    expect(adapter.isSpeaking()).toBe(false);
    expect(() => adapter.speak("hello", "en-IN")).not.toThrow();
    expect(() => adapter.stop()).not.toThrow();
  });

  it("factory does not throw", () => {
    expect(() => createTextToSpeechAdapter()).not.toThrow();
  });
});