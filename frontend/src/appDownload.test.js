import { describe, expect, it } from "vitest";
import { ANDROID_APP, detectPlatform } from "./appDownload.js";

const UA = {
  android: "Mozilla/5.0 (Linux; Android 16; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Mobile Safari/537.36",
  iphone: "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
  ipadAsMac: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
  windows: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0",
};

describe("detectPlatform", () => {
  it("puts the download first on Android", () => {
    expect(detectPlatform({ userAgent: UA.android })).toBe("android");
  });

  it("recognises iPhones, and iPads that report themselves as a Mac", () => {
    expect(detectPlatform({ userAgent: UA.iphone })).toBe("ios");
    expect(detectPlatform({ userAgent: UA.ipadAsMac, maxTouchPoints: 5 })).toBe("ios");
  });

  it("treats computers (a Mac without touch included) as desktop", () => {
    expect(detectPlatform({ userAgent: UA.windows })).toBe("desktop");
    expect(detectPlatform({ userAgent: UA.ipadAsMac, maxTouchPoints: 0 })).toBe("desktop");
    expect(detectPlatform(null)).toBe("desktop");
  });
});

describe("ANDROID_APP", () => {
  it("links the versioned APK on the public release, never a placeholder", () => {
    expect(ANDROID_APP.url).toMatch(/^https:\/\/github\.com\/[^/]+\/[^/]+\/releases\/download\/android-v[\d.]+\/.+\.apk$/);
    expect(ANDROID_APP.url.endsWith(`/android-v${ANDROID_APP.version}/${ANDROID_APP.fileName}`)).toBe(true);
    expect(ANDROID_APP.sha256).toMatch(/^[0-9a-f]{64}$/);
    expect(ANDROID_APP.sizeBytes).toBeGreaterThan(1_000_000);
  });
});
