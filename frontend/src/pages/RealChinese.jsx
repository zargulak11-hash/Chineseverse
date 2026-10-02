import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

// Real Chinese: real-life situations played as dialogues at the learner's
// own tier (services/real_life.py). These pages only browse; a scene is
// played as a server-graded practice round (/practice?source=scene).

function TierCard({ tier, rules }) {
  const { t } = useTranslation();
  return (
    <div className="card side-card">
      <p className="side-title">{t("realLife.yourTier")}</p>
      <span className="badge accent">{t(`realLife.tier.${tier}`)}</span>
      <p className="sub" style={{ marginTop: 8 }}>{t(`realLife.tierHow.${tier}`)}</p>
      <ul className="scene-rules">
        <li>{t("realLife.rule.options", { count: rules.options })}</li>
        <li>{t(rules.show_text ? (rules.show_pinyin ? "realLife.rule.textPinyin" : "realLife.rule.text") : "realLife.rule.audioFirst")}</li>
        <li>{t("realLife.rule.listening", { count: rules.listening })}</li>
        <li>{t("realLife.rule.newWords", { count: rules.new_words })}</li>
      </ul>
    </div>
  );
}

export default function RealChinese() {
  const { t } = useTranslation();
  const { data, error } = useApi("/real-life/scenes");

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading /></Layout>;

  const played = data.scenes.filter((s) => s.completed > 0).length;
  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="mapPin" size={13} /> {t("nav.realChinese")}</div>
          <h1 className="h1">{t("realLife.title")}</h1>
          <p className="sub">{t("realLife.subtitle")}</p>
        </div>
        <div className="kpi-row">
          <div className="kpi">
            <span className="kpi-value">HSK {data.level}</span>
            <span className="kpi-label">{t("realLife.yourLevel")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{played}/{data.scenes.length}</span>
            <span className="kpi-label">{t("realLife.played")}</span>
          </div>
        </div>
      </header>

      <div className="ws">
        <div className="ws-main">
          <h2 className="h2 section-title">{t("realLife.situations")}</h2>
          <div className="grid cards">
            {data.scenes.map((s) => (
              <Link key={s.slug} to={`/real-chinese/${s.slug}`} className="card hover scene-card">
                <div className="row spread" style={{ margin: 0 }}>
                  <span className="scene-icon" aria-hidden="true">{s.icon}</span>
                  {s.completed > 0 && (
                    <span className="badge good">{t("realLife.best", { score: Math.round(s.best_score) })}</span>
                  )}
                </div>
                <h3 className="h2" style={{ marginTop: 12 }}>{s.title}</h3>
                <p className="sub">{s.description}</p>
                <p className="sub scene-meta">
                  <span lang="zh-CN">{s.npc.zh}</span> · {s.npc.role}
                </p>
                <div className="row" style={{ gap: 8, flexWrap: "wrap", marginTop: 8 }}>
                  <span className="badge">{t("realLife.exchanges", { count: s.exchanges })}</span>
                  {s.new_words > 0 && <span className="badge accent">{t("realLife.newWordsCount", { count: s.new_words })}</span>}
                </div>
              </Link>
            ))}
          </div>
        </div>
        <aside className="ws-side">
          <TierCard tier={data.tier} rules={data.rules} />
          <div className="card side-card">
            <p className="side-title">{t("nav.sentence")}</p>
            <p className="sub">{t("sentenceLesson.teaser")}</p>
            <Link to="/sentence" className="btn" style={{ marginTop: 12 }}>
              <Icon name="sparkles" size={15} /> {t("sentenceLesson.open")}
            </Link>
          </div>
        </aside>
      </div>
    </Layout>
  );
}

export function RealChineseScene() {
  const { t } = useTranslation();
  const { slug } = useParams();
  const { data, error } = useApi(`/real-life/scenes/${slug}`);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading /></Layout>;

  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="mapPin" size={13} /> {t("nav.realChinese")}</div>
          <h1 className="h1"><span aria-hidden="true">{data.icon}</span> {data.title}</h1>
          <p className="sub">{data.description}</p>
        </div>
        <div className="kpi-row">
          <div className="kpi">
            <span className="kpi-value">{data.exchanges}</span>
            <span className="kpi-label">{t("realLife.exchangesLabel")}</span>
          </div>
          <div className="kpi">
            <span className="kpi-value">{data.completed ? `${Math.round(data.best_score)}%` : "—"}</span>
            <span className="kpi-label">{t("realLife.bestLabel")}</span>
          </div>
        </div>
      </header>

      <div className="ws">
        <div className="ws-main">
          <div className="card">
            <p className="sub">
              {t("realLife.youTalkTo")} <b lang="zh-CN">{data.npc.zh}</b> · {data.npc.role}
            </p>
            <div className="row" style={{ marginTop: 16, flexWrap: "wrap" }}>
              <Link to={`/practice?source=scene&scene=${data.slug}`} className="btn primary">
                <Icon name="play" size={15} /> {data.completed ? t("realLife.playAgain") : t("realLife.start")}
              </Link>
              <Link to="/real-chinese" className="btn ghost">{t("practice.back")}</Link>
            </div>
          </div>

          <h2 className="h2 section-title">{t("realLife.wordsForYou")}</h2>
          {data.new_words.length === 0 ? (
            <Empty>{t("realLife.noNewWords")}</Empty>
          ) : (
            <div className="grid cards">
              {data.new_words.map((w) => (
                <div key={w.hanzi} className="card flat scene-word">
                  <div className="row spread" style={{ margin: 0 }}>
                    <span className="scene-line-zh" lang="zh-CN">{w.hanzi}</span>
                    {w.level && <span className="badge">HSK {w.level}</span>}
                  </div>
                  <div className="sub">{w.pinyin}</div>
                  <div>{w.meaning}</div>
                </div>
              ))}
            </div>
          )}

          {data.grammar.length > 0 && (
            <>
              <h2 className="h2 section-title">{t("realLife.grammarInScene")}</h2>
              <div className="card">
                <ul className="scene-rules" style={{ marginTop: 0 }}>
                  {data.grammar.map((g) => (
                    <li key={g.title}>
                      <b>{g.title}</b> {g.pattern && <span className="sub">· <span lang="zh-CN">{g.pattern}</span></span>}
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}
        </div>
        <aside className="ws-side">
          <TierCard tier={data.tier} rules={data.rules} />
        </aside>
      </div>
    </Layout>
  );
}
