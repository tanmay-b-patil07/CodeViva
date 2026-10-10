from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEVELOPMENT_JWT_SECRET = (
    "codeviva-development-only-secret-replace-before-production-2026"
)
DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:password@localhost:5432/codecomp"
_DEVELOPMENT_ORIGIN = "http://localhost:3000"
_KNOWN_WEAK_SECRETS = {"change-me", "secret", "password", "development-secret"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "CodeViva API"
    api_prefix: str = "/api"
    environment: str = "development"
    allow_database_reset: bool = False

    # Database
    database_url: str = Field(
        default=DEFAULT_DATABASE_URL
    )

    # Authentication
    jwt_secret: str = Field(default=DEVELOPMENT_JWT_SECRET, repr=False)
    jwt_expire_minutes: int = 480

    # Teacher registration
    teacher_invite_code: str = Field(default="")

    # Agnes AI (OpenAI-compatible API)
    agnes_api_key: str = ""
    agnes_api_base_url: str = "https://apihub.agnes-ai.com/v1"

    # Models
    model_practice: str = "agnes-2.5-flash"
    model_exam: str = "agnes-2.5-flash"

    # CORS
    allowed_origins: str = _DEVELOPMENT_ORIGIN

    # Cookies
    cookie_secure: bool = False

    # Exam generation
    generation_lead_minutes: int = 30
    confidence_review_threshold: float = 0.6
    exam_grace_seconds: int = Field(default=30, ge=0)

    @property
    def allowed_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def validate_jwt_secret(environment: str, secret: str) -> None:
    """Fail closed on signing keys that are unsafe for the configured environment."""
    normalized_environment = environment.strip().lower()
    if normalized_environment not in {"development", "test", "production"}:
        raise RuntimeError("ENVIRONMENT must be development, test, or production.")
    if not secret or len(secret.encode("utf-8")) < 32:
        raise RuntimeError("JWT_SECRET must contain at least 32 bytes.")
    if normalized_environment == "production" and (
        secret == DEVELOPMENT_JWT_SECRET
        or "development-only" in secret.lower()
        or secret.strip().lower() in _KNOWN_WEAK_SECRETS
    ):
        raise RuntimeError("Production requires a unique, non-placeholder JWT_SECRET.")


def validate_runtime_settings(config: Settings) -> None:
    """Validate deployment-critical settings without exposing their values."""
    if "environment" not in config.model_fields_set:
        raise RuntimeError("ENVIRONMENT must be set explicitly for application startup.")
    environment = config.environment.strip().lower()
    validate_jwt_secret(environment, config.jwt_secret)

    if "*" in config.allowed_origins_list:
        raise RuntimeError("ALLOWED_ORIGINS must use explicit origins.")

    if environment != "production":
        return

    origins = config.allowed_origins_list
    if not origins or origins == [_DEVELOPMENT_ORIGIN]:
        raise RuntimeError("Production requires an explicit ALLOWED_ORIGINS allowlist.")
    for origin in origins:
        parsed = urlsplit(origin)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        ):
            raise RuntimeError("Production ALLOWED_ORIGINS must contain HTTPS origins only.")

    database = urlsplit(config.database_url)
    if (
        config.database_url == DEFAULT_DATABASE_URL
        or (database.username == "postgres" and database.password == "password")
    ):
        raise RuntimeError("Production requires an explicitly configured DATABASE_URL.")
    if not config.cookie_secure:
        raise RuntimeError("COOKIE_SECURE must be enabled in production.")
    if config.teacher_invite_code.strip().lower() in _KNOWN_WEAK_SECRETS | {
        "choose-a-code"
    }:
        raise RuntimeError("Production requires a unique TEACHER_INVITE_CODE.")
