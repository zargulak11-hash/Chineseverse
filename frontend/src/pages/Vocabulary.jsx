import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import Layout from "../components/Layout.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";
import { speakChinese } from "../zhSpeech.js";
import Icon from "../components/Icon.jsx";

export default function Vocabulary() {
  const { t } = useTranslation();
  const [level, setLevel] = useState(1);
  const { data, error } = useApi(`/vocab?hsk_level=${level}`);
  const { data: roadmap } = useApi("/hsk/roadmap");
  const words = data || [];
  // Clicking a card only plays it: mastery is earned in the graded
  // practice round (/practice), never by clicking a card.
  const [playing, setPlaying] = useState(null);

  function hear(w) {
    speakChinese(w.simplified, {
      onStart: () => setPlaying(w.id),
      onEnd: () => setPlaying(null),
    });
  }

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading /></Layout>;

  const counts = {};
  for (const lv of roadmap?.levels || []) counts[lv.level] = lv.vocab_total;

  return (
    <Layout>
      <h1 className="h1">{t("pages.vocabulary.title")}</h1>
      <p className="sub">{t("pages.vocabulary.subtitle")}</p>

      <div className="row" style={{ marginTop: 14, flexWrap: "wrap" }}>
        {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((lv) => (
          <button
            key={lv}
            className={`btn small${level === lv ? " primary" : ""}`}
            onClick={() => setLevel(lv)}
          >
            HSK {lv} {counts[lv] > 0 ? `(${counts[lv]})` : ""}
          </button>
        ))}
      </div>

      {words.length > 0 && (
        <div className="row" style={{ marginTop: 14, flexWrap: "wrap", gap: 8 }}>
          <Link to={`/practice?source=vocab&level=${level}`}>
            <button className="btn primary">{t("practice.startLevel", { level })}</button>
          </Link>
          <span className="sub">{t("pages.vocabulary.tapToHear")}</span>
        </div>
      )}

      {words.some((w) => w.due_for_review) && (
        <p className="sub" style={{ marginTop: 14 }}>
          <Icon name="clock" size={13} style={{ verticalAlign: -2 }} /> {t("pages.vocabulary.dueForReview", { count: words.filter((w) => w.due_for_review).length })}
          {words.some((w) => w.slipping) && (
            <> · {t("pages.vocabulary.slippingCount", { count: words.filter((w) => w.slipping).length })}</>
          )}
        </p>
      )}

      <div className="grid cards" style={{ marginTop: 16 }}>
        {words.map((w) => (
          <button
            key={w.id}
            className={`card hover animal${w.due_for_review ? " is-due" : ""}`}
            style={{ textAlign: "center", position: "relative" }}
            onClick={() => hear(w)}
            aria-pressed={playing === w.id}
          >
            {/* A word they knew, well past its review date, says so: it is
                fading (services/srs.is_slipping), not merely due. */}
            {w.due_for_review && (
              <span className={`badge ${w.slipping ? "bad" : "accent"} word-due-badge`}>
                {t(w.slipping ? "pages.vocabulary.slipping" : "pages.vocabulary.due")}
              </span>
            )}
            <div style={{ fontSize: 24, fontWeight: 800 }}>{w.simplified}</div>
            {w.traditional && w.traditional !== w.simplified && (
              <div className="muted" style={{ fontSize: 13 }}>{w.traditional}</div>
            )}
            <div className="sub" style={{ color: "var(--accent2)" }}>{w.pinyin}</div>
            <div className="sub">{w.meanings}</div>
            {w.word_type && (
              <span className="ilb" style={{ marginTop: 6 }}>
                {/* English part-of-speech labels are UI text; raw dictionary
                    POS codes (r, g, nz, ...) have no translation and show as-is. */}
                {t(`wordType.${w.word_type.replace(/[\s-]+/g, "_")}`, { defaultValue: w.word_type })}
              </span>
            )}
            <div style={{ marginTop: 8, width: "100%" }}>
              <Bar value={w.mastery ?? 0} alt />
            </div>
          </button>
        ))}
      </div>
      {words.length === 0 && <Empty>{t("pages.vocabulary.empty")}</Empty>}
    </Layout>
  );
}