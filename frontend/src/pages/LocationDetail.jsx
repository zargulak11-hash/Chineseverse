import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

export default function LocationDetail() {
  const { t } = useTranslation();
  const { slug } = useParams();
  const { data: loc, error } = useApi(`/world/locations/${slug}`);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!loc) return <Layout><Loading>{t("pages.locationDetail.entering")}</Loading></Layout>;

  return (
    <Layout>
      <Link to="/world" className="sub">← {t("pages.locationDetail.worldMap")}</Link>
      <div className="row spread" style={{ marginTop: 10 }}>
        <div className="row">
          <span style={{ fontSize: 44 }}>{loc.icon}</span>
          <div>
            <h1 className="h1">{loc.name}</h1>
            <p className="sub">{loc.kind}</p>
          </div>
        </div>
      </div>
      <p className="sub" style={{ marginTop: 10 }}>{loc.description}</p>

      {loc.status !== "unlocked" && (
        <div className="card center" style={{ marginTop: 20 }}>
          <div style={{ fontSize: 40 }}>🔒</div>
          <p>
            {loc.status === "next"
              ? t("pages.locationDetail.almostThere")
              : t("pages.locationDetail.stillLocked")}
          </p>
        </div>
      )}

      {loc.npcs?.length > 0 && (
        <div style={{ marginTop: 20 }}>
          <h2 className="h2">{t("pages.locationDetail.peopleHere")}</h2>
          <div className="grid cards">
            {loc.npcs.map((n) => (
              <div key={n.id} className="card">
                <b>{n.name}</b>
                <span className="badge accent">{n.role}</span>
                <p className="sub" style={{ fontSize: 12.5, marginTop: 8 }}>{n.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {loc.scenarios?.length > 0 && (
        <div style={{ marginTop: 22 }}>
          <h2 className="h2">{t("pages.locationDetail.conversations")}</h2>
          <div className="col">
            {loc.scenarios.map((s) => (
              <div key={s.id} className="card">
                <div className="row spread">
                  <div className="row">
                    <span className="ic">
                      <Icon name={s.is_case ? "search" : "chat"} size={16} />
                    </span>
                    <div>
                      <b>{s.title}</b>
                      <p className="sub" style={{ fontSize: 12 }}>{s.description}</p>
                    </div>
                  </div>
                  <div className="row">
                    <span className="ilb">HSK {s.min_hsk_level}</span>
                    <span className="ilb">★{s.difficulty}</span>
                    {s.is_case ? (
                      <Link to={`/cases/${s.slug}`}>
                        <button className="btn small">{t("pages.locationDetail.solveCase")}</button>
                      </Link>
                    ) : (
                      <Link to={`/conversation/${s.slug}`}>
                        <button className="btn small primary">{t("pages.locationDetail.talk")}</button>
                      </Link>
                    )}
                  </div>
                </div>
                {s.requires_voice && <p className="sub" style={{ fontSize: 11.5, marginTop: 6 }}>🎙️ {t("pages.locationDetail.usesVoice")}</p>}
              </div>
            ))}
          </div>
        </div>
      )}
    </Layout>
  );
}