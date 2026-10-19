import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { APP_SHELL, INDEXED_PAGES, SITE_URL, canonicalUrl, pageTitle, renderHead } from "./seo.js";

const read = (rel) => readFileSync(new URL(rel, import.meta.url), "utf8");
const appJsx = read("./App.jsx");
const nginx = read("../nginx.conf");
const sitemap = read("../public/sitemap.xml");
const robots = read("../public/robots.txt");

// The noindex app-shell location in nginx.conf, as a JS regex.
const shellLine = nginx.split("\n").find((l) => l.includes("location ~ ^/(?:login|"));
const SHELL_ROUTE = new RegExp(shellLine.trim().replace(/^location ~ /, "").replace(/ \{$/, ""));

// Every route in App.jsx, with its parameters filled in as a visitor's URL.
const ROUTES = [...appJsx.matchAll(/path="([^"]+)"/g)]
  .map((m) => m[1])
  .filter((p) => p !== "*");
const asUrl = (route) => route.replace(/:[A-Za-z]+/g, "x1").replace(/\/\*$/, "/x1");

describe("which pages search engines may index", () => {
  it("serves every app route as either a public page or the noindex app shell", () => {
    expect(ROUTES.length).toBeGreaterThan(40);
    const unmapped = ROUTES.filter((r) => !(r in INDEXED_PAGES) && !SHELL_ROUTE.test(asUrl(r)));
    expect(unmapped).toEqual([]);
  });

  it("never sends a public page to the noindex shell, and gives each its own file", () => {
    for (const [path, page] of Object.entries(INDEXED_PAGES)) {
      expect(ROUTES).toContain(path);
      expect(SHELL_ROUTE.test(path)).toBe(false);
      expect(nginx).toContain(`location = ${path} {\n        try_files /${page.file} =404;`);
    }
  });

  it("keeps the shell noindex both in the page and in the response header", () => {
    expect(nginx).toMatch(/location = \/app\.html \{\s+internal;\s+add_header X-Robots-Tag "noindex" always;/);
    expect(nginx).toContain("error_page 404 /app.html;");
    // The page rules are regex locations; the API and uploads must not fall into them.
    for (const prefix of ["/api/assistant/", "/api/", "/static/"]) {
      expect(nginx).toContain(`location ^~ ${prefix} {`);
    }
    expect(renderHead(null)).toContain('<meta name="robots" content="noindex" />');
    expect(renderHead(null)).not.toContain("canonical");
  });
});

describe("sitemap.xml and robots.txt", () => {
  it("lists exactly the indexable pages, as absolute canonical https URLs", () => {
    expect(sitemap.startsWith('<?xml version="1.0" encoding="UTF-8"?>')).toBe(true);
    expect(sitemap).toContain('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">');
    const locs = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);
    expect(locs).toEqual(Object.keys(INDEXED_PAGES).map(canonicalUrl));
    for (const loc of locs) expect(loc.startsWith(`${SITE_URL}/`)).toBe(true);
    expect(sitemap.match(/<url>/g).length).toBe(sitemap.match(/<\/url>/g).length);
  });

  it("points crawlers at the sitemap without blocking any public page", () => {
    expect(robots).toContain(`Sitemap: ${SITE_URL}/sitemap.xml`);
    const disallowed = [...robots.matchAll(/^Disallow:\s*(\S*)/gm)].map((m) => m[1]);
    expect(disallowed).toEqual(["/api/", "/static/"]);
    for (const path of Object.keys(INDEXED_PAGES)) {
      expect(disallowed.some((d) => path.startsWith(d))).toBe(false);
    }
  });
});

describe("page metadata", () => {
  const pages = Object.entries(INDEXED_PAGES);

  it("gives every public page its own title and description of a sensible length", () => {
    const titles = pages.map(([, p]) => p.title);
    const descriptions = pages.map(([, p]) => p.description);
    expect(new Set(titles).size).toBe(titles.length);
    expect(new Set(descriptions).size).toBe(descriptions.length);
    for (const t of titles) expect(t.length).toBeLessThanOrEqual(60);
    for (const d of descriptions) {
      expect(d.length).toBeGreaterThanOrEqual(70);
      expect(d.length).toBeLessThanOrEqual(170);
    }
    for (const t of titles) expect(t).toContain("ChineseVerse");
  });

  it("writes a canonical, share tags and valid JSON-LD into each page head", () => {
    for (const [path, page] of pages) {
      const head = renderHead(path);
      expect(head).toContain(`<link rel="canonical" href="${canonicalUrl(path)}" />`);
      expect(head).toContain(`<meta property="og:url" content="${canonicalUrl(path)}" />`);
      expect(head).not.toContain("noindex");
      const ld = head.match(/<script type="application\/ld\+json">(.*)<\/script>/);
      if (page.jsonLd) {
        const data = JSON.parse(ld[1]);
        expect(data["@context"]).toBe("https://schema.org");
        expect(data.url).toBe(canonicalUrl(path));
      } else {
        expect(ld).toBeNull();
      }
    }
    expect(canonicalUrl("/")).toBe("https://chineseverse.qobus.tj/");
    expect(canonicalUrl("/download")).toBe("https://chineseverse.qobus.tj/download");
  });

  it("serves Google's exact Search Console verification tag on the home page", () => {
    expect(renderHead("/")).toContain(
      '<meta name="google-site-verification" content="7QRYysqWa6gXXBFJiFq4DXTnAtkDlz6dFA102f9vlkI" />'
    );
  });

  it("keeps the tab title in step on client-side navigation", () => {
    expect(pageTitle("/")).toBe(INDEXED_PAGES["/"].title);
    expect(pageTitle("/dashboard")).toBe(APP_SHELL.title);
  });
});
