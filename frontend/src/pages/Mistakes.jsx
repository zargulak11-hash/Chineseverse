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
// answering correctly again (reinforce_mistake / the mix-up replay).

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

// Cases log grammar mistakes against the scenario slug (ascii-kebab), which
// only the living world can re-test; grammar-point mistakes go to Review.
function practiceRoute(m) {
  if (m.mistake_type === "grammar" && /^[a-z0-9-]+$/.test(m.reference)) return `/real-chinese/case/${m.reference}`;
  return PRACTICE_ROUTE[m.mistake_type] || "/review";
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

// One mistake: a word or character leads with its Chinese and gloss, then
// what the learner chose instead; spoken and grammar slips keep their
// prompt, what was said and the expected answer.
function MistakeText({ m }) {
  const { t } = useTranslation();
  const v = mistakeView(m);
  if (v.zh) {
    return (
      <div className="notebook-item-text">
        <b className="notebook-zh" lang="zh-CN">{v.zh}</b>
        <p className="sub">
          {v.gloss}
          {v.chose && <>{v.gloss && " · "}{t("pages.mistakes.youChose")}: <span lang="zh-CN">{v.chose}</span></>}
        </p>
      </div>
    );
  }
  return (
    <div className="notebook-item-text">
      <b>{v.text}</b>
      <p className="sub">
        {v.said && <>{t("pages.mistakes.youSaid")}: <em>{v.said}</em> · </>}
        {m.correct_answer && <>{t("pages.mistakes.correct")}: <b>{m.correct_answer}</b></>}
      </p>
    </div>
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

export default function Mistakes() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data, setData, error, setError } = useApi("/mistakes");
  const { data: mix, error: mixError } = useApi("/mistakes/mixups");

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
  const grouped = GROUPS.map((g) => [g, open.filter((m) => (GROUP_OF[m.mistake_type] || "other") === g)])
    .filter(([, list]) => list.length > 0);
  const resolveAfter = mix.active[0]?.resolve_after ?? mix.resolved[0]?.resolve_after ?? 3;

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
          <div className="kpi"><span className="kpi-value">{done.length + mix.resolved.length}</span><span className="kpi-label">{t("pages.mistakes.mastered")}</span></div>
        </div>
      </header>

      <section className="notebook-section">
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
        {mix.resolved.length > 0 && (
          <>
            <p className="side-title notebook-label">{t("pages.mistakes.resolvedTitle")}</p>
            <ul className="notebook-resolved">
              {mix.resolved.map((p) => (
                <li key={`${p.item_type}-${p.a.hanzi}-${p.b.hanzi}`}>
                  <Icon name="check" size={15} />
                  <b lang="zh-CN">{p.a.hanzi}</b> / <b lang="zh-CN">{p.b.hanzi}</b>
                  <span className="sub">{t("pages.mistakes.resolvedLine", { count: p.told_apart })}</span>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      <section className="notebook-section">
        <div className="row spread notebook-head">
          <h2 className="h2">{t("pages.mistakes.otherTitle")} ({open.length})</h2>
          {open.length > 0 && (
            <Link to="/review" className="btn">{t("pages.mistakes.reviewNow")}</Link>
          )}
        </div>
        {grouped.map(([group, list]) => (
          <div key={group}>
            <p className="side-title notebook-label">{t(`pages.mistakes.group.${group}`)}</p>
            <div className="col">
              {list.map((m) => (
                <div key={m.id} className="card notebook-item">
                  <MistakeText m={m} />
                  <div className="notebook-item-side">
                    <span className={`badge ${m.due_for_review ? "accent" : "bad"}`}>
                      {m.due_for_review ? t("pages.mistakes.dueNow") : `×${m.occurrences}`}
                    </span>
                    <button type="button" className="btn small" onClick={() => practice(m)}>
                      {t("pages.mistakes.practiceThis")}
                    </button>
                  </div>
                </div>
              ))}
            </div>
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

      {done.length > 0 && (
        <section className="notebook-section">
          <p className="side-title notebook-label">{t("pages.mistakes.mastered")} ({done.length})</p>
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
        </section>
      )}
    </Layout>
  );
}
