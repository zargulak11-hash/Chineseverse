import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import Layout from "../components/Layout.jsx";
import { Empty, Loading, Stat } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

// Owner-only. GET /api/admin/dashboard requires app.deps.require_admin the
// same way every other /api/admin/* route does — this page and its
// RequireAdmin route guard are UX only, never the security boundary.
export default function AdminHome() {
  const { t } = useTranslation();
  const { data, error } = useApi("/admin/dashboard");

  return (
    <Layout>
      <h1 className="h1">{t("pages.adminHome.title")}</h1>
      <p className="sub">{t("pages.adminHome.subtitle")}</p>

      {error && <Empty>{error}</Empty>}
      {!data && !error && <Loading>{t("common.loading")}</Loading>}

      {data && (
        <div className="card" style={{ marginTop: 16, maxWidth: 320 }}>
          <div className="scores">
            <Stat label={t("pages.adminHome.registeredUsers")} value={data.total_users} tone="var(--accent)" />
          </div>
        </div>
      )}

      <div className="row" style={{ marginTop: 20 }}>
        <Link to="/admin/users" className="btn primary">
          {t("nav.adminUsers")}
        </Link>
      </div>
    </Layout>
  );
}
