import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base: "./" so the static bundle works on Pages/Vercel subpaths alike.
export default defineConfig({
  plugins: [react()],
  base: "./",
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: true,
    css: true,
  },
});
