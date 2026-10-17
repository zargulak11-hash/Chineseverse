import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import BrandLogo from "./BrandLogo.jsx";
import LanguagePicker from "./LanguagePicker.jsx";

// The top row of the Login and Register cards: the logo, which leads back
// to the main page, and the language. These pages have no header, so a
// visitor who arrived on /login from a shared link had no way to the
// landing page or the app download except the browser's back button.
export default function AuthCardTools() {
  const { t } = useTranslation();
  return (
    <div className="formcard-tools">
      <Link to="/" className="brand formcard-brand" aria-label={t("nav.toLanding")}>
        <BrandLogo className="brand-logo--bar" />
      </Link>
      <LanguagePicker />
    </div>
  );
}
