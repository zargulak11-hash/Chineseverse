import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import { PrefsProvider } from "./prefs.jsx";
import { ThemeProvider } from "./theme.jsx";
import "./i18n.js";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ThemeProvider>
      <PrefsProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </PrefsProvider>
    </ThemeProvider>
  </React.StrictMode>
);