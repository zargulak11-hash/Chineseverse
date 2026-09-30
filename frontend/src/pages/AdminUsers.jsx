import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api.js";
import { useAuth } from "../auth.js";
import AnimalAvatar from "../components/AnimalAvatar.jsx";
import Layout from "../components/Layout.jsx";
import Icon from "../components/Icon.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

const PAGE_SIZE = 25;

// Timestamps are stored as naive UTC (datetime.utcnow()); without a zone
// marker the browser would read them as local time and shift them.
function parseUtc(iso) {
  if (!iso) return null;
  return new Date(/[zZ]|[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`);
}

// Owner-only user management. The real access control is server-side
// (GET/DELETE /api/admin/users both require app.deps.require_admin) — this
// page and its RequireAdmin route guard only decide what an admin *sees*,
// never what they're *allowed* to do. A non-admin who reaches this route
// some other way still gets a 401/403 from the API itself.
//
// Everything shown comes from the `users` table of the database the API
// is connected to; the banner names that database (local vs production),
// since the two environments are separate databases and never mixed here.
export default function AdminUsers() {
  const { t, i18n } = useTranslation();
  const { user: me } = useAuth();
  const [query, setQuery] = useState("");
  const [q, setQ] = useState("");
  const [offset, setOffset] = useState(0);
  const path = `/admin/users?limit=${PAGE_SIZE}&offset=${offset}${q ? `&q=${encodeURIComponent(q)}` : ""}`;
  const { data, setData, error, reload } = useApi(path);
  const [target, setTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const [toast, setToast] = useState(null);

  // Debounce the search box so each keystroke doesn't hit the API.
  useEffect(() => {
    const id = setTimeout(() => {
      setQ(query.trim());
      setOffset(0);
    }, 300);
    return () => clearTimeout(id);
  }, [query]);

  // Deleting the last user on a later page leaves that page empty: step back.
  useEffect(() => {
    if (data && data.users.length === 0 && offset > 0) setOffset(Math.max(0, offset - PAGE_SIZE));
  }, [data, offset]);

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
      // then refetch so totals/order reflect the database's real state.
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
  const fmtDate = (iso) => parseUtc(iso)?.toLocaleDateString(i18n.language) ?? "—";
  const fmtDateTime = (iso) =>
    iso ? parseUtc(iso).toLocaleString(i18n.language, { dateStyle: "medium", timeStyle: "short" }) : t("pages.adminUsers.never");

  const statusBadge = (u) => (
    <span className={`badge ${u.is_active ? "good" : "bad"}`}>
      {u.is_active ? t("pages.adminUsers.active") : t("pages.adminUsers.inactive")}
    </span>
  );

  const roleBadge = (u) => (
    <span className={`badge ${u.is_admin ? "accent" : ""}`}>
      {u.is_admin ? t("pages.adminUsers.roleAdmin") : t("pages.adminUsers.roleUser")}
    </span>
  );

  const authCell = (u) => (
    <div>
      <span className="badge">
        {u.auth_method === "google" ? t("pages.adminUsers.authGoogle") : t("pages.adminUsers.authPassword")}
      </span>
      {u.google_sub && (
        <div className="admin-mono" title={t("pages.adminUsers.googleId")}>
          {t("pages.adminUsers.googleId")}: {u.google_sub}
        </div>
      )}
    </div>
  );

  const progressCell = (u) =>
    u.hsk_level != null ? (
      <div>
        <div>{t("pages.adminUsers.hskMastery", { level: u.hsk_level, mastery: Math.round(u.mastery ?? 0) })}</div>
        <div className="sub" style={{ fontSize: 12 }}>
          {t("pages.adminUsers.xp", { xp: u.total_xp })}
          {u.current_streak ? ` · ${t("pages.adminUsers.streak", { count: u.current_streak })}` : ""}
        </div>
      </div>
    ) : (
      <span className="sub">{t("pages.adminUsers.noProgress")}</span>
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
        <div className="email">
          #{u.id} · {u.companion_name || t("pages.adminUsers.noCompanion")}
        </div>
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

  const db = data?.database;
  const envKey = db?.environment === "production" ? "dbProduction" : db?.environment === "local" ? "dbLocal" : "dbTest";
  const from = data && data.total > 0 ? data.offset + 1 : 0;
  const to = data ? Math.min(data.offset + users.length, data.total) : 0;

  return (
    <Layout>
      <h1 className="h1">{t("pages.adminUsers.users")}</h1>
      <p className="sub">{t("pages.adminUsers.subtitle")}</p>

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

      {data && !error && (
        <>
          {db && (
            <div className={`card admin-db-banner env-${db.environment}`} style={{ marginTop: 16 }}>
              <div className="row spread" style={{ flexWrap: "wrap", gap: 8 }}>
                <div>
                  <div className="admin-db-label">{t(`pages.adminUsers.${envKey}`)}</div>
                  <div className="sub" style={{ fontSize: 12 }}>
                    {t("pages.adminUsers.dbSource", { engine: db.engine, name: db.name || "—" })}
                    {db.host ? ` @ ${db.host}` : ""} · {t("pages.adminUsers.servedBy", { host: db.served_by })}
                  </div>
                </div>
                <div className="row" style={{ gap: 6, flexWrap: "wrap" }}>
                  <span className="badge accent">{t("pages.adminUsers.totalUsers", { count: data.total_users })}</span>
                  <span className="badge">{t("pages.adminUsers.adminCount", { count: data.admin_count })}</span>
                  <span className="badge">{t("pages.adminUsers.regularCount", { count: data.regular_count })}</span>
                </div>
              </div>
              <p className="sub" style={{ fontSize: 12, marginTop: 8 }}>{t("pages.adminUsers.dbNote")}</p>
            </div>
          )}

          <div className="row" style={{ marginTop: 14, gap: 8, flexWrap: "wrap" }}>
            <input
              type="search"
              className="input admin-search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t("pages.adminUsers.searchPlaceholder")}
              aria-label={t("pages.adminUsers.searchPlaceholder")}
            />
            {data.total > 0 && (
              <span className="sub">{t("pages.adminUsers.pageRange", { from, to, total: data.total })}</span>
            )}
          </div>

          {users.length === 0 && (
            <Empty>{q ? t("pages.adminUsers.noMatches", { query: q }) : t("pages.adminUsers.empty")}</Empty>
          )}

          {users.length > 0 && (
            <>
              <div className="card admin-users-table" style={{ marginTop: 16 }}>
                <table className="data">
                  <thead>
                    <tr>
                      <th>{t("pages.adminUsers.user")}</th>
                      <th>{t("pages.adminUsers.colAuth")}</th>
                      <th>{t("pages.adminUsers.colProgress")}</th>
                      <th>{t("pages.adminUsers.registeredCol")}</th>
                      <th>{t("pages.adminUsers.colLastActivity")}</th>
                      <th>{t("pages.adminUsers.colRole")}</th>
                      <th>{t("pages.adminUsers.status")}</th>
                      <th className="col-actions">{t("pages.adminUsers.actions")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((u) => (
                      <tr key={u.id}>
                        <td>{identity(u)}</td>
                        <td>{authCell(u)}</td>
                        <td>{progressCell(u)}</td>
                        <td>{fmtDate(u.created_at)}</td>
                        <td>{fmtDateTime(u.last_activity_at)}</td>
                        <td>{roleBadge(u)}</td>
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
                        {roleBadge(u)}
                        {statusBadge(u)}
                      </div>
                      {authCell(u)}
                      {progressCell(u)}
                      <span className="sub">{t("pages.adminUsers.registered", { date: fmtDate(u.created_at) })}</span>
                      <span className="sub">
                        {t("pages.adminUsers.colLastActivity")}: {fmtDateTime(u.last_activity_at)}
                      </span>
                    </div>
                    {deleteButton(u)}
                  </div>
                ))}
              </div>
            </>
          )}

          {data.total > PAGE_SIZE && (
            <div className="row" style={{ marginTop: 14, gap: 8, justifyContent: "center" }}>
              <button
                type="button"
                className="btn small"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              >
                {t("pages.adminUsers.prev")}
              </button>
              <button
                type="button"
                className="btn small"
                disabled={offset + PAGE_SIZE >= data.total}
                onClick={() => setOffset(offset + PAGE_SIZE)}
              >
                {t("pages.adminUsers.next")}
              </button>
            </div>
          )}

          <p className="sub" style={{ fontSize: 12, marginTop: 12 }}>{t("pages.adminUsers.authNote")}</p>
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
