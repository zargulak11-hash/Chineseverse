import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.js";
import AnimalAvatar from "../components/AnimalAvatar.jsx";
import Layout from "../components/Layout.jsx";

export default function AnimalSelect() {
  const { user, setCurrentUser } = useAuth();
  const navigate = useNavigate();
  const [animals, setAnimals] = useState([]);
  const [picked, setPicked] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/animals").then(setAnimals).catch(() => setAnimals([]));
    api.get("/me").then((me) => {
      if (me.user.animal_id) setPicked(me.user.animal_id);
    }).catch(() => {});
  }, []);

  async function choose(id) {
    setBusy(true);
    setError("");
    try {
      await api.post("/me/animal", { animal_id: id });
      setPicked(id);
      const me = await api.get("/me");
      setCurrentUser(me.user);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Layout>
      <div className="row spread">
        <div>
          <h1 className="h1">Choose your companion</h1>
          <p className="sub">
            Each one teaches with a different style. You can change later —
            {user?.username || "friend"}.
          </p>
        </div>
      </div>
      {error && <p className="formerr">{error}</p>}
      <div className="grid cards" style={{ marginTop: 18 }}>
        {animals.map((a) => (
          <div
            key={a.id}
            className={`card hover animal${picked === a.id ? " picked" : ""}`}
            style={
              picked === a.id
                ? {
                    borderColor: a.accent_color || "#f59e0b",
                    boxShadow: `var(--shadow), 0 0 28px -6px ${a.accent_color || "#f59e0b"}`,
                  }
                : undefined
            }
            onClick={() => !busy && choose(a.id)}
          >
            <div className="face">
              <AnimalAvatar slug={a.slug} accentColor={a.accent_color} size={76} />
            </div>
            <div className="name">{a.name}</div>
            <div className="species">{a.species}</div>
            <div className="desc">{a.description}</div>
            <div className="ability">✨ {a.special_ability}</div>
            <div className="statsrow">
              {a.personality && <span className="statpill">{a.personality}</span>}
              {a.tone_style && <span className="statpill">{a.tone_style}</span>}
            </div>
          </div>
        ))}
      </div>
    </Layout>
  );
}