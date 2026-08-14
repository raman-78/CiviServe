import { beforeEach, describe, expect, it } from "vitest";
import { useSettingsStore } from "@/store/settingsSlice";

describe("language persistence", () => {
  beforeEach(() => {
    window.localStorage.clear();
    useSettingsStore.setState({ language: "en" });
  });

  it("persists the chosen language to localStorage", () => {
    useSettingsStore.getState().setLanguage("ta");
    const raw = window.localStorage.getItem("civiserve-settings");
    expect(raw).toBeTruthy();
    const parsed = JSON.parse(raw!) as { state?: { language?: string } };
    expect(parsed.state?.language).toBe("ta");
  });

  it("survives a store rehydration from persisted state", async () => {
    window.localStorage.setItem(
      "civiserve-settings",
      JSON.stringify({ state: { language: "bn" } }),
    );
    await useSettingsStore.persist.rehydrate();
    expect(useSettingsStore.getState().language).toBe("bn");
  });
});

describe("voice settings persistence", () => {
  beforeEach(() => {
    window.localStorage.clear();
    useSettingsStore.setState({
      voiceAssistance: false,
      speechSpeed: "normal",
      repeatConfirmation: true,
      preferredVoice: "",
    });
  });

  it("defaults voice assistance to OFF", () => {
    expect(useSettingsStore.getState().voiceAssistance).toBe(false);
  });

  it("toggles voice assistance and persists it", () => {
    useSettingsStore.getState().setVoiceAssistance(true);
    const raw = window.localStorage.getItem("civiserve-settings");
    const parsed = JSON.parse(raw!) as { state?: { voiceAssistance?: boolean } };
    expect(parsed.state?.voiceAssistance).toBe(true);
  });

  it("stores speech speed, repeat confirmation and preferred voice", () => {
    const { setSpeechSpeed, setRepeatConfirmation, setPreferredVoice } =
      useSettingsStore.getState();
    setSpeechSpeed("slow");
    setRepeatConfirmation(false);
    setPreferredVoice("hi-IN-male");
    const state = useSettingsStore.getState();
    expect(state.speechSpeed).toBe("slow");
    expect(state.repeatConfirmation).toBe(false);
    expect(state.preferredVoice).toBe("hi-IN-male");
  });
});
