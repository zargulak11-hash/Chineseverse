export function Bar({ value, max = 100, alt = false }) {
  const width = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className={`bar${alt ? " alt" : ""}`}>
      <div style={{ width: `${width}%` }} />
    </div>
  );
}

export function Ring({ value, max = 100 }) {
  const p = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className="ring" style={{ "--p": p }}>
      <div>{Math.round(value)}</div>
    </div>
  );
}

// The app's signature number — used once per page, at hero scale, with a
// slowly rotating gradient stroke and a drifting glow. Not the same
// component as the small inline Ring above; this one is meant to anchor
// a whole panel.
export function RingHero({ value, max = 100, label = "overall" }) {
  const p = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className="ring-hero" style={{ "--p": p }}>
      <div className="ring-track" />
      <div className="ring-face">
        <div>
          <div className="ring-value">{value.toFixed(1)}</div>
          <div className="ring-label center">{label}</div>
        </div>
      </div>
    </div>
  );
}

export function Badge({ children, tone = "" }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

export function Stat({ label, value, tone }) {
  return (
    <div className="scorecard">
      <div className="num" style={{ color: tone || "var(--text)" }}>
        {value}
      </div>
      <div className="lbl">{label}</div>
    </div>
  );
}

export function Empty({ children }) {
  return <div className="empty">{children}</div>;
}

export function Loading({ children = "Loading…" }) {
  return (
    <div className="loading">
      <div className="spinner" />
      <p className="sub">{children}</p>
    </div>
  );
}

export function Puff({ show, children }) {
  return show && <div className="modal">{children}</div>;
}