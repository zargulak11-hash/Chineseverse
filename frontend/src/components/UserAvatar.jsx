// The USER's own avatar: their uploaded picture (user.profile.avatar_url),
// otherwise their initial. It deliberately never falls back to the
// companion animal -- the companion is a separate character with its own
// portrait (AnimalAvatar), not a stand-in for the person's profile photo.
export default function UserAvatar({ url, name, size = 36, className = "" }) {
  const style = { width: size, height: size };
  if (url) {
    return <img src={url} alt="" className={`avatar-preview ${className}`} style={style} />;
  }
  const initial = (name || "?").trim().charAt(0).toUpperCase() || "?";
  return (
    <span
      className={`user-avatar-initial ${className}`}
      style={{ ...style, fontSize: Math.round(size * 0.42) }}
      aria-hidden="true"
    >
      {initial}
    </span>
  );
}
