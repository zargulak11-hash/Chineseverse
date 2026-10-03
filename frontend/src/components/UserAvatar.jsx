import { useEffect, useState } from "react";

// The one avatar rule for a PERSON (the signed-in user, duel opponents,
// people in Community, notification senders): their uploaded photo, or
// else the initial of their name. Never the companion animal, never a stock
// picture -- the companion is a separate character (AnimalAvatar). The
// backend only sends `url` for a photo that really exists
// (services/avatars.py); if one still fails to load, the initial takes its
// place instead of a broken-image icon.

const segmenter = typeof Intl !== "undefined" && Intl.Segmenter ? new Intl.Segmenter(undefined, { granularity: "grapheme" }) : null;

function graphemes(text) {
  return segmenter ? Array.from(segmenter.segment(text), (s) => s.segment) : Array.from(text);
}

// First letter of the name in any script (Zarina -> Z, Зарина -> З,
// Ҷамшед -> Ҷ, 张伟 -> 张), skipping leading symbols such as "_" or "@";
// a digit if the name has no letter at all.
export function initialOf(name) {
  const chars = graphemes(String(name || "").trim());
  const pick = chars.find((c) => /\p{L}/u.test(c)) || chars.find((c) => /\p{N}/u.test(c));
  return pick ? pick.toLocaleUpperCase() : "?";
}

export default function UserAvatar({ url, name, size = 36, className = "" }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [url]);

  const style = { width: size, height: size };
  if (url && !failed) {
    return (
      <img src={url} alt="" className={`avatar-preview ${className}`} style={style} onError={() => setFailed(true)} />
    );
  }
  return (
    <span
      className={`user-avatar-initial ${className}`}
      style={{ ...style, fontSize: Math.round(size * 0.42) }}
      aria-hidden="true"
    >
      {initialOf(name)}
    </span>
  );
}
