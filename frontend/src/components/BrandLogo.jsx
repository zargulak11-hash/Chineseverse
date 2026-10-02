import logoUrl from "../../photo/Chineseverse logo 🎀❤️✨.png";

// The real ChineseVerse logo, imported straight from frontend/photo/ so
// Vite fingerprints and emits it — no copy to keep in sync, and the file
// itself is never re-encoded, recoloured or redrawn.
//
// Two variants, both cut from this one asset:
//   "lockup" — the full horizontal lockup (pagoda-and-book emblem +
//     "ChineseVerse" wordmark), the default wherever there is room for it.
//   "mark"   — the emblem alone, cropped out of the same 1753x591 PNG for
//     the collapsed sidebar. Keeping it a crop means the sidebar mark can
//     never drift out of sync with the full logo.
//
// The PNG is fully opaque on a near-white (#fefefe) ground, so unlike the
// previous transparent logo it can't be recoloured per theme with filters —
// that would turn the whole canvas into a solid block. Instead the theme
// only changes how that white ground meets the page (see .brand-logo in
// index.css): blended away on Paper, a rounded white tile on Ink.
//
// Sizing lives entirely in CSS (.brand-logo* in index.css) so the image
// is always driven by a single dimension with the other left to `auto` —
// the browser preserves the intrinsic 1753:591 ratio, so the logo can't be
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
