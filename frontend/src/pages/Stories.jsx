import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

// Chinese Stories (/stories): graded stories from HSK 1 to 9. Status comes
// from the learner's own rounds (services/stories.py); a story above their
// level says when it opens instead of just showing a lock.

const LEVELS = [1, 2, 3, 4, 5, 6, 7, 8, 9];

function StoryCard({ s, recommended }) {
  const { t } = useTranslation();
  const locked = s.status === "locked";
  const badge = locked
    ? t("stories.status.locked", { level: s.gate })
    : s.status === "read"
      ? t("stories.status.read", { best: Math.round(s.best) })
      : t(`stories.status.${s.status}`);
  const body = (
    <>
      <div className="row spread" style={{ margin: 0 }}>
        <span className="tale-icon" aria-hidden="true">{s.icon}</span>
        <span className="row" style={{ gap: 6, margin: 0 }}>
          {recommended && <span className="badge accent">{t("stories.startHere")}</span>}
          <span className="badge">HSK {s.level}</span>
        </span>
      </div>
      <h3 className="tale-title">{s.title}</h3>
      <span className="tale-title-zh" lang="zh-CN">{s.title_zh}</span>
      <p className="sub">{s.summary}</p>
      <span className="sub tale-length">{t("stories.length", { count: s.sentences, chars: s.characters })}</span>
      <span className={`badge tale-status ${s.status === "read" ? "good" : locked ? "" : "accent"}`}>
        {locked && <Icon name="lock" size={11} />} {badge}
      </span>
      {locked && <span className="sub tale-locked-how">{t("stories.lockedHow")}</span>}
    </>
  );
  return locked ? (
    <div className={`card tale-card is-locked`} aria-label={`${s.title} — ${badge}`}>{body}</div>
  ) : (
    <Link to={`/stories/${s.slug}`} className={`card hover tale-card${recommended ? " is-recommended" : ""}`}>{body}</Link>
  );
}

export default function Stories() {
  const { t } = useTranslation();
  const { data, error } = useApi("/stories");
  const [params, setParams] = useSearchParams();
  const filter = Number(params.get("level")) || null;
  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading /></Layout>;
  const read = data.stories.filter((s) => s.status === "read").length;
  const shown = data.stories.filter((s) => !filter || s.level === filter);
  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="bookOpen" size={13} /> {t("stories.eyebrow")}</div>
          <h1 className="h1">{t("stories.title")}</h1>
          <p className="sub">{t("stories.subtitle")}</p>
        </div>
        <div className="kpi-row">
          <div className="kpi">
            <span className="kpi-value">{read}/{data.stories.length}</span>
            <span className="kpi-label">{t("stories.read")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">HSK {data.level}</span>
            <span className="kpi-label">{t("stories.yourLevel")}</span>
          </div>
        </div>
      </header>

      {data.level === 1 && <p className="sub tale-hint"><Icon name="sparkles" size={13} /> {t("stories.beginnerHint")}</p>}

      <div className="row tale-filter" role="group" aria-label="HSK">
        <button type="button" className={`btn small${filter ? " ghost" : " primary"}`} aria-pressed={!filter}
                onClick={() => setParams({}, { replace: true })}>{t("stories.all")}</button>
        {LEVELS.map((l) => (
          <button key={l} type="button" className={`btn small${filter === l ? " primary" : " ghost"}`} aria-pressed={filter === l}
                  onClick={() => setParams({ level: String(l) }, { replace: true })}>HSK {l}</button>
        ))}
      </div>

      {shown.length === 0 ? (
        <Empty>{t("stories.empty")}</Empty>
      ) : (
        <div className="grid cards" style={{ marginTop: 16 }}>
          {shown.map((s) => <StoryCard key={s.slug} s={s} recommended={s.slug === data.recommended} />)}
        </div>
      )}
      <p className="sub" style={{ marginTop: 24 }}>{t("stories.why")}</p>
    </Layout>
  );
}
