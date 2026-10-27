import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

// nginx drops every inherited add_header in a block that sets one of its
// own, so a location with add_header but without the include would send
// none of the security headers (security-headers.conf explains them).
// There is no nginx here to run `nginx -t`; this checks the shape instead,
// and that the report-only CSP really allows what the pages load -- so the
// reports it produces are real ones, and enforcing it later is safe.
// LF line endings, as git stores the files and every Linux build (CI, the
// server's image) serves them: a Windows checkout's CRLF copy of index.html
// hashes differently, and that hash once made it into the CSP by mistake.
const read = (rel) => readFileSync(new URL(rel, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const nginx = read("../nginx.conf");
const snippet = read("../security-headers.conf");
const dockerfile = read("../Dockerfile");
const indexHtml = read("../index.html");
const INCLUDE = "include /etc/nginx/snippets/security-headers.conf;";

// Each `location ... { ... }` block's text (they don't nest here).
function locationBlocks(conf) {
  const blocks = [];
  const re = /^\s*location\b[^{]*\{/gm;
  let m;
  while ((m = re.exec(conf))) {
    let depth = 1;
    let i = m.index + m[0].length;
    while (depth && i < conf.length) {
      if (conf[i] === "{") depth += 1;
      if (conf[i] === "}") depth -= 1;
      i += 1;
    }
    blocks.push(conf.slice(m.index, i));
  }
  return blocks;
}

const code = (text) => text.split("\n").filter((l) => !l.trim().startsWith("#")).join("\n");
const headerLine = (name) => code(snippet).split("\n").find((l) => l.includes(`add_header ${name} `));
const headerValue = (name) => headerLine(name).match(/add_header \S+ "([^"]*)"/)[1];

function cspDirectives() {
  const parts = headerValue("Content-Security-Policy-Report-Only").split(";").map((d) => d.trim()).filter(Boolean);
  const names = parts.map((d) => d.split(/\s+/)[0]);
  return { names, map: Object.fromEntries(parts.map((d) => [d.split(/\s+/)[0], d.split(/\s+/).slice(1)])) };
}

// Whether a CSP source list allows a URL: a host source ("https://x.com")
// any path there, a path ending in "/" that prefix, otherwise that path.
function allows(sources, url) {
  const u = new URL(url);
  return sources.some((s) => {
    if (!/^https:\/\//.test(s)) return false;
    const src = new URL(s);
    if (src.origin !== u.origin) return false;
    if (s === src.origin) return true;
    return s.endsWith("/") ? u.pathname.startsWith(src.pathname) : u.pathname === src.pathname;
  });
}

// The scripts the browser runs from the page's own text (a JSON-LD block is
// data, not run, so CSP does not apply to it).
const inlineScripts = (html) =>
  [...html.matchAll(/<script(?![^>]*\bsrc=)([^>]*)>([\s\S]*?)<\/script>/g)]
    .filter((m) => !/type="application\/ld\+json"/.test(m[1]))
    .map((m) => m[2]);

describe("security headers", () => {
  it("are set for the whole server, before any location", () => {
    const conf = code(nginx);
    const at = conf.indexOf(INCLUDE);
    expect(at).toBeGreaterThan(-1);
    expect(at).toBeLessThan(conf.search(/^\s*location\b/m));
    expect(conf).toContain("server_tokens off;");
  });

  it("are repeated in every location that sets its own add_header", () => {
    const blocks = locationBlocks(code(nginx));
    expect(blocks.length).toBeGreaterThan(5);
    const withHeaders = blocks.filter((b) => b.includes("add_header"));
    expect(withHeaders.length).toBeGreaterThanOrEqual(3);
    for (const block of withHeaders) expect(block, block.split("\n")[0]).toContain(INCLUDE);
  });

  it("reach the 404 page too (it is the app shell, served by its own location)", () => {
    expect(code(nginx)).toContain("error_page 404 /app.html;");
    const shell = locationBlocks(code(nginx)).find((b) => /location = \/app\.html\s*\{/.test(b));
    expect(shell).toContain(INCLUDE);
  });

  it("ship with the image, outside conf.d", () => {
    // conf.d/*.conf is included at the http level as well; the snippet
    // there would be loaded twice over and send every header twice.
    const copy = dockerfile.split("\n").find((l) => l.includes("security-headers.conf"));
    expect(copy).toBe("COPY security-headers.conf /etc/nginx/snippets/security-headers.conf");
    expect(dockerfile).toMatch(/^FROM nginx:1\.30-alpine$/m);
  });

  it("send each header once", () => {
    // Each security header is defined once in the snippet...
    const names = [...code(snippet).matchAll(/^\s*add_header (\S+) /gm)].map((m) => m[1]);
    expect(new Set(names).size).toBe(names.length);
    // ...and no block both uses `expires` (which emits its own
    // Cache-Control) and adds a Cache-Control header of its own.
    for (const block of locationBlocks(code(nginx))) {
      if (/add_header Cache-Control /.test(block)) expect(block, block.trim().split("\n")[0]).not.toMatch(/^\s*expires\s/m);
    }
  });

  it("are syntactically plausible nginx (no `nginx -t` available here)", () => {
    // Not a parser: balanced braces, and every directive line ends in ; { or }.
    for (const [file, text] of [["nginx.conf", nginx], ["security-headers.conf", snippet]]) {
      const body = code(text);
      expect((body.match(/\{/g) || []).length, `${file} braces`).toBe((body.match(/\}/g) || []).length);
      for (const line of body.split("\n").map((l) => l.trim()).filter(Boolean)) {
        expect(/[;{}]$/.test(line), `${file}: ${line}`).toBe(true);
      }
    }
  });

  it("cover the expected protections, all with `always`", () => {
    for (const name of [
      "Strict-Transport-Security",
      "X-Content-Type-Options",
      "X-Frame-Options",
      "Referrer-Policy",
      "Permissions-Policy",
      "Content-Security-Policy-Report-Only",
    ]) {
      const line = headerLine(name);
      expect(line, name).toBeTruthy();
      expect(line.trim().endsWith("always;"), name).toBe(true);
    }
    expect(headerValue("X-Content-Type-Options")).toBe("nosniff");
    expect(headerValue("X-Frame-Options")).toBe("DENY");
    // The microphone stays allowed for the app itself (Tone Coach).
    expect(headerValue("Permissions-Policy")).toContain("microphone=(self)");
  });

  it("pin HTTPS for this host only", () => {
    // qobus.tj's other subdomains are not this app's to decide for.
    const hsts = headerValue("Strict-Transport-Security");
    expect(hsts).toMatch(/^max-age=\d+$/);
    expect(Number(hsts.split("=")[1])).toBeGreaterThanOrEqual(86400);
  });
});

describe("content security policy (report-only)", () => {
  it("stays report-only until it has been checked in a browser", () => {
    expect(code(snippet)).not.toMatch(/add_header Content-Security-Policy "/);
  });

  it("is well formed and keeps its hard limits", () => {
    const { names, map } = cspDirectives();
    expect(new Set(names).size, "no directive twice").toBe(names.length);
    expect(map["default-src"]).toEqual(["'self'"]);
    expect(map["object-src"]).toEqual(["'none'"]);
    expect(map["base-uri"]).toEqual(["'self'"]);
    expect(map["frame-ancestors"]).toEqual(["'none'"]);
    expect(map["script-src"]).not.toContain("'unsafe-inline'");
    expect(map["script-src"]).not.toContain("'unsafe-eval'");
  });

  it("allows every inline script the pages run, by its current hash", () => {
    const { map } = cspDirectives();
    const scripts = inlineScripts(indexHtml);
    expect(scripts.length).toBeGreaterThan(0);
    for (const body of scripts) {
      const hash = `'sha256-${createHash("sha256").update(body, "utf8").digest("base64")}'`;
      expect(map["script-src"], `index.html inline script changed: put ${hash} in security-headers.conf`).toContain(hash);
    }
  });

  it("allows exactly the inline event handlers the pages use, by hash", () => {
    // 'unsafe-hashes' lets a handler run only when its exact text is listed.
    const { map } = cspDirectives();
    const handlers = [...indexHtml.matchAll(/\son[a-z]+\s*=\s*"([^"]*)"/g)].map((m) => m[1]);
    const hashed = map["script-src"].filter((s) => s.startsWith("'sha256-"));
    if (handlers.length) expect(map["script-src"]).toContain("'unsafe-hashes'");
    for (const value of handlers) {
      const hash = `'sha256-${createHash("sha256").update(value, "utf8").digest("base64")}'`;
      expect(map["script-src"], `inline handler ${value} changed: put ${hash} in security-headers.conf`).toContain(hash);
    }
    // No stale hashes: every listed one belongs to an inline script or handler.
    const live = new Set(
      [...inlineScripts(indexHtml), ...handlers].map((b) => `'sha256-${createHash("sha256").update(b, "utf8").digest("base64")}'`),
    );
    for (const h of hashed) expect(live.has(h), `${h} matches nothing in index.html any more`).toBe(true);
  });

  it("allows every outside script and stylesheet index.html loads", () => {
    const { map } = cspDirectives();
    const scripts = [...indexHtml.matchAll(/<script\b[^>]*\bsrc="(https:[^"]+)"/g)].map((m) => m[1]);
    const styles = [...indexHtml.matchAll(/<link\b[^>]*>/g)]
      .map((m) => m[0])
      .filter((tag) => /rel="stylesheet"/.test(tag))
      .map((tag) => tag.match(/href="(https:[^"]+)"/)?.[1])
      .filter(Boolean);
    expect(scripts.length).toBeGreaterThan(0); // Google sign-in
    expect(styles.length).toBeGreaterThan(0); // Google Fonts
    for (const url of scripts) expect(allows(map["script-src"], url), url).toBe(true);
    for (const url of styles) expect(allows(map["style-src"], url), url).toBe(true);
    // The fonts those stylesheets point at.
    if (indexHtml.includes("https://fonts.gstatic.com")) {
      expect(allows(map["font-src"], "https://fonts.gstatic.com/s/manrope/v1/x.woff2")).toBe(true);
    }
  });

  it("lets Google sign-in open its frame and reach its endpoint", () => {
    const { map } = cspDirectives();
    expect(allows(map["frame-src"], "https://accounts.google.com/gsi/iframe/select")).toBe(true);
    expect(allows(map["connect-src"], "https://accounts.google.com/gsi/status")).toBe(true);
    expect(allows(map["style-src"], "https://accounts.google.com/gsi/style")).toBe(true);
  });
});
