import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useApi } from "../hooks/useApi.js";
import Icon from "./Icon.jsx";
import { nextTitle } from "./NextStep.jsx";

// "What is this place, and why would I use it?" -- shown at the top of each
// special feature (Sound World, Detective, Passport, Learning Compass, One
// Sentence, Chinese Internet, Word Ecosystem): what it is, why it helps, when
// it's worth it, one concrete first task, and how it ties into the journey
// (whether /api/journey suggests it now, and the learner's real next step).
// Hiding it leaves a "What is this?" button -- never gone for good. The
// choice is a per-browser convenience, so storage failures just show it.

const KEY = (feature) => `chineseverse_intro_${feature}`;

function readHidden(feature) {
  try {
    return localStorage.getItem(KEY(feature)) === "hidden";
  } catch {
    return false;
  }
}

function writeHidden(feature, hidden) {
  try {
    if (hidden) localStorage.setItem(KEY(feature), "hidden");
    else localStorage.removeItem(KEY(feature));
  } catch {
    /* private mode: the card simply shows again next time */
  }
}

export default function FeatureIntro({ feature }) {
  const { t } = useTranslation();
  const { data: journey } = useApi("/journey");
  const [hidden, setHidden] = useState(() => readHidden(feature));
  const id = `intro-${feature}`;

  function toggle(next) {
    setHidden(next);
    writeHidden(feature, next);
  }

  if (hidden) {
    return (
      <button type="button" className="btn small ghost feature-intro-open" aria-expanded="false" aria-controls={id}
              onClick={() => toggle(false)}>
        <Icon name="sparkles" size={13} /> {t("intro.whatIsThis")}
      </button>
    );
  }
  const ft = journey?.features?.find((f) => f.key === feature);
  const next = journey?.next;
  return (
    <section className="card feature-intro" id={id} aria-labelledby={`${id}-title`}>
      <div className="feature-intro-head">
        <p className="side-title" id={`${id}-title`}>{t("intro.eyebrow")}</p>
        {ft && <span className={`badge ${ft.suggested ? "accent" : ""}`}>{ft.suggested ? t("journey.goodNow") : t("journey.later")}</span>}
        <button type="button" className="icon-btn feature-intro-close" aria-expanded="true" aria-controls={id}
                aria-label={t("intro.hide")} title={t("intro.hide")} onClick={() => toggle(true)}>
          <Icon name="x" size={15} />
        </button>
      </div>
      <dl className="feature-intro-grid">
        {["what", "why", "when"].map((k) => (
          <div key={k}>
            <dt>{t(`intro.${k}`)}</dt>
            <dd>{t(`intro.${feature}.${k}`)}</dd>
          </div>
        ))}
      </dl>
      <p className="feature-intro-task">
        <Icon name="target" size={15} />
        <span><b>{t("intro.firstTask")}</b> {t(`intro.${feature}.task`)}</span>
      </p>
      {next && (
        <p className="sub feature-intro-journey">
          <Icon name="route" size={13} /> {t("intro.journey")}{" "}
          <Link to={next.to}>{nextTitle(t, next)}</Link>
          {" · "}
          <Link to="/journey">{t("journey.allSteps")}</Link>
        </p>
      )}
    </section>
  );
}
