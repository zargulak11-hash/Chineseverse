import { animate, cleanInlineStyles } from "animejs";
import { prefersReducedMotion } from "./anime.js";

// Satisfying press/hover feedback for every button-like element in the app,
// via one delegated listener pair instead of converting every <button
// className="btn..."> call site individually. Real spring-physics release
// (a slight overshoot past 1, settling back) instead of a CSS ease-out.
const PRESSABLE = ".btn, .option, .quick-action, .theme-toggle, .sidebar-collapse-btn, .sidebar-logout-btn, .notif-btn, .mobile-menu-btn";
const GLOW = "0 0 0 rgba(201, 151, 74, 0)";
const GLOW_LIT = "0 0 18px -2px rgba(201, 151, 74, 0.65)";

let attached = false;

export function initButtonFX() {
  if (attached || typeof document === "undefined" || prefersReducedMotion()) return;
  attached = true;

  function press(e) {
    const el = e.target.closest?.(PRESSABLE);
    if (!el || el.disabled) return;
    animate(el, { scale: 0.94, duration: 110, ease: "outQuad" });
  }

  function release(e) {
    const el = e.target.closest?.(PRESSABLE);
    if (!el) return;
    animate(el, {
      scale: [0.94, 1.045, 1],
      boxShadow: [GLOW_LIT, GLOW],
      duration: 460,
      ease: "outElastic(1, .65)",
      onComplete: () => cleanInlineStyles(el),
    });
  }

  document.addEventListener("pointerdown", press);
  document.addEventListener("pointerup", release);
  document.addEventListener("pointercancel", release);
}
