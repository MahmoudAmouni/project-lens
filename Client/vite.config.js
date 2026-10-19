import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev proxy: every /api call goes to the FastAPI Server on port 8000.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
