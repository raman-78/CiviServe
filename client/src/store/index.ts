/**
 * Combined client state (docs/architecture/09).
 * Two stores, no more: TanStack Query for server state, Zustand for UI state.
 */
export { useChatStore } from "./chatSlice";
export { useSettingsStore } from "./settingsSlice";
export { useUiStore, type Theme } from "./uiSlice";
