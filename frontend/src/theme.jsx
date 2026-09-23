import { createContext, useContext, useEffect, useState } from "react";

const STORAGE_KEY = "chineseverse_theme";
export const ThemeContext = createContext(null);

function getInitialTheme() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "ink" || saved === "paper") return saved;
  } catch {
    // ignore — storage may be unavailable (private mode, etc.)
  }
  return "ink";
}

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(getInitialTheme);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // ignore
    }
  }, [theme]);

  function toggleTheme() {
    setTheme((t) => (t === "ink" ? "paper" : "ink"));
  }

  return <ThemeContext.Provider value={{ theme, toggleTheme }}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  return useContext(ThemeContext);
}
