import { useMemo } from "react";

const MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

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
        marks.push({ week: wi, label: MONTH_LABELS[m] });
        lastMonth = m;
      }
    });
    return { weeks: weeksArr, monthMarks: marks, maxActions: max };
  }, [days]);

  const gridStyle = { gridTemplateColumns: `repeat(${weeks.length}, 11px)` };

  return (
    <div className="heatmap-wrap">
      <div className="heatmap-scroll">
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
                    title={`${day.date}: ${day.actions} action${day.actions === 1 ? "" : "s"} · ${day.minutes} min`}
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
        <span className="muted" style={{ fontSize: 11 }}>Less</span>
        {[0, 1, 2, 3, 4].map((l) => (
          <span key={l} className={`heatmap-cell level-${l}`} />
        ))}
        <span className="muted" style={{ fontSize: 11 }}>More</span>
      </div>
    </div>
  );
}
