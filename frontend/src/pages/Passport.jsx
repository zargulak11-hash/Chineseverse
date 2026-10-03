import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import Icon from "../components/Icon.jsx";
import FeatureIntro from "../components/FeatureIntro.jsx";
import Layout from "../components/Layout.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

// Chinese Passport (GET /api/passport): what this learner can actually DO in
// Chinese, each capability with the evidence behind it (graded answers,
// mastery, rounds completed, Learning DNA) and a story of real milestones.
// The server decides every band from stored activity -- nothing here is
// derived from XP, and nothing is shown that the data doesn't support.

const LOCALE = { en: "en-US", ru: "ru-RU", tg: "tg-TJ", zh: "zh-CN" };
const BAND_TONE = { strong: "good", developing: "accent", emerging: "", none: "" };
const WORLD_TONE = { can_do: "good", trying: "accent", not_yet: "" };
const EVENT_ICON = {
  joined: "user", first_practice: "target", first_lesson: "book", level_started: "trending", exam_passed: "award",
  words_mastered: "type", chars_mastered: "pen", first_written: "pen", mistake_conquered: "check",
  review_recovery: "clock", comeback: "heart", scene_done: "mapPin", cases_solved: "search", sound_stage: "ear",
  first_internet: "eye", first_sentence: "sparkles", first_voice: "mic", first_duel_win: "swords", achievement: "trophy",
};
const CAP_ICON = { vocabulary: "type", characters: "pen", reading: "book", listening: "ear", grammar: "seal", speaking: "mic" };

function useDate() {
  const { i18n } = useTranslation();
  return (iso, opts = { dateStyle: "medium" }) => {
    if (!iso) return "";
    try {
      return new Intl.DateTimeFormat(LOCALE[i18n.language] || "en-US", opts).format(new Date(iso));
    } catch {
      return iso.slice(0, 10);
    }
  };
}

function Capability({ c, min }) {
  const { t } = useTranslation();
  const date = useDate();
  const s = c.stats;
  const enough = s.answers >= min && s.accuracy != null;
  const useRecent = s.recent_answers >= min && s.recent_accuracy != null;
  return (
    <div className="card passport-cap">
      <div className="row spread" style={{ margin: 0, gap: 8 }}>
        <span className="passport-cap-icon"><Icon name={CAP_ICON[c.code]} size={18} /></span>
        <span className={`badge ${BAND_TONE[c.band]}`}>{t(`passport.band.${c.band}`)}</span>
      </div>
      <h3 className="h2" style={{ marginTop: 12 }}>{t(`passport.cap.${c.code}.title`)}</h3>
      <p className="passport-can">{t(`passport.cap.${c.code}.can.${c.band}`)}</p>
      <p className="sub">
        {t(`passport.cap.${c.code}.facts`, Object.fromEntries(Object.entries(c.facts).map(([k, v]) => [k, v ?? "—"])))}
      </p>
      <details className="passport-why">
        <summary>{t("passport.why")}</summary>
        <ul className="scene-rules">
          {c.code === "speaking" ? (
            <li>{enough ? t("passport.evidence.speaking", { count: s.answers, avg: s.accuracy }) : t("passport.evidence.notEnough", { count: s.answers, min })}</li>
          ) : enough ? (
            <li>
              {useRecent
                ? t("passport.evidence.recent", { count: s.recent_answers, pct: s.recent_accuracy })
                : t("passport.evidence.allTime", { count: s.answers, pct: s.accuracy })}
            </li>
          ) : (
            <li>{t("passport.evidence.notEnough", { count: s.answers, min })}</li>
          )}
          {s.last_at && <li>{t("passport.evidence.last", { date: date(s.last_at) })}</li>}
          <li>
            {t("passport.evidence.dna", { skill: t(`companionReact.skill.${c.dna}`), value: Math.round(c.dna_value) })}{" "}
            <Link to={`/dna?focus=${c.dna}`}>{t("passport.openDna")}</Link>
          </li>
          <li className="sub">{t(`passport.cap.${c.code}.basis`)}</li>
        </ul>
      </details>
      <Link to={c.action} className="btn small" style={{ marginTop: 12, alignSelf: "flex-start" }}>
        {t(`passport.cap.${c.code}.action`)} <Icon name="arrowRight" size={13} />
      </Link>
    </div>
  );
}

function WorldSkill({ w }) {
  const { t } = useTranslation();
  const date = useDate();
  return (
    <div className={`card flat passport-world is-${w.status}`}>
      <div className="row spread" style={{ margin: 0, gap: 8 }}>
        <b>{t(`passport.world.${w.code}`)}</b>
        <span className={`badge ${WORLD_TONE[w.status]}`}>{t(`passport.worldStatus.${w.status}`)}</span>
      </div>
      <ul className="scene-rules">
        {w.scene && (
          <li>
            {t("passport.worldEvidence.scene", {
              title: w.scene.title, score: Math.round(w.scene.score),
              tier: t(`realLife.tier.${w.scene.tier || "beginner"}`), date: date(w.scene.at),
            })}
          </li>
        )}
        {w.sound_rounds > 0 && <li>{t("passport.worldEvidence.sound", { count: w.sound_rounds, best: Math.round(w.sound_best) })}</li>}
        {w.net_reads > 0 && <li>{t("passport.worldEvidence.net", { count: w.net_reads })}</li>}
        {!w.scene && !w.sound_rounds && !w.net_reads && <li>{t("passport.worldEvidence.none")}</li>}
      </ul>
      <Link to={w.action} className="btn small ghost" style={{ marginTop: 8 }}>
        {t(w.status === "not_yet" ? "passport.worldGo" : "passport.worldAgain")} <Icon name="arrowRight" size={13} />
      </Link>
    </div>
  );
}

function eventText(t, e) {
  const d = e.data || {};
  return t(`passport.event.${e.kind}`, {
    ...d,
    count: d.count ?? d.items ?? d.times ?? d.days,
    score: d.score != null ? Math.round(d.score) : "",
    title: d.title || "",
  });
}

function Story({ events }) {
  const { t } = useTranslation();
  const date = useDate();
  if (events.length <= 1) {
    return <Empty>{t("passport.storyEmpty")}</Empty>;
  }
  let lastMonth = "";
  return (
    <ol className="story">
      {[...events].reverse().map((e, i) => {
        const month = date(e.at, { year: "numeric", month: "long" });
        const header = month !== lastMonth ? month : null;
        lastMonth = month;
        const body = (
          <>
            <span className="story-icon"><Icon name={EVENT_ICON[e.kind] || "star"} size={15} /></span>
            <div className="story-body">
              <div className="story-text">{eventText(t, e)}</div>
              <div className="sub">{date(e.at)}</div>
            </div>
          </>
        );
        return (
          <li key={`${e.kind}-${e.at}-${i}`} className={`story-item is-${e.kind}`}>
            {header && <div className="story-month">{header}</div>}
            {e.link ? <Link to={e.link} className="story-card">{body}</Link> : <div className="story-card">{body}</div>}
          </li>
        );
      })}
    </ol>
  );
}

function recText(t, r) {
  switch (r.kind) {
    case "review": return t("passport.rec.review", { count: r.due });
    case "exam": return t("passport.rec.exam", { level: r.level });
    case "weak_chars": return t("passport.rec.weakChars", { count: r.count });
    case "world": return t("passport.rec.world", { skill: t(`passport.world.${r.code}`) });
    default:
      return r.band === "none"
        ? t("passport.rec.noEvidence", { skill: t(`passport.cap.${r.code}.title`) })
        : t("passport.rec.capability", { skill: t(`passport.cap.${r.code}.title`), pct: r.accuracy ?? 0, count: r.answers });
  }
}

export default function Passport() {
  const { t } = useTranslation();
  const date = useDate();
  const { data, error } = useApi("/passport");

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading /></Layout>;

  const caps = Object.fromEntries(data.capabilities.map((c) => [c.code, c]));
  const h = data.hsk;
  return (
    <Layout>
      <header className="page-head passport-head">
        <div>
          <div className="page-eyebrow"><Icon name="award" size={13} /> {t("nav.passport")}</div>
          <h1 className="h1">{t("passport.title")}</h1>
          <p className="sub">{t("passport.subtitle", { name: data.user.username, date: date(data.user.since) })}</p>
        </div>
        <div className="kpi-row">
          <div className="kpi">
            <span className="kpi-value">HSK {h.level}</span>
            <span className="kpi-label">{t("passport.level")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{caps.vocabulary.facts.known}</span>
            <span className="kpi-label">{t("passport.wordsKnown")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{caps.characters.facts.learned}</span>
            <span className="kpi-label">{t("passport.charsLearned")}</span>
          </div>
        </div>
      </header>
      <FeatureIntro feature="passport" />

      <div className="ws">
        <div className="ws-main">
          <div className="card">
            <div className="row spread" style={{ margin: 0, flexWrap: "wrap" }}>
              <h2 className="h2">{t("passport.hskTitle", { level: h.level })}</h2>
              <Link to="/roadmap" className="btn small ghost">{t("nav.roadmap")} <Icon name="arrowRight" size={13} /></Link>
            </div>
            <div className="passport-hsk">
              {h.lessons && (
                <div>
                  <div className="sub">{t("passport.hskLessons", { done: h.lessons.completed, total: h.lessons.total })}</div>
                  <Bar value={h.lessons.completed} max={Math.max(1, h.lessons.total)} />
                </div>
              )}
              {[["vocab", "passport.hskVocab"], ["hanzi", "passport.hskHanzi"], ["grammar", "passport.hskGrammar"]].map(([k, key]) => (
                <div key={k}>
                  <div className="sub">{t(key, { done: h[k].mastered, total: h[k].total })}</div>
                  <Bar value={h[k].mastered} max={Math.max(1, h[k].total)} alt />
                </div>
              ))}
            </div>
            {h.exam && <p className="sub" style={{ marginTop: 12 }}>{t(`passport.exam.${h.exam}`, { level: h.level, next: h.next })}</p>}
          </div>

          <h2 className="h2 section-title">{t("passport.canDo")}</h2>
          <div className="grid cards passport-caps">
            {data.capabilities.map((c) => <Capability key={c.code} c={c} min={data.min_evidence} />)}
          </div>

          <h2 className="h2 section-title">{t("passport.worldTitle")}</h2>
          <div className="passport-worlds">
            {data.world.map((w) => <WorldSkill key={w.code} w={w} />)}
          </div>

          <h2 className="h2 section-title">{t("passport.storyTitle")}</h2>
          <div className="card">
            <Story events={data.timeline} />
          </div>
        </div>

        <aside className="ws-side">
          <div className="card side-card">
            <p className="side-title">{t("passport.next")}</p>
            {data.recommendations.length === 0 ? (
              <p className="sub">{t("passport.allGood")}</p>
            ) : (
              <ul className="passport-recs">
                {data.recommendations.map((r, i) => (
                  <li key={i}>
                    <Link to={r.to} className="passport-rec">
                      <span>{recText(t, r)}</span>
                      <Icon name="chevronRight" size={15} />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
          {data.weak_characters.length > 0 && (
            <div className="card side-card">
              <p className="side-title">{t("passport.weakChars")}</p>
              <div className="chip-row">
                {data.weak_characters.map((c) => (
                  <Link key={c.char} to={`/hanzi/${encodeURIComponent(c.char)}`} className="char-chip">
                    <b lang="zh-CN">{c.char}</b>
                    <span className="sub">{c.pinyin}</span>
                    <span className="char-chip-meaning">{t("passport.missedTimes", { count: c.missed })}</span>
                  </Link>
                ))}
              </div>
            </div>
          )}
          <div className="card side-card">
            <p className="side-title">{t("passport.howTitle")}</p>
            <p className="sub">{t("passport.how", { min: data.min_evidence })}</p>
            <p className="sub">{t("passport.totals", { answers: data.totals.answers, count: data.totals.rounds })}</p>
          </div>
        </aside>
      </div>
    </Layout>
  );
}
