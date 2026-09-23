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
  const { data, error } = useApi("/achievements");
  const badges = data || [];

  if (error) return <Layout><Empty>{error}</Empty></Layout>;

  const unlocked = badges.filter((b) => b.unlocked);

  return (
    <Layout>
      <h1 className="h1">Achievements</h1>
      <p className="sub">
        {unlocked.length}/{badges.length} earned
      </p>

      <div className="grid cards" style={{ marginTop: 18 }}>
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
              {b.unlocked ? "Unlocked" : b.category || "hidden"}
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
