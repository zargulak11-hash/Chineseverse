import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.js";
import CompanionPicker from "../components/CompanionPicker.jsx";
import Layout from "../components/Layout.jsx";

// Changing the companion after onboarding (Dashboard, Profile and Companion
// link here). The first pick is onboarding's own step; this page is behind
// the onboarding guard, so it is only ever a change, never a way into
// onboarding -- it used to send anyone still marked "not onboarded" into the
// questions again after picking.
export default function AnimalSelect() {
  const { t } = useTranslation();
  const { user, setCurrentUser } = useAuth();
  const navigate = useNavigate();
  const [picked, setPicked] = useState(user?.animal_id ?? null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

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
      <h1 className="h1">{t("pages.animalSelect.title")}</h1>
      <p className="sub">{t("pages.animalSelect.subtitle", { name: user?.username || "" })}</p>
      {error && <p className="formerr">{error}</p>}
      <CompanionPicker picked={picked} busy={busy} onChoose={choose} />
    </Layout>
  );
}
