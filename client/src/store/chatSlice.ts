import { create } from "zustand";

interface ChatState {
  /** Text currently in the composer. */
  draftInput: string;
  /** Selected conversation id (null = new chat). */
  activeSessionId: string | null;
  /** Assistant "typing" indicator. */
  isAssistantTyping: boolean;
  setDraftInput: (text: string) => void;
  setActiveSessionId: (id: string | null) => void;
  setAssistantTyping: (typing: boolean) => void;
  resetChat: () => void;
}

/**
 * Ephemeral chat UI state (docs/architecture/09). Message history is server
 * state (TanStack Query); only transient UI flags live here.
 */
export const useChatStore = create<ChatState>()((set) => ({
  draftInput: "",
  activeSessionId: null,
  isAssistantTyping: false,
  setDraftInput: (draftInput) => set({ draftInput }),
  setActiveSessionId: (activeSessionId) => set({ activeSessionId }),
  setAssistantTyping: (isAssistantTyping) => set({ isAssistantTyping }),
  resetChat: () =>
    set({ draftInput: "", activeSessionId: null, isAssistantTyping: false }),
}));
