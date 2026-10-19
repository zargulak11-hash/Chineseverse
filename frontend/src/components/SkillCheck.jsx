import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import Icon from "./Icon.jsx";
import { Bar } from "./ui.jsx";

// The skill check (backend services/diagnostic.py, practice source
// "diagnostic"): a short graded round with a few questions per skill at a
// level, and its result skill by skill -- right answers out of asked, the
// weak ones marked, each with where to practise it. Everything shown is
// counted by the server from the stored answers.

export function SkillBreakdown({ skills }) {
  const { t } = useTranslation();
  if (!skills?.length) return null;
  return (
    <ul className="skill-breakdown">
      {skills.map((s) => (
        <li key={s.skill} className={s.weak ? "is-weak" : ""}>
          <div className="row spread" style={{ margin: 0, gap: 8 }}>
            <b>{t(`companionReact.skill.${s.skill}`, { defaultValue: s.skill })}</b>
            <span className={`badge ${s.weak ? "bad" : "good"}`}>
              {t("skillCheck.score", { correct: s.correct, total: s.total })}
            </span>
          </div>
          <Bar value={s.correct} max={Math.max(s.total, 1)} />
          {s.weak && (
            <Link to={s.to} className="btn small">
              <Icon name="target" size={13} /> {t("skillCheck.practise")}
            </Link>
          )}
        </li>
      ))}
    </ul>
  );
}

// The Journey page's card: start a check (at the learner's level or one they
// choose), and the last result with what still needs practice.
export default function SkillCheckCard({ level, check }) {
  const { t } = useTranslation();
  const [chosen, setChosen] = useState(Math.min(Math.max(level || 1, 1), 6));
  const weak = check?.weak || [];
  return (
    <section className="card skill-check" aria-labelledby="skill-check-title">
      <div className="row spread" style={{ margin: 0, gap: 12, flexWrap: "wrap" }}>
        <h2 className="h2" id="skill-check-title"><Icon name="target" size={17} /> {t("skillCheck.title")}</h2>
        {check && <span className="sub">{t("skillCheck.last", { level: check.level })}</span>}
      </div>
      <p className="sub">{t("skillCheck.body")}</p>
      {check && (
        <>
          <SkillBreakdown skills={check.skills} />
          <p className="sub">
            {weak.length > 0
              ? t("skillCheck.weakLeft", { count: weak.length })
              : t("skillCheck.noneWeak")}
          </p>
        </>
      )}
      <div className="row" style={{ gap: 8, flexWrap: "wrap", margin: 0 }} role="group" aria-label={t("skillCheck.levelLabel")}>
        {[1, 2, 3, 4, 5, 6].map((lv) => (
          <button key={lv} type="button" className={`btn small${lv === chosen ? " primary" : " ghost"}`}
                  aria-pressed={lv === chosen} onClick={() => setChosen(lv)}>
            HSK {lv}
          </button>
        ))}
      </div>
      <div className="row" style={{ marginTop: 12 }}>
        <Link to={`/practice?source=diagnostic&level=${chosen}`} className={`btn${check ? "" : " primary"}`}>
          <Icon name="play" size={15} /> {check ? t("skillCheck.again") : t("skillCheck.start")}
        </Link>
      </div>
    </section>
  );
}
