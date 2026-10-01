import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import Layout from "../components/Layout.jsx";
import { Empty, Loading, Stat } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

const STATUS_TONE = { sent: "good", failed: "bad", pending: "warn", skipped: "warn", sending: "accent", no_address: "bad" };

// Why a follow email did or didn't arrive, from the running backend itself
// (GET /api/admin/email): SMTP settings as loaded (presence only), the
// retry sweep, and each recent email's status + masked SMTP error.
function EmailDelivery() {
  const { t, i18n } = useTranslation();
  const { data, error, reload } = useApi("/admin/email");
  const [busy, setBusy] = useState("");
  const [result, setResult] = useState(null);

  async function run(kind) {
    setBusy(kind);
    setResult(null);
    try {
      if (kind === "test") {
        const r = await api.post("/admin/email/test");
        setResult(r.ok ? { ok: true, text: t("pages.adminHome.email.testOk") } : { ok: false, text: r.error });
      } else {
        await api.post("/admin/email/retry");
        setResult({ ok: true, text: t("pages.adminHome.email.retryQueued") });
        setTimeout(reload, 4000);
      }
    } catch (e) {
      setResult({ ok: false, text: e.message });
    } finally {
      setBusy("");
    }
  }

  if (error) return <div className="card" style={{ marginTop: 16 }}><Empty>{error}</Empty></div>;
  if (!data) return <div className="card" style={{ marginTop: 16 }}><Loading /></div>;

  const c = data.config;
  const yes = (v) => (v ? t("pages.adminHome.email.yes") : t("pages.adminHome.email.no"));
  const checks = [
    [t("pages.adminHome.email.enabled"), yes(c.enabled), c.enabled],
    [t("pages.adminHome.email.host"), c.host || "—", !!c.host],
    [t("pages.adminHome.email.portSecurity"), `${c.port} · ${c.security}`, true],
    [t("pages.adminHome.email.username"), yes(c.username_set), c.username_set],
    [t("pages.adminHome.email.password"), yes(c.password_set), c.password_set],
    [t("pages.adminHome.email.from"), yes(c.from_set), c.from_set || c.username_set],
    [t("pages.adminHome.email.fromMatches"), yes(c.from_matches_username), c.from_matches_username],
    [t("pages.adminHome.email.sweep"), yes(data.sweep_running), data.sweep_running],
  ];

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <div className="row spread" style={{ flexWrap: "wrap", gap: 8 }}>
        <h2 className="h2" style={{ margin: 0 }}>{t("pages.adminHome.email.title")}</h2>
        <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
          <button type="button" className="btn small" disabled={!!busy} onClick={() => run("test")}>
            {t("pages.adminHome.email.sendTest")}
          </button>
          <button type="button" className="btn small ghost" disabled={!!busy} onClick={() => run("retry")}>
            {t("pages.adminHome.email.retryNow")}
          </button>
          <button type="button" className="btn small ghost" disabled={!!busy} onClick={reload}>
            {t("pages.adminHome.email.refresh")}
          </button>
        </div>
      </div>
      {result && (
        <p role="status" className="sub" style={{ color: result.ok ? "var(--good)" : "var(--bad)", overflowWrap: "anywhere" }}>
          {result.text}
        </p>
      )}
      {!c.enabled && <p className="sub" style={{ color: "var(--bad)" }}>{t("pages.adminHome.email.disabledHint")}</p>}
      <div className="email-diag-grid">
        {checks.map(([label, value, ok]) => (
          <div key={label} className="row spread email-diag-item">
            <span className="sub">{label}</span>
            <b style={{ color: ok ? "var(--text)" : "var(--bad)", overflowWrap: "anywhere" }}>{value}</b>
          </div>
        ))}
      </div>
      <p className="sub" style={{ fontSize: 12.5 }}>
        {t("pages.adminHome.email.renotifyHint", { hours: data.renotify_after_hours })}
      </p>
      <div style={{ overflowX: "auto" }}>
        <table className="data" style={{ minWidth: 560 }}>
          <thead>
            <tr>
              <th>#</th>
              <th>{t("pages.adminHome.email.colCreated")}</th>
              <th>{t("pages.adminHome.email.colStatus")}</th>
              <th>{t("pages.adminHome.email.colAttempts")}</th>
              <th>{t("pages.adminHome.email.colError")}</th>
            </tr>
          </thead>
          <tbody>
            {data.recent.length === 0 && (
              <tr><td colSpan={5} className="sub">{t("pages.adminHome.email.none")}</td></tr>
            )}
            {data.recent.map((n) => (
              <tr key={n.id}>
                <td>{n.id}</td>
                <td>{n.created_at ? new Date(n.created_at + "Z").toLocaleString(i18n.language) : "—"}</td>
                <td>
                  <span className={`badge ${STATUS_TONE[n.email_status] || ""}`}>
                    {t(`pages.adminHome.email.status_${n.email_status}`, { defaultValue: n.email_status })}
                  </span>
                </td>
                <td>{n.email_attempts}/{data.max_attempts}</td>
                <td style={{ overflowWrap: "anywhere", fontSize: 12.5 }}>
                  {n.email_error || (n.recipient_has_email ? "" : t("pages.adminHome.email.noAddress"))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

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

      <EmailDelivery />

      <div className="row" style={{ marginTop: 20 }}>
        <Link to="/admin/users" className="btn primary">
          {t("nav.adminUsers")}
        </Link>
      </div>
    </Layout>
  );
}
