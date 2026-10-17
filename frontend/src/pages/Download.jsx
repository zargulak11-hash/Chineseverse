import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { ANDROID_APP, RELEASES_URL, detectPlatform } from "../appDownload.js";
import { useAuth } from "../auth.js";
import Icon from "../components/Icon.jsx";
import PublicHeader from "../components/PublicHeader.jsx";
import { isNativeApp } from "../platform.js";

// /download: the Android app for anyone, signed in or not. The visitor's own
// device decides what comes first -- the download on an Android phone, the
// way to get it onto a phone from a computer, the honest iPhone status on an
// iPhone (there is no iOS build to install yet, so no iOS button). The file
// itself lives on a GitHub Release (appDownload.js), not in this bundle.

const PAGE_URL = "chineseverse.qobus.tj/download";
const BENEFITS = [
  ["user", "benefit1"],
  ["volume", "benefit2"],
  ["mic", "benefit3"],
  ["phone", "benefit4"],
];
const STEPS = ["step1", "step2", "step3", "step4", "step5", "step6"];
const HELP = ["help1", "help2", "help3", "help4", "help5", "help6"];

function AndroidButton() {
  const { t } = useTranslation();
  return (
    <a className="btn primary dl-btn" href={ANDROID_APP.url} download={ANDROID_APP.fileName}>
      <Icon name="download" size={18} /> {t("download.androidButton")}
    </a>
  );
}

function Meta() {
  const { t, i18n } = useTranslation();
  const size = (ANDROID_APP.sizeBytes / 1e6).toLocaleString(i18n.language, { maximumFractionDigits: 1 });
  return <p className="dl-meta">{t("download.meta", { version: ANDROID_APP.version, size, android: ANDROID_APP.minAndroid })}</p>;
}

export default function Download() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const platform = useMemo(() => detectPlatform(), []);

  if (isNativeApp) {
    return (
      <>
        <PublicHeader />
        <div className="page">
          <div className="card dl-hero">
            <h1 className="h1">{t("download.inAppTitle")}</h1>
            <p className="sub">{t("download.inAppText")}</p>
            <Link to="/dashboard" className="btn primary">{t("download.inAppButton")}</Link>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <PublicHeader />
      <div className="page dl-page">
        <div className="page-eyebrow"><Icon name="phone" size={13} /> {t("download.eyebrow")}</div>
        <h1 className="h1">{t("download.title")}</h1>
        <p className="sub">{t("download.subtitle")}</p>

        {platform === "ios" ? (
          <section className="card dl-hero" aria-labelledby="dl-ios">
            <h2 className="h2" id="dl-ios">{t("download.iosTitle")}</h2>
            <p className="sub">{t("download.iosText")}</p>
            <div className="row">
              <Link to="/login" className="btn primary">{t("download.iosButton")}</Link>
            </div>
            <p className="dl-meta">{t("download.iosAndroidNote")}</p>
          </section>
        ) : (
          <section className="card dl-hero" aria-labelledby="dl-get">
            <h2 className="h2" id="dl-get">
              {platform === "android" ? t("download.forAndroidTitle") : t("download.desktopTitle")}
            </h2>
            <p className="sub">
              {platform === "android" ? t("download.forAndroidText") : t("download.desktopText", { url: PAGE_URL })}
            </p>
            <AndroidButton />
            <Meta />
            {platform === "desktop" && (
              <div className="dl-alt">
                <p className="side-title">{t("download.desktopAltTitle")}</p>
                <ol className="dl-steps">
                  <li>{t("download.desktopAlt1")}</li>
                  <li>{t("download.desktopAlt2")}</li>
                  <li>{t("download.desktopAlt3")}</li>
                </ol>
              </div>
            )}
          </section>
        )}

        <h2 className="h2 section-title dl-section">{t("download.benefitsTitle")}</h2>
        <div className="dl-benefits">
          {BENEFITS.map(([icon, key]) => (
            <div className="card flat dl-benefit" key={key}>
              <span className="dl-benefit-ic" aria-hidden="true"><Icon name={icon} size={18} /></span>
              <h3 className="dl-benefit-title">{t(`download.${key}Title`)}</h3>
              <p className="sub">{t(`download.${key}Text`)}</p>
            </div>
          ))}
        </div>

        <div className="grid grid-2 dl-section">
          <section className="card" aria-labelledby="dl-install">
            <h2 className="h2" id="dl-install">{t("download.installTitle")}</h2>
            <ol className="dl-steps">
              {STEPS.map((key) => <li key={key}>{t(`download.${key}`)}</li>)}
            </ol>
            <div className="dl-note" role="note">
              <Icon name="alert" size={17} />
              <div>
                <p className="dl-note-title">{t("download.warningTitle")}</p>
                <p className="sub">{t("download.warningText")}</p>
              </div>
            </div>
          </section>

          <div className="col dl-side">
            <section className="card" aria-labelledby="dl-online">
              <h2 className="h2" id="dl-online">{t("download.onlineTitle")}</h2>
              <p className="sub">{t("download.onlineText")}</p>
              <p className="sub">{t("download.signInNote")}</p>
            </section>
            {platform !== "ios" && (
              <section className="card" aria-labelledby="dl-ios-status">
                <h2 className="h2" id="dl-ios-status">{t("download.iosTitle")}</h2>
                <p className="sub">{t("download.iosText")}</p>
              </section>
            )}
            <section className="card" aria-labelledby="dl-file">
              <h2 className="h2" id="dl-file">{t("download.detailsTitle")}</h2>
              <dl className="dl-file">
                <dt>{t("download.fileName")}</dt>
                <dd>{ANDROID_APP.fileName}</dd>
                <dt>{t("download.checksum")}</dt>
                <dd className="dl-sum">{ANDROID_APP.sha256}</dd>
              </dl>
              <a className="btn small ghost" href={RELEASES_URL} target="_blank" rel="noopener noreferrer">
                {t("download.allVersions")}
              </a>
            </section>
          </div>
        </div>

        {/* What to do when the download or the install fails -- the page
            explained the happy path only, so a blocked install or a
            "problem parsing the package" left the visitor with nothing. */}
        <section className="card dl-section" aria-labelledby="dl-help">
          <h2 className="h2" id="dl-help">{t("download.helpTitle")}</h2>
          <dl className="dl-help">
            {HELP.map((key) => (
              <div className="dl-help-item" key={key}>
                <dt>{t(`download.${key}Q`)}</dt>
                <dd className="sub">
                  {t(`download.${key}A`, { file: ANDROID_APP.fileName, android: ANDROID_APP.minAndroid })}
                </dd>
              </div>
            ))}
          </dl>
          <div className="dl-help-fallback">
            <p className="sub">{t("download.helpFallback")}</p>
            <Link to={user ? "/dashboard" : "/login"} className="btn small">{t("download.helpWebsite")}</Link>
          </div>
        </section>
      </div>
    </>
  );
}
