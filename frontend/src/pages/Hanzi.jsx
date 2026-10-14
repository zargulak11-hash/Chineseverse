import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import HanziDetail from "../components/HanziDetail.jsx";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

// The characters of one HSK level as a table of tiles -- each the
// character, its reading, and a fill along its foot for recognition (and a
// second for writing, where HSK 3.0 asks for handwriting) -- with one
// character open beside it in full (HanziDetail, inline): hear it, check
// yourself, trace it, write it from memory, see its words. A level used to
// be hundreds of full cards, tens of thousands of pixels tall.

function fold(s) {
  return String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/ü/g, "v")
    .replace(/[\s\d'·-]+/g, "").toLowerCase();
}

const FILTERS = ["all", "due", "writing", "new"];

export default function Hanzi() {
  const { t } = useTranslation();
  const [level, setLevel] = useState(1);
  const { data, setData, error } = useApi(`/hanzi?hsk_level=${level}`);
  const { data: roadmap } = useApi("/hsk/roadmap");
  const chars = data || [];
  const [detail, setDetail] = useState(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const panelRef = useRef(null);

  useEffect(() => {
    setDetail(null);
    setQuery("");
    setFilter("all");
  }, [level]);

  function applyUpdate(updated) {
    setData((items) => (items || []).map((x) => (x.id === updated.id ? { ...x, ...updated } : x)));
  }

  const shown = useMemo(() => {
    const q = query.trim();
    const fq = fold(q);
    return chars.filter((c) => {
      if (filter === "due" && !c.due_for_review) return false;
      if (filter === "writing" && !c.handwriting_tier) return false;
      if (filter === "new" && (c.mastery ?? 0) > 0) return false;
      if (!q) return true;
      return c.character === q || (fq && fold(c.pinyin).startsWith(fq)) || (c.meaning || "").toLowerCase().includes(q.toLowerCase());
    });
  }, [chars, query, filter]);

  function open(ch) {
    setDetail(ch);
    if (window.matchMedia?.("(max-width: 1080px)").matches) panelRef.current?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  }

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  // Without this the empty state ("no characters") flashed while the
  // request was still in flight, even for levels that have 300+ Hanzi.
  if (!data) return <Layout><Loading /></Layout>;

  const counts = {};
  for (const lv of roadmap?.levels || []) counts[lv.level] = lv.hanzi_total;
  const due = chars.filter((c) => c.due_for_review).length;
  const writing = chars.filter((c) => c.handwriting_tier).length;
  const known = chars.filter((c) => (c.mastery ?? 0) >= 80).length;
  const open_ = detail ? chars.find((c) => c.id === detail.id) || detail : null;

  return (
    <Layout>
      <header className="page-head">
        <div>
          <div className="page-eyebrow"><Icon name="pen" size={13} /> HSK {level}</div>
          <h1 className="h1">{t("pages.hanzi.title")}</h1>
          <p className="sub">{t("pages.hanzi.subtitle")}</p>
        </div>
        <div className="kpi-row">
          <div className="kpi"><span className="kpi-value">{chars.length}</span><span className="kpi-label">{t("pages.hanzi.kpiChars")}</span></div>
          <div className="kpi"><span className="kpi-value">{known}</span><span className="kpi-label">{t("pages.vocabulary.kpiKnown")}</span></div>
          <div className="kpi"><span className="kpi-value">{writing}</span><span className="kpi-label">{t("pages.hanzi.handwriting")}</span></div>
        </div>
      </header>

      <div className="dict-bar">
        <label className="dict-search">
          <Icon name="search" size={18} />
          <input className="input" type="search" value={query} onChange={(e) => setQuery(e.target.value)}
                 placeholder={t("pages.hanzi.searchPlaceholder")} aria-label={t("pages.hanzi.searchLabel", { level })} />
        </label>
        <div className="dict-levels" role="group" aria-label={t("pages.vocabulary.levelLabel")}>
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((lv) => (
            <button key={lv} type="button" className={`btn small${level === lv ? " primary" : " ghost"}`}
                    aria-pressed={level === lv} onClick={() => setLevel(lv)}>
              HSK {lv} {counts[lv] > 0 ? <span className="dict-level-n">{counts[lv]}</span> : ""}
            </button>
          ))}
        </div>
      </div>

      {chars.length > 0 && (
        <div className="dict-meta">
          <Link to={`/practice?source=hanzi&level=${level}`} className="btn primary">{t("practice.startLevel", { level })}</Link>
          <div className="row hz-filters" role="group" aria-label={t("pages.hanzi.filterLabel")}>
            {FILTERS.map((f) => (
              <button key={f} type="button" className={`btn small${filter === f ? " primary" : " ghost"}`}
                      aria-pressed={filter === f} onClick={() => setFilter(f)}>
                {t(`pages.hanzi.filter_${f}`)}
                {f === "due" && due > 0 && <span className="dict-level-n">{due}</span>}
              </button>
            ))}
          </div>
        </div>
      )}

      {chars.length === 0 ? (
        <Empty>{t("pages.hanzi.empty")}</Empty>
      ) : (
        <div className="hz">
          <section className="card hz-table-card" aria-label={t("pages.hanzi.title")}>
            <p className="dict-list-head sub" aria-live="polite">
              {t("pages.hanzi.shownCount", { count: shown.length, total: chars.length })}
            </p>
            {shown.length === 0 ? (
              <p className="sub dict-none">{t("pages.vocabulary.noMatch")}</p>
            ) : (
              <ul className="hz-table">
                {shown.map((ch) => (
                  <li key={ch.id}>
                    <button type="button" className={`hz-tile${open_?.id === ch.id ? " is-open" : ""}${ch.due_for_review ? " is-due" : ""}`}
                            onClick={() => open(ch)} aria-pressed={open_?.id === ch.id}
                            aria-label={`${ch.character} ${ch.pinyin} ${ch.meaning || ""}`}>
                      {ch.due_for_review && <span className="hz-due" title={t("pages.vocabulary.due")} aria-hidden="true" />}
                      {ch.handwriting_tier && <span className="hz-pen" title={t("pages.hanzi.handwriting")} aria-hidden="true"><Icon name="pen" size={11} /></span>}
                      <span className="hz-char" lang="zh-CN" aria-hidden="true">{ch.character}</span>
                      <span className="hz-py" aria-hidden="true">{ch.pinyin}</span>
                      <span className="hz-fill" aria-hidden="true">
                        <span style={{ width: `${Math.round(ch.mastery ?? 0)}%` }} />
                        {ch.handwriting_tier && <span className="is-writing" style={{ width: `${Math.round(ch.writing_mastery ?? 0)}%` }} />}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <div className="hz-panel" ref={panelRef}>
            {open_ ? (
              <HanziDetail
                key={open_.id}
                inline
                hanzi={open_}
                level={level}
                onClose={() => setDetail(null)}
                onUpdated={(updated) => {
                  applyUpdate(updated);
                  setDetail(updated);
                }}
              />
            ) : (
              <div className="card hz-empty">
                <span className="hz-empty-char" lang="zh-CN" aria-hidden="true">字</span>
                <p className="sub">{t("pages.hanzi.pickOne")}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </Layout>
  );
}
