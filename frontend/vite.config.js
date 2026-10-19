import { readFileSync, rmSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { INDEXED_PAGES, APP_SHELL, renderHead } from "./src/seo.js";

// Writes one HTML file per public page, each with its own title,
// description, canonical address and share tags, plus the noindex app shell
// for everything else (src/seo.js explains why; nginx.conf decides which URL
// gets which file). The files differ only in <head>: the same bundle boots
// in all of them. The phone app (--mode mobile) loads index.html from the
// device and is never crawled, so it is left as built.
function seoPages(mode) {
  let outDir;
  return {
    name: "chineseverse-seo-pages",
    apply: "build",
    configResolved(config) {
      outDir = resolve(config.root, config.build.outDir);
    },
    closeBundle() {
      if (mode === "mobile") {
        // The phone app never shows the landing page (App.jsx sends "/" to
        // sign-in), so the landing video tour (public/media/, ~15 MB) stays
        // out of the APK/IPA. The website build keeps it.
        rmSync(resolve(outDir, "media"), { recursive: true, force: true });
        return;
      }
      const built = readFileSync(resolve(outDir, "index.html"), "utf8");
      const TITLE = /<title>[^<]*<\/title>/;
      if (!TITLE.test(built)) throw new Error("index.html has no <title> to replace with the SEO head");
      const write = (file, path) =>
        writeFileSync(resolve(outDir, file), built.replace(TITLE, () => renderHead(path)));
      // index.html last: every other file is made from the built original.
      for (const [path, page] of Object.entries(INDEXED_PAGES)) if (page.file !== "index.html") write(page.file, path);
      write(APP_SHELL.file, null);
      write(INDEXED_PAGES["/"].file, "/");
    },
  };
}

export default defineConfig(({ mode }) => ({
  plugins: [react(), seoPages(mode)],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      // Uploaded profile pictures (see backend app/main.py's /static mount).
      "/static": {
        target: process.env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
}));
