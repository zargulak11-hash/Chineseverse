// The Android app visitors download from /download. The APK is not in this
// repository or the website build: it is an asset of a GitHub Release on
// the public repo, served over HTTPS to anyone without signing in. Releasing
// a new build means a new release plus these five values, nothing else --
// docs/MOBILE_APP.md ("Publishing the downloadable APK").
//
// The button links the versioned file, so the version, size and checksum
// shown on the page always describe exactly what is downloaded.
// RELEASES_URL lists every published version.
const REPO = "https://github.com/zargulak11-hash/Chineseverse";

export const ANDROID_APP = {
  version: "1.0",
  fileName: "ChineseVerse-1.0-android.apk",
  url: `${REPO}/releases/download/android-v1.0/ChineseVerse-1.0-android.apk`,
  sizeBytes: 5933442,
  sha256: "1fec6fc9fd177d2d781463fb795b27402c4b18a34fa8d2e71ea95f390e9cc568",
  // minSdkVersion 24 (frontend/android/variables.gradle).
  minAndroid: "7.0",
};

export const RELEASES_URL = `${REPO}/releases`;

// Which device is reading the page, to put its own instructions first.
// iPadOS reports itself as a Mac; a touch screen gives it away.
export function detectPlatform(nav = typeof navigator === "undefined" ? null : navigator) {
  const ua = nav?.userAgent || "";
  if (/Android/i.test(ua)) return "android";
  if (/iPhone|iPad|iPod/i.test(ua) || (/Macintosh/i.test(ua) && (nav?.maxTouchPoints || 0) > 1)) return "ios";
  return "desktop";
}
