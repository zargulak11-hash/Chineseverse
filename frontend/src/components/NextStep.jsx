import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useApi } from "../hooks/useApi.js";
import Icon from "./Icon.jsx";

// "What should I do next?" -- answered everywhere from GET /api/journey
// (services/journey.py), which reads only the learner's own records. The
// hero sits at the top of the Dashboard and the journey page; the bar ends a
// practice round, so finishing anything leads straight on.

export function nextTitle(t, next) {
  if (!next) return "";
  if (next.kind === "foundation") return t(`journey.step.${next.key}.title`);
  if (next.kind === "lesson") return t("journey.next.lesson", { title: next.title });
  if (next.kind === "review") return t("journey.next.review", { count: next.count });
  if (next.kind === "exam") return t("journey.next.exam", { level: next.level });
  return t("journey.next.stories");
}

export function nextWhy(t, next) {
  if (!next) return "";
  if (next.kind === "foundation") return t(`journey.step.${next.key}.what`);
  return t(`journey.nextWhy.${next.kind}`);
}

export function NextStepHero({ journey }) {
  const { t } = useTranslation();
  const next = journey?.next;
  if (!next) return null;
  const steps = journey.foundation?.steps || [];
  const n = steps.findIndex((s) => s.key === next.key) + 1;
  return (
    <section className="next-hero" aria-labelledby="next-hero-title">
      <div className="next-hero-body">
        <div className="page-eyebrow"><Icon name="route" size={13} /> {t("journey.nextTitle")}</div>
        {next.kind === "foundation" && n > 0 && (
          <span className="next-hero-step">{t("journey.stepOf", { n, total: steps.length })}</span>
        )}
        <h2 className="next-hero-title" id="next-hero-title">{nextTitle(t, next)}</h2>
        <p className="sub">{nextWhy(t, next)}</p>
        <div className="row" style={{ gap: 12, marginTop: 16, flexWrap: "wrap" }}>
          <Link to={next.to} className="btn primary next-hero-go">
            {t(journey.foundation?.done ? "journey.continue" : "journey.go")} <Icon name="arrowRight" size={16} />
          </Link>
          <Link to="/journey" className="btn ghost">{t("journey.allSteps")}</Link>
        </div>
      </div>
      {next.kind === "foundation" && steps.length > 0 && (
        <ol className="next-hero-steps" aria-label={t("journey.foundationTitle")}>
          {steps.map((s, i) => (
            <li key={s.key} className={`is-${s.status}`}
                title={`${t(`journey.step.${s.key}.title`)} — ${t(`journey.status.${s.status}`)}`}>
              <span className="next-dot" aria-hidden="true">{s.status === "done" ? <Icon name="check" size={12} /> : i + 1}</span>
              <span className="next-dot-label">{t(`journey.step.${s.key}.title`)}</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

// A compact "Next: ..." line for the end of an activity.
export default function NextStepBar() {
  const { t } = useTranslation();
  const { data } = useApi("/journey");
  const next = data?.next;
  if (!next) return null;
  return (
    <div className="next-bar" role="status">
      <span className="next-bar-label"><Icon name="route" size={15} /> {t("journey.nextTitle")}</span>
      <b className="next-bar-title">{nextTitle(t, next)}</b>
      <Link to={next.to} className="btn primary small">
        {t("journey.continue")} <Icon name="arrowRight" size={14} />
      </Link>
    </div>
  );
}
