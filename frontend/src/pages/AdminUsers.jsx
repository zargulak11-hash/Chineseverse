import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api.js";
import { useAuth } from "../auth.js";
import AnimalAvatar from "../components/AnimalAvatar.jsx";
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
  const { data, setData, error, reload } = useApi("/admin/users");
  const [target, setTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const [toast, setToast] = useState(null);

  // There's no app-wide toast system yet, so this page keeps its own small
  // one: a fixed-position, self-dismissing status message.
  useEffect(() => {
    if (!toast) return undefined;
    const id = setTimeout(() => setToast(null), 4000);
    return () => clearTimeout(id);
  }, [toast]);

  function openConfirm(u) {
    setDeleteError("");
    setTarget(u);
  }

  async function confirmDelete() {
    if (!target || deleting) return;
    setDeleting(true);
    setDeleteError("");
    try {
      await api.del(`/admin/users/${target.id}`);
      // Drop the row immediately so the list never shows a deleted user,
      // then refetch so total/order reflect the database's real state.
      setData((d) =>
        d ? { ...d, total: d.total - 1, users: d.users.filter((u) => u.id !== target.id) } : d
      );
      setToast({ tone: "good", title: t("pages.adminUsers.deleteSuccessGeneric"), detail: target.username });
      setTarget(null);
      reload();
    } catch (e) {
      // The user stays in the list; the dialog stays open with the reason.
      setDeleteError(e.message);
    } finally {
      setDeleting(false);
    }
  }

  const users = data?.users || [];
  const fmtDate = (iso) => new Date(iso).toLocaleDateString();

  const statusBadge = (u) => (
    <span className={`badge ${u.is_active ? "good" : "bad"}`}>
      {u.is_active ? t("pages.adminUsers.active") : t("pages.adminUsers.inactive")}
    </span>
  );

  const identity = (u) => (
    <div className="admin-user-id">
      {/* The user's permanent main companion (chosen during onboarding),
          never their uploaded profile photo and never the Daily Voice
          Companion — see schemas.AdminUserSummary.companion_slug. */}
      <AnimalAvatar slug={u.companion_slug} size={40} />
      <div style={{ minWidth: 0 }}>
        <div style={{ fontWeight: 700 }}>
          {u.username}
          {u.is_admin && (
            <span className="badge accent" style={{ marginLeft: 6 }}>{t("pages.adminUsers.admin")}</span>
          )}
        </div>
        <div className="email">{u.email}</div>
      </div>
    </div>
  );

  const deleteButton = (u) => {
    const isSelf = u.id === me?.id;
    return (
      <button
        type="button"
        className="icon-btn danger"
        disabled={isSelf}
        title={isSelf ? t("pages.adminUsers.cannotDeleteSelf") : t("pages.adminUsers.deleteUser")}
        aria-label={t("pages.adminUsers.deleteAria", { username: u.username })}
        onClick={() => openConfirm(u)}
      >
        <Icon name="trash" size={18} />
      </button>
    );
  };

  return (
    <Layout>
      <h1 className="h1">{t("pages.adminUsers.users")}</h1>
      <p className="sub">{t("pages.adminUsers.subtitle")}</p>

      {data && !error && (
        <div className="row" style={{ marginTop: 10 }}>
          <span className="badge accent">{t("pages.adminUsers.totalUsers", { count: data.total })}</span>
        </div>
      )}

      {error && (
        <div className="card" style={{ marginTop: 16, borderColor: "var(--bad)" }}>
          <div style={{ fontWeight: 700 }}>{t("common.error")}</div>
          <p className="sub">{t("pages.adminUsers.loadFailed")}: {error}</p>
          <button type="button" className="btn small" onClick={reload}>
            {t("pages.adminUsers.retry")}
          </button>
        </div>
      )}

      {!data && !error && <Loading>{t("common.loading")}</Loading>}

      {data && !error && users.length === 0 && <Empty>{t("pages.adminUsers.empty")}</Empty>}

      {data && !error && users.length > 0 && (
        <>
          <div className="card admin-users-table" style={{ marginTop: 16 }}>
            <table className="data">
              <thead>
                <tr>
                  <th>{t("pages.adminUsers.user")}</th>
                  <th>{t("pages.adminUsers.registeredCol")}</th>
                  <th>{t("pages.adminUsers.status")}</th>
                  <th className="col-actions">{t("pages.adminUsers.actions")}</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>{identity(u)}</td>
                    <td>{fmtDate(u.created_at)}</td>
                    <td>{statusBadge(u)}</td>
                    <td className="col-actions">{deleteButton(u)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="admin-users-cards" style={{ marginTop: 16 }}>
            {users.map((u) => (
              <div key={u.id} className="card" style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 8 }}>
                  {identity(u)}
                  <div className="row" style={{ gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                    {statusBadge(u)}
                    <span className="sub">{t("pages.adminUsers.registered", { date: fmtDate(u.created_at) })}</span>
                  </div>
                </div>
                {deleteButton(u)}
              </div>
            ))}
          </div>
        </>
      )}

      {target && (
        <div
          className="modal-backdrop"
          onClick={() => !deleting && setTarget(null)}
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100, padding: 16 }}
        >
          <div
            className="card"
            role="dialog"
            aria-modal="true"
            aria-labelledby="admin-delete-title"
            onClick={(e) => e.stopPropagation()}
            style={{ maxWidth: 420, width: "100%" }}
          >
            <h3 id="admin-delete-title" style={{ marginTop: 0 }}>{t("pages.adminUsers.confirmTitle")}</h3>
            <div className="card" style={{ marginBottom: 12 }}>{identity(target)}</div>
            <p className="sub">
              {t("pages.adminUsers.confirmBody", { username: target.username })}
            </p>
            {deleteError && (
              <div className="card" role="alert" style={{ borderColor: "var(--bad)", marginBottom: 12 }}>
                <div style={{ fontWeight: 700 }}>{t("pages.adminUsers.deleteFailed")}</div>
                <div className="sub">{deleteError}</div>
              </div>
            )}
            <div className="row" style={{ justifyContent: "flex-end", gap: 8 }}>
              <button type="button" className="btn ghost" disabled={deleting} onClick={() => setTarget(null)}>
                {t("common.cancel")}
              </button>
              <button type="button" className="btn danger" disabled={deleting} onClick={confirmDelete}>
                <Icon name="trash" size={14} style={{ verticalAlign: -2, marginRight: 4 }} />
                {deleting ? t("pages.adminUsers.deleting") : t("common.delete")}
              </button>
            </div>
          </div>
        </div>
      )}

      {toast && (
        <div className={`card admin-toast ${toast.tone}`} role="status" aria-live="polite">
          <Icon name="check" size={16} style={{ color: "var(--good)" }} />
          <div>
            <div style={{ fontWeight: 700 }}>{toast.title}</div>
            {toast.detail && <div className="sub">{toast.detail}</div>}
          </div>
        </div>
      )}
    </Layout>
  );
}
