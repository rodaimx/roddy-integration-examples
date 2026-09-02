import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Everything under /api is Acme's own backend (server/server.js). The
    // chat itself does NOT go through this proxy — the browser calls Roddy's
    // web-chat host directly with the visitor token.
    proxy: {
      "/api": "http://localhost:8787",
    },
  },
});
