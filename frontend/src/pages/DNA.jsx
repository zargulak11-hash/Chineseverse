import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Bar, Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

const CATS = {
  listening: "ear",
  speaking: "mic",
  reading: "eye",
  writing: "pen",
  grammar: "book",
  vocabulary: "type",
  tones: "chat",
  memory: "search",
  reaction_speed: "trending",
};

export default function DNA() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const focus = params.get("focus");
  const { data: dna, error } = useApi("/dna");

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!dna) return <Layout><Loading>{t("pages.dna.loading")}</Loading></Layout>;

  return (
    <Layout>
      <h1 className="h1">{t("pages.dna.title")}</h1>
      <p className="sub">{t("pages.dna.subtitle")}</p>

      <div className="card" style={{ marginTop: 18, textAlign: "center" }}>
        <div className="h1" style={{ fontSize: 42 }}>{dna.overall.toFixed(1)}</div>
        <p className="sub">{t("pages.dna.overall")}</p>
        <div className="col" style={{ maxWidth: 520, margin: "0 auto" }}>
          <div className="hbar">
            <span className="badge warn">{t("pages.dna.weak")} · {dna.weak_areas.join(", ") || t("pages.dna.none")}</span>
          </div>
          <div className="hbar">
            <span className="badge good">{t("pages.dna.strong")} · {dna.strong_areas.join(", ") || t("pages.dna.none")}</span>
          </div>
        </div>
      </div>

      <div className="grid grid-2" style={{ marginTop: 18 }}>
        {dna.skills.map((s) => {
          const cat = CATS[s.code] || "dna";
          return (
            <div
              key={s.code}
              className="card"
              style={focus === s.code ? { borderColor: "var(--accent-border)", boxShadow: "var(--ring-accent)" } : {}}
            >
              <div className="row spread">
                <div className="row">
                  <span className="ic">
                    <Icon name={cat} size={17} />
                  </span>
                  <div>
                    <b>{s.name}</b>
                    <div className="muted" style={{ fontSize: 11.5 }}>
                      {s.code} · {s.xp} {t("common.xp")}
                    </div>
                  </div>
                </div>
                <BadgeTone s={s} />
              </div>
              <Bar value={s.mastery} alt={s.status === "weak"} />
              <div className="muted" style={{ fontSize: 11.5, marginTop: 6 }}>
                {s.mastery.toFixed(0)}% · {t(`pages.dna.status.${s.status}`)}
              </div>
            </div>
          );
        })}
      </div>
    </Layout>
  );
}

function BadgeTone({ s }) {
  const { t } = useTranslation();
  const tone = s.status === "strong" ? "good" : s.status === "weak" ? "bad" : "accent";
  return <span className={`badge ${tone}`}>{t(`pages.dna.status.${s.status}`)}</span>;
}