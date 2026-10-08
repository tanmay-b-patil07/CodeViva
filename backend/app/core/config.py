from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Database
    database_url: str = Field(
        default="postgresql+psycopg://postgres:password@localhost:5432/codecomp"
    )

    # Authentication
    jwt_secret: str = Field(default="change-me")
    jwt_expire_minutes: int = 480

    # Teacher registration
    teacher_invite_code: str = Field(default="choose-a-code")

    # Anthropic
    anthropic_api_key: str = ""

    # Models
    model_practice: str = "claude-haiku-4-5-20251001"
    model_exam: str = "claude-sonnet-5-5"

    # CORS
    allowed_origins: str = "http://localhost:3000"

    # Cookies
    cookie_secure: bool = False

    # Exam generation
    generation_lead_minutes: int = 30
    confidence_review_threshold: float = 0.6

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