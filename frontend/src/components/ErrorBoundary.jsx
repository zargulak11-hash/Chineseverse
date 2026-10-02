import { Component } from "react";
import i18n from "../i18n.js";

// App-wide safety net: without it, any render error (like the undeclared
// variable that once blanked the Vocabulary page) makes React unmount the
// whole tree and the user sees an empty screen. This shows a translated
// message and a Reload button instead. `resetKey` (the current path) clears
// the error on navigation, so one broken page doesn't lock the whole app.
//
// Two are mounted: one around all routes in App.jsx (landing, auth, and the
// shell itself), and one inside AppShell around the page outlet. Without the
// inner one, a single page's render error replaced the whole shell, and the
// next navigation mounted a fresh sidebar: scrolled back to the top, with
// its collapse state re-read from storage.
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("Render error caught by ErrorBoundary:", error, info?.componentStack);
  }

  componentDidUpdate(prevProps) {
    if (this.state.error && prevProps.resetKey !== this.props.resetKey) {
      this.setState({ error: null });
    }
  }

  render() {
    if (!this.state.error) return this.props.children;
    // `inShell`: the boundary around the page outlet inside the persistent
    // app shell (Layout.jsx AppShell). The message then takes the page's
    // place under the sidebar and top bar instead of a full-screen takeover.
    const inShell = this.props.inShell;
    return (
      <div className={inShell ? "page" : "boot"} role="alert">
        <div className="card" style={{ maxWidth: 420, margin: inShell ? "0 auto" : undefined, textAlign: "center", letterSpacing: "normal", textTransform: "none" }}>
          <h2 className="h2" style={{ marginTop: 0 }}>{i18n.t("common.renderError")}</h2>
          <p className="sub">{i18n.t("common.renderErrorHint")}</p>
          <button type="button" className="btn primary" style={{ marginTop: 12 }} onClick={() => window.location.reload()}>
            {i18n.t("common.reload")}
          </button>
        </div>
      </div>
    );
  }
}
