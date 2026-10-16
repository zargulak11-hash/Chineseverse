import { SystemBars, SystemBarsStyle } from "@capacitor/core";
import { App as CapApp } from "@capacitor/app";
import { SplashScreen } from "@capacitor/splash-screen";
import { isNativeApp, nativePlatform } from "./platform.js";

// What only the Android / iOS app needs from the page; the website never
// runs any of it (every export returns at once outside the app).

// Called before React renders. The app draws edge to edge (under the status
// bar and the home indicator) and index.css's "Mobile app" section pads the
// shell by env(safe-area-inset-*) -- those insets are only reported with
// viewport-fit=cover, which the website deliberately doesn't set (it would
// push its pages under an iPhone's notch in landscape).
export function initNativeShell() {
  if (!isNativeApp) return;
  const root = document.documentElement;
  root.classList.add("is-native", `is-${nativePlatform}`);
  const viewport = document.querySelector('meta[name="viewport"]');
  if (viewport && !/viewport-fit/.test(viewport.content)) {
    viewport.content = `${viewport.content}, viewport-fit=cover`;
  }

  // Status bar text follows the theme: light text on Ink, dark on Paper.
  // theme.jsx writes data-theme on <html>, so watching it covers the topbar
  // toggle, Settings and the pre-paint script in index.html alike.
  // Android WebViews older than Chromium 140 can't draw under the bars, so
  // Capacitor pads the window and the bars show its fixed Ink background
  // (android/.../values/colors.xml): light text there in both themes, or
  // Paper's dark text would vanish into it (seen on a stock Android 16
  // emulator, which ships WebView 133).
  const chromium = Number((navigator.userAgent.match(/Chrome\/(\d+)/) || [])[1] || 0);
  const paddedBars = nativePlatform === "android" && chromium > 0 && chromium < 140;
  const syncBars = () => {
    const paper = root.getAttribute("data-theme") === "paper" && !paddedBars;
    SystemBars.setStyle({ style: paper ? SystemBarsStyle.Light : SystemBarsStyle.Dark }).catch(() => {});
  };
  syncBars();
  new MutationObserver(syncBars).observe(root, { attributes: true, attributeFilter: ["data-theme"] });

  // Android's back button walks the app's own history the way the browser's
  // Back does; on the first screen it leaves the app instead of doing
  // nothing (Capacitor's default with no listener is to exit at once, even
  // three pages deep in a lesson).
  CapApp.addListener("backButton", ({ canGoBack }) => {
    if (canGoBack) window.history.back();
    else CapApp.exitApp();
  });
}

// Called once the first screen has rendered, so the splash hands over to
// real content rather than to a blank page. capacitor.config.json also
// auto-hides it after a few seconds, so a start-up crash can't leave the
// learner staring at the logo forever.
export function hideSplash() {
  if (!isNativeApp) return;
  SplashScreen.hide().catch(() => {});
}
