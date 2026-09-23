import { animate, createTimeline, stagger, svg } from "animejs";
import { useEffect, useId, useRef } from "react";
import { prefersReducedMotion } from "../anime.js";

// A plain button — press/hover feedback is now handled app-wide by a single
// delegated Anime.js listener (see buttonFx.js), which matches on the same
// `.btn`/`.option`/`.quick-action` classes every call site here already
// passes in. Kept as a named export so existing call sites don't need to
// change, and so the intent ("this button has motion") stays legible.
export function MotionButton({ className = "", children, ...props }) {
  return (
    <button className={className} {...props}>
      {children}
    </button>
  );
}

const SPARK_COUNT = 16;

// A reusable celebratory moment — level-up, achievement unlock, duel win —
// choreographed as a real Anime.js timeline: backdrop fade, an elastic
// scale-pop of the card, the icon popping in with a little overshoot spin,
// a radiating particle burst, and (when `countTo` is given) the headline
// number counting up rather than just appearing. `show` toggles it; the
// exit is a plain unmount (no fancy reverse sequence) — the entrance is
// where the celebration lives.
export function Celebration({
  show,
  icon = "🎉",
  title,
  subtitle,
  onClose,
  tone = "accent",
  actionLabel = "Nice!",
  countTo,
  countLabel,
}) {
  const backdropRef = useRef(null);
  const cardRef = useRef(null);
  const iconRef = useRef(null);
  const countRef = useRef(null);
  const sparkRefs = useRef([]);
  sparkRefs.current = [];

  useEffect(() => {
    if (!show) return undefined;
    const backdrop = backdropRef.current;
    const card = cardRef.current;
    if (!backdrop || !card) return undefined;

    if (prefersReducedMotion()) {
      backdrop.style.opacity = 1;
      card.style.opacity = 1;
      if (iconRef.current) iconRef.current.style.opacity = 1;
      sparkRefs.current.forEach((el) => {
        el.style.opacity = 0;
      });
      if (countRef.current && countTo != null) countRef.current.textContent = countTo;
      return undefined;
    }

    const tl = createTimeline({ defaults: { ease: "outExpo" } });
    tl.add(backdrop, { opacity: [0, 1], duration: 220 }, 0)
      .add(card, { opacity: [0, 1], scale: [0.55, 1.06, 1], duration: 640, ease: "outElastic(1, .65)" }, 70)
      .add(iconRef.current, { opacity: [0, 1], scale: [0, 1.3, 1], rotate: [-30, 10, 0], duration: 650, ease: "outElastic(1, .55)" }, 160)
      .add(
        sparkRefs.current,
        {
          opacity: [1, 1, 0],
          scale: [0, 1, 0.6],
          translateX: () => (Math.random() - 0.5) * 240,
          translateY: () => (Math.random() - 0.5) * 240 - 20,
          duration: 950,
          delay: stagger(15),
        },
        180
      );

    if (countTo != null && countRef.current) {
      const counter = { value: 0 };
      tl.add(
        counter,
        {
          value: countTo,
          round: 1,
          duration: 900,
          ease: "outCubic",
          onUpdate: () => {
            if (countRef.current) countRef.current.textContent = Math.round(counter.value);
          },
        },
        260
      );
    }

    return () => tl.revert();
  }, [show, countTo]);

  if (!show) return null;

  return (
    <div className="celebration-backdrop" ref={backdropRef} style={{ opacity: 0 }} onClick={onClose}>
      <div
        className={`celebration-card tone-${tone}`}
        ref={cardRef}
        style={{ opacity: 0 }}
        onClick={(e) => e.stopPropagation()}
      >
        {Array.from({ length: SPARK_COUNT }).map((_, i) => (
          <span
            key={i}
            className="celebration-spark"
            ref={(el) => el && sparkRefs.current.push(el)}
            style={{ opacity: 0 }}
          />
        ))}
        <div className="celebration-icon" ref={iconRef} style={{ opacity: 0 }}>
          {icon}
        </div>
        {countTo != null && (
          <div className="celebration-count">
            <span ref={countRef}>0</span>
            {countLabel && <span className="celebration-count-label">{countLabel}</span>}
          </div>
        )}
        <h2 className="h1" style={{ marginTop: 6 }}>{title}</h2>
        {subtitle && <p className="sub" style={{ marginTop: 6 }}>{subtitle}</p>}
        <MotionButton className="btn primary" style={{ marginTop: 16 }} onClick={onClose}>
          {actionLabel}
        </MotionButton>
      </div>
    </div>
  );
}

export function Bar({ value, max = 100, alt = false }) {
  const width = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className={`bar${alt ? " alt" : ""}`}>
      <div style={{ width: `${width}%` }} />
    </div>
  );
}

// A real SVG progress ring: the stroke draws in on load/on value change via
// Anime.js's svg.createDrawable + `draw` property, instead of an instant
// conic-gradient fill — the number counts up in lockstep.
export function Ring({ value, max = 100 }) {
  const p = Math.max(0, Math.min(100, (value / max) * 100));
  const circleRef = useRef(null);
  const valueRef = useRef(null);

  useEffect(() => {
    const circle = circleRef.current;
    if (!circle) return undefined;
    const fraction = p / 100;
    const [drawable] = svg.createDrawable(circle);

    if (prefersReducedMotion()) {
      drawable.draw = `0 ${fraction}`;
      if (valueRef.current) valueRef.current.textContent = Math.round(value);
      return undefined;
    }

    drawable.draw = "0 0";
    const a1 = animate(drawable, { draw: ["0 0", `0 ${fraction}`], duration: 1100, ease: "outCubic" });
    const counter = { v: 0 };
    const a2 = animate(counter, {
      v: value,
      duration: 1100,
      ease: "outCubic",
      onUpdate: () => {
        if (valueRef.current) valueRef.current.textContent = Math.round(counter.v);
      },
    });
    return () => {
      a1.revert();
      a2.revert();
    };
  }, [p, value]);

  return (
    <div className="ring">
      <svg viewBox="0 0 132 132" className="ring-svg">
        <circle cx="66" cy="66" r="58" className="ring-track-bg" />
        <circle ref={circleRef} cx="66" cy="66" r="58" className="ring-track-fg" transform="rotate(-90 66 66)" />
      </svg>
      <div className="ring-center">
        <span ref={valueRef}>0</span>
      </div>
    </div>
  );
}

// The app's signature number — used once per page, at hero scale. A real
// SVG ring (gradient stroke, drawn in on load) replaces the old CSS
// conic-gradient + perpetual-rotation trick; the ambient glow pulse behind
// it stays (pure decoration, not the data itself).
export function RingHero({ value, max = 100, label = "overall" }) {
  const p = Math.max(0, Math.min(100, (value / max) * 100));
  const gradId = useId();
  const circleRef = useRef(null);
  const valueRef = useRef(null);

  useEffect(() => {
    const circle = circleRef.current;
    if (!circle) return undefined;
    const fraction = p / 100;
    const [drawable] = svg.createDrawable(circle);

    if (prefersReducedMotion()) {
      drawable.draw = `0 ${fraction}`;
      if (valueRef.current) valueRef.current.textContent = value.toFixed(1);
      return undefined;
    }

    drawable.draw = "0 0";
    const a1 = animate(drawable, { draw: ["0 0", `0 ${fraction}`], duration: 1500, delay: 120, ease: "outCubic" });
    const counter = { v: 0 };
    const a2 = animate(counter, {
      v: value,
      duration: 1500,
      delay: 120,
      ease: "outCubic",
      onUpdate: () => {
        if (valueRef.current) valueRef.current.textContent = counter.v.toFixed(1);
      },
    });
    return () => {
      a1.revert();
      a2.revert();
    };
  }, [p, value]);

  return (
    <div className="ring-hero">
      <svg viewBox="0 0 176 176" className="ring-hero-svg">
        <defs>
          <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style={{ stopColor: "var(--accent-soft)" }} />
            <stop offset="55%" style={{ stopColor: "var(--accent-strong)" }} />
            <stop offset="100%" style={{ stopColor: "var(--accent)" }} />
          </linearGradient>
        </defs>
        <circle cx="88" cy="88" r="80" className="ring-hero-track-bg" />
        <circle
          ref={circleRef}
          cx="88"
          cy="88"
          r="80"
          className="ring-hero-track-fg"
          stroke={`url(#${gradId})`}
          transform="rotate(-90 88 88)"
        />
      </svg>
      <div className="ring-face">
        <div>
          <div className="ring-value">
            <span ref={valueRef}>0.0</span>
          </div>
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
