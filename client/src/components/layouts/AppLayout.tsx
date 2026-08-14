import { Suspense, useEffect } from "react";
import { Outlet, ScrollRestoration } from "react-router-dom";
import { Header } from "@/components/shared/Header";
import { Footer } from "@/components/shared/Footer";
import { LoadingState } from "@/components/shared/LoadingState";
import { MobileNav } from "@/components/layouts/MobileNav";
import { stopAllSpeech } from "@/hooks/useSpeaker";

/** Authenticated (or guest) app shell: chrome + routed Outlet (docs/architecture/08). */
export function AppLayout() {
  // Cancel any read-aloud when the route changes so speech never lingers
  // across pages (docs: single-speaker-at-a-time, no auto-TTS lingering).
  useEffect(() => {
    const onPopState = () => stopAllSpeech();
    window.addEventListener("popstate", onPopState);
    return () => {
      window.removeEventListener("popstate", onPopState);
      stopAllSpeech();
    };
  }, []);

  return (
    <div className="flex min-h-dvh flex-col">
      <MobileNav />
      <Header />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
        <Suspense fallback={<LoadingState />}>
          <Outlet />
        </Suspense>
      </main>
      <Footer />
      <ScrollRestoration />
    </div>
  );
}
