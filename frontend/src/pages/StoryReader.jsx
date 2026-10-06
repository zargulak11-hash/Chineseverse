import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api.js";
import Art, { bookArt } from "../components/Art.jsx";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import ReadingHelp, { HELP_ACTIONS } from "../components/ReadingHelp.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";
import { useApi } from "../hooks/useApi.js";
import { speakChinese } from "../zhSpeech.js";
import { BookStats } from "./StoryBook.jsx";

// Reading one chapter (/stories/:slug/read/:n). The page is the Chinese
// text: no translations laid over it. Help is the learner's choice --
//   tap a word        -> its curriculum entry (and its sentence to explain)
//   select any text   -> a small menu: Explain / Pinyin / Translate / Words / Grammar
// Text stays selectable (words are spans, not buttons; a tap that ends a
// drag-selection is ignored). The bookmark follows the sentence being read
// and is saved on the server, so "Continue reading" returns here.

const CJK = /[㐀-鿿]/;
const KEEP = /[㐀-鿿　-〿＀-￯“”‘’…—·]/g;
const SAVE_MS = 1500;

function selectedChinese(sel) {
  return (sel.toString().match(KEEP) || []).join("");
}

export default function StoryReader() {
  const { t } = useTranslation();
  const { slug, n } = useParams();
  const chapter = Number(n) || 1;
  const navigate = useNavigate();
  const { refresh } = useDashboard() || {};
  const { data, error } = useApi(`/stories/${slug}/chapters/${chapter}`);
  const [pinyin, setPinyin] = useState(false);
  const [help, setHelp] = useState(null);
  const [menu, setMenu] = useState(null); // {text, x, y}
  const [playing, setPlaying] = useState(-1);
  const [finish, setFinish] = useState(null);
  const [busy, setBusy] = useState(false);
  const textRef = useRef(null);
  const sentRefs = useRef([]);
  const stopRef = useRef(false);
  const saved = useRef({ chapter: null, position: null });
  const pending = useRef(null);

  useEffect(() => {
    if (!data) return;
    setPinyin(data.support.pinyin === "on");
    setHelp(null);
    setFinish(null);
    saved.current = { chapter, position: data.position };
    // Resume at the bookmark.
    if (data.position > 0) {
      requestAnimationFrame(() => sentRefs.current[data.position]?.scrollIntoView({ block: "center" }));
    } else {
      window.scrollTo(0, 0);
    }
  }, [data?.slug, data?.n]); // eslint-disable-line react-hooks/exhaustive-deps

  // --- the bookmark: the sentence at the reading line, saved after a pause
  const flush = useCallback(() => {
    const pos = pending.current;
    if (pos === null || (saved.current.chapter === chapter && saved.current.position === pos)) return;
    saved.current = { chapter, position: pos };
    api.put(`/stories/${slug}/progress`, { chapter, position: pos }).catch(() => {});
  }, [slug, chapter]);

  useEffect(() => {
    if (!data) return undefined;
    let frame = 0;
    let timer = 0;
    function onScroll() {
      setMenu(null); // the menu is placed at the selection on screen
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const line = window.innerHeight * 0.35;
        let best = 0;
        sentRefs.current.forEach((el, i) => {
          if (el && el.getBoundingClientRect().top <= line) best = i;
        });
        pending.current = best;
        clearTimeout(timer);
        timer = setTimeout(flush, SAVE_MS);
      });
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      cancelAnimationFrame(frame);
      clearTimeout(timer);
      flush();
    };
  }, [data, flush]);

  // --- selection -> the help menu
  useEffect(() => {
    let timer = 0;
    function onSelect() {
      clearTimeout(timer);
      timer = setTimeout(() => {
        const sel = window.getSelection();
        const root = textRef.current;
        if (!sel || sel.isCollapsed || !root || !sel.rangeCount) return setMenu(null);
        const range = sel.getRangeAt(0);
        if (!root.contains(range.commonAncestorContainer)) return setMenu(null);
        const text = selectedChinese(sel);
        if (!CJK.test(text)) return setMenu(null);
        const r = range.getBoundingClientRect();
        setMenu({ text: text.slice(0, 200), x: Math.min(Math.max(r.left + r.width / 2, 120), window.innerWidth - 120), y: r.bottom + 8 });
      }, 250);
    }
    document.addEventListener("selectionchange", onSelect);
    return () => {
      document.removeEventListener("selectionchange", onSelect);
      clearTimeout(timer);
    };
  }, []);

  useEffect(() => () => {
    stopRef.current = true;
    window.speechSynthesis?.cancel();
  }, []);

  if (error) {
    return (
      <Layout>
        <Empty>{error}</Empty>
        <div className="row" style={{ justifyContent: "center", marginTop: 12 }}>
          <Link to={`/stories/${slug}`} className="btn">{t("stories.reader.toBook")}</Link>
          <Link to="/journey" className="btn primary">{t("stories.lockedCta")}</Link>
        </div>
      </Layout>
    );
  }
  if (!data) return <Layout><Loading /></Layout>;

  const sentences = data.paragraphs.flat();
  const rate = data.support.rate;
  const say = (text, onEnd) => speakChinese(text, { profile: { rate, pitch: 1, volume: 1 }, onEnd, whole: true });

  function playFrom(i) {
    if (i >= sentences.length || stopRef.current) {
      setPlaying(-1);
      return;
    }
    setPlaying(i);
    sentRefs.current[i]?.scrollIntoView({ block: "center", behavior: "smooth" });
    say(sentences[i].zh, () => playFrom(i + 1));
  }
  function toggleListen() {
    if (playing >= 0) {
      stopRef.current = true;
      window.speechSynthesis?.cancel();
      setPlaying(-1);
      return;
    }
    stopRef.current = false;
    api.post(`/stories/${slug}/listen`, { chapter }).catch(() => {});
    playFrom(Math.max(0, pending.current ?? 0));
  }

  function openWord(tk, s) {
    const sel = window.getSelection();
    if (sel && !sel.isCollapsed) return; // the tap ended a selection
    setMenu(null);
    setHelp({ mode: "word", wordId: tk.word_id, sentence: s.zh });
    api.post(`/stories/${slug}/lookup`, { word_id: tk.word_id }).catch(() => {});
  }
  function explain(text, focus) {
    setMenu(null);
    window.getSelection()?.removeAllRanges();
    setHelp({ mode: "text", text, focus, key: Date.now() });
  }

  async function finishChapter() {
    setBusy(true);
    try {
      flush();
      const r = await api.post(`/stories/${slug}/chapters/${chapter}/finish`);
      refresh?.();
      if (r.just_completed) {
        setFinish(r);
        window.scrollTo({ top: 0, behavior: "smooth" });
      } else if (r.next_chapter) {
        navigate(`/stories/${slug}/read/${r.next_chapter}`);
      } else {
        navigate(`/stories/${slug}`);
      }
    } catch {
      setBusy(false);
      return;
    }
    setBusy(false);
  }

  const last = data.n === data.total;
  return (
    <Layout>
      <div className="reader-top">
        <Link to={`/stories/${slug}`} className="btn ghost small"><Icon name="arrowLeft" size={13} /> {t("stories.reader.toBook")}</Link>
        <span className="sub reader-where">
          <span lang="zh-CN">《{data.book_title_zh}》</span> · {t("stories.reader.chapterOf", { n: data.n, total: data.total })}
        </span>
        <div className="reader-progress"><Bar value={finish?.book_completed ? 100 : data.percent} /></div>
      </div>

      {finish && (
        <section className="card book-done book-done-celebrate" aria-live="polite">
          <p className="page-eyebrow"><Icon name="award" size={13} /> {t("stories.done.title")}</p>
          <h2 className="h2" lang="zh-CN">《{data.book_title_zh}》</h2>
          <p className="sub">{t("stories.done.body", { title: data.book_title })}</p>
          {finish.stats && <BookStats stats={finish.stats} />}
          <div className="row">
            {finish.next ? (
              <Link to={`/stories/${finish.next.slug}`} className="btn primary">
                <Art name={bookArt(finish.next.slug)} size={28} shape="round" flat />
                {t("stories.done.next")}: <span lang="zh-CN">《{finish.next.title_zh}》</span> <Icon name="arrowRight" size={13} />
              </Link>
            ) : null}
            <Link to="/stories" className="btn ghost">{t("stories.done.library")}</Link>
          </div>
        </section>
      )}

      <div className={`reader${help ? " has-help" : ""}`}>
        <article className="card reader-page" aria-labelledby="chapter-title">
          <header className="reader-head">
            <p className="page-eyebrow">{t("stories.reader.chapterOf", { n: data.n, total: data.total })} · {data.title}</p>
            <h1 className="h1 reader-title" id="chapter-title" lang="zh-CN">{data.title_zh}</h1>
            <div className="row reader-tools">
              <button type="button" className={`btn small${playing >= 0 ? " primary" : ""}`} onClick={toggleListen} aria-pressed={playing >= 0}>
                <Icon name={playing >= 0 ? "stop" : "play"} size={13} /> {playing >= 0 ? t("stories.reader.stop") : t("stories.reader.listen")}
              </button>
              <button type="button" className={`btn small${pinyin ? "" : " ghost"}`} aria-pressed={pinyin} onClick={() => setPinyin((v) => !v)}>
                {t("stories.reader.pinyin")}
              </button>
            </div>
            <p className="sub reader-hint"><Icon name="sparkles" size={13} /> {t("stories.reader.hint")}</p>
          </header>

          <div ref={textRef} className={`reader-text${pinyin ? " with-pinyin" : ""}`} lang="zh-CN">
            {data.paragraphs.map((para, pi) => (
              <p key={pi} className="reader-para">
                {para.map((s) => (
                  <span key={s.i} ref={(el) => (sentRefs.current[s.i] = el)}
                        className={`reader-sentence${playing === s.i ? " is-playing" : ""}`}>
                    <span className="reader-zh">
                      {s.tokens.map((tk, j) => tk.word_id ? (
                        <span key={j} role="button" tabIndex={0}
                              className={`tale-word is-${tk.state}${help?.wordId === tk.word_id ? " is-open" : ""}`}
                              onClick={() => openWord(tk, s)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter" || e.key === " ") {
                                  e.preventDefault();
                                  openWord(tk, s);
                                }
                              }}>
                          {tk.text}
                        </span>
                      ) : tk.name ? (
                        <span key={j} className="reader-name" title={tk.name}>{tk.text}</span>
                      ) : <span key={j}>{tk.text}</span>)}
                    </span>
                    {pinyin && <span className="reader-py" aria-hidden="true">{s.pinyin}</span>}
                  </span>
                ))}
              </p>
            ))}
          </div>

          <ul className="tale-legend sub" aria-label={t("stories.reader.legend")}>
            {["new", "review", "learning", "known"].map((k) => (
              <li key={k}><span className={`tale-word is-${k}`} aria-hidden="true">字</span> {t(`stories.state.${k}`)}</li>
            ))}
          </ul>

          <footer className="reader-foot">
            {data.n > 1 ? (
              <Link to={`/stories/${slug}/read/${data.n - 1}`} className="btn ghost small">
                <Icon name="arrowLeft" size={13} /> {t("stories.reader.prev")}
              </Link>
            ) : <span />}
            <div className="row reader-foot-main">
              {data.questions > 0 && (
                <Link to={`/practice?source=story&story=${slug}&chapter=${data.n}`} className="btn small">
                  {t("stories.book.check")}
                </Link>
              )}
              {data.done && !last ? (
                <Link to={`/stories/${slug}/read/${data.n + 1}`} className="btn primary">
                  {t("stories.reader.next")} <Icon name="arrowRight" size={13} />
                </Link>
              ) : (
                <button type="button" className="btn primary" onClick={finishChapter} disabled={busy}>
                  <Icon name="check" size={14} /> {t(last ? "stories.reader.finishLast" : "stories.reader.finish")}
                </button>
              )}
            </div>
          </footer>
        </article>

        <ReadingHelp key={help?.key || help?.wordId || "none"} slug={slug} chapter={chapter} help={help} rate={rate}
                     onClose={() => setHelp(null)} onExplain={explain} />
      </div>

      {menu && (
        <div className="read-menu" role="toolbar" aria-label={t("stories.help.actions")}
             style={{ left: menu.x, top: Math.min(menu.y, window.innerHeight - 64) }}>
          {HELP_ACTIONS.map((a) => (
            <button key={a} type="button" className="btn small" onMouseDown={(e) => e.preventDefault()}
                    onClick={() => explain(menu.text, a)}>
              {t(`stories.help.${a}`)}
            </button>
          ))}
        </div>
      )}
    </Layout>
  );
}
