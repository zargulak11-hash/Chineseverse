import fs from "node:fs";
import { createInstance } from "i18next";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { I18nextProvider, initReactI18next } from "react-i18next";
import { describe, expect, it } from "vitest";
import PromoVideo, { PROMO_VIDEO } from "./components/PromoVideo.jsx";

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");
const publicFile = (url) => new URL(`../public${url}`, import.meta.url);
const LOCALES = ["en", "ru", "tg", "zh"];
const KEYS = ["videoEyebrow", "videoTitle", "videoText", "videoVoiceNote", "videoDownload"];

async function render(lang) {
  const resources = Object.fromEntries(
    LOCALES.map((l) => [l, { translation: JSON.parse(read(`./locales/${l}.json`)) }]),
  );
  const i18n = createInstance();
  await i18n.use(initReactI18next).init({ lng: lang, fallbackLng: "en", resources });
  return renderToStaticMarkup(createElement(I18nextProvider, { i18n }, createElement(PromoVideo)));
}

describe("the landing page video tour", () => {
  it("ships the video and its poster as static files", () => {
    // In public/, so the production build copies them to dist/media/ and the
    // URL works after deployment (no local or temporary path).
    expect(PROMO_VIDEO.src).toMatch(/^\/media\/[\w.-]+\.mp4$/);
    expect(PROMO_VIDEO.poster).toMatch(/^\/media\/[\w.-]+\.jpg$/);
    const video = fs.readFileSync(publicFile(PROMO_VIDEO.src));
    expect(video.length).toBeGreaterThan(1_000_000);
    // MP4 with its index (moov) before the media data: the browser can start
    // playing and seeking before the whole file has arrived.
    const head = video.subarray(0, 4096).toString("latin1");
    expect(head.slice(4, 8)).toBe("ftyp");
    expect(head.indexOf("moov")).toBeGreaterThan(0);
    expect(fs.statSync(publicFile(PROMO_VIDEO.poster)).size).toBeGreaterThan(1000);
  });

  it("gives the visitor the player's controls, with sound and without autoplay", async () => {
    const html = await render("en");
    expect(html).toContain("<video");
    expect(html).toContain("controls");
    expect(html).toContain('preload="none"');
    expect(html).toContain("playsInline".toLowerCase());
    expect(html).toContain(`poster="${PROMO_VIDEO.poster}"`);
    expect(html).toContain(`<source src="${PROMO_VIDEO.src}" type="video/mp4"/>`);
    // Attributes of the <video> tag itself (the page uses a "muted" CSS class).
    const tag = html.match(/<video[^>]*>/)[0];
    expect(tag).not.toMatch(/\sautoplay/i);
    expect(tag).not.toMatch(/\smuted/i);
  });

  it("is titled in each of the four languages", async () => {
    const titles = {};
    for (const lang of LOCALES) {
      const landing = JSON.parse(read(`./locales/${lang}.json`)).landing;
      for (const key of KEYS) expect(landing[key], `${lang}: landing.${key}`).toBeTruthy();
      const html = await render(lang);
      expect(html).toContain(landing.videoTitle.replace(/&/g, "&amp;"));
      titles[lang] = landing.videoTitle;
    }
    expect(new Set(Object.values(titles)).size).toBe(LOCALES.length);
  });

  it("sits on the landing page, which only the website shows", () => {
    expect(read("./pages/Landing.jsx")).toContain("<PromoVideo />");
    // The phone app opens on sign-in, so its build drops the 15 MB media/.
    expect(read("../vite.config.js")).toMatch(/mode === "mobile"[\s\S]*rmSync\(resolve\(outDir, "media"\)/);
  });

  it("is served by nginx as a static file", () => {
    expect(read("../nginx.conf")).toMatch(/location \^~ \/media\/ \{\s+try_files \$uri =404;/);
  });
});
