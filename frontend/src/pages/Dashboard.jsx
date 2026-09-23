import { motion } from "framer-motion";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import AnimalAvatar from "../components/AnimalAvatar.jsx";
import Icon from "../components/Icon.jsx";
import InkBrush from "../components/InkBrush.jsx";
import Layout from "../components/Layout.jsx";
import { Bar, Badge, Empty, Loading, RingHero } from "../components/ui.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";
import { staggerContainer, staggerItem } from "../motion.js";

const QUICK_ACTIONS = [
  ["/world", "dashboard.exploreWorld", "world", "linear-gradient(135deg, #2b6f93, #4fc3f7)"],
  ["/dna", "dashboard.viewDna", "dna", "linear-gradient(135deg, #2f7a4c, #4cc26b)"],
  ["/duels", "dashboard.startDuel", "swords", "linear-gradient(135deg, #b1501c, #ff8a3d)"],
  ["/missions", "dashboard.pickMission", "flag", "linear-gradient(135deg, var(--accent-soft), var(--accent-strong))"],
];

export default function Dashboard() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { dashboard: d, error } = useDashboard();

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!d) return <Layout><Loading>{t("common.loadingWorld")}</Loading></Layout>;

  const skillAnchor = (code) => navigate(`/dna?focus=${code}`);
  const questsDone = d.quests_today.filter((q) => q.completed).length;
  const questsTotal = d.quests_today.length;
  const badgesUnlocked = d.achievements.filter((a) => a.unlocked).length;

  return (
    <Layout>
      <div className="hero-banner" style={{ position: "relative" }}>
        <InkBrush variant="hero" />
        <span className="kicker">{t("landing.kicker")}</span>
        <h1>你好, {d.user.username}</h1>
        <p className="sub">
          HSK {d.hsk_level} · {d.mastery.toFixed(0)}{t("dashboard.overallMastery")} · {t("dashboard.goal", { minutes: d.daily_goal.minutes ?? 20 })}
        </p>
        <div className="hero-stats-row">
          <div className="hero-stat-pill">
            <span className="ic"><Icon name="target" size={15} /></span>
            <div>
              <div className="num">{questsDone}/{questsTotal || 0}</div>
              <div className="lbl">{t("dashboard.todaysQuests")}</div>
            </div>
          </div>
          <div className="hero-stat-pill">
            <span className="ic"><Icon name="flame" size={15} /></span>
            <div>
              <div className="num">{d.streak.current_streak}</div>
              <div className="lbl">{t("dashboard.dayStreak")}</div>
            </div>
          </div>
          <div className="hero-stat-pill">
            <span className="ic"><Icon name="coin" size={15} /></span>
            <div>
              <div className="num">{d.user.coins}</div>
              <div className="lbl">{t("dashboard.coins")}</div>
            </div>
          </div>
          <div className="hero-stat-pill">
            <span className="ic"><Icon name="trending" size={15} /></span>
            <div>
              <div className="num">HSK {d.hsk_level}</div>
              <div className="lbl">{t("dashboard.level")}</div>
            </div>
          </div>
        </div>
      </div>

      <motion.div className="quick-actions" variants={staggerContainer} initial="initial" animate="animate">
        {QUICK_ACTIONS.map(([to, labelKey, icon, gradient]) => (
          <motion.div key={to} variants={staggerItem} whileHover={{ y: -4 }} whileTap={{ scale: 0.97 }}>
            <Link to={to} className="quick-action" style={{ background: gradient }}>
              <div className="qa-top">
                <span className="ic"><Icon name={icon} size={19} /></span>
                <Icon name="arrowRight" size={17} className="arrow" />
              </div>
              <span className="label">{t(labelKey)}</span>
            </Link>
          </motion.div>
        ))}
      </motion.div>

      <motion.div className="stat-grid" variants={staggerContainer} initial="initial" animate="animate">
        <motion.div className="stat-card" variants={staggerItem} style={{ "--stat-color": "#ff8a3d" }}>
          <span className="ic"><Icon name="flame" size={18} /></span>
          <div className="num">{d.streak.current_streak}</div>
          <div className="lbl">{t("dashboard.dayStreak")}</div>
        </motion.div>
        <motion.div className="stat-card" variants={staggerItem} style={{ "--stat-color": "var(--accent)" }}>
          <span className="ic"><Icon name="coin" size={18} /></span>
          <div className="num">{d.user.coins}</div>
          <div className="lbl">{t("dashboard.coinsEarned")}</div>
        </motion.div>
        <motion.div className="stat-card" variants={staggerItem} style={{ "--stat-color": "#3fb6a8" }}>
          <span className="ic"><Icon name="dna" size={18} /></span>
          <div className="num">{d.mastery.toFixed(0)}%</div>
          <div className="lbl">{t("dashboard.hskMastery")}</div>
        </motion.div>
        <motion.div className="stat-card" variants={staggerItem} style={{ "--stat-color": "#9b6fe0" }}>
          <span className="ic"><Icon name="award" size={18} /></span>
          <div className="num">{badgesUnlocked}</div>
          <div className="lbl">{t("nav.achievements")}</div>
        </motion.div>
      </motion.div>

      <div className="bento" style={{ marginTop: 16 }}>
        <div className="card bento-2">
          <div className="row">
            {d.animal ? (
              <>
                <AnimalAvatar slug={d.animal.slug} size={64} />
                <div>
                  <h2 className="h2">{d.animal.name}</h2>
                  <p className="sub">{d.animal.species}</p>
                  <p className="sub">{d.animal.special_ability}</p>
                </div>
              </>
            ) : (
              <Link to="/animals">
                <button className="btn primary">{t("dashboard.chooseCompanion")}</button>
              </Link>
            )}
          </div>
        </div>
        <div className="card bento-4 center dna-hero-card">
          <RingHero value={d.dna.overall} label={t("dashboard.learningDnaOverall")} />
        </div>
      </div>

      <div className="bento" style={{ marginTop: 16 }}>
        <div className="card bento-3">
          <h2 className="h2">{t("dashboard.todaysQuests")}</h2>
          {d.quests_today.length === 0 && <Empty>No quests today — go explore.</Empty>}
          <div className="col">
            {d.quests_today.map((q) => (
              <div key={q.id} className="hbar">
                <span className="ic" style={{ width: 30, height: 30 }}>
                  <Icon name={q.completed ? "check" : "target"} size={14} />
                </span>
                <div style={{ flex: 1 }}>
                  <div className="row spread" style={{ margin: 0 }}>
                    <b>{q.title}</b>
                    <span className="muted">
                      {q.progress}/{q.target}
                    </span>
                  </div>
                  <Bar value={q.progress} max={q.target} />
                </div>
              </div>
            ))}
          </div>
          <Link to="/quests">
            <button className="btn small ghost" style={{ marginTop: 12 }}>{t("common.allQuests")}</button>
          </Link>
        </div>

        <div className="card bento-3">
          <h2 className="h2">{t("dashboard.prosConsDna")}</h2>
          <div className="col">
            {d.dna.skills.slice(0, 6).map((s) => (
              <div key={s.code} className="hbar" onClick={() => skillAnchor(s.code)}>
                <span className="muted" style={{ width: 90, fontSize: 12.5 }}>
                  {s.name}
                </span>
                <Bar value={s.mastery} />
                <span style={{ width: 34, textAlign: "right" }}>{s.mastery.toFixed(0)}</span>
              </div>
            ))}
          </div>
          <Link to="/dna">
            <button className="btn small ghost" style={{ marginTop: 12 }}>{t("dashboard.fullDna")}</button>
          </Link>
        </div>
      </div>

      <div className="bento" style={{ marginTop: 16 }}>
        <div className="card bento-3">
          <h2 className="h2">{t("dashboard.nextLocation")}</h2>
          {d.next_location ? (
            <Link to={`/world/${d.next_location.slug}`}>
              <button className="btn primary">
                {d.next_location.icon} {d.next_location.name}
              </button>
            </Link>
          ) : (
            <p className="sub">{t("dashboard.exploreEverything")}</p>
          )}
        </div>
        <div className="card bento-3">
          <h2 className="h2">{t("dashboard.recommendedMission")}</h2>
          {d.recommended_mission ? (
            <p className="sub">{d.recommended_mission.title}</p>
          ) : (
            <p className="sub">{t("dashboard.onARoll")}</p>
          )}
          <Link to="/missions">
            <button className="btn small">{t("dashboard.viewAllMissions")}</button>
          </Link>
        </div>
      </div>

      {d.recent_mistakes.length > 0 && (
        <div className="card" style={{ marginTop: 16 }}>
          <h2 className="h2">{t("dashboard.needsWork")}</h2>
          <div className="col">
            {d.recent_mistakes.slice(0, 4).map((m) => (
              <div key={m.id} className="row spread">
                <span className="muted">{m.answer_given || m.question_text}</span>
                <Badge tone="bad">×{m.occurrences}</Badge>
              </div>
            ))}
          </div>
          <Link to="/mistakes">
            <button className="btn small ghost" style={{ marginTop: 12 }}>{t("dashboard.reviewMistakes")}</button>
          </Link>
        </div>
      )}
    </Layout>
  );
}
