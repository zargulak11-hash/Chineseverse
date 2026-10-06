import Art, { bookArt } from "./Art.jsx";

// A book's cover in the Chinese Stories library: a painting of the story
// (components/Art.jsx bookArt -- its own motif, or the place it happens in),
// the Chinese title under it and the HSK level as a seal, on a bound cover
// with a spine. A book a content author adds without its own painting
// still gets one, from its topic.
export default function BookCover({ slug, topic, titleZh, level, size = "md" }) {
  return (
    <div className={`book-cover book-cover-${size}`} aria-hidden="true">
      <Art name={bookArt(slug, topic)} size={size === "lg" ? 112 : 80} flat className="book-cover-art" />
      <span className="book-cover-title" lang="zh-CN">{titleZh}</span>
      <span className="book-cover-seal">HSK {level}</span>
    </div>
  );
}
