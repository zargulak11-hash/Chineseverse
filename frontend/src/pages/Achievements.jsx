import { animate, stagger } from "animejs";
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { prefersReducedMotion } from "../anime.js";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Empty } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

const CAT_ICON = {
  voice: "mic",
  social: "swords",
  progress: "trending",
  case_skill: "search",
  default: "award",
};

export default function Achievements() {
  const { t } = useTranslation();
  const { data, error } = useApi("/achievements");
  const badges = data || [];
  const gridRef = useRef(null);

  useEffect(() => {
    const root = gridRef.current;
    if (!root || badges.length === 0) return;
    const targets = Array.from(root.children);
    if (prefersReducedMotion()) {
      targets.forEach((el) => {
        el.style.opacity = 1;
      });
      return;
    }
    animate(targets, {
      opacity: [0, 1],
      translateY: [26, 0],
      scale: [0.88, 1],
      duration: 640,
      delay: stagger(50),
      ease: "outElastic(1, .7)",
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [badges.length]);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;

  const unlocked = badges.filter((b) => b.unlocked);

  return (
    <Layout>
      <h1 className="h1">{t("pages.achievements.title")}</h1>
      <p className="sub">
        {t("pages.achievements.earned", { unlocked: unlocked.length, total: badges.length })}
      </p>

      <div className="grid cards" style={{ marginTop: 18 }} ref={gridRef} data-self-animate="true">
        {badges.map((b) => (
          <div key={b.id} className={`card hover${b.unlocked ? " burst" : ""}`}
            style={
              b.unlocked
                ? { borderColor: "var(--accent-border)", boxShadow: "var(--ring-accent)" }
                : { opacity: 0.6 }
            }>
            <div className={`seal-stamp${b.unlocked ? "" : " locked"}`}>
              <Icon name={b.unlocked ? (CAT_ICON[b.category] || CAT_ICON.default) : "lock"} size={19} />
            </div>
            <b style={{ display: "block", marginTop: 10 }}>{b.title}</b>
            <p className="sub" style={{ fontSize: 12, marginTop: 4 }}>{b.description}</p>
            <span className={`badge ${b.unlocked ? "good" : ""}`}>
              {b.unlocked
                ? t("pages.achievements.unlocked")
                : t(`pages.achievements.category.${b.category}`, { defaultValue: b.category || t("pages.achievements.hidden") })}
            </span>
            {b.unlocked_at && (
              <p className="muted" style={{ fontSize: 11, marginTop: 8 }}>
                {new Date(b.unlocked_at).toLocaleDateString()}
              </p>
            )}
          </div>
        ))}
      </div>
    </Layout>
  );
}
