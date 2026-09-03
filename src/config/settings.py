from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class NoDecode:
    """Marker annotation to prevent pydantic from JSON-decoding list fields from env vars."""


class Settings(BaseSettings):
    """Central configuration - loaded from environment variables and .env file"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    # -----------Application---------------------------------
    ENVIRONMENT: str = Field(default="development", description="devlopment | staging | UAT | production")
    DEBUG: bool = Field(default=True, description="Expose tracebacks in error responses")
    LOG_LEVEL: str = Field(default="INFO", description="Root log level")
    API_HOST: str = Field(default="0.0.0.0")  # noqa:S104
    API_PORT: int = Field(default=8000)
    API_V1_PREFIX: str = Field(default="/v1")
    BASE_DIR: str = Field(default_factory=lambda: str(Path(__file__).resolve().parent.parent.parent))

    # --Database ---------------------------------------------
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/bolierplate",
        description="Async PostgreSQL connection string",
    )
    DB_SCHEMA: str = Field(default="app", description="PostgreSQL schema for all tables")
    DB_ECHO: bool = Field(default=False, description="Echo SQL queries to log")
    DB_POOL_SIZE: int = Field(default=10, description="SQLAlchemy connection pool size")

    # ---------------Authentication-----------------------------------------------------------
    REQUIRE_AUTH: bool = Field(
        default=True,
        description="Require JWT on all endpoints. Fail-closed: default is True.",
    )
    OAuth_ALGORITHMS: Annotated[list[str], NoDecode] = Field(
        default=["RS256"],
        description="Allowed JWT signature algorithms --asymmetric only (RS256, RS384, RS512, ES256).",
    )
    OAUTH_TENANT_ID: str = Field(default="", description="Azure AD tenant ID")
    OAUTH_JWKS_URL: str = Field(
        default="",
        description="JWKS endpoint URL. AUto-derived from OAUTH_TENANT_ID if empty.",
    )
    OAUTH_AUDIENCE: str = Field(default="", description="Expected JWT audience claim")
    INITIAL_ADMIN_EMAILS: str = Field(default="", description="Comma-seperated bootstrap admin emails for first deployment")
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:5173"],
        description="Allowed CORS origins.Never user '*' with credentials",
    )

    #  -----------Azure OpenAI---------------------------------------------------------------------------

    AZURE_OPENAI_ENDPOINT: str = Field(default="", description="Azure OpenAI resource endpoint")
    AZURE_OPENAI_API_KEY: str = Field(default="", description="Azure OpenAI API key")
    AZURE_OPENAI_API_VERSION: str = Field(default="2024-06-01")
    AZURE_OPENAI_DEPLOYMENT: str = Field(default="gpt-4o", description="Chat completion deployment name")
    EMBEDDING_MODEL: str = Field(default="text-embedding-3-small")
    EMBEDDING_DIMENSIONS: int = Field(default=1536)

    # - Feature Flags
    BACKGROUND_JOBS_ENABLED: bool = Field(default=False, description="Enable SQS-based background jobs")
    RAG_ENABLED: bool = Field(default=False, description="Enable RAG document ingestion and search")
    RATE_LIMITING_ENABLED: bool = Field(default=False, description="Enable per-session/per-user rate limits")

    # - Rate Limiting
    RATE_LIMIT_PER_SESSION: int = Field(default=500, description="Max LLM calls per session")
    RATE_LIMIT_PER_USER_HOURLY: int = Field(default=100, description="Max LLM calls per user per hour")

    # - Broker
    DEFAULT_BROKER: str = Field(default="sqs", description="Message broker type")
    AWS_REGION: str = Field(default="us-east-1")
    AWS_ENDPOINT_URL: str = Field(default="http://localhost:4566", description="LocalStack endpoint for dev")

    # - Validators
    @field_validator("OAuth_ALGORITHMS", mode="before")
    @classmethod
    def guard_jwt_algorithms(cls, v: str | list[str]) -> list[str]:
        """Reject unsafe JWT algorithms that enable algorithm confusion attacks (PSEC T-017)."""
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except json.JSONDecodeError:
                v = [a.strip() for a in v.split(",") if a.strip()]
        algorithms = [str(a).strip() for a in v]
        for alg in algorithms:
            if alg.upper().startswith("HS") or alg.upper() == "NONE":
                msg = f"Unsafe JWT algorithm '{alg}' rejected. HS*/none algorithms enable algorithm confusion attacks. Use asymmetric algorithms: RS256, RS384, RS512, ES256."
                raise ValueError(msg)
        return algorithms

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def current_version(self) -> str:
        version_file = Path(self.BASE_DIR) / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()
        return "0.0.0"

    @property
    def jwks_url(self) -> str:
        if self.OAUTH_JWKS_URL:
            return self.OAUTH_JWKS_URL
        if self.OAUTH_TENANT_ID:
            return f"https://login.microsoftonline.com/{self.OAUTH_TENANT_ID}/discovery/v2.0/keys"
        return ""


settings = Settings()
