import { lazy, Suspense, useEffect, useState } from "react";
import { Link, Navigate, Route, Routes, useLocation, useParams } from "react-router-dom";
import { api, clearSession, getSavedUser, getToken, onSessionExpired, SESSION_KEYS } from "./api.js";
import { AuthContext, useAuth } from "./auth.js";
import { initButtonFX } from "./buttonFx.js";
import BrandLogo from "./components/BrandLogo.jsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import { AppShell } from "./components/Layout.jsx";
import { DashboardProvider } from "./context/DashboardContext.jsx";
import Landing from "./pages/Landing.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import GitHubCallback from "./pages/GitHubCallback.jsx";

// Every page behind sign-in is its own chunk, loaded when first opened: the
// whole app used to ship as one 1.4 MB script, so the landing and login
// pages downloaded every page of the product before showing anything. The
// public entry pages above stay in the main bundle.
const AnimalSelect = lazy(() => import("./pages/AnimalSelect.jsx"));
const Onboarding = lazy(() => import("./pages/Onboarding.jsx"));
const Dashboard = lazy(() => import("./pages/Dashboard.jsx"));
const DNA = lazy(() => import("./pages/DNA.jsx"));
const Roadmap = lazy(() => import("./pages/Roadmap.jsx"));
const Lessons = lazy(() => import("./pages/Lessons.jsx"));
const LessonDetail = lazy(() => import("./pages/LessonDetail.jsx"));
const Vocabulary = lazy(() => import("./pages/Vocabulary.jsx"));
const Grammar = lazy(() => import("./pages/Grammar.jsx"));
const GrammarTopic = lazy(() => import("./pages/GrammarTopic.jsx"));
const Hanzi = lazy(() => import("./pages/Hanzi.jsx"));
const Conversation = lazy(() => import("./pages/Conversation.jsx"));
const CaseSolve = lazy(() => import("./pages/CaseSolve.jsx"));
const Quests = lazy(() => import("./pages/Quests.jsx"));
const Missions = lazy(() => import("./pages/Missions.jsx"));
const Duels = lazy(() => import("./pages/Duels.jsx"));
const DuelBattle = lazy(() => import("./pages/DuelBattle.jsx"));
const Achievements = lazy(() => import("./pages/Achievements.jsx"));
const Companion = lazy(() => import("./pages/Companion.jsx"));
const VoiceCompanion = lazy(() => import("./pages/VoiceCompanion.jsx"));
const PetTeacher = lazy(() => import("./pages/PetTeacher.jsx"));
const Mistakes = lazy(() => import("./pages/Mistakes.jsx"));
const Practice = lazy(() => import("./pages/Practice.jsx"));
const RealChinese = lazy(() => import("./pages/RealChinese.jsx"));
const RealChineseScene = lazy(() => import("./pages/RealChinese.jsx").then((m) => ({ default: m.RealChineseScene })));
const SentenceLesson = lazy(() => import("./pages/SentenceLesson.jsx"));
const Detective = lazy(() => import("./pages/Detective.jsx"));
const DetectiveFile = lazy(() => import("./pages/DetectiveFile.jsx"));
const SoundWorld = lazy(() => import("./pages/SoundWorld.jsx"));
const CharacterDNA = lazy(() => import("./pages/CharacterDNA.jsx"));
const Ecosystem = lazy(() => import("./pages/Ecosystem.jsx"));
const ChineseInternet = lazy(() => import("./pages/ChineseInternet.jsx"));
const InternetItem = lazy(() => import("./pages/ChineseInternet.jsx").then((m) => ({ default: m.InternetItem })));
const Passport = lazy(() => import("./pages/Passport.jsx"));
const Exam = lazy(() => import("./pages/Exam.jsx"));
const Progress = lazy(() => import("./pages/Progress.jsx"));
const Profile = lazy(() => import("./pages/Profile.jsx"));
const Settings = lazy(() => import("./pages/Settings.jsx"));
const Assistant = lazy(() => import("./pages/Assistant.jsx"));
const Community = lazy(() => import("./pages/Community.jsx"));
const PublicProfile = lazy(() => import("./pages/PublicProfile.jsx"));
const AdminUsers = lazy(() => import("./pages/AdminUsers.jsx"));
const AdminHome = lazy(() => import("./pages/AdminHome.jsx"));
const Journey = lazy(() => import("./pages/Journey.jsx"));
const Foundation = lazy(() => import("./pages/Foundation.jsx"));
const Stories = lazy(() => import("./pages/Stories.jsx"));
const StoryBook = lazy(() => import("./pages/StoryBook.jsx"));
const StoryReader = lazy(() => import("./pages/StoryReader.jsx"));

// Onboarding is a one-time setup the server records
// (user_profiles.onboarding_completed, carried on every auth//me `user`).
// Until it is done, every signed-in page -- typed URL, bookmark, old link --
// leads back to /onboarding; the shell route is wrapped in this too, so the
// sidebar and top bar never render around an unfinished onboarding. Only the
// stored flag decides, never which pages were visited: deciding by the
// visited page is what let onboarding come back after a refresh or a new
// sign-in.
function RequireAuth({ children }) {
  const { user } = useAuth();
  const location = useLocation();
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  if (!user.onboarding_completed) return <Navigate to="/onboarding" replace />;
  return children;
}

// The other side of the same gate: /onboarding is only for a learner who
// hasn't finished it. Once the server says it's done, it can't be reopened.
function RequireOnboarding({ children }) {
  const { user } = useAuth();
  const location = useLocation();
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  if (user.onboarding_completed) return <Navigate to="/dashboard" replace />;
  return children;
}

// Login and Register are for signed-out visitors. A signed-in one (a
// bookmark, the Back button after signing in, a GitHub callback opened a
// second time and sent back to /login) goes where the onboarding flag says
// instead of seeing a form for an account they're already in.
function RedirectIfAuthed({ children }) {
  const { user } = useAuth();
  if (user) return <Navigate to={user.onboarding_completed ? "/dashboard" : "/onboarding"} replace />;
  return children;
}

// Frontend visibility is NOT the security boundary here — it's only UX
// (don't show a page whose API calls would fail anyway). A non-admin who
// reaches /admin/users by any means still gets a real 401/403 from
// GET/DELETE /api/admin/users (see app.deps.require_admin); this redirect
// just avoids flashing an error-filled page first.
function RequireAdmin({ children }) {
  const { user } = useAuth();
  const location = useLocation();
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  if (!user.is_admin) return <Navigate to="/dashboard" replace />;
  return children;
}

// The old World map (/world) is now the living world on /real-chinese, and its
// talks and cases moved under it. Bookmarks and shared links to the old
// addresses still land in the right place.
function MovedTo({ base }) {
  const { scenarioId } = useParams();
  return <Navigate to={scenarioId ? `${base}/${scenarioId}` : base} replace />;
}

function NavLink({ to, children }) {
  return (
    <Link to={to} className="navlink">
      {children}
    </Link>
  );
}

export default function App() {
  // Signed in only with BOTH halves of a session. A saved user without a
  // token (storage partly cleared, or a request finishing after sign-out
  // wrote the user back) used to count as signed in until every request
  // came back 401 -- /login even bounced to an empty Dashboard.
  const [user, setUser] = useState(() => (getToken() ? getSavedUser() : null));
  const [booted, setBooted] = useState(false);
  const { pathname } = useLocation();

  useEffect(() => {
    if (!getToken() || !getSavedUser()) {
      if (getToken() || getSavedUser()) clearSession(); // drop the stray half
      setUser(null);
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

  // A request answered 401 mid-session (token expired, account
  // deactivated): api.js has cleared storage; drop the in-memory user too,
  // so the route guards send the learner to /login instead of leaving a
  // page up whose every request fails.
  useEffect(() => onSessionExpired(() => setUser(null)), []);

  // Another tab signed out, or signed in as someone else: follow it, so two
  // tabs never act as two different accounts on one stored token.
  useEffect(() => {
    function onStorage(e) {
      if (e.key !== null && !SESSION_KEYS.includes(e.key)) return;
      setUser(getToken() ? getSavedUser() : null);
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
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
    return (
      <div className="boot">
        <BrandLogo className="brand-logo--boot" />
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user, setCurrentUser, logout }}>
      <DashboardProvider>
      <ErrorBoundary resetKey={pathname}>
      <Suspense fallback={<div className="boot"><BrandLogo className="brand-logo--boot" /></div>}>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route
          path="/login"
          element={
            <RedirectIfAuthed>
              <Login />
            </RedirectIfAuthed>
          }
        />
        <Route
          path="/register"
          element={
            <RedirectIfAuthed>
              <Register />
            </RedirectIfAuthed>
          }
        />
        {/* The backend's GitHub callback lands here (routers/auth.py). */}
        <Route path="/auth/github" element={<GitHubCallback />} />
        {/* Onboarding is full-screen, outside the app shell: no sidebar or
            navigation to leave it by before it's finished. */}
        <Route
          path="/onboarding"
          element={
            <RequireOnboarding>
              <Onboarding />
            </RequireOnboarding>
          }
        />
        {/* Every signed-in page shares ONE persistent shell (sidebar + top bar,
            components/Layout.jsx AppShell): it stays mounted across navigation
            so the sidebar keeps its scroll position and state. */}
        <Route
          element={
            <RequireAuth>
              <AppShell />
            </RequireAuth>
          }
        >
          <Route
            path="/animals"
            element={
              <RequireAuth>
                <AnimalSelect />
              </RequireAuth>
            }
          />
          <Route
            path="/journey"
            element={
              <RequireAuth>
                <Journey />
              </RequireAuth>
            }
          />
          <Route
            path="/foundation"
            element={
              <RequireAuth>
                <Foundation />
              </RequireAuth>
            }
          />
          <Route
            path="/stories"
            element={
              <RequireAuth>
                <Stories />
              </RequireAuth>
            }
          />
          <Route
            path="/stories/:slug"
            element={
              <RequireAuth>
                <StoryBook />
              </RequireAuth>
            }
          />
          <Route
            path="/stories/:slug/read/:n"
            element={
              <RequireAuth>
                <StoryReader />
              </RequireAuth>
            }
          />
          <Route
            path="/real-chinese"
            element={
              <RequireAuth>
                <RealChinese />
              </RequireAuth>
            }
          />
          <Route
            path="/real-chinese/:slug"
            element={
              <RequireAuth>
                <RealChineseScene />
              </RequireAuth>
            }
          />
          <Route
            path="/sentence"
            element={
              <RequireAuth>
                <SentenceLesson />
              </RequireAuth>
            }
          />
          <Route
            path="/detective"
            element={
              <RequireAuth>
                <Detective />
              </RequireAuth>
            }
          />
          <Route
            path="/detective/file/:slug"
            element={
              <RequireAuth>
                <DetectiveFile />
              </RequireAuth>
            }
          />
          <Route
            path="/sound-world"
            element={
              <RequireAuth>
                <SoundWorld />
              </RequireAuth>
            }
          />
          <Route
            path="/hanzi/:char"
            element={
              <RequireAuth>
                <CharacterDNA />
              </RequireAuth>
            }
          />
          <Route
            path="/ecosystem"
            element={
              <RequireAuth>
                <Ecosystem />
              </RequireAuth>
            }
          />
          <Route
            path="/internet"
            element={
              <RequireAuth>
                <ChineseInternet />
              </RequireAuth>
            }
          />
          <Route
            path="/internet/:slug"
            element={
              <RequireAuth>
                <InternetItem />
              </RequireAuth>
            }
          />
          <Route
            path="/passport"
            element={
              <RequireAuth>
                <Passport />
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
            path="/grammar"
            element={
              <RequireAuth>
                <Grammar />
              </RequireAuth>
            }
          />
          <Route
            path="/grammar/:topicId"
            element={
              <RequireAuth>
                <GrammarTopic />
              </RequireAuth>
            }
          />
          <Route
            path="/hanzi"
            element={
              <RequireAuth>
                <Hanzi />
              </RequireAuth>
            }
          />
          <Route
            path="/real-chinese/talk/:scenarioId"
            element={
              <RequireAuth>
                <Conversation />
              </RequireAuth>
            }
          />
          <Route
            path="/real-chinese/case/:scenarioId"
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
            path="/voice-companion"
            element={
              <RequireAuth>
                <VoiceCompanion />
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
            path="/practice"
            element={
              <RequireAuth>
                <Practice />
              </RequireAuth>
            }
          />
          <Route
            path="/exam/:level"
            element={
              <RequireAuth>
                <Exam />
              </RequireAuth>
            }
          />
          <Route
            path="/review"
            element={
              <RequireAuth>
                <Practice forceSource="review" />
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
          <Route
            path="/admin"
            element={
              <RequireAdmin>
                <AdminHome />
              </RequireAdmin>
            }
          />
          <Route
            path="/admin/users"
            element={
              <RequireAdmin>
                <AdminUsers />
              </RequireAdmin>
            }
          />
        </Route>
        <Route path="/world/*" element={<MovedTo base="/real-chinese" />} />
        <Route path="/conversation/:scenarioId" element={<MovedTo base="/real-chinese/talk" />} />
        <Route path="/cases/:scenarioId" element={<MovedTo base="/real-chinese/case" />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </Suspense>
      </ErrorBoundary>
      </DashboardProvider>
    </AuthContext.Provider>
  );
}