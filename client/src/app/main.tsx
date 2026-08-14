import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import "@/i18n";
import { Providers } from "@/app/Providers";
import { RootErrorBoundary } from "@/app/RootErrorBoundary";
import { router } from "@/router";
import "@/styles/globals.css";

const container = document.getElementById("root");

if (!container) {
  throw new Error("Root element #root not found");
}

createRoot(container).render(
  <StrictMode>
    <RootErrorBoundary>
      <Providers>
        <RouterProvider router={router} />
      </Providers>
    </RootErrorBoundary>
  </StrictMode>,
);
