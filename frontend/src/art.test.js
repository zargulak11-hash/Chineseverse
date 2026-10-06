import fs from "node:fs";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import Art, { bookArt, caseArt, netArt, placeArt, pronArt, sceneArt, soundArt } from "./components/Art.jsx";
import { BOOK_ART } from "./components/art/books.jsx";
import { CASE_ART, FILE_ART, NET_ART, PRON_ART } from "./components/art/objects.jsx";
import { PLACE_ART } from "./components/art/places.jsx";

// The world's content lives in the backend; read its keys from the source so
// a place, scene or lesson added there without artwork fails here instead of
// quietly showing the generic fallback.
const src = (path) => fs.readFileSync(new URL(`../../backend/app/services/${path}`, import.meta.url), "utf8");
const BOOKS_DIR = new URL("../../backend/app/seed_content/books/", import.meta.url);
const BOOKS = fs.readdirSync(BOOKS_DIR).flatMap((lv) => fs.readdirSync(new URL(`${lv}/`, BOOKS_DIR))
  .map((f) => JSON.parse(fs.readFileSync(new URL(`${lv}/${f}`, BOOKS_DIR), "utf8"))));
const all = (text, re) => [...text.matchAll(re)].map((m) => m[1]);

const PLACES = all(src("world_places.py"), /^\s+P\("([a-z_]+)"/gm);
const SCENES = all(src("real_life_content.py"), /"slug": "([a-z-]+)"/g);
const SOUNDS = all(src("sound_world.py"), /^\s+"([a-z_]+)": \{"icon"/gm);
const LESSONS = all(src("pronunciation.py"), /\{"key": "([a-z_]+)", "icon"/g);
const NET_KINDS = all(src("internet_content.py"), /"kind": "([a-z]+)"/g);
const NET_SLUGS = all(src("internet_content.py"), /"slug": "([a-z-]+)", "kind"/g);
const CASES = all(src("detective.py").match(/^ICONS = \{.*\}$/m)[0], /"([a-z_]+)":/g);

const family = (name) => ({ book: BOOK_ART, place: PLACE_ART, net: NET_ART, case: CASE_ART, file: FILE_ART, pron: PRON_ART })[name.split(".")[0]];
const drawn = (name) => Boolean(family(name)[name.slice(name.indexOf(".") + 1)]);

describe("the world's illustrations", () => {
  it("paints every one of the places on the map", () => {
    expect(PLACES.length).toBe(40);
    expect(PLACES.filter((k) => !drawn(placeArt(k)))).toEqual([]);
  });

  it("shows each Real Chinese scene and Sound World place at a painted place", () => {
    expect(SCENES.length).toBeGreaterThan(0);
    expect(SCENES.filter((s) => !drawn(sceneArt(s)))).toEqual([]);
    expect(SOUNDS.length).toBeGreaterThan(0);
    expect(SOUNDS.filter((e) => !drawn(soundArt(e)))).toEqual([]);
  });

  it("paints every Internet page kind, case type and pronunciation lesson", () => {
    expect(NET_KINDS.filter((k) => !drawn(netArt(k)))).toEqual([]);
    expect(NET_SLUGS.filter((s) => !drawn(netArt(s)))).toEqual([]);
    expect(CASES.filter((k) => !drawn(caseArt(k)))).toEqual([]);
    expect(LESSONS.filter((k) => !drawn(pronArt(k)))).toEqual([]);
  });

  it("gives every book in the Stories library a cover painting of its own story", () => {
    expect(BOOKS.length).toBeGreaterThan(100);
    // A book missing here falls back to its topic; add it to BOOK_COVER in components/Art.jsx.
    expect(BOOKS.filter((b) => bookArt(b.slug, "") === "book.reading").map((b) => b.slug)).toEqual([]);
    expect(BOOKS.filter((b) => !drawn(bookArt(b.slug, b.topic))).map((b) => b.slug)).toEqual([]);
  });

  it("has a cover for every story topic, for books without their own yet", () => {
    const topics = [...new Set(BOOKS.map((b) => b.topic))];
    expect(topics.filter((tp) => bookArt("not-a-book", tp) === "book.reading")).toEqual([]);
    expect(topics.filter((tp) => !drawn(bookArt("not-a-book", tp)))).toEqual([]);
  });

  it("sends a played case file to its own painting", () => {
    expect(caseArt("file:the-forged-letter")).toBe("file.the-forged-letter");
    expect(caseArt("who_took")).toBe("case.who_took");
  });

  it("renders every painting, and an unknown key as its family's fallback, never an emoji", () => {
    const names = [
      ...Object.keys(PLACE_ART).map((k) => `place.${k}`), ...Object.keys(NET_ART).map((k) => `net.${k}`),
      ...Object.keys(CASE_ART).map((k) => `case.${k}`), ...Object.keys(FILE_ART).map((k) => `file.${k}`),
      ...Object.keys(PRON_ART).map((k) => `pron.${k}`), ...Object.keys(BOOK_ART).map((k) => `book.${k}`),
      "book.unknown", "place.not_built_yet", "net.unknown", "case.unknown", "file.unknown", "pron.unknown",
    ];
    for (const name of names) {
      const html = renderToStaticMarkup(createElement(Art, { name, size: 48 }));
      expect(html).toMatch(/^<svg[^>]*class="cv-art is-tile"/);
      expect(html).not.toMatch(/\p{Extended_Pictographic}/u);
    }
  });
});
