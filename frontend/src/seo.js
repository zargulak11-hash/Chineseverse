// What search engines see before any JavaScript runs.
//
// The site is a single-page app: nginx used to answer EVERY path -- private
// pages, /robots.txt, /sitemap.xml, a typo -- with the same index.html and a
// 200, which carried no description, no canonical address and the bare title
// "ChineseVerse". Google treated the typos as copies of the home page (soft
// 404s) and had no sitemap to start from.
//
// Only two pages are public and worth a search result: the landing page and
// the Android download page. Everything else is behind sign-in (learning
// progress, profiles, admin) or a sign-in form, and is served as "app.html",
// marked noindex. vite.config.js writes the three HTML files from this
// module at build time; nginx.conf maps the URLs onto them;
// public/sitemap.xml lists exactly INDEXED_PAGES; seo.test.js keeps all of
// them in step with the routes in App.jsx.
//
// The language a visitor sees is chosen in the browser (i18n.js:
// localStorage, then the browser's language) and every language shares one
// URL, so there are no per-language addresses to announce with hreflang. The
// HTML a crawler receives is the English default.
//
// Keep every claim here checkable in the product itself: no user counts,
// ratings or awards.

export const SITE_URL = "https://chineseverse.qobus.tj";
export const SITE_NAME = "ChineseVerse";

// The square emblem already shipped as the app icon (public/icon-512.png).
const SHARE_IMAGE = { url: `${SITE_URL}/icon-512.png`, width: 512, height: 512 };

const HOME_DESCRIPTION =
  "ChineseVerse is a free Mandarin Chinese course online: lessons, Hanzi, grammar, " +
  "graded stories and speaking practice, from your first tones to HSK 9.";

// path -> the HTML file nginx serves for it, and its search-result text.
export const INDEXED_PAGES = {
  "/": {
    file: "index.html",
    title: "ChineseVerse — Learn Chinese Online, HSK 1 to 9",
    description: HOME_DESCRIPTION,
    // Google Search Console ownership check: Google looks for this exact tag
    // in the home page's HTML. Removing it un-verifies the property.
    googleSiteVerification: "7QRYysqWa6gXXBFJiFq4DXTnAtkDlz6dFA102f9vlkI",
    // Names the site in search results ("ChineseVerse" rather than the
    // domain) and tells Google the spaced spelling is the same site.
    jsonLd: {
      "@context": "https://schema.org",
      "@type": "WebSite",
      "@id": `${SITE_URL}/#website`,
      name: SITE_NAME,
      alternateName: ["Chinese Verse"],
      url: `${SITE_URL}/`,
      inLanguage: ["en", "ru", "tg", "zh"],
    },
  },
  "/download": {
    file: "download.html",
    title: "ChineseVerse App for Android — Download",
    description:
      "Download the ChineseVerse app for Android and learn Chinese on your phone: the same " +
      "account, lessons, reviews and progress as the website, with install steps.",
  },
};

// Sign-in forms, private pages and unknown addresses (404).
export const APP_SHELL = {
  file: "app.html",
  title: SITE_NAME,
  description: HOME_DESCRIPTION,
};

// The browser tab title as the visitor moves around the app without a
// reload: the public pages keep their own, everything else is the name.
export function pageTitle(pathname) {
  return INDEXED_PAGES[pathname]?.title ?? SITE_NAME;
}

export function canonicalUrl(path) {
  return path === "/" ? `${SITE_URL}/` : `${SITE_URL}${path}`;
}

function attr(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// The <head> tags for one served file. `path` is null for the app shell:
// no canonical (it answers many addresses) and noindex, so a private page
// or a typo never becomes a search result. The share tags stay, so a link
// to any page still previews as ChineseVerse in a messenger.
export function renderHead(path) {
  const page = path === null ? APP_SHELL : INDEXED_PAGES[path];
  if (!page) throw new Error(`No SEO entry for ${path}`);
  const tags = [
    `<title>${attr(page.title)}</title>`,
    `<meta name="description" content="${attr(page.description)}" />`,
  ];
  if (path === null) {
    tags.push(`<meta name="robots" content="noindex" />`);
  } else {
    tags.push(`<link rel="canonical" href="${attr(canonicalUrl(path))}" />`);
  }
  if (page.googleSiteVerification) {
    tags.push(`<meta name="google-site-verification" content="${attr(page.googleSiteVerification)}" />`);
  }
  tags.push(
    `<meta property="og:site_name" content="${SITE_NAME}" />`,
    `<meta property="og:type" content="website" />`,
    `<meta property="og:title" content="${attr(page.title)}" />`,
    `<meta property="og:description" content="${attr(page.description)}" />`
  );
  if (path !== null) tags.push(`<meta property="og:url" content="${attr(canonicalUrl(path))}" />`);
  tags.push(
    `<meta property="og:image" content="${SHARE_IMAGE.url}" />`,
    `<meta property="og:image:width" content="${SHARE_IMAGE.width}" />`,
    `<meta property="og:image:height" content="${SHARE_IMAGE.height}" />`,
    `<meta property="og:image:alt" content="${SITE_NAME}" />`,
    `<meta name="twitter:card" content="summary" />`
  );
  if (page.jsonLd) {
    // "<" escaped so the JSON can never close the <script> early.
    const json = JSON.stringify(page.jsonLd).replace(/</g, "\\u003c");
    tags.push(`<script type="application/ld+json">${json}</script>`);
  }
  return tags.join("\n    ");
}
