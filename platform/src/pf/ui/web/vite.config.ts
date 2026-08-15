import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Built output lands in `../static/dist`, which the FastAPI app mounts. One
// server, one port, one thing to start: the API and the page it serves are the
// same process, so there is no CORS story and no second runtime to deploy.
//
// `npm run dev` still works for UI iteration — it proxies /api to the running
// `pf ui`, so the dev server never needs its own copy of the data.
export default defineConfig({
  plugins: [react()],
  base: "/app/",
  build: {
    outDir: "../static/dist",
    emptyOutDir: true,
    sourcemap: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:8787", changeOrigin: true },
    },
  },
});
