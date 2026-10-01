import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import UserAvatar from "../components/UserAvatar.jsx";
import { Empty, Loading } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

// Real 1-vs-1 duels. Everything that matters (who may accept, the shared
// questions, each player's clock, the result) lives on the server; this page
// only lists duels, sends a challenge and answers incoming ones.

export const DUEL_FOCUS = ["mix", "vocab", "listening", "hanzi", "tones", "grammar"];
const LEVELS = [1, 2, 3, 4, 5, 6, 7];
const LIST_POLL_MS = 10000;

export function duelErrorText(t, e) {
  if (!e) return "";
  if (e.code) {
    const base = e.code.replace(/_(pending|active|completed|declined|cancelled|expired)$/, "");
    return t(`pages.duels.errors.${base}`, { defaultValue: e.message || t("pages.duels.errors.generic") });
  }
  return e.message || t("pages.duels.errors.generic");
}

function ChallengeModal({ onClose, onCreated }) {
  const { t } = useTranslation();
  const [query, setQuery] = useState("");
  const [people, setPeople] = useState(null);
  const [rules, setRules] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [selected, setSelected] = useState(null);
  const [level, setLevel] = useState("");
  const [focus, setFocus] = useState("mix");
  const [sending, setSending] = useState(false);
  const [formError, setFormError] = useState("");

  // One request per (debounced) query; a stale response never overwrites a
  // newer one.
  useEffect(() => {
    let cancelled = false;
    const q = query.trim();
    const id = setTimeout(() => {
      setLoadError("");
      api
        .get(q ? `/duels/opponents?q=${encodeURIComponent(q)}` : "/duels/opponents")
        .then((d) => {
          if (cancelled) return;
          setPeople(d.opponents);
          setRules(d.rules);
        })
        .catch((e) => !cancelled && setLoadError(duelErrorText(t, e)));
    }, q ? 300 : 0);
    return () => {
      cancelled = true;
      clearTimeout(id);
    };
  }, [query, t]);

  async function send() {
    if (!selected || sending) return;
    setFormError("");
    setSending(true);
    try {
      const d = await api.post("/duels", {
        opponent_id: selected.id,
        hsk_level: level ? Number(level) : null,
        focus,
      });
      onCreated(d);
    } catch (e) {
      setFormError(duelErrorText(t, e));
      setSending(false);
    }
  }

  return (
    <div className="modal" role="dialog" aria-modal="true" aria-label={t("pages.duels.challengeSomeone")}>
      <div className="card duel-modal">
        <div className="row spread">
          <h2 className="h2">{t("pages.duels.challengeSomeone")}</h2>
          <button type="button" className="btn small ghost" onClick={onClose} aria-label={t("common.cancel")}>
            <Icon name="x" size={14} />
          </button>
        </div>

        <div className="field" style={{ marginTop: 12 }}>
          <label htmlFor="duel-search">{t("pages.duels.opponent")}</label>
          <input
            id="duel-search"
            className="input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("pages.duels.searchPlaceholder")}
            autoComplete="off"
          />
        </div>
        <p className="sub" style={{ fontSize: 12, margin: "4px 0 6px" }}>
          {query.trim() ? t("pages.duels.searchResults") : t("pages.duels.yourPeople")}
        </p>
        <div className="duel-people" role="listbox" aria-label={t("pages.duels.pickOpponent")}>
          {loadError && <p className="formerr">{loadError}</p>}
          {!loadError && people === null && <Loading />}
          {people && people.length === 0 && (
            <p className="sub">{query.trim() ? t("pages.duels.noMatches") : t("pages.duels.noPeople")}</p>
          )}
          {(people || []).map((p) => {
            const busy = !!p.open_duel_id;
            const isSel = selected?.id === p.id;
            return (
              <div key={p.id} className={`duel-person${isSel ? " is-selected" : ""}${busy ? " is-busy" : ""}`}>
                <button
                  type="button"
                  role="option"
                  aria-selected={isSel}
                  className="duel-person-pick"
                  disabled={busy}
                  onClick={() => setSelected(p)}
                >
                  <UserAvatar url={p.avatar_url} name={p.username} size={32} />
                  <span className="duel-person-name">{p.username}</span>
                  <span className="badge">{t("pages.duels.levelN", { level: p.hsk_level })}</span>
                </button>
                {busy && (
                  <Link to={`/duels/${p.open_duel_id}`} className="btn small ghost" onClick={onClose}>
                    {t("pages.duels.alreadyOpen")}
                  </Link>
                )}
              </div>
            );
          })}
        </div>

        <div className="grid grid-2 duel-options">
          <div className="field">
            <label htmlFor="duel-level">{t("pages.duels.level")}</label>
            <select id="duel-level" className="input" value={level} onChange={(e) => setLevel(e.target.value)}>
              <option value="">{t("pages.duels.levelAuto")}</option>
              {LEVELS.map((l) => (
                <option key={l} value={l}>{t("pages.duels.levelN", { level: l === 7 ? "7–9" : l })}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="duel-focus">{t("pages.duels.focus")}</label>
            <select id="duel-focus" className="input" value={focus} onChange={(e) => setFocus(e.target.value)}>
              {DUEL_FOCUS.map((f) => (
                <option key={f} value={f}>{t(`pages.duels.focusType.${f}`)}</option>
              ))}
            </select>
          </div>
        </div>
        {rules && (
          <p className="sub" style={{ fontSize: 12 }}>
            {t("pages.duels.rulesLine", { count: rules.question_count, minutes: rules.time_limit_seconds / 60 })}
          </p>
        )}
        {formError && <p className="formerr">{formError}</p>}
        <div className="row" style={{ marginTop: 10 }}>
          <button type="button" className="btn primary" onClick={send} disabled={!selected || sending}>
            <Icon name="swords" size={14} /> {sending ? t("pages.duels.sending") : t("pages.duels.sendChallenge")}
          </button>
          <button type="button" className="btn ghost" onClick={onClose} disabled={sending}>
            {t("common.cancel")}
          </button>
        </div>
      </div>
    </div>
  );
}

function DuelRow({ d, onAction, busyId }) {
  const { t } = useTranslation();
  const opp = d.opponent || {};
  const name = opp.username || "—";
  const total = d.question_count;
  const busy = busyId === d.id;
  let line;
  if (d.status === "pending") {
    line = d.my_role === "opponent" ? t("pages.duels.challengedYou", { name }) : t("pages.duels.youChallenged", { name });
  } else if (d.status === "active") {
    line = t("pages.duels.progressLine", { mine: d.me?.answered ?? 0, theirs: opp.answered ?? 0, total, name });
  } else if (d.status === "completed" && d.result) {
    line = t(`pages.duels.outcome.${d.result.outcome}`, { name });
  } else {
    line = t(`pages.duels.status.${d.status}`);
  }
  const badge =
    d.status === "completed" && d.result
      ? d.result.outcome === "win" ? "good" : d.result.outcome === "loss" ? "bad" : ""
      : d.status === "active" || d.status === "pending" ? "accent" : "";
  return (
    <div className="card duel-row">
      <UserAvatar url={opp.avatar_url} name={name} size={40} />
      <div className="duel-row-main">
        <b className="duel-row-name">{name}</b>
        <span className="sub">{line}</span>
        {d.hsk_level && (
          <span className="sub" style={{ fontSize: 12 }}>
            {t("pages.duels.meta", { level: d.hsk_level, focus: t(`pages.duels.focusType.${d.focus || "mix"}`) })}
          </span>
        )}
      </div>
      <span className={`badge ${badge}`}>{t(`pages.duels.status.${d.status}`)}</span>
      <div className="duel-row-actions">
        {d.can_accept && (
          <>
            <button type="button" className="btn small primary" disabled={busy} onClick={() => onAction(d, "accept")}>
              {t("pages.duels.accept")}
            </button>
            <button type="button" className="btn small ghost" disabled={busy} onClick={() => onAction(d, "decline")}>
              {t("pages.duels.decline")}
            </button>
          </>
        )}
        {d.can_cancel && (
          <button type="button" className="btn small ghost" disabled={busy} onClick={() => onAction(d, "cancel")}>
            {t("pages.duels.cancelChallenge")}
          </button>
        )}
        <Link to={`/duels/${d.id}`} className="btn small">
          {d.status === "active" && !d.me?.finished
            ? t("pages.duels.play")
            : d.status === "completed"
            ? t("pages.duels.viewResult")
            : t("pages.duels.open")}
        </Link>
      </div>
    </div>
  );
}

export default function Duels() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data, setData, error, reload } = useApi("/duels");
  const [open, setOpen] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const [actionError, setActionError] = useState("");
  const inFlight = useRef(false);

  // Incoming challenges / acceptances show up without a page refresh. One
  // interval for the page, skipped while the tab is hidden or a request is
  // still running.
  const poll = useCallback(() => {
    if (document.hidden || inFlight.current) return;
    inFlight.current = true;
    api
      .get("/duels")
      .then(setData)
      .catch(() => {}) // keep the last good list; the next poll retries
      .finally(() => {
        inFlight.current = false;
      });
  }, [setData]);

  useEffect(() => {
    const id = setInterval(poll, LIST_POLL_MS);
    document.addEventListener("visibilitychange", poll);
    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", poll);
    };
  }, [poll]);

  async function onAction(d, action) {
    setActionError("");
    setBusyId(d.id);
    try {
      const updated = await api.post(`/duels/${d.id}/${action}`);
      if (action === "accept") {
        navigate(`/duels/${d.id}`);
        return;
      }
      setData((list) => (list || []).map((x) => (x.id === d.id ? { ...updated, current: null, review: null } : x)));
    } catch (e) {
      setActionError(duelErrorText(t, e));
      reload();
    } finally {
      setBusyId(null);
    }
  }

  if (error) return <Layout><Empty>{error}</Empty></Layout>;
  if (!data) return <Layout><Loading /></Layout>;

  const incoming = data.filter((d) => d.status === "pending" && d.my_role === "opponent");
  const outgoing = data.filter((d) => d.status === "pending" && d.my_role === "challenger");
  const active = data.filter((d) => d.status === "active");
  const history = data.filter((d) => !["pending", "active"].includes(d.status));
  const sections = [
    ["incoming", incoming],
    ["inProgress", active],
    ["outgoing", outgoing],
    ["history", history],
  ];

  return (
    <Layout>
      <div className="row spread duel-head">
        <div>
          <h1 className="h1">{t("pages.duels.title")}</h1>
          <p className="sub">{t("pages.duels.subtitle")}</p>
        </div>
        <button type="button" className="btn primary" onClick={() => setOpen(true)}>
          <Icon name="swords" size={14} /> {t("pages.duels.newDuel")}
        </button>
      </div>

      {open && (
        <ChallengeModal
          onClose={() => setOpen(false)}
          onCreated={(d) => {
            setOpen(false);
            navigate(`/duels/${d.id}`);
          }}
        />
      )}

      {actionError && <p className="formerr" style={{ marginTop: 12 }}>{actionError}</p>}

      {data.length === 0 ? (
        <Empty>{t("pages.duels.empty")}</Empty>
      ) : (
        sections.map(([key, list]) =>
          list.length ? (
            <section key={key} style={{ marginTop: 20 }}>
              <h2 className="h2" style={{ fontSize: 17, marginBottom: 10 }}>
                {t(`pages.duels.${key}`)} <span className="sub">({list.length})</span>
              </h2>
              <div className="col">
                {list.map((d) => (
                  <DuelRow key={d.id} d={d} onAction={onAction} busyId={busyId} />
                ))}
              </div>
            </section>
          ) : null
        )
      )}
    </Layout>
  );
}
