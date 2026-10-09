import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import { PrefsProvider } from "./prefs.jsx";
import { ThemeProvider } from "./theme.jsx";
import { i18nReady } from "./i18n.js";
import "./index.css";

// Wait for the learner's language (i18n.js loads all but English on demand);
// a failed load still renders, in English.
i18nReady.finally(() => ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ThemeProvider>
      <PrefsProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </PrefsProvider>
    </ThemeProvider>
  </React.StrictMode>
));
