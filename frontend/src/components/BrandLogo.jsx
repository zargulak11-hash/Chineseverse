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
// The lockup renders as two stacked copies of the SAME file, each clipped to
// one half, so the seal and the wordmark can be coloured independently on
// the dark theme (red seal, white wordmark) without touching the artwork.
// A single CSS filter chain cannot do that: it would have to push the
// near-black wordmark up to white and pull the cinnabar seal down to red in
// one pass, and the wordmark ink is itself very slightly blue (#181828), so
// a saturating chain turns the wordmark blue instead of the seal red.
//
// The split sits at 30.64% of the canvas, which is inside the logo's only
// wide blank column run (x 624..631, fully transparent) — so the seam falls
// in empty space and the two halves recompose into the original image
// pixel-for-pixel. On the light theme both copies are unfiltered, which is
// why the light appearance is exactly the untouched photo.
//
// Sizing lives entirely in CSS (.brand-logo* in index.css) so the image
// is always driven by a single dimension with the other left to `auto` —
// the browser preserves the intrinsic 8:3 ratio, so the mark can't be
// stretched or squashed at any breakpoint.
export default function BrandLogo({ variant = "lockup", className = "", ...rest }) {
  return (
    <span className={`brand-logo brand-logo--${variant}${className ? ` ${className}` : ""}`}>
      {variant === "mark" ? (
        <img
          className="brand-logo__img brand-logo__img--seal"
          src={logoUrl}
          alt="ChineseVerse"
          draggable="false"
          decoding="async"
          {...rest}
        />
      ) : (
        <>
          <img
            className="brand-logo__img brand-logo__img--word"
            src={logoUrl}
            alt="ChineseVerse"
            draggable="false"
            decoding="async"
            {...rest}
          />
          <img
            className="brand-logo__img brand-logo__img--seal"
            src={logoUrl}
            alt=""
            aria-hidden="true"
            draggable="false"
            decoding="async"
          />
        </>
      )}
    </span>
  );
}
