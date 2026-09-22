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

    # AI (never hardcode values here — always via .env)
    ai_provider: str = "auto"  # "openai" | "offline" | "auto"
    ai_api_key: str | None = None
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4o-mini"
    ai_speech_model: str = "whisper-1"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()