import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import type { InlineConfig } from "vitest";

declare module "vite" {
  interface UserConfig {
    test?: InlineConfig;
  }
}

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@schemesathi/shared": path.resolve(__dirname, "../shared/src/index.ts"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        configure(proxy) {
          // Dev-only demo bridge: when VITE_DEMO_AUTH=true, every proxied API
          // call acts as the demo user via the server's DEV_BYPASS_AUTH header
          // contract (see server/app/core/security.py). Never applied in build.
          if (process.env.VITE_DEMO_AUTH === "true") {
            proxy.on("proxyReq", (proxyReq) => {
              proxyReq.setHeader("X-Dev-User-Id", process.env.VITE_DEMO_USER_ID ?? "demo-citizen");
              proxyReq.setHeader(
                "X-Dev-User-Role",
                process.env.VITE_DEMO_USER_ROLE ?? "admin",
              );
            });
          }
        },
      },
    },
  },
  build: {
    sourcemap: false,
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) {
            if (id.includes("/src/i18n/resources/")) return "i18n-resources";
            return undefined;
          }
          if (/[\\/]node_modules[\\/](leaflet|react-leaflet)/.test(id)) return "maps";
          if (/[\\/]node_modules[\\/]tesseract/.test(id)) return "speech";
          if (/[\\/]node_modules[\\/](react|react-dom|react-router)([\\/]|$)/.test(id)) return "react";
          if (/[\\/]node_modules[\\/]@tanstack/.test(id)) return "query";
          if (/[\\/]node_modules[\\/](i18next|react-i18next)([\\/]|$)/.test(id)) return "i18n";
          if (/[\\/]node_modules[\\/]lucide-react/.test(id)) return "icons";
          if (/[\\/]node_modules[\\/](sonner|zod|react-hook-form|date-fns)([\\/]|$)/.test(id)) {
            return "ui-vendor";
          }
          return undefined;
        },
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: true,
  },
});
