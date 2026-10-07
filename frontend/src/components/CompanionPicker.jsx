import { useTranslation } from "react-i18next";
import { useApi } from "../hooks/useApi.js";
import AnimalAvatar from "./AnimalAvatar.jsx";
import Icon from "./Icon.jsx";
import { Empty, Loading } from "./ui.jsx";

// The one companion grid: onboarding's first step and /animals (changing the
// companion later) both render it, so there is a single way to pick one --
// POST /api/me/animal, done by the caller's onChoose. useApi refetches on a
// language change, so names and descriptions follow the UI language.
export default function CompanionPicker({ picked, busy, onChoose }) {
  const { t } = useTranslation();
  const { data: animals, error } = useApi("/animals");

  if (error) return <Empty>{error}</Empty>;
  if (!animals) return <Loading />;

  return (
    <div className="grid cards" style={{ marginTop: 16 }}>
      {animals.map((a) => (
        <button
          key={a.id}
          type="button"
          className={`card hover animal${picked === a.id ? " picked" : ""}`}
          data-picked-label={t("pages.animalSelect.picked")}
          aria-pressed={picked === a.id}
          disabled={busy}
          onClick={() => onChoose(a.id)}
        >
          <div className="face">
            <AnimalAvatar slug={a.slug} size={76} state={picked === a.id ? "happy" : "idle"} />
          </div>
          <div className="name">{a.name}</div>
          <div className="species">{a.species}</div>
          <div className="desc">{a.description}</div>
          <div className="ability">
            <Icon name="sparkles" size={12} style={{ verticalAlign: -2, marginRight: 4 }} />
            {a.special_ability}
          </div>
          {a.preferred_mechanics && (
            <div className="ability" style={{ opacity: 0.85 }}>
              <Icon name="target" size={12} style={{ verticalAlign: -2, marginRight: 4 }} />
              {a.preferred_mechanics}
            </div>
          )}
          <div className="statsrow">
            {a.personality && <span className="statpill">{a.personality}</span>}
            {a.tone_style && <span className="statpill">{a.tone_style}</span>}
          </div>
        </button>
      ))}
    </div>
  );
}
