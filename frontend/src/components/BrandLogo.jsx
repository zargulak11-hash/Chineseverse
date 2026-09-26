import logoUrl from "../../photo/23c6a98a-13b9-46f0-a284-8261be1dd082.png";

// The real ChineseVerse logo, imported straight from frontend/photo/ so
// Vite fingerprints and emits it — no copy to keep in sync, and the file
// itself is never re-encoded or redrawn.
//
// Two variants, both cut from this one asset:
//   "lockup" — the full horizontal lockup (ink seal + "ChineseVerse"
//     wordmark), the default wherever there is room for it.
//   "mark"   — the square seal alone, cropped out of the same 2048x768
//     PNG for the collapsed sidebar. Keeping it a crop means the sidebar
//     mark can never drift out of sync with the full logo.
//
// Sizing lives entirely in CSS (.brand-logo* in index.css) so the image
// is always driven by a single dimension with the other left to `auto` —
// the browser preserves the intrinsic 8:3 ratio, so the mark can't be
// stretched or squashed at any breakpoint.
export default function BrandLogo({ variant = "lockup", className = "", ...rest }) {
  return (
    <span className={`brand-logo brand-logo--${variant}${className ? ` ${className}` : ""}`}>
      <img
        className="brand-logo__img"
        src={logoUrl}
        alt="ChineseVerse"
        draggable="false"
        decoding="async"
        {...rest}
      />
    </span>
  );
}
