import { defineConfig } from "vitest/config";

// Unit tests for the browser-side logic that every page relies on (the HTTP
// client, error translation). Kept apart from vite.config.js so the
// production build is untouched; plain Node is enough for these modules.
export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.js"],
    setupFiles: ["./src/test/setup.js"],
  },
});
