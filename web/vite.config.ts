import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  build: { outDir: "dist", emptyOutDir: true },
  server: {
    port: 5173,
    open: true,
    proxy: {
      "/optimize": "http://localhost:8000",
      "/health": "http://localhost:8000"
    }
  }
});
