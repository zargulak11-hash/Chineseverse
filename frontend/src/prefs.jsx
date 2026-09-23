import { createContext, useContext, useEffect, useState } from "react";

const SOUND_KEY = "chineseverse_sound_enabled";
const NOTIF_KEY = "chineseverse_notif_enabled";

const PrefsContext = createContext(null);

function readBool(key, fallback) {
  try {
    const saved = localStorage.getItem(key);
    if (saved === "0") return false;
    if (saved === "1") return true;
  } catch {
    // ignore — storage may be unavailable
  }
  return fallback;
}

// App-wide, persisted, genuinely-wired preferences — mirrors the existing
// ThemeProvider pattern (localStorage-backed React context) rather than a
// one-off per-component localStorage read, so every mounted component
// (Topbar's notification bell, DuelBattle's TTS) sees a change the moment
// Settings saves it, not just after a remount.
export function PrefsProvider({ children }) {
  const [soundEnabled, setSoundEnabledState] = useState(() => readBool(SOUND_KEY, true));
  const [notifEnabled, setNotifEnabledState] = useState(() => readBool(NOTIF_KEY, true));

  useEffect(() => {
    try {
      localStorage.setItem(SOUND_KEY, soundEnabled ? "1" : "0");
    } catch {
      // ignore
    }
  }, [soundEnabled]);

  useEffect(() => {
    try {
      localStorage.setItem(NOTIF_KEY, notifEnabled ? "1" : "0");
    } catch {
      // ignore
    }
  }, [notifEnabled]);

  return (
    <PrefsContext.Provider
      value={{
        soundEnabled,
        setSoundEnabled: setSoundEnabledState,
        notifEnabled,
        setNotifEnabled: setNotifEnabledState,
      }}
    >
      {children}
    </PrefsContext.Provider>
  );
}

export function usePrefs() {
  return useContext(PrefsContext);
}
