import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useApi } from "../hooks/useApi.js";
import { speakChinese } from "../zhSpeech.js";
import CompanionFigure from "./CompanionFigure.jsx";
import Icon from "./Icon.jsx";
import { Loading } from "./ui.jsx";
import { achievementTitle } from "../achievements.js";

// The permanent companion remembering the learner's journey. Every memory
// comes from GET /api/companion/memory (services/companion_memory.py), which
// derives it from stored activity -- this component only words it. The
// companion is always dashboard.animal (the learner's own choice), never
// the Daily Voice Companion.

const LINKS = {
  welcome_back: "/review",
  lesson_completed: null, // set from data.lesson_id
  difficult_chars: "/hanzi",
  confused_pair: "/review",
  recent_mistakes: "/mistakes",
  improving_listening: "/real-chinese",
  stale_area: null, // set from data.area
  weak_skill: "/dna",
  new_learner: "/lessons",
  achievement: "/achievements",
  mastered_recently: "/vocabulary",
};
const DAY_KINDS = new Set(["welcome_back", "streak", "lesson_completed", "stale_area"]);
const AREA_PATH = { vocab: "/vocabulary", hanzi: "/hanzi", grammar: "/grammar" };

function linkFor(m) {
  if (m.kind === "passport_milestone") return "/passport";
  if (m.kind === "lesson_completed") return `/lessons/${m.data.lesson_id}`;
  if (m.kind === "stale_area") return AREA_PATH[m.data.area];
  return LINKS[m.kind] || null;
}

function useMemoryLine() {
  const { t } = useTranslation();
  return (m, name) => {
    const d = m.data || {};
    const vars = {
      name,
      // Plural form follows the number the sentence actually says.
      count: DAY_KINDS.has(m.kind) ? d.days ?? 0 : d.count ?? 0,
      days: d.days ?? 0,
      total: d.total ?? 0,
      title: achievementTitle(t, d.code, d.title || ""),
      word: d.item?.hanzi || "",
      a: d.a?.hanzi || "",
      b: d.b?.hanzi || "",
      times: d.count ?? 0,
      recent: d.recent ?? 0,
      before: d.before ?? 0,
      value: Math.round(d.value ?? 0),
      skill: d.skill ? t(`companionReact.skill.${d.skill}`, { defaultValue: d.skill }) : "",
      area: d.area ? t(`companionMemory.area.${d.area}`) : "",
    };
    let key = `companionMemory.kind.${m.kind}`;
    if (m.kind === "lesson_completed" && d.days === 0) key = "companionMemory.kind.lesson_completed_today";
    if (m.kind === "stale_area" && d.days == null) key = "companionMemory.kind.stale_area_never";
    if (m.kind === "welcome_back" && d.active_today) key = "companionMemory.kind.welcome_back_active";
    if (m.kind === "passport_milestone") {
      const e = d.event_data || {};
      vars.event = t(`passport.event.${d.event}`, {
        ...e, count: e.count ?? e.items ?? e.times ?? e.days,
        score: e.score != null ? Math.round(e.score) : "", title: e.title || "",
      });
    }
    return t(key, vars);
  };
}

function Items({ m }) {
  const items = m.data?.items || (m.data?.item ? [m.data.item] : []) || [];
  const pair = m.kind === "confused_pair" ? [m.data.a, m.data.b] : null;
  const list = pair || items.filter((x) => x.hanzi);
  if (!list.length) return null;
  return (
    <div className="memory-items">
      {list.map((x, i) => (
        <button key={`${x.hanzi}-${i}`} type="button" className="cr-word" onClick={() => speakChinese(x.hanzi)}>
          <b lang="zh-CN">{x.hanzi}</b>
          {x.pinyin && <span className="sub">{x.pinyin}</span>}
        </button>
      ))}
    </div>
  );
}

export default function CompanionMemory({ animal, full = false }) {
  const { t } = useTranslation();
  const { data, error } = useApi("/companion/memory");
  const line = useMemoryLine();
  const name = animal?.name || t("companionReact.fallbackName");

  if (error) return <p className="sub">{error}</p>;
  if (!data) return <Loading />;

  const head = data.headline;
  const rest = data.memories.filter((m) => m !== head && m.kind !== head.kind).slice(0, full ? 20 : 3);
  const headLink = linkFor(head);
  return (
    <div className="companion-memory" aria-live="polite">
      <div className={`companion-reaction mood-${head.mood}`}>
        {animal?.slug && <CompanionFigure slug={animal.slug} mood={head.mood} size={full ? 96 : 72} />}
        <div className="companion-reaction-text">
          <div className="cr-bubble" lang="zh-CN">
            <span>{head.zh}</span>
          </div>
          <p className="cr-line">{line(head, name)}</p>
          <Items m={head} />
          {headLink && (
            <Link to={headLink} className="btn small" style={{ marginTop: 8 }}>
              {t(`companionMemory.action.${head.kind}`, { defaultValue: t("companionMemory.action.default") })}
              <Icon name="arrowRight" size={13} />
            </Link>
          )}
        </div>
      </div>
      {rest.length > 0 && (
        <>
          <p className="side-title" style={{ marginTop: 16 }}>{t("companionMemory.remembers", { name })}</p>
          <ul className="memory-list">
            {rest.map((m, i) => {
              const to = linkFor(m);
              return (
                <li key={`${m.kind}-${i}`} className="memory-item">
                  <span className={`memory-dot mood-${m.mood}`} aria-hidden="true" />
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div>{line(m, name)}</div>
                    <Items m={m} />
                  </div>
                  {to && (
                    <Link to={to} className="icon-btn" aria-label={t("companionMemory.action.default")}>
                      <Icon name="chevronRight" size={15} />
                    </Link>
                  )}
                </li>
              );
            })}
          </ul>
        </>
      )}
      {!animal && (
        <Link to="/animals" className="btn small primary" style={{ marginTop: 12 }}>{t("dashboard.chooseCompanion")}</Link>
      )}
    </div>
  );
}
