import { animate, stagger } from "animejs";
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { prefersReducedMotion } from "../anime.js";
import AnimalAvatar from "../components/AnimalAvatar.jsx";
import Art, { placeArt } from "../components/Art.jsx";
import CompanionMemory from "../components/CompanionMemory.jsx";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { NextStepHero, TodayPlan } from "../components/NextStep.jsx";
import { Bar, Badge, Empty, Loading } from "../components/ui.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";
import { useApi } from "../hooks/useApi.js";
import { achievementHow, achievementIcon, achievementTitle, progressText } from "../achievements.js";

// Staggered entrance for the quest rows. Opts its container out of Layout's
// page-level reveal via data-self-animate so the two don't stack.
function useCardStagger(deps) {
  const ref = useRef(null);
  useEffect(() => {
    const root = ref.current;
    if (!root) return;
    const targets = Array.from(root.children);
    if (targets.length === 0) return;
    if (prefersReducedMotion()) {
      targets.forEach((el) => {
        el.style.opacity = 1;
      });
      return;
    }
    animate(targets, {
      opacity: [0, 1],
      translateY: [12, 0],
      duration: 420,
      delay: stagger(50),
      ease: "outQuad",
      onComplete: () => {
        targets.forEach((el) => {
          el.style.opacity = "";
          el.style.transform = "";
        });
      },
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return ref;
}

// Old World location slugs (the dashboard's "next location") -> places of
// the living world on /real-chinese.
const LOCATION_PLACE = {
  home: "home", "city-street": "street", restaurant: "restaurant", shop: "shop", university: "university",
  hospital: "hospital", "train-station": "train_station", hotel: "hotel", airport: "airport",
};

// The Dashboard answers, in this order: what to do now (the next step and
// today's plan), what to fix, what has been built, then everything else.
// It used to open with a greeting banner, four gradient shortcut tiles and
// two rows of the same stats (streak and coins twice each) before any of
// that -- twelve blocks of equal weight. Every number here is read from the
// learner's own records (GET /api/dashboard, /api/journey, the mix-ups).
export default function Dashboard() {
  const { t } = useTranslation();
  const { dashboard: d, error } = useDashboard();
  const { data: journey } = useApi("/journey");
  const { data: mix } = useApi("/mistakes/mixups");

  const questsListRef = useCardStagger([d?.quests_today?.length ?? 0]);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!d) return <Layout><Loading>{t("common.loadingWorld")}</Loading></Layout>;

  const due = journey?.due_reviews ?? d.review_due ?? 0;
  const pairs = mix?.active || [];
  const mistakes = d.recent_mistakes.slice(0, 3);
  const nothingToFix = due === 0 && pairs.length === 0 && mistakes.length === 0;
  const today = journey?.today;
  const placeSlug = d.next_location ? LOCATION_PLACE[d.next_location.slug] || "" : "";

  return (
    <Layout>
      <header className="dash-greeting">
        <h1 className="h1"><span lang="zh-CN">你好</span>, {d.user.username}</h1>
        <p className="sub">HSK {d.hsk_level} · {t("dashboard.goal", { minutes: d.daily_goal.daily_goal_minutes })}</p>
      </header>

      <NextStepHero journey={journey} />
      <TodayPlan
        today={today}
        next={journey?.next}
        skills={Object.fromEntries((d.dna?.skills || []).map((s) => [s.code, s.name]))}
      />

      <div className="dash-row">
        <section className="card" aria-labelledby="dash-fix">
          <div className="row spread dash-card-head">
            <h2 className="h2" id="dash-fix">{t("dashboard.fix.title")}</h2>
            <Link to="/mistakes" className="btn small ghost">{t("nav.mistakes")}</Link>
          </div>
          {nothingToFix && <p className="sub">{t("dashboard.fix.clear")}</p>}
          <ul className="fix-list">
            {due > 0 && (
              <li>
                <Link to="/review" className="fix-row">
                  <Icon name="clock" size={16} />
                  <span className="fix-text">
                    <b>{t("dashboard.fix.due", { count: due })}</b>
                    <span className="sub">{t("dashboard.fix.dueWhy")}</span>
                  </span>
                  <Icon name="chevronRight" size={15} />
                </Link>
              </li>
            )}
            {pairs.length > 0 && (
              <li>
                <Link to="/practice?source=mixups" className="fix-row">
                  <Icon name="crosshair" size={16} />
                  <span className="fix-text">
                    <b>{t("today.mixups", { count: pairs.length })}</b>
                    <span className="fix-pairs" lang="zh-CN">
                      {pairs.slice(0, 3).map((p) => (
                        <span key={`${p.a.hanzi}-${p.b.hanzi}`}>{p.a.hanzi} ≠ {p.b.hanzi}</span>
                      ))}
                    </span>
                  </span>
                  <Icon name="chevronRight" size={15} />
                </Link>
              </li>
            )}
            {mistakes.map((m) => (
              <li key={m.id} className="fix-mistake">
                <span className="fix-text">{m.question_text || m.reference}</span>
                <Badge tone="bad">×{m.occurrences}</Badge>
              </li>
            ))}
          </ul>
        </section>

        <section className="card" aria-labelledby="dash-built">
          <div className="row spread dash-card-head">
            <h2 className="h2" id="dash-built">{t("dashboard.built.title")}</h2>
            <Link to="/progress" className="btn small ghost">{t("nav.progress")}</Link>
          </div>
          <div className="dash-facts">
            <div className="kpi">
              <span className="kpi-value">HSK {d.hsk_level}</span>
              <span className="kpi-label">{t("dashboard.built.level")}</span>
            </div>
            <div className="kpi">
              <span className="kpi-value">{journey?.known_words ?? "—"}</span>
              <span className="kpi-label">{t("dashboard.built.words")}</span>
            </div>
            <div className="kpi">
              <span className="kpi-value">{journey?.lessons_done ?? "—"}</span>
              <span className="kpi-label">{t("dashboard.built.lessons")}</span>
            </div>
            <div className="kpi">
              <span className="kpi-value">{d.streak.current_streak}</span>
              <span className="kpi-label">{t("dashboard.built.streak")}</span>
            </div>
          </div>
          {today && (
            <div className="dash-goal">
              <div className="row spread" style={{ margin: 0 }}>
                <span className="sub">{t("dashboard.built.today")}</span>
                <span className="sub">{t("dashboard.built.minutes", { minutes: today.minutes, goal: today.goal_minutes })}</span>
              </div>
              <Bar value={Math.min(today.minutes, today.goal_minutes)} max={today.goal_minutes || 1} />
            </div>
          )}
        </section>
      </div>

      <section className="card dash-section" aria-labelledby="dash-companion">
        <div className="row spread dash-card-head">
          <div className="row" style={{ margin: 0, gap: 12 }}>
            {d.animal && <AnimalAvatar slug={d.animal.slug} size={44} />}
            <h2 className="h2" id="dash-companion">
              {t("companionMemory.title", { name: d.animal?.name || t("companionReact.fallbackName") })}
            </h2>
          </div>
          {d.animal ? (
            <Link to="/passport" className="btn small ghost"><Icon name="award" size={13} /> {t("nav.passport")}</Link>
          ) : (
            <Link to="/animals" className="btn small primary">{t("dashboard.chooseCompanion")}</Link>
          )}
        </div>
        <CompanionMemory animal={d.animal} />
      </section>

      <div className="dash-row">
        <section className="card" aria-labelledby="dash-compass">
          <div className="row spread dash-card-head">
            <h2 className="h2" id="dash-compass">{t("dashboard.prosConsDna")}</h2>
            <Link to="/dna" className="btn small ghost">{t("dashboard.fullDna")}</Link>
          </div>
          <div className="col">
            {d.dna.skills.slice(0, 6).map((s) => (
              <Link key={s.code} to={`/dna?focus=${s.code}`} className="hbar hbar-link">
                <span className="muted hbar-name">{s.name}</span>
                <Bar value={s.mastery} />
                <span className="hbar-value">{s.mastery.toFixed(0)}</span>
              </Link>
            ))}
          </div>
        </section>

        <section className="card" aria-labelledby="dash-quests">
          <div className="row spread dash-card-head">
            <h2 className="h2" id="dash-quests">{t("dashboard.todaysQuests")}</h2>
            <Link to="/quests" className="btn small ghost">{t("common.allQuests")}</Link>
          </div>
          {d.quests_today.length === 0 && <p className="sub">{t("dashboard.noQuestsToday")}</p>}
          <div className="col" ref={questsListRef} data-self-animate="true">
            {d.quests_today.map((q) => (
              <div key={q.id} className="hbar">
                <span className="ic" style={{ width: 30, height: 30 }}>
                  <Icon name={q.completed ? "check" : "target"} size={14} />
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="row spread" style={{ margin: 0 }}>
                    <b>{q.title}</b>
                    <span className="muted">{q.progress}/{q.target}</span>
                  </div>
                  <Bar value={q.progress} max={q.target} />
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="dash-row">
        <section className="card" aria-labelledby="dash-world">
          <h2 className="h2" id="dash-world">{t("dashboard.nextLocation")}</h2>
          {d.next_location ? (
            <Link to={`/real-chinese?place=${placeSlug}`} className="btn primary" style={{ marginTop: 12 }}>
              <Art name={placeArt(placeSlug || d.next_location.slug)} size={24} shape="round" flat />
              {d.next_location.name}
            </Link>
          ) : (
            <p className="sub">{t("dashboard.exploreEverything")}</p>
          )}
          <p className="sub" style={{ marginTop: 16 }}>
            {t("dashboard.recommendedMission")}:{" "}
            {d.recommended_mission ? <b>{d.recommended_mission.title}</b> : t("dashboard.onARoll")}
          </p>
          <Link to="/missions" className="btn small ghost" style={{ marginTop: 8 }}>{t("dashboard.viewAllMissions")}</Link>
        </section>

        {d.next_achievements?.length > 0 && (
          <section className="card" aria-labelledby="dash-ach">
            <div className="row spread dash-card-head">
              <h2 className="h2" id="dash-ach">{t("achievements.dashboard.title")}</h2>
              <Link to="/achievements" className="btn small ghost">{t("achievements.dashboard.all")}</Link>
            </div>
            <div className="ach-next">
              {d.next_achievements.map((a) => (
                <Link key={a.id} to={a.to || "/achievements"} className="ach-next-row">
                  <span className="seal-stamp locked"><Icon name={achievementIcon(a)} size={15} /></span>
                  <span className="ach-next-text">
                    <b className="ach-title">{achievementTitle(t, a.code, a.title)}</b>
                    <span className="ach-text">{achievementHow(t, a)}</span>
                    {a.target > 1 && <Bar value={a.progress} max={a.target} />}
                  </span>
                  {a.target > 1 && <span className="muted">{progressText(a)}</span>}
                </Link>
              ))}
            </div>
          </section>
        )}
      </div>
    </Layout>
  );
}
