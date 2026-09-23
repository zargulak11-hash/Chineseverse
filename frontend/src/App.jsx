import { useEffect, useState } from "react";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { api, clearSession, getSavedUser, getToken } from "./api.js";
import { AuthContext, useAuth } from "./auth.js";
import { initButtonFX } from "./buttonFx.js";
import { DashboardProvider } from "./context/DashboardContext.jsx";
import Landing from "./pages/Landing.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import AnimalSelect from "./pages/AnimalSelect.jsx";
import Onboarding from "./pages/Onboarding.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import DNA from "./pages/DNA.jsx";
import Roadmap from "./pages/Roadmap.jsx";
import Lessons from "./pages/Lessons.jsx";
import LessonDetail from "./pages/LessonDetail.jsx";
import Vocabulary from "./pages/Vocabulary.jsx";
import WorldMap from "./pages/WorldMap.jsx";
import LocationDetail from "./pages/LocationDetail.jsx";
import Conversation from "./pages/Conversation.jsx";
import CaseSolve from "./pages/CaseSolve.jsx";
import Quests from "./pages/Quests.jsx";
import Missions from "./pages/Missions.jsx";
import Duels from "./pages/Duels.jsx";
import DuelBattle from "./pages/DuelBattle.jsx";
import Achievements from "./pages/Achievements.jsx";
import Companion from "./pages/Companion.jsx";
import PetTeacher from "./pages/PetTeacher.jsx";
import Mistakes from "./pages/Mistakes.jsx";
import Progress from "./pages/Progress.jsx";
import Profile from "./pages/Profile.jsx";
import Settings from "./pages/Settings.jsx";
import Assistant from "./pages/Assistant.jsx";
import Community from "./pages/Community.jsx";
import PublicProfile from "./pages/PublicProfile.jsx";

function RequireAuth({ children }) {
  const { user } = useAuth();
  const location = useLocation();
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  return children;
}

function NavLink({ to, children }) {
  return (
    <Link to={to} className="navlink">
      {children}
    </Link>
  );
}

export default function App() {
  const [user, setUser] = useState(getSavedUser());
  const [booted, setBooted] = useState(false);

  useEffect(() => {
    if (!getToken() || !getSavedUser()) {
      setBooted(true);
      return;
    }
    api
      .get("/me")
      .then((me) => {
        const fresh = me.user;
        saveSelf(fresh);
        setUser(fresh);
      })
      .catch(() => {
        clearSession();
        setUser(null);
      })
      .finally(() => setBooted(true));
  }, []);

  useEffect(() => {
    initButtonFX();
  }, []);

  function saveSelf(u) {
    localStorage.setItem("linguaverse_user", JSON.stringify(u));
  }

  function setCurrentUser(next) {
    if (next) saveSelf(next);
    setUser(next);
  }

  function logout() {
    clearSession();
    setUser(null);
  }

  if (!booted) {
    return <div className="boot">中 ChineseVerse…</div>;
  }

  return (
    <AuthContext.Provider value={{ user, setCurrentUser, logout }}>
      <DashboardProvider>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          path="/animals"
          element={
            <RequireAuth>
              <AnimalSelect />
            </RequireAuth>
          }
        />
        <Route
          path="/onboarding"
          element={
            <RequireAuth>
              <Onboarding />
            </RequireAuth>
          }
        />
        <Route
          path="/dashboard"
          element={
            <RequireAuth>
              <Dashboard />
            </RequireAuth>
          }
        />
        <Route
          path="/dna"
          element={
            <RequireAuth>
              <DNA />
            </RequireAuth>
          }
        />
        <Route
          path="/roadmap"
          element={
            <RequireAuth>
              <Roadmap />
            </RequireAuth>
          }
        />
        <Route
          path="/lessons"
          element={
            <RequireAuth>
              <Lessons />
            </RequireAuth>
          }
        />
        <Route
          path="/lessons/:lessonId"
          element={
            <RequireAuth>
              <LessonDetail />
            </RequireAuth>
          }
        />
        <Route
          path="/vocabulary"
          element={
            <RequireAuth>
              <Vocabulary />
            </RequireAuth>
          }
        />
        <Route
          path="/world"
          element={
            <RequireAuth>
              <WorldMap />
            </RequireAuth>
          }
        />
        <Route
          path="/world/:slug"
          element={
            <RequireAuth>
              <LocationDetail />
            </RequireAuth>
          }
        />
        <Route
          path="/conversation/:scenarioId"
          element={
            <RequireAuth>
              <Conversation />
            </RequireAuth>
          }
        />
        <Route
          path="/cases/:scenarioId"
          element={
            <RequireAuth>
              <CaseSolve />
            </RequireAuth>
          }
        />
        <Route
          path="/quests"
          element={
            <RequireAuth>
              <Quests />
            </RequireAuth>
          }
        />
        <Route
          path="/missions"
          element={
            <RequireAuth>
              <Missions />
            </RequireAuth>
          }
        />
        <Route
          path="/duels"
          element={
            <RequireAuth>
              <Duels />
            </RequireAuth>
          }
        />
        <Route
          path="/duels/:duelId"
          element={
            <RequireAuth>
              <DuelBattle />
            </RequireAuth>
          }
        />
        <Route
          path="/achievements"
          element={
            <RequireAuth>
              <Achievements />
            </RequireAuth>
          }
        />
        <Route
          path="/companion"
          element={
            <RequireAuth>
              <Companion />
            </RequireAuth>
          }
        />
        <Route
          path="/pet-teacher"
          element={
            <RequireAuth>
              <PetTeacher />
            </RequireAuth>
          }
        />
        <Route
          path="/mistakes"
          element={
            <RequireAuth>
              <Mistakes />
            </RequireAuth>
          }
        />
        <Route
          path="/progress"
          element={
            <RequireAuth>
              <Progress />
            </RequireAuth>
          }
        />
        <Route
          path="/profile"
          element={
            <RequireAuth>
              <Profile />
            </RequireAuth>
          }
        />
        <Route
          path="/settings"
          element={
            <RequireAuth>
              <Settings />
            </RequireAuth>
          }
        />
        <Route
          path="/assistant"
          element={
            <RequireAuth>
              <Assistant />
            </RequireAuth>
          }
        />
        <Route
          path="/community"
          element={
            <RequireAuth>
              <Community />
            </RequireAuth>
          }
        />
        <Route
          path="/u/:userId"
          element={
            <RequireAuth>
              <PublicProfile />
            </RequireAuth>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </DashboardProvider>
    </AuthContext.Provider>
  );
}