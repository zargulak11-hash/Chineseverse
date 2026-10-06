import { describe, expect, it } from "vitest";
import { PAGE, libraryPath } from "./storiesQuery.js";

const params = (path) => Object.fromEntries(new URL(path, "http://x").searchParams);

describe("the Stories library request", () => {
  it("asks for one card until the learner's level is known", () => {
    expect(params(libraryPath({ ready: false, level: 1 }))).toEqual({ limit: "1" });
  });

  it("asks for one level, a page at a time", () => {
    expect(params(libraryPath({ ready: true, level: 3 }))).toEqual({ limit: String(PAGE), level: "3" });
    expect(params(libraryPath({ ready: true, level: 3, pages: 3 })).limit).toBe(String(PAGE * 3));
  });

  it("sends only the filters that narrow the list, with the server's names", () => {
    const p = params(libraryPath({ ready: true, level: 2, status: "completed", topic: "food", time: "short", q: "雨" }));
    expect(p).toEqual({ limit: String(PAGE), level: "2", status: "completed", topic: "food", length: "short", q: "雨" });
    const plain = params(libraryPath({ ready: true, level: 2, status: "all", topic: "all", time: "any", q: "" }));
    expect(Object.keys(plain).sort()).toEqual(["level", "limit"]);
  });

  it("encodes search text safely", () => {
    expect(libraryPath({ ready: true, level: 1, q: "a&b=c" })).toContain("q=a%26b%3Dc");
  });
});
