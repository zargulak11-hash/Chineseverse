import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import CompanionFigure from "./CompanionFigure.jsx";
import Icon from "./Icon.jsx";
import WordHelper from "./WordHelper.jsx";
import { speakChinese } from "../zhSpeech.js";

// The panels around the city map of /real-chinese (pages/RealChinese.jsx):
// a place's details, the next suggested stop, how Learning DNA adapts the
// scenes, and the bottom sheet that holds them on phones.

const LINK_LABEL = {
  "/assistant": "nav.assistant", "/sentence": "nav.sentence", "/detective": "nav.detective",
  "/sound-world": "nav.soundWorld", "/ecosystem": "nav.ecosystem", "/voice-companion": "nav.voiceCompanion",
  "/hanzi": "nav.hanzi", "/review": "nav.review", "/duels": "nav.duels", "/vocabulary": "nav.vocabulary",
};

const MOOD = { locked: "encouraging", open: "happy", explored: "proud", mastered: "celebrating" };

function companionLine(t, p) {
  const lit = p.topics.filter((x) => x.lit).length;
  if (p.status === "locked") {
    return t("world.companion.locked", { level: p.min_level });
  }
  if (p.status === "mastered") return t("world.companion.mastered", { score: Math.round(p.scene?.best || 0) });
  if (p.status === "explored") {
    return p.scene?.rounds
      ? t("world.companion.explored", { score: Math.round(p.scene.best) })
      : t("world.companion.exploredOther");
  }
  return p.topics.length ? t("world.companion.freshTopics", { lit, total: p.topics.length }) : t("world.companion.fresh");
}

function Greeting({ g, onWord, picked }) {
  const { t } = useTranslation();
  if (!g) return null;
  return (
    <div className="lw-greeting">
      <span className="speaker">
        <span lang="zh-CN">{g.speaker?.zh}</span>
        {g.speaker?.role && g.speaker.role !== g.speaker.zh && <> · {g.speaker.role}</>}
      </span>
      <p lang="zh-CN">
        {g.tokens.map((tk, i) =>
          tk.word_id ? (
            <button key={i} type="button" className={`net-word${picked === tk.word_id ? " is-selected" : ""}`}
                    onClick={() => onWord(tk.word_id)} title={tk.meaning}>
              {tk.text}
            </button>
          ) : (
            <span key={i}>{tk.text}</span>
          )
        )}
        <button type="button" className="btn small ghost net-say" onClick={() => speakChinese(g.zh)}
                aria-label={t("companionReact.hear")} title={t("companionReact.hear")}>
          <Icon name="ear" size={12} />
        </button>
      </p>
      {g.py && <span className="pinyin">{g.py}</span>}
      <span className="sub lw-hint">{t("world.tapWords")}</span>
    </div>
  );
}

// The extra states a place can be in, as badges (map card, panel, list).
export function StateBadges({ p, recommended, current }) {
  const { t } = useTranslation();
  return (
    <>
      {current && <span className="badge accent">{t("world.state.current")}</span>}
      {recommended && <span className="badge accent">{t("world.state.recommended")}</span>}
      {p.new && <span className="badge accent">{t("world.state.new")}</span>}
      {p.visited && <span className="badge">{t("world.state.visited")}</span>}
    </>
  );
}

function recommendReason(t, rec) {
  if (!rec) return "";
  if (rec.reason === "skill") return t("world.recommend.skill", { skill: t(`companionReact.skill.${rec.skill}`).toLowerCase() });
  if (rec.reason === "words") return t("world.recommend.words", { count: rec.known });
  return t("world.recommend.next");
}

export function NextStopCard({ rec, place, onShow, compact }) {
  const { t } = useTranslation();
  if (!rec || !place) return null;
  // Over the map it is only a chip -- the city stays in view; the reason is
  // in the place's details once it opens.
  if (compact) {
    return (
      <button type="button" className="lw-nextstop" onClick={() => onShow(place.key)} title={recommendReason(t, rec)}>
        <span className="lw-nextstop-k">{t("world.state.recommended")}</span>
        <span aria-hidden="true">{place.icon}</span>
        <b>{t(`world.place.${place.key}.name`)}</b>
        <Icon name="chevronRight" size={14} />
      </button>
    );
  }
  return (
    <div className="card side-card lw-next">
      <p className="side-title">{t("world.recommend.title")}</p>
      <div className="row" style={{ margin: 0, gap: 12 }}>
        <span className="scene-icon" aria-hidden="true">{place.icon}</span>
        <b>{t(`world.place.${place.key}.name`)}</b>
      </div>
      <p className="sub" style={{ marginTop: 8 }}>{recommendReason(t, rec)}</p>
      <button type="button" className="btn small" onClick={() => onShow(place.key)}>
        <Icon name="mapPin" size={13} /> {t("world.recommend.show")}
      </button>
    </div>
  );
}

export default function PlacePanel({ p, animal, onClose, rec, current, level }) {
  const { t } = useTranslation();
  const [word, setWord] = useState(null);
  useEffect(() => setWord(null), [p.key]);
  const status = t(`world.status.${p.status}`);
  return (
    <div className="lw-panel" aria-live="polite">
      <div className="row spread" style={{ margin: 0, gap: 8 }}>
        <div className="row" style={{ margin: 0, gap: 12, minWidth: 0 }}>
          <span className="scene-icon" aria-hidden="true">{p.icon}</span>
          <div style={{ minWidth: 0 }}>
            <h2 className="h2" style={{ margin: 0 }}>{t(`world.place.${p.key}.name`)}</h2>
            <span className="sub">{t(`world.district.${p.district}`)}</span>
          </div>
        </div>
        {onClose && (
          <button type="button" className="icon-btn" onClick={onClose} aria-label={t("pages.hanzi.close")}>
            <Icon name="x" size={15} />
          </button>
        )}
      </div>
      <div className="row lw-badges" style={{ gap: 6, flexWrap: "wrap", margin: "12px 0 0" }}>
        <span className={`badge ${p.status === "mastered" ? "good" : p.status === "locked" ? "" : "accent"}`}>{status}</span>
        {p.status !== "locked" && p.theme.total > 0 && (
          <span className="badge">{t("world.wordsKnown", { known: p.theme.known, total: p.theme.total })}</span>
        )}
        <StateBadges p={p} recommended={rec?.key === p.key} current={current} />
      </div>
      {rec?.key === p.key && <p className="sub lw-rec-why lw-peek-hide">{recommendReason(t, rec)}</p>}
      <p className="sub lw-peek-hide" style={{ marginTop: 8 }}>{t(`world.place.${p.key}.desc`)}</p>

      {p.status !== "locked" && (
        <>
          <div className="lw-actions">
            {p.scene && (
              <Link to={`/practice?source=scene&scene=${p.scene.slug}`} className="btn primary">
                <Icon name="play" size={15} /> {p.scene.rounds ? t("world.sceneAgain") : t("world.sceneStart")}
              </Link>
            )}
            {p.gateway && (
              <Link to={p.gateway} className={`btn ${p.scene ? "" : "primary"}`}>
                <Icon name="arrowRight" size={15} /> {t(`world.place.${p.key}.enter`)}
              </Link>
            )}
            {!p.scene && !p.gateway && p.topics.length > 0 && (
              <Link to={`/sentence?text=${encodeURIComponent(p.topics[0].sentence)}`} className="btn primary">
                <Icon name="sparkles" size={15} /> {t("world.learnHere")}
              </Link>
            )}
            {p.scene && (
              <Link to={`/real-chinese/${p.scene.slug}`} className="btn small ghost">{t("world.sceneDetails")}</Link>
            )}
          </div>
          {p.scene && (
            <p className="sub" style={{ marginTop: 8 }}>
              {p.scene.rounds
                ? t("world.sceneRecord", { best: Math.round(p.scene.best), count: p.scene.rounds })
                : t("world.sceneNew", { count: p.scene.exchanges })}
            </p>
          )}
        </>
      )}

      <div className={`companion-reaction mood-${MOOD[p.status]} lw-companion-line`}>
        {animal?.slug && <CompanionFigure slug={animal.slug} mood={MOOD[p.status]} size={56} />}
        <p className="cr-line" style={{ margin: 0 }}>{companionLine(t, p)}</p>
      </div>

      {p.status === "locked" ? (
        // A locked place shows only what opens it: its HSK level. Its words,
        // talks and scene stay closed (the server doesn't even send them).
        <div className="lw-section">
          <p className="side-title">{t("world.toOpen")}</p>
          <p className="sub">{t("world.toOpenText", { level: p.min_level, current: level })}</p>
          <Link to="/roadmap" className="btn small" style={{ marginTop: 4 }}>
            <Icon name="trending" size={13} /> {t("world.toRoadmap")}
          </Link>
        </div>
      ) : (
        <>
          <Greeting g={p.greeting} onWord={setWord} picked={word} />

          {p.talks.length > 0 && (
            <div className="lw-section">
              <p className="side-title">{t("world.people")}</p>
              <ul className="lw-list-plain">
                {p.talks.map((tk) => (
                  <li key={tk.slug}>
                    {tk.locked ? (
                      <span className="lw-talk is-locked">
                        <Icon name="lock" size={13} /> {tk.title}
                        <span className="badge">HSK {tk.min_level}</span>
                      </span>
                    ) : (
                      <Link to={`/real-chinese/${tk.case ? "case" : "talk"}/${tk.slug}?place=${p.key}`} className="lw-talk">
                        <Icon name={tk.case ? "search" : "mic"} size={13} /> {tk.title}
                        {tk.tried && <span className="badge good">{t("world.talked")}</span>}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {p.topics.length > 0 && (
            <div className="lw-section">
              <p className="side-title">{t("world.topics")}</p>
              <ul className="lw-topics">
                {p.topics.map((tp) => (
                  <li key={tp.key} className={`lw-topic${tp.lit ? " is-lit" : ""}`}>
                    <div className="row spread" style={{ margin: 0, gap: 8 }}>
                      <b>{t(`world.topic.${tp.key}`)}</b>
                      <span className={`badge ${tp.lit ? "good" : ""}`}>{tp.lit ? t("world.topicLit") : t("world.topicDim")}</span>
                    </div>
                    <div className="chip-row" style={{ marginTop: 8 }}>
                      {tp.words.map((w) => (
                        <button key={w.text} type="button" className={`lw-word is-${w.status}`} onClick={() => w.id && setWord(w.id)}>
                          <span lang="zh-CN">{w.text}</span>
                        </button>
                      ))}
                    </div>
                    <Link to={`/sentence?text=${encodeURIComponent(tp.sentence)}`} className="lw-topic-link">
                      <span lang="zh-CN">{tp.sentence}</span> <Icon name="arrowRight" size={12} />
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {(p.sound || p.internet.length > 0 || p.links?.length > 0) && (
            <div className="lw-section">
              <p className="side-title">{t("world.alsoHere")}</p>
              <ul className="lw-list-plain">
                {p.sound && (
                  <li>
                    <Link to={`/practice?source=sound&env=${p.sound.env}`} className="lw-talk">
                      <Icon name="ear" size={13} /> {t("world.listenHere")}
                      {p.sound.rounds > 0 && <span className="badge good">{Math.round(p.sound.best)}%</span>}
                    </Link>
                  </li>
                )}
                {(p.links || []).filter((to) => LINK_LABEL[to]).map((to) => (
                  <li key={to}>
                    <Link to={to} className="lw-talk">
                      <Icon name="arrowRight" size={13} /> {t(LINK_LABEL[to])}
                    </Link>
                  </li>
                ))}
                {p.internet.map((it) => (
                  <li key={it.slug}>
                    <Link to={`/internet/${it.slug}`} className="lw-talk">
                      <span aria-hidden="true">{it.icon}</span> <span lang="zh-CN">{it.title}</span>
                      {it.read && <span className="badge good">{Math.round(it.best)}%</span>}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}

      {word && (
        <div className="lw-section">
          <WordHelper wordId={word} onClose={() => setWord(null)} />
        </div>
      )}
    </div>
  );
}

// On a phone the chosen place's details are a bottom sheet: a peek (name,
// state, the main action) that drags or taps open to most of the screen,
// and down to close. The map stays visible and usable above it.
export function BottomSheet({ children, label, onClose }) {
  const { t } = useTranslation();
  const [full, setFull] = useState(false);
  const drag = useRef(null);
  const [dy, setDy] = useState(0);
  const end = () => {
    if (drag.current === null) return;
    if (dy > 70) {
      if (full) setFull(false);
      else onClose();
    } else if (dy < -50) setFull(true);
    drag.current = null;
    setDy(0);
  };
  return (
    <aside className={`lw-bottomsheet${full ? " is-full" : ""}`} aria-label={label}
           style={dy ? { transform: `translateY(${Math.max(dy, full ? 0 : -40)}px)`, transition: "none" } : undefined}>
      <button type="button" className="lw-grip" aria-expanded={full}
              aria-label={full ? t("world.sheet.collapse") : t("world.sheet.expand")}
              onClick={() => setFull((f) => !f)}
              onTouchStart={(e) => { drag.current = e.touches[0].clientY; }}
              onTouchMove={(e) => drag.current !== null && setDy(e.touches[0].clientY - drag.current)}
              onTouchEnd={end} onTouchCancel={end}>
        <span aria-hidden="true" />
      </button>
      <div className="lw-bottomsheet-body">{children}</div>
    </aside>
  );
}

export function AdaptationCard({ ad, tier }) {
  const { t } = useTranslation();
  return (
    <div className="card side-card">
      <p className="side-title">{t("world.adaptTitle")}</p>
      <span className="badge accent">{t(`realLife.tier.${tier}`)}</span>
      <ul className="scene-rules">
        <li>{t(`world.adapt.speech.${ad.speech}`, { value: Math.round(ad.listening) })}</li>
        <li>{t(`world.adapt.words.${ad.words}`, { value: Math.round(ad.vocabulary) })}</li>
        <li>{t(`world.adapt.grammar.${ad.grammar}`, { value: Math.round(ad.grammar_value) })}</li>
      </ul>
      {!ad.evidence && <p className="sub">{t("world.adaptNoEvidence")}</p>}
      <Link to="/dna" className="btn small ghost" style={{ marginTop: 8 }}>{t("dashboard.fullDna")}</Link>
    </div>
  );
}
