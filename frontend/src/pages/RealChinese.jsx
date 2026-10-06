import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams, useSearchParams } from "react-router-dom";
import Art, { placeArt, sceneArt } from "../components/Art.jsx";
import CompanionMemory from "../components/CompanionMemory.jsx";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";
import { useApi } from "../hooks/useApi.js";
import CityMap from "../components/CityMap.jsx";
import PlacePanel, { AdaptationCard, BottomSheet, NextStopCard } from "../components/CityPanels.jsx";

// Живой китайский — the single living world of ChineseVerse.
//
// GET /api/real-life/world (services/world_map.py) says, from the learner's
// own records only, which places are open, which are explored or mastered,
// which conversation topics their vocabulary has lit up, where they were
// last and how Learning DNA tunes the scenes. This page only draws that:
// places lead into the systems that already exist (Real Chinese scenes on
// the practice engine, the World voice talks and cases, Sound World,
// Chinese Internet, Detective Mode, lessons, Character DNA, the Vocabulary
// Ecosystem, the Passport). Nothing here unlocks or completes anything.

function useNarrow(query = "(max-width: 640px)") {
  const [narrow, setNarrow] = useState(() => typeof window !== "undefined" && window.matchMedia(query).matches);
  useEffect(() => {
    const m = window.matchMedia(query);
    const on = () => setNarrow(m.matches);
    m.addEventListener("change", on);
    return () => m.removeEventListener("change", on);
  }, [query]);
  return narrow;
}

export default function RealChinese() {
  const { t } = useTranslation();
  const { dashboard } = useDashboard() || {};
  const animal = dashboard?.animal;
  const { data, error } = useApi("/real-life/world");
  const [params, setParams] = useSearchParams();
  const narrow = useNarrow();
  // Map first: details open only for a place the learner chose (?place=).
  const selectedKey = params.get("place");

  const byKey = useMemo(() => Object.fromEntries((data?.places || []).map((p) => [p.key, p])), [data]);

  function pick(key) {
    setParams({ place: key }, { replace: true });
  }
  const close = () => setParams({}, { replace: true });
  const open = Boolean(selectedKey);
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => e.key === "Escape" && setParams({}, { replace: true });
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, setParams]);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading>{t("world.loading")}</Loading></Layout>;

  const selected = byKey[selectedKey] || null;
  const pp = data.passport;
  const names = Object.fromEntries(data.places.map((p) => [p.key, t(`world.place.${p.key}.name`)]));
  const W = data.map?.w || 100;
  const H = data.map?.h || 70;
  const order = data.map?.districts || [...new Set(data.places.map((p) => p.district))];
  const rec = data.recommended;
  const panel = selected && (
    <PlacePanel p={selected} animal={animal} rec={rec} current={selected.key === data.current} level={data.level}
                onClose={close} />
  );
  return (
    <Layout variant="world">
      <header className="lw-head">
        <div className="lw-head-title">
          <div className="page-eyebrow"><Icon name="mapPin" size={13} /> {t("nav.realChinese")}</div>
          <h1 className="h1">{t("world.title")}</h1>
        </div>
        <Link to="/passport" className="lw-head-stats lw-passport" aria-label={t("world.passportLink")}>
          {[["mapPin", `${pp.explored}/${pp.total}`, "world.explored"],
            ["play", `${pp.scenes_done}/${pp.scenes_total}`, "world.scenesDone"],
            ["award", `${pp.skills_shown}/${pp.skills_total}`, "world.skillsShown"]].map(([icon, value, label]) => (
            <span key={label} className="lw-stat" title={t(label)}>
              <Icon name={icon} size={13} /> <b>{value}</b> <span className="lw-stat-label">{t(label)}</span>
            </span>
          ))}
        </Link>
      </header>

      <CityMap data={data} W={W} H={H} order={order} names={names} selected={selected} animal={animal}
               onPick={pick} narrow={narrow}
               sheet={panel && <aside className="lw-sheet" aria-label={names[selected.key]}>{panel}</aside>}
               overlay={!selected && <NextStopCard rec={rec} place={byKey[rec?.key]} onShow={pick} compact />} />

      {narrow && panel && <BottomSheet key={selected.key} label={names[selected.key]} onClose={close}>{panel}</BottomSheet>}
      {/* Room at the end of the page so nothing hides behind the sheet. */}
      {narrow && panel && <div className="lw-sheet-spacer" aria-hidden="true" />}

      {narrow && (
        <div className="lw-places" aria-label={t("world.allPlaces")}>
          {order.map((d) => (
            <details key={d} className="lw-district-list" open={selected?.district === d}>
              <summary className="side-title">
                {t(`world.district.${d}`)}
                <span className="sub"> · {data.places.filter((p) => p.district === d && p.status !== "locked").length}/{data.places.filter((p) => p.district === d).length}</span>
              </summary>
              <ul className="lw-list-plain">
                {data.places.filter((p) => p.district === d).map((p) => (
                  <li key={p.key}>
                    <button type="button" className={`lw-place-row is-${p.status}${p.key === selected?.key ? " is-selected" : ""}`}
                            onClick={() => pick(p.key)}>
                      <Art name={placeArt(p.key)} size={40} />
                      <span className="lw-place-name">{t(`world.place.${p.key}.name`)}</span>
                      {p.key === rec?.key && <span className="badge accent">{t("world.state.recommended")}</span>}
                      {p.new && <span className="badge accent">{t("world.state.new")}</span>}
                      <span className={`badge ${p.status === "mastered" ? "good" : p.status === "locked" ? "" : "accent"}`}>
                        {t(`world.status.${p.status}`)}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </details>
          ))}
        </div>
      )}

      {/* Below the map: what travels with you and how the city works. */}
      <section className="lw-below">
        <div className="card lw-below-wide">
          <h2 className="h2">{t("world.companionTitle", { name: animal?.name || t("companionReact.fallbackName") })}</h2>
          <CompanionMemory animal={animal} />
        </div>
        <AdaptationCard ad={data.adaptation} tier={data.tier} />
        <div className="card side-card">
          <p className="side-title">{t("world.howTitle")}</p>
          <p className="sub">{t("world.subtitle")}</p>
          <p className="sub">{t("world.how")}</p>
          <Bar value={data.passport.open} max={data.passport.total} />
          <p className="sub" style={{ marginTop: 8 }}>{t("world.openCount", { open: pp.open, total: pp.total })}</p>
        </div>
      </section>
    </Layout>
  );
}

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

export function RealChineseScene() {
  const { t } = useTranslation();
  const { slug } = useParams();
  const { data, error } = useApi(`/real-life/scenes/${slug}`);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading /></Layout>;

  return (
    <Layout>
      <header className="page-head">
        <div className="scene-head">
          <Art name={sceneArt(data.slug)} size={88} />
          <div>
            <div className="page-eyebrow"><Icon name="mapPin" size={13} /> {t("nav.realChinese")}</div>
            <h1 className="h1">{data.title}</h1>
            <p className="sub">{data.description}</p>
          </div>
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
