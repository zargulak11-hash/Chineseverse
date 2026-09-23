import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import Layout from "../components/Layout.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

// The API has always carried real position_x/position_y per location (0-100
// scale) — the old UI ignored it and rendered a plain card grid instead.
// This draws them on an actual SVG canvas and threads a "road" through them
// in roughly the order the city unlocks, so progression reads as a journey.
const ROUTE_ORDER = [
  "home", "city-street", "hospital", "restaurant",
  "shop", "university", "train-station", "hotel", "airport",
];

const STATUS_LABEL = {
  locked: "Locked",
  next: "Almost there",
  unlocked: "Open",
};

export default function WorldMap() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data, error } = useApi("/world/locations");
  const [hovered, setHovered] = useState(null);

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading>Drawing the map…</Loading></Layout>;

  const locations = data;
  const bySlug = Object.fromEntries(locations.map((l) => [l.slug, l]));
  const routePoints = ROUTE_ORDER.map((s) => bySlug[s]).filter(Boolean);
  const roadPath = routePoints
    .map((l, i) => `${i === 0 ? "M" : "L"} ${l.position_x} ${l.position_y}`)
    .join(" ");
  const hoveredLoc = hovered ? bySlug[hovered] : null;

  return (
    <Layout>
      <h1 className="h1">{t("pages.world.title")}</h1>
      <p className="sub">{t("pages.world.subtitle")}</p>

      <div className="worldmap-wrap" style={{ marginTop: 18 }}>
        <svg viewBox="0 0 100 100" className="worldmap-svg" preserveAspectRatio="xMidYMid meet">
          <defs>
            <radialGradient id="wm-bg" cx="50%" cy="30%" r="80%">
              <stop offset="0%" stopColor="#18181b" />
              <stop offset="100%" stopColor="#09090b" />
            </radialGradient>
          </defs>
          <rect x="0" y="0" width="100" height="100" rx="3" fill="url(#wm-bg)" />
          {roadPath && (
            <path
              d={roadPath}
              fill="none"
              stroke="#2a2a2e"
              strokeWidth="1.4"
              strokeDasharray="2.6 2.2"
              strokeLinecap="round"
            />
          )}
          {locations.map((loc) => (
            <g
              key={loc.slug}
              transform={`translate(${loc.position_x}, ${loc.position_y})`}
              className={`wm-node${loc.status === "locked" ? " locked" : ""}${loc.status === "next" ? " next" : ""}`}
              onMouseEnter={() => setHovered(loc.slug)}
              onMouseLeave={() => setHovered((h) => (h === loc.slug ? null : h))}
              onClick={() => navigate(`/world/${loc.slug}`)}
              role="button"
              aria-label={`${loc.name} — ${STATUS_LABEL[loc.status] || ""}`}
            >
              {loc.status === "next" && (
                <circle r="6.6" fill="none" stroke="#eab244" strokeWidth="0.6" className="wm-pulse" />
              )}
              <circle
                r="5.6"
                fill={loc.status === "locked" ? "#1c1c1f" : loc.status === "next" ? "#eab244" : "#e9e6df"}
                stroke="#09090b"
                strokeWidth="0.7"
                className="wm-dot"
              />
              <text textAnchor="middle" dominantBaseline="central" fontSize="5.4" className="wm-icon">
                {loc.status === "locked" ? "🔒" : loc.icon || "📍"}
              </text>
              <text textAnchor="middle" y="9.5" fontSize="3" className="wm-label">
                {loc.name}
              </text>
            </g>
          ))}
        </svg>

        {hoveredLoc && (
          <div
            className="wm-tooltip"
            style={{ left: `${hoveredLoc.position_x}%`, top: `${hoveredLoc.position_y}%` }}
          >
            <b>{hoveredLoc.icon} {hoveredLoc.name}</b>
            <p className="sub" style={{ fontSize: 12, margin: "4px 0" }}>{hoveredLoc.description}</p>
            {hoveredLoc.status === "locked" && (
              <span className="badge bad">Unlocks HSK {hoveredLoc.unlock_level}</span>
            )}
            {hoveredLoc.status === "next" && <span className="badge warn">Almost there</span>}
            {hoveredLoc.status === "unlocked" && <span className="badge good">Open — click to enter</span>}
          </div>
        )}
      </div>
      <p className="scrollhint center" style={{ marginTop: 10 }}>{t("pages.world.tapToEnter")}</p>
    </Layout>
  );
}
