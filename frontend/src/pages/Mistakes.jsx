import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import NextStepBar from "../components/NextStep.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";
import { mistakeView } from "../mistakes.js";
import { speakChinese } from "../zhSpeech.js";

// The mistake notebook (错题本). Two kinds of entries, both read from the
// learner's own answers:
//   mix-ups   pairs they took for each other (GET /api/mistakes/mixups,
//             services/mixups.py) -- drilled side by side until told apart;
//   mistakes  everything else they missed (GET /api/mistakes), grouped by
//             what it is, each with where it is actually earned back.
// Nothing here marks anything learned: mastery only ever comes from
// answering correctly again (reinforce_mistake / the mix-up replay). The
// "test yourself" pass is a self-check that records nothing -- it ends in
// the graded practice that does.

// Where each mistake type is earned back. Words, characters and grammar
// points return in Review; a character missed while writing is re-traced on
// its page; tone and pronunciation slips come from speaking, and the
// pronunciation course in Sound World is where tones are trained (they used
// to send the learner to Duels, which never clears them).
const PRACTICE_ROUTE = {
  word: "/review",
  hanzi: "/review",
  character: "/review",
  hanzi_write: "/hanzi",
  pinyin: "/sound-world",
  tone: "/sound-world",
  grammar: "/review",
};
const GROUP_OF = {
  word: "word", hanzi: "hanzi", character: "hanzi", hanzi_write: "hanzi",
  tone: "sound", pinyin: "sound", grammar: "grammar",
};
const GROUPS = ["word", "hanzi", "sound", "grammar", "other"];
const GROUP_ICON = { word: "type", hanzi: "pen", sound: "ear", grammar: "route", other: "bookmark" };

// Cases log grammar mistakes against the scenario slug (ascii-kebab), which
// only the living world can re-test; grammar-point mistakes go to Review.
function practiceRoute(m) {
  if (m.mistake_type === "grammar" && /^[a-z0-9-]+$/.test(m.reference)) return `/real-chinese/case/${m.reference}`;
  return PRACTICE_ROUTE[m.mistake_type] || "/review";
}

const groupOf = (m) => GROUP_OF[m.mistake_type] || "other";
const CJK = "\\u3400-\\u9fff";
const hasChinese = (s) => new RegExp(`[${CJK}]`).test(s || "");
// Stored answers can carry their pinyin ("是 shì"): only the Chinese is spoken.
const say = (s) => speakChinese((String(s).match(new RegExp(`[${CJK}，。！？、]+`, "g")) || []).join(""));

// What the self-check asks, and what it then reveals. Only entries where
// the question and the answer differ can be asked (a word saved without
// its gloss has nothing to hide behind).
function quizOf(m) {
  const v = mistakeView(m);
  if (v.zh) return v.gloss ? { ask: v.gloss, answer: v.zh, mine: v.chose } : null;
  return m.correct_answer && v.text && v.text !== m.correct_answer ? { ask: v.text, answer: m.correct_answer, mine: v.said } : null;
}

function Side({ s }) {
  return (
    <button type="button" className="mixup-side" onClick={() => speakChinese(s.hanzi)}>
      <b lang="zh-CN">{s.hanzi}</b>
      {s.pinyin && <span className="sub">{s.pinyin}</span>}
      {s.meaning && <span className="mixup-meaning">{s.meaning}</span>}
    </button>
  );
}

function MixupCard({ p }) {
  const { t } = useTranslation();
  return (
    <div className="card mixup-card">
      <div className="mixup-pair">
        <Side s={p.a} />
        <span className="mixup-vs" aria-hidden="true">≠</span>
        <Side s={p.b} />
      </div>
      <div className="mixup-meta">
        <span className="badge bad">{t("pages.mistakes.confused", { count: p.confused })}</span>
        <span className="sub">{t("pages.mistakes.toldApart", { done: p.told_apart, need: p.resolve_after })}</span>
      </div>
      <Bar value={p.told_apart} max={p.resolve_after} />
    </div>
  );
}

// How often it was missed, as marks rather than a number to decode.
function Pips({ n }) {
  const { t } = useTranslation();
  const shown = Math.min(n, 5);
  return (
    <span className="nb-pips" title={t("pages.mistakes.missedTimes", { count: n })} aria-label={t("pages.mistakes.missedTimes", { count: n })}>
      {Array.from({ length: shown }, (_, i) => <i key={i} />)}
      {n > 5 && <span>+{n - 5}</span>}
    </span>
  );
}

// One notebook line: the thing itself, then the answer given against the
// right one, then how often and where to earn it back.
function Entry({ m, onPractice }) {
  const { t } = useTranslation();
  const v = mistakeView(m);
  const lead = v.zh || v.text;
  const mine = v.zh ? v.chose : v.said;
  const right = v.zh ? null : m.correct_answer;
  return (
    <li className={`nb-entry${m.due_for_review ? " is-due" : ""}`}>
      <div className="nb-lead">
        <span className={v.zh ? "nb-zh" : "nb-text"} lang={hasChinese(lead) ? "zh-CN" : undefined}>{lead}</span>
        {hasChinese(lead) && (
          <button type="button" className="icon-btn nb-say" onClick={() => say(v.zh || lead)} aria-label={t("pages.mistakes.listen")}>
            <Icon name="volume" size={15} />
          </button>
        )}
      </div>
      <div className="nb-body">
        {v.zh && v.gloss && <p className="nb-gloss">{v.gloss}</p>}
        {(mine || right) && (
          <p className="nb-compare">
            {mine && (
              <span className="nb-wrong">
                <span className="nb-tag">{v.zh ? t("pages.mistakes.youChose") : t("pages.mistakes.youSaid")}</span>
                <s lang={hasChinese(mine) ? "zh-CN" : undefined}>{mine}</s>
              </span>
            )}
            {right && (
              <span className="nb-right">
                <span className="nb-tag">{t("pages.mistakes.correct")}</span>
                <b lang={hasChinese(right) ? "zh-CN" : undefined}>{right}</b>
              </span>
            )}
          </p>
        )}
      </div>
      <div className="nb-side">
        {m.due_for_review ? <span className="badge accent">{t("pages.mistakes.dueNow")}</span> : <Pips n={m.occurrences} />}
        <button type="button" className="btn small" onClick={() => onPractice(m)}>
          {t("pages.mistakes.practiceThis")} <Icon name="arrowRight" size={13} />
        </button>
      </div>
    </li>
  );
}

// The focused pass: one entry at a time, the answer hidden until asked for.
function SelfCheck({ items, onPractice, onClose }) {
  const { t } = useTranslation();
  const [i, setI] = useState(0);
  const [shown, setShown] = useState(false);
  const done = i >= items.length;
  const cur = items[i];
  const q = cur && quizOf(cur);

  function next() {
    setShown(false);
    setI((x) => x + 1);
  }

  return (
    <section className="card nb-focus" aria-labelledby="nb-focus-title" data-self-animate="true">
      <div className="nb-focus-head">
        <h2 className="h2" id="nb-focus-title">{t("pages.mistakes.focusTitle")}</h2>
        {!done && <span className="sub">{t("pages.mistakes.focusCount", { n: i + 1, total: items.length })}</span>}
        <button type="button" className="icon-btn nb-close" onClick={onClose} aria-label={t("pages.mistakes.focusClose")}>
          <Icon name="x" size={16} />
        </button>
      </div>
      <div className="nb-focus-bar" aria-hidden="true"><span style={{ width: `${(Math.min(i, items.length) / items.length) * 100}%` }} /></div>
      {done ? (
        <div className="nb-focus-card">
          <p className="nb-focus-done">{t("pages.mistakes.focusDone")}</p>
          <div className="row" style={{ justifyContent: "center", flexWrap: "wrap" }}>
            <Link to="/review" className="btn primary">{t("pages.mistakes.reviewNow")}</Link>
            <button type="button" className="btn ghost" onClick={onClose}>{t("pages.mistakes.focusClose")}</button>
          </div>
        </div>
      ) : (
        <div className="nb-focus-card" aria-live="polite">
          <span className="nb-tag">{t(`pages.mistakes.group.${groupOf(cur)}`)}</span>
          <p className="nb-focus-ask" lang={hasChinese(q.ask) ? "zh-CN" : undefined}>{q.ask}</p>
          {!shown ? (
            <>
              <p className="sub">{t("pages.mistakes.focusPrompt")}</p>
              <button type="button" className="btn primary" onClick={() => setShown(true)}>
                <Icon name="eye" size={15} /> {t("pages.mistakes.reveal")}
              </button>
            </>
          ) : (
            <>
              <div className="nb-focus-answer">
                <b lang={hasChinese(q.answer) ? "zh-CN" : undefined}>{q.answer}</b>
                {hasChinese(q.answer) && (
                  <button type="button" className="icon-btn nb-say" onClick={() => say(q.answer)} aria-label={t("pages.mistakes.listen")}>
                    <Icon name="volume" size={16} />
                  </button>
                )}
              </div>
              {q.mine && (
                <p className="nb-compare" style={{ justifyContent: "center" }}>
                  <span className="nb-wrong">
                    <span className="nb-tag">{t("pages.mistakes.lastTime")}</span>
                    <s lang={hasChinese(q.mine) ? "zh-CN" : undefined}>{q.mine}</s>
                  </span>
                </p>
              )}
              <div className="row" style={{ justifyContent: "center", flexWrap: "wrap" }}>
                <button type="button" className="btn" onClick={() => onPractice(cur)}>{t("pages.mistakes.practiceThis")}</button>
                <button type="button" className="btn primary" onClick={next}>
                  {t("pages.mistakes.focusNext")} <Icon name="arrowRight" size={14} />
                </button>
              </div>
            </>
          )}
        </div>
      )}
      <p className="sub nb-focus-note"><Icon name="alert" size={12} /> {t("pages.mistakes.focusNote")}</p>
    </section>
  );
}

export default function Mistakes() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data, setData, error, setError } = useApi("/mistakes");
  const { data: mix, error: mixError } = useApi("/mistakes/mixups");
  const [tab, setTab] = useState("all");
  const [focus, setFocus] = useState(false);

  async function practice(m) {
    try {
      const updated = await api.patch(`/mistakes/${m.id}`, { request_retest: true });
      setData((ms) => (ms || []).map((x) => (x.id === m.id ? updated : x)));
    } catch (e) {
      setError(e.message);
    }
    navigate(practiceRoute(m));
  }

  if (error || mixError) return <Layout><Empty>{error || mixError}</Empty></Layout>;
  if (!data || !mix) return <Layout><Loading /></Layout>;

  const open = data.filter((m) => !m.mastered);
  const done = data.filter((m) => m.mastered);
  const grouped = GROUPS.map((g) => [g, open.filter((m) => groupOf(m) === g)])
    .filter(([, list]) => list.length > 0);
  const shownGroups = tab === "all" ? grouped : grouped.filter(([g]) => g === tab);
  const resolveAfter = mix.active[0]?.resolve_after ?? mix.resolved[0]?.resolve_after ?? 3;
  // Due first, then the ones missed most: what the self-check walks through.
  const quiz = [...open]
    .filter((m) => quizOf(m))
    .sort((a, b) => (b.due_for_review - a.due_for_review) || (b.occurrences - a.occurrences));
  const earned = done.length + mix.resolved.length;
  const total = data.length + mix.active.length + mix.resolved.length;

  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="pen" size={13} /> {t("nav.review")}</div>
          <h1 className="h1">{t("pages.mistakes.title")}</h1>
          <p className="sub">{t("pages.mistakes.subtitle")}</p>
        </div>
        <div className="kpi-row">
          <div className="kpi"><span className="kpi-value">{mix.active.length}</span><span className="kpi-label">{t("pages.mistakes.mixupsTitle")}</span></div>
          <div className="kpi"><span className="kpi-value">{open.length}</span><span className="kpi-label">{t("pages.mistakes.stillWorking")}</span></div>
          <div className="kpi"><span className="kpi-value">{earned}</span><span className="kpi-label">{t("pages.mistakes.mastered")}</span></div>
        </div>
      </header>

      <div className="ws">
        <div className="ws-main">
          {focus && quiz.length > 0 && (
            <SelfCheck items={quiz} onPractice={practice} onClose={() => setFocus(false)} />
          )}

          <section className="notebook-section nb-mixups">
            <div className="row spread notebook-head">
              <div>
                <h2 className="h2">{t("pages.mistakes.mixupsTitle")}</h2>
                <p className="sub">{t("pages.mistakes.mixupsSub", { n: resolveAfter })}</p>
              </div>
              {mix.active.length > 0 && (
                <Link to="/practice?source=mixups" className="btn primary">
                  {t("pages.mistakes.drill")}
                </Link>
              )}
            </div>
            {mix.active.length > 0 ? (
              <div className="mixup-grid">
                {mix.active.map((p) => <MixupCard key={`${p.item_type}-${p.a.hanzi}-${p.b.hanzi}`} p={p} />)}
              </div>
            ) : (
              <p className="sub">{t("pages.mistakes.mixupsEmpty")}</p>
            )}
          </section>

          <section className="notebook-section">
            <div className="row spread notebook-head">
              <h2 className="h2">{t("pages.mistakes.otherTitle")} ({open.length})</h2>
              {open.length > 0 && (
                <div className="row" style={{ margin: 0, gap: 8, flexWrap: "wrap" }}>
                  {quiz.length > 0 && !focus && (
                    <button type="button" className="btn primary" onClick={() => { setFocus(true); window.scrollTo?.({ top: 0, behavior: "smooth" }); }}>
                      <Icon name="eye" size={15} /> {t("pages.mistakes.focusStart")}
                    </button>
                  )}
                  <Link to="/review" className="btn">{t("pages.mistakes.reviewNow")}</Link>
                </div>
              )}
            </div>
            {grouped.length > 1 && (
              <div className="row nb-tabs" role="group" aria-label={t("pages.mistakes.filterLabel")}>
                {[["all", open.length], ...grouped.map(([g, list]) => [g, list.length])].map(([g, n]) => (
                  <button key={g} type="button" className={`btn small${tab === g ? " primary" : " ghost"}`}
                          aria-pressed={tab === g} onClick={() => setTab(g)}>
                    {g === "all" ? t("pages.mistakes.tabAll") : t(`pages.mistakes.group.${g}`)} <span className="nb-count">{n}</span>
                  </button>
                ))}
              </div>
            )}
            {shownGroups.map(([group, list]) => (
              <div key={group} className="nb-group">
                <p className="side-title notebook-label"><Icon name={GROUP_ICON[group]} size={13} /> {t(`pages.mistakes.group.${group}`)}</p>
                <ul className="nb-list">
                  {list.map((m) => <Entry key={m.id} m={m} onPractice={practice} />)}
                </ul>
              </div>
            ))}
            {data.length === 0 && (
              <>
                <Empty>{t("pages.mistakes.empty")}</Empty>
                <p className="sub empty-teach">{t("pages.mistakes.emptyTeach")}</p>
                <NextStepBar />
              </>
            )}
          </section>
        </div>

        <aside className="ws-side">
          <div className="card side-card">
            <p className="side-title">{t("pages.mistakes.progressTitle")}</p>
            <p className="nb-progress-num"><b>{earned}</b> <span className="sub">/ {total}</span></p>
            <Bar value={earned} max={Math.max(total, 1)} />
            <p className="sub nb-progress-line">{t("pages.mistakes.progressLine")}</p>
          </div>
          {mix.resolved.length > 0 && (
            <div className="card side-card">
              <p className="side-title">{t("pages.mistakes.resolvedTitle")}</p>
              <ul className="notebook-resolved">
                {mix.resolved.map((p) => (
                  <li key={`${p.item_type}-${p.a.hanzi}-${p.b.hanzi}`}>
                    <Icon name="check" size={15} />
                    <b lang="zh-CN">{p.a.hanzi}</b> / <b lang="zh-CN">{p.b.hanzi}</b>
                    <span className="sub">{t("pages.mistakes.resolvedLine", { count: p.told_apart })}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {done.length > 0 && (
            <div className="card side-card">
              <p className="side-title">{t("pages.mistakes.mastered")} ({done.length})</p>
              <ul className="notebook-resolved">
                {done.map((m) => {
                  const v = mistakeView(m);
                  return (
                    <li key={m.id}>
                      <Icon name="check" size={15} />
                      {v.zh ? <><b lang="zh-CN">{v.zh}</b>{v.gloss && <span>{v.gloss}</span>}</> : <span>{v.text}</span>}
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </aside>
      </div>
    </Layout>
  );
}
