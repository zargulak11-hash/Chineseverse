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

// Today's plan (journey.today, services/journey.py): a few real tasks with
// why each is suggested, ticked off only by what the learner did today.
// `skills` maps a Compass skill code to its localized name.
export function TodayPlan({ today, next, skills = {} }) {
  const { t } = useTranslation();
  if (!today?.tasks?.length) return null;
  // A new learner's plan is just the hero's one next step: don't repeat it.
  if (today.tasks.length === 1 && today.tasks[0].key === "learn" && today.rounds === 0) return null;
  const done = today.tasks.length - today.left;
  const title = (task) => {
    if (task.key === "review") return t("today.review", { count: task.count });
    if (task.key === "learn") return nextTitle(t, task.next || next);
    if (task.key === "weak") return t("today.weak", { skill: skills[task.skill] || task.skill });
    if (task.key === "mixups") return t("today.mixups", { count: task.count });
    return t("today.read");
  };
  const why = (task) => {
    if (task.key === "review") return t("today.reviewWhy");
    if (task.key === "learn") return nextWhy(t, task.next || next);
    if (task.key === "weak") return t("today.weakWhy", { mastery: task.mastery });
    if (task.key === "mixups") return t("today.mixupsWhy");
    return t("today.readWhy");
  };
  return (
    <section className="card today-plan" aria-labelledby="today-title">
      <div className="row spread today-head">
        <h2 className="h2" id="today-title"><Icon name="clock" size={17} /> {t("today.title")}</h2>
        <span className={`badge${today.left === 0 ? " good" : ""}`}>{t("today.progress", { done, total: today.tasks.length })}</span>
      </div>
      {today.left === 0 && <p className="sub">{t("today.allDone")}</p>}
      <ul className="today-list">
        {today.tasks.map((task) => (
          <li key={task.key}>
            <Link to={task.to} className={`today-task${task.done ? " is-done" : ""}`}>
              <span className="today-dot" aria-hidden="true">{task.done ? <Icon name="check" size={13} /> : null}</span>
              <span className="today-text">
                <b>{title(task)}</b>
                <span className="sub">{task.done ? t("today.doneToday") : why(task)}</span>
              </span>
              <Icon name="chevronRight" size={15} />
            </Link>
          </li>
        ))}
      </ul>
      <p className="sub today-summary">
        {t("today.summary", { rounds: today.rounds, words: today.words, minutes: today.minutes, goal: today.goal_minutes })}
      </p>
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
