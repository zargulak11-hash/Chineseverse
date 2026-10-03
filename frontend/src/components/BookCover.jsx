// A book's cover in the Chinese Stories library: its icon, its Chinese
// title set like a book spine, and the HSK level as a seal. No artwork
// files -- the same cover renders for any book a content author adds.
export default function BookCover({ icon, titleZh, level, size = "md" }) {
  return (
    <div className={`book-cover book-cover-${size}`} aria-hidden="true">
      <span className="book-cover-icon">{icon}</span>
      <span className="book-cover-title" lang="zh-CN">{titleZh}</span>
      <span className="book-cover-seal">HSK {level}</span>
    </div>
  );
}
