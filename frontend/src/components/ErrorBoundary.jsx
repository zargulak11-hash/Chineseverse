import { Component } from "react";
import i18n from "../i18n.js";

// App-wide safety net: without it, any render error (like the undeclared
// variable that once blanked the Vocabulary page) makes React unmount the
// whole tree and the user sees an empty screen. This shows a translated
// message and a Reload button instead. `resetKey` (the current path) clears
// the error on navigation, so one broken page doesn't lock the whole app.
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
    return (
      <div className="boot" role="alert">
        <div className="card" style={{ maxWidth: 420, textAlign: "center", letterSpacing: "normal", textTransform: "none" }}>
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
