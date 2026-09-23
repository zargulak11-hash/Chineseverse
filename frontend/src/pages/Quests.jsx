import { animate, stagger } from "animejs";
import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { prefersReducedMotion } from "../anime.js";
import Icon from "../components/Icon.jsx";
import Layout from "../components/Layout.jsx";
import { Bar, Empty } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";

export default function Quests() {
  const { data, setData, error } = useApi("/quests/today");
  const quests = data || [];
  const [claimError, setClaimError] = useState("");
  const listRef = useRef(null);

  useEffect(() => {
    const root = listRef.current;
    if (!root || quests.length === 0) return;
    const targets = Array.from(root.children);
    if (prefersReducedMotion()) {
      targets.forEach((el) => {
        el.style.opacity = 1;
      });
      return;
    }
    animate(targets, {
      opacity: [0, 1],
      translateY: [22, 0],
      duration: 560,
      delay: stagger(55),
      ease: "outElastic(1, .75)",
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quests.length]);

  async function claim(q) {
    setClaimError("");
    try {
      const updated = await api.post(`/quests/${q.id}/claim`);
      setData((qs) => (qs || []).map((x) => (x.id === q.id ? updated : x)));
    } catch (e) {
      setClaimError(e.message);
    }
  }

  if (error) return <Layout><Empty>{error}</Empty></Layout>;

  return (
    <Layout>
      <h1 className="h1">Daily quests</h1>
      <p className="sub">
        Generated from your DNA every day. Complete them to feed your companion.
      </p>
      {claimError && <p className="formerr">{claimError}</p>}

      <div className="col" style={{ marginTop: 18 }} ref={listRef} data-self-animate="true">
        {quests.map((q) => (
          <div key={q.id} className="card" style={{ borderColor: q.completed ? "var(--good)" : undefined }}>
            <div className="row spread">
              <div className="row">
                <span className="ic">
                  <Icon name={q.completed ? "check" : "target"} size={17} />
                </span>
                <div>
                  <b>{q.title}</b>
                  <p className="sub" style={{ fontSize: 12 }}>{q.description}</p>
                  {q.flavor && <p className="muted" style={{ fontSize: 11.5 }}>{q.flavor}</p>}
                </div>
              </div>
              <div className="row">
                <span className="ilb">+{q.reward_xp} xp</span>
                <span className="ilb">
                  <Icon name="coin" size={11} style={{ verticalAlign: -1, marginRight: 3 }} />
                  {q.reward_coins}
                </span>
              </div>
            </div>
            <div className="hbar" style={{ marginTop: 10 }}>
              <span className="muted" style={{ fontSize: 12 }}>
                {q.progress}/{q.target}
              </span>
              <Bar value={q.progress} max={q.target} />
            </div>
            {q.completed && !q.claimed && (
              <button className="btn primary small" style={{ marginTop: 12 }} onClick={() => claim(q)}>
                Claim reward
              </button>
            )}
            {q.claimed && (
              <span className="badge good" style={{ marginTop: 12 }}>
                <Icon name="check" size={10} /> Claimed
              </span>
            )}
          </div>
        ))}
      </div>
      {quests.length === 0 && <Empty>Nothing today. Take a walk around the world.</Empty>}
    </Layout>
  );
}
