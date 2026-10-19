import { useTranslation } from "react-i18next";
import Icon from "./Icon.jsx";

// The promotional video tour on the landing page. The files live in
// public/media/, so Vite copies them unchanged into dist/media/ and nginx
// serves them as plain static files (with byte-range requests, which is what
// lets a visitor seek). The phone app never shows the landing page, so the
// mobile build leaves media/ out (vite.config.js) instead of carrying 15 MB.
//
// preload="none": nothing of the video is downloaded until the visitor
// presses play; the page only fetches the small poster image. No autoplay,
// no muted: the voice-over is the point of the video.
export const PROMO_VIDEO = {
  src: "/media/chineseverse-promo-ru.mp4",
  poster: "/media/chineseverse-promo-poster.jpg",
  type: "video/mp4",
  lang: "ru",
  width: 1080,
  height: 1920,
};

export default function PromoVideo() {
  const { t } = useTranslation();
  return (
    <section className="card promo-video" aria-labelledby="promo-video-title">
      <div className="promo-video-text">
        <p className="page-eyebrow">
          <Icon name="play" size={13} /> {t("landing.videoEyebrow")}
        </p>
        <h2 className="h2 promo-video-title" id="promo-video-title">
          {t("landing.videoTitle")}
        </h2>
        <p className="sub">{t("landing.videoText")}</p>
        <p className="muted promo-video-note">{t("landing.videoVoiceNote")}</p>
      </div>
      <div className="promo-video-frame">
        <video
          className="promo-video-player"
          controls
          playsInline
          preload="none"
          poster={PROMO_VIDEO.poster}
          width={PROMO_VIDEO.width}
          height={PROMO_VIDEO.height}
          aria-label={t("landing.videoTitle")}
        >
          <source src={PROMO_VIDEO.src} type={PROMO_VIDEO.type} />
          <a href={PROMO_VIDEO.src} download>
            {t("landing.videoDownload")}
          </a>
        </video>
      </div>
    </section>
  );
}
