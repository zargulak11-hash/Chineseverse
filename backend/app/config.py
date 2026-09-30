from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LinguaVerse API"
    app_version: str = "2.0.0"
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/linguaverse"
    )
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Security
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    # Google Sign-In (Google Identity Services ID-token flow).
    # Only the client ID is required to verify tokens; the secret is reserved
    # for a future server-side authorization-code flow and unused today.
    google_client_id: str | None = None
    google_client_secret: str | None = None

    # Accounts whose Google-VERIFIED email is listed here are granted
    # is_admin on Google sign-in. Only the Google path consults this list:
    # a password registration never proves email ownership, so it must not
    # be able to claim admin by typing an allowlisted address. Override
    # with ADMIN_EMAILS='["a@x.com","b@y.com"]' in backend/.env.
    admin_emails: list[str] = ["zargulak11@gmail.com"]

    # AI (never hardcode values here — always via .env)
    # "gemini" | "offline" | "auto" ("auto" = Gemini when GEMINI_API_KEY is
    # set, else offline). Gemini has its own GEMINI_* names so leftover
    # AI_API_KEY/AI_BASE_URL/AI_MODEL lines from the old OpenAI setup are
    # ignored -- an OpenAI key must never be sent to Google.
    ai_provider: str = "auto"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"

    # Outgoing email (notification emails). Credentials only ever come from
    # backend/.env / the environment. With SMTP_HOST unset, email is simply
    # disabled: notifications are still stored and shown in the app.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None  # e.g. "ChineseVerse <no-reply@example.com>"
    smtp_security: str = "starttls"  # "starttls" | "ssl" | "none"
    smtp_timeout_seconds: int = 15
    # Public address of the frontend, for links inside emails.
    public_app_url: str = "https://chineseverse.qobus.tj"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()