import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import Icon from "./Icon.jsx";

// A quiet strip while the device has no connection (a phone on the metro,
// the app opened in airplane mode). Requests then fail with the localized
// apiErrors.network message, page by page; this says why once, up front,
// and that nothing is lost: answers are graded and saved by the server, so
// there is no half-saved progress waiting on the device. It goes away by
// itself when the connection is back.
export default function NetworkBanner() {
  const { t } = useTranslation();
  const [online, setOnline] = useState(() => (typeof navigator === "undefined" ? true : navigator.onLine !== false));

  useEffect(() => {
    const up = () => setOnline(true);
    const down = () => setOnline(false);
    window.addEventListener("online", up);
    window.addEventListener("offline", down);
    return () => {
      window.removeEventListener("online", up);
      window.removeEventListener("offline", down);
    };
  }, []);

  if (online) return null;
  return (
    <div className="net-banner" role="status" aria-live="polite">
      <Icon name="alert" size={15} />
      <span>{t("network.offline")}</span>
    </div>
  );
}
