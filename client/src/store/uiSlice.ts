import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Theme = "light" | "dark" | "system";

interface UiState {
  /** Current theme choice. "system" follows the OS. */
  theme: Theme;
  /** Mobile nav drawer visibility. */
  sidebarOpen: boolean;
  setTheme: (theme: Theme) => void;
  toggleSidebar: () => void;
  closeSidebar: () => void;
  openSidebar: () => void;
}

/**
 * Client/UI state (docs/architecture/09). Theme is the only field persisted
 * from this slice; everything else is ephemeral.
 */
export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      theme: "system",
      sidebarOpen: false,
      setTheme: (theme) => set({ theme }),
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      closeSidebar: () => set({ sidebarOpen: false }),
      openSidebar: () => set({ sidebarOpen: true }),
    }),
    {
      name: "scheme-sathi-ui",
      partialize: (s) => ({ theme: s.theme }) as Partial<UiState>,
    },
  ),
);
