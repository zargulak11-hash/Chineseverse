import { afterEach, describe, expect, it, vi } from "vitest";

// platform.js decides its API origin once, at import, from Capacitor; each
// case re-imports it (and api.js) under the platform it pretends to be.
async function loadAs(platform) {
  vi.resetModules();
  vi.doMock("@capacitor/core", () => ({
    Capacitor: {
      isNativePlatform: () => platform !== "web",
      getPlatform: () => platform,
    },
  }));
  return {
    platform: await import("./platform.js"),
    api: await import("./api.js"),
  };
}

afterEach(() => {
  vi.doUnmock("@capacitor/core");
  vi.resetModules();
});

function respond(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

describe("on the website", () => {
  it("keeps same-origin /api and leaves avatar paths alone", async () => {
    const { platform, api } = await loadAs("web");
    expect(platform.isNativeApp).toBe(false);
    expect(platform.assetUrl("/static/uploads/a.png")).toBe("/static/uploads/a.png");
    fetch.mockResolvedValue(respond(200, {}));
    await api.api.get("/me");
    expect(fetch.mock.calls.at(-1)[0]).toBe("/api/me");
  });
});

describe.each(["android", "ios"])("in the %s app", (os) => {
  it("calls the production API by its full address", async () => {
    const { platform, api } = await loadAs(os);
    expect(platform.isNativeApp).toBe(true);
    expect(platform.API_ORIGIN).toBe("https://chineseverse.qobus.tj");
    fetch.mockResolvedValue(respond(200, {}));
    await api.api.get("/me");
    expect(fetch.mock.calls.at(-1)[0]).toBe("https://chineseverse.qobus.tj/api/me");
    expect(api.githubStartUrl("login")).toBe("https://chineseverse.qobus.tj/api/auth/github/start?page=login");
  });

  it("resolves server-relative avatars against the API, and nothing else", async () => {
    const { platform } = await loadAs(os);
    expect(platform.assetUrl("/static/uploads/a.png")).toBe("https://chineseverse.qobus.tj/static/uploads/a.png");
    expect(platform.assetUrl("https://cdn.example/a.png")).toBe("https://cdn.example/a.png");
    expect(platform.assetUrl("//cdn.example/a.png")).toBe("//cdn.example/a.png");
    expect(platform.assetUrl("data:image/png;base64,AAAA")).toBe("data:image/png;base64,AAAA");
    expect(platform.assetUrl(null)).toBe(null);
  });
});
