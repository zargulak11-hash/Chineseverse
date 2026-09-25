import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api.js";
import { useAuth } from "../auth.js";
import Layout from "../components/Layout.jsx";
import Icon from "../components/Icon.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

// Owner-only user management. The real access control is server-side
// (GET/DELETE /api/admin/users both require app.deps.require_admin) — this
// page and its RequireAdmin route guard only decide what an admin *sees*,
// never what they're *allowed* to do. A non-admin who reaches this route
// some other way still gets a 401/403 from the API itself.
export default function AdminUsers() {
  const { t } = useTranslation();
  const { user: me } = useAuth();
  const { data, error, reload } = useApi("/admin/users");
  const [target, setTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const [flash, setFlash] = useState("");

  async function confirmDelete() {
    if (!target || deleting) return;
    setDeleting(true);
    setDeleteError("");
    try {
      await api.del(`/admin/users/${target.id}`);
      setTarget(null);
      setFlash(t("pages.adminUsers.deleteSuccess", { username: target.username }));
      reload();
    } catch (e) {
      setDeleteError(e.message);
    } finally {
      setDeleting(false);
    }
  }

  if (error) return <Layout><Empty>{error}</Empty></Layout>;

  const users = data?.users || [];

  return (
    <Layout>
      <h1 className="h1">{t("pages.adminUsers.title")}</h1>
      <p className="sub">{t("pages.adminUsers.subtitle")}</p>

      {data && (
        <div className="row" style={{ marginTop: 10 }}>
          <span className="badge accent">{t("pages.adminUsers.totalUsers", { count: data.total })}</span>
        </div>
      )}

      {flash && (
        <div className="card" style={{ marginTop: 14, borderColor: "var(--good)" }}>
          {flash}
        </div>
      )}

      {!data && !error && <Loading>{t("common.loading")}</Loading>}

      {data && users.length === 0 && <Empty>{t("pages.adminUsers.empty")}</Empty>}

      <div className="grid cards" style={{ marginTop: 16 }}>
        {users.map((u) => (
          <div key={u.id} className="card" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: 16 }}>{u.username}</div>
                <div className="sub">{u.email}</div>
              </div>
              <div className="row" style={{ gap: 6 }}>
                {u.is_admin && <span className="badge accent">{t("pages.adminUsers.admin")}</span>}
                <span className={`badge ${u.is_active ? "good" : "bad"}`}>
                  {u.is_active ? t("pages.adminUsers.active") : t("pages.adminUsers.inactive")}
                </span>
              </div>
            </div>

            <div className="statsrow">
              <span className="statpill">#{u.id}</span>
              {u.hsk_level != null && <span className="statpill">HSK {u.hsk_level}</span>}
              {u.current_streak != null && (
                <span className="statpill">{t("pages.adminUsers.streak", { count: u.current_streak })}</span>
              )}
              <span className="statpill">{u.total_xp} {t("common.xp")}</span>
            </div>

            <div className="sub">
              {t("pages.adminUsers.registered", { date: new Date(u.created_at).toLocaleDateString() })}
            </div>

            <button
              type="button"
              className="btn small danger"
              style={{ marginTop: 4, alignSelf: "flex-start" }}
              disabled={u.id === me?.id}
              title={u.id === me?.id ? t("pages.adminUsers.cannotDeleteSelf") : undefined}
              onClick={() => {
                setDeleteError("");
                setTarget(u);
              }}
            >
              <Icon name="x" size={13} style={{ verticalAlign: -2, marginRight: 4 }} />
              {t("pages.adminUsers.deleteUser")}
            </button>
          </div>
        ))}
      </div>

      {target && (
        <div
          className="modal-backdrop"
          onClick={() => !deleting && setTarget(null)}
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100, padding: 16 }}
        >
          <div
            className="card"
            onClick={(e) => e.stopPropagation()}
            style={{ maxWidth: 420, width: "100%" }}
          >
            <h3 style={{ marginTop: 0 }}>{t("pages.adminUsers.confirmTitle")}</h3>
            <p className="sub">
              {t("pages.adminUsers.confirmBody", { username: target.username })}
            </p>
            {deleteError && (
              <div className="card" style={{ borderColor: "var(--bad)", marginBottom: 12 }}>
                {deleteError}
              </div>
            )}
            <div className="row" style={{ justifyContent: "flex-end", gap: 8 }}>
              <button type="button" className="btn ghost" disabled={deleting} onClick={() => setTarget(null)}>
                {t("common.cancel")}
              </button>
              <button type="button" className="btn danger" disabled={deleting} onClick={confirmDelete}>
                {deleting ? t("common.loading") : t("pages.adminUsers.deleteUser")}
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
