import { animate, stagger } from "animejs";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import {
  achievementDone,
  achievementHow,
  achievementIcon,
  achievementTitle,
  progressText,
  ratio,
  remainingText,
} from "../achievements.js";
import { prefersReducedMotion } from "../anime.js";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";
import { useApi } from "../hooks/useApi.js";

// Category order on the page and in the filter (the backend's categories).
const CATEGORIES = ["start", "places", "words", "characters", "listening", "speaking", "reading", "stories",
  "hsk", "review", "habit", "companion", "world"];

function AchCard({ a, fmtDate }) {
  const { t } = useTranslation();
  const title = achievementTitle(t, a.code, a.title);
  if (a.unlocked) {
    return (
      <div className="card ach-card is-earned">
        <div className="seal-stamp"><Icon name={achievementIcon(a)} size={19} /></div>
        <b className="ach-title">{title}</b>
        <p className="ach-text">{achievementDone(t, a)}</p>
        <div className="ach-foot">
          <span className="badge good"><Icon name="check" size={13} /> {t("achievements.page.done")}</span>
          {a.unlocked_at && <span className="ach-date">{fmtDate(a.unlocked_at)}</span>}
        </div>
      </div>
    );
  }
  const left = remainingText(t, a);
  return (
    <div className="card ach-card">
      <div className="seal-stamp locked"><Icon name={achievementIcon(a)} size={19} /></div>
      <b className="ach-title">{title}</b>
      <p className="ach-text">{achievementHow(t, a)}</p>
      {a.target > 1 && (
        <div className="metric">
          <div className="metric-head">
            <span>{t("achievements.progress")}</span>
            <b>{progressText(a)}</b>
          </div>
          <Bar value={ratio(a) * 100} alt={a.progress === 0} />
        </div>
      )}
      {left && <p className="ach-left">{left}</p>}
      {a.to && (
        <div className="ach-foot">
          <Link to={a.to} className="btn small">
            {t("achievements.page.go")} <Icon name="arrowRight" size={13} />
          </Link>
        </div>
      )}
    </div>
  );
}

export default function Achievements() {
  const { t, i18n } = useTranslation();
  const { data, error } = useApi("/achievements");
  // XP / streak / level come from the dashboard the app already shares
  // (DashboardContext) -- no extra request for this page.
  const { dashboard } = useDashboard() || {};
  const badges = data || [];
  const rootRef = useRef(null);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    const root = rootRef.current;
    if (!root || badges.length === 0) return undefined;
    const targets = Array.from(root.querySelectorAll(".ach-grid > .card"));
    if (prefersReducedMotion()) {
      targets.forEach((el) => {
        el.style.opacity = 1;
      });
      return undefined;
    }
    const anim = animate(targets, {
      opacity: [0, 1],
      translateY: [16, 0],
      duration: 480,
      delay: stagger(35),
      ease: "outQuad",
    });
    return () => anim.revert();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [badges.length, filter]);

  const groups = useMemo(() => {
    const unlocked = badges.filter((b) => b.unlocked);
    const locked = badges.filter((b) => !b.unlocked);
    // 1. What am I close to? Started multi-step ones, nearest first.
    const close = locked
      .filter((b) => b.target > 1 && b.progress > 0)
      .sort((a, b) => ratio(b) - ratio(a) || a.order - b.order)
      .slice(0, 4);
    // 2. What can I try next? One real step each, beginner-first order.
    const next = locked
      .filter((b) => b.target === 1 && b.progress === 0)
      .sort((a, b) => a.order - b.order)
      .slice(0, 4);
    const featured = new Set([...close, ...next].map((b) => b.id));
    const rest = locked.filter((b) => !featured.has(b.id)).sort((a, b) => a.order - b.order);
    return { unlocked, locked, close, next, rest };
  }, [badges]);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading /></Layout>;

  const { unlocked, close, next, rest } = groups;
  const completion = badges.length ? (unlocked.length / badges.length) * 100 : 0;
  const fmtDate = (iso) => new Date(iso).toLocaleDateString(i18n.language);
  const catLabel = (c) => t(`achievements.cat.${c}`, { defaultValue: c });
  const shown = (list) => (filter === "all" ? list : list.filter((b) => b.category === filter));
  const present = CATEGORIES.filter((c) => badges.some((b) => b.category === c));

  const recent = [...unlocked]
    .filter((b) => b.unlocked_at)
    .sort((a, b) => new Date(b.unlocked_at) - new Date(a.unlocked_at))
    .slice(0, 5);

  const byCategory = present.map((key) => {
    const all = badges.filter((b) => b.category === key);
    return { key, total: all.length, done: all.filter((b) => b.unlocked).length };
  });

  const earnedShown = shown(unlocked).sort((a, b) => new Date(b.unlocked_at) - new Date(a.unlocked_at));
  const restShown = shown(rest);

  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow">
            <Icon name="award" size={13} /> {t("pages.achievements.earned", { unlocked: unlocked.length, total: badges.length })}
          </div>
          <h1 className="h1">{t("pages.achievements.title")}</h1>
          <p className="sub">{t("achievements.page.subtitle")}</p>
          <div className="hbar" style={{ marginTop: 12, maxWidth: 520 }}>
            <Bar value={completion} />
            <span style={{ fontWeight: 800 }}>{completion.toFixed(0)}%</span>
          </div>
        </div>
        <div className="kpi-row">
          <div className="kpi">
            <span className="kpi-value">{unlocked.length}/{badges.length}</span>
            <span className="kpi-label">{t("pages.achievements.unlocked")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{dashboard?.user?.total_xp ?? "—"}</span>
            <span className="kpi-label">{t("common.xp")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{dashboard?.streak?.current_streak ?? "—"}</span>
            <span className="kpi-label">{t("dashboard.dayStreak")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{dashboard ? `HSK ${dashboard.hsk_level}` : "—"}</span>
            <span className="kpi-label">{t("dashboard.level")}</span>
          </div>
        </div>
      </header>

      <div className="ws">
        <div className="ws-main" ref={rootRef} data-self-animate="true">
          {badges.length === 0 && <Empty>{t("pages.achievements.noneYet")}</Empty>}

          {close.length > 0 && (
            <section>
              <h2 className="h2 section-title">{t("achievements.page.close")}</h2>
              <p className="sub ach-section-sub">{t("achievements.page.closeHint")}</p>
              <div className="ach-grid">{close.map((a) => <AchCard key={a.id} a={a} fmtDate={fmtDate} />)}</div>
            </section>
          )}

          {next.length > 0 && (
            <section>
              <h2 className="h2 section-title">{t("achievements.page.tryNext")}</h2>
              <p className="sub ach-section-sub">{t("achievements.page.tryNextHint")}</p>
              <div className="ach-grid">{next.map((a) => <AchCard key={a.id} a={a} fmtDate={fmtDate} />)}</div>
            </section>
          )}

          {badges.length > 0 && (
            <div className="row ach-filter" role="group" aria-label={t("achievements.page.filter")}>
              {["all", ...present].map((c) => (
                <button key={c} type="button" aria-pressed={filter === c}
                  className={`btn small ${filter === c ? "primary" : "ghost"}`} onClick={() => setFilter(c)}>
                  {c === "all" ? t("achievements.page.all") : catLabel(c)}
                </button>
              ))}
            </div>
          )}

          {earnedShown.length > 0 && (
            <section>
              <h2 className="h2 section-title">{t("achievements.page.achieved")} · {earnedShown.length}</h2>
              <div className="ach-grid">{earnedShown.map((a) => <AchCard key={a.id} a={a} fmtDate={fmtDate} />)}</div>
            </section>
          )}
          {unlocked.length === 0 && badges.length > 0 && filter === "all" && (
            <p className="sub">{t("pages.achievements.noneYet")}</p>
          )}

          {restShown.length > 0 && (
            <section>
              <h2 className="h2 section-title">{t("achievements.page.toEarn")} · {restShown.length}</h2>
              <div className="ach-grid">{restShown.map((a) => <AchCard key={a.id} a={a} fmtDate={fmtDate} />)}</div>
            </section>
          )}
        </div>

        <aside className="ws-side">
          <div className="card side-card">
            <p className="side-title">{t("pages.achievements.recent")}</p>
            {recent.length === 0 ? (
              <p className="sub">{t("pages.achievements.noneYet")}</p>
            ) : (
              <div className="ach-recent">
                {recent.map((b) => (
                  <div key={b.id} className="ach-recent-row">
                    <div className="seal-stamp">
                      <Icon name={achievementIcon(b)} size={15} />
                    </div>
                    <div style={{ minWidth: 0 }}>
                      <b className="ach-title" style={{ display: "block" }}>{achievementTitle(t, b.code, b.title)}</b>
                      <span className="ach-date">{fmtDate(b.unlocked_at)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card side-card">
            <p className="side-title">{t("pages.achievements.byCategory")}</p>
            <div style={{ display: "grid", gap: 12 }}>
              {byCategory.map((c) => (
                <div key={c.key} className="metric">
                  <div className="metric-head">
                    <span>{catLabel(c.key)}</span>
                    <b>{c.done}/{c.total}</b>
                  </div>
                  <Bar value={(c.done / c.total) * 100} alt={c.done === 0} />
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </Layout>
  );
}
