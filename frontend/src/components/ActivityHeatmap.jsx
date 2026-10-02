import { useLayoutEffect, useMemo, useRef } from "react";
import { useTranslation } from "react-i18next";

// Short month names in the UI language (Intl), not a fixed English list.
function monthLabel(month, lang) {
  try {
    return new Date(2024, month, 1).toLocaleDateString(lang, { month: "short" });
  } catch {
    return String(month + 1);
  }
}

function levelOf(actions, max) {
  if (!actions || max <= 0) return 0;
  const ratio = actions / max;
  if (ratio > 0.75) return 4;
  if (ratio > 0.5) return 3;
  if (ratio > 0.25) return 2;
  return 1;
}

// A GitHub-contributions-style calendar built from real per-day activity
// (see /api/analytics/activity's `days`, backed by ActivityEvent rows) —
// weeks as columns, days as rows, cell shading by that day's real action
// count relative to this user's own busiest day.
export default function ActivityHeatmap({ days }) {
  const { t, i18n } = useTranslation();
  const { weeks, monthMarks, maxActions } = useMemo(() => {
    if (!days || days.length === 0) return { weeks: [], monthMarks: [], maxActions: 0 };
    const max = Math.max(...days.map((d) => d.actions), 1);
    const first = new Date(`${days[0].date}T00:00:00`);
    const firstWeekday = first.getDay(); // 0 = Sun
    const padded = Array(firstWeekday).fill(null).concat(days);
    const weeksArr = [];
    for (let i = 0; i < padded.length; i += 7) {
      weeksArr.push(padded.slice(i, i + 7));
    }
    const marks = [];
    let lastMonth = null;
    weeksArr.forEach((week, wi) => {
      const firstDay = week.find((d) => d);
      if (!firstDay) return;
      const m = new Date(`${firstDay.date}T00:00:00`).getMonth();
      if (m !== lastMonth) {
        marks.push({ week: wi, label: monthLabel(m, i18n.language) });
        lastMonth = m;
      }
    });
    return { weeks: weeksArr, monthMarks: marks, maxActions: max };
  }, [days, i18n.language]);

  // The 53-week grid (~740px) is wider than a phone or tablet card, and a
  // scroll box starts at its left edge -- a year ago -- so the recent weeks,
  // where today's activity is, were off-screen and the card looked empty.
  // Open it scrolled to the newest week instead.
  const scrollRef = useRef(null);
  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollLeft = el.scrollWidth;
  }, [weeks.length]);

  const gridStyle = { gridTemplateColumns: `repeat(${weeks.length}, 11px)` };

  return (
    <div className="heatmap-wrap">
      <div className="heatmap-scroll" ref={scrollRef}>
        <div className="heatmap-months" style={gridStyle}>
          {monthMarks.map((m, i) => (
            <span key={i} className="heatmap-month" style={{ gridColumnStart: m.week + 1 }}>
              {m.label}
            </span>
          ))}
        </div>
        <div className="heatmap-grid" style={gridStyle}>
          {weeks.map((week, wi) => (
            <div className="heatmap-col" key={wi}>
              {week.map((day, di) =>
                day ? (
                  <div
                    key={di}
                    className={`heatmap-cell level-${levelOf(day.actions, maxActions)}`}
                    title={t("ui.heatmapDay", { date: day.date, actions: t("ui.actions", { count: day.actions }), minutes: day.minutes })}
                  />
                ) : (
                  <div key={di} className="heatmap-cell empty" />
                )
              )}
            </div>
          ))}
        </div>
      </div>
      <div className="heatmap-legend">
        <span className="muted" style={{ fontSize: "var(--text-2xs)" }}>{t("ui.heatmapLess")}</span>
        {[0, 1, 2, 3, 4].map((l) => (
          <span key={l} className={`heatmap-cell level-${l}`} />
        ))}
        <span className="muted" style={{ fontSize: "var(--text-2xs)" }}>{t("ui.heatmapMore")}</span>
      </div>
    </div>
  );
}
