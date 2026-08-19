from typing import List, Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application
    PROJECT_NAME: str = "Selnikel AI"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    LOG_LEVEL: str = "INFO"
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3005",
        "http://127.0.0.1:3005",
        "http://localhost:8000",
    ]

    # Database (PostgreSQL)
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/selnikel_ai"
    )

    # Qdrant Vector DB
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_GRPC_PORT: int = 6334
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION_NAME: str = "selnikel_docs"
    QDRANT_PREFER_GRPC: bool = False

    # LLM Settings
    LLM_PROVIDER: Literal["openai", "ollama"] = "openai"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_API_KEY: Optional[str] = None

    # Ollama Settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"

    # Embedding Settings
    EMBEDDING_PROVIDER: str = "bge-m3"
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_DIMENSION: int = 1024

    # Storage
    STORAGE_DIR: str = "./data/documents"

    # Authentication & Security
    AUTH_MODE: Literal["development", "oidc", "bff"] = "development"
    JWT_SECRET_KEY: str = "dev-insecure-jwt-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    OIDC_ISSUER: Optional[str] = None
    OIDC_CLIENT_ID: Optional[str] = None
    OIDC_AUDIENCE: Optional[str] = None
    OIDC_JWKS_URI: Optional[str] = None
    OIDC_TENANT_ID: Optional[str] = None
    SESSION_COOKIE_NAME: str = "selnikel_session"
    SESSION_SECRET_KEY: str = "dev-insecure-session-secret-change-in-production-min32char"

    def validate_auth_configuration(self) -> None:
        """Fail-fast validation for startup security and authentication modes."""
        if self.ENVIRONMENT == "production":
            # 1. Reject development auth in production
            if self.AUTH_MODE == "development":
                raise RuntimeError("Security Violation: AUTH_MODE 'development' is forbidden in production.")

            # 2. Reject wildcard CORS in production
            if "*" in self.BACKEND_CORS_ORIGINS:
                raise RuntimeError("Security Violation: Wildcard '*' in BACKEND_CORS_ORIGINS is forbidden in production.")

            # 3. Validate OIDC in production
            if self.AUTH_MODE == "oidc":
                if not self.OIDC_ISSUER or not self.OIDC_CLIENT_ID:
                    raise RuntimeError("AUTH_MODE 'oidc' in production requires OIDC_ISSUER and OIDC_CLIENT_ID.")
                if self.JWT_ALGORITHM == "HS256" and not self.OIDC_JWKS_URI:
                    raise RuntimeError("Security Violation: Production OIDC requires asymmetric RS256/ES256 with JWKS.")

            # 4. Validate BFF in production
            elif self.AUTH_MODE == "bff":
                if len(self.SESSION_SECRET_KEY) < 32 or self.SESSION_SECRET_KEY.startswith("dev-"):
                    raise RuntimeError("Security Violation: Production BFF mode requires a 32+ char secure SESSION_SECRET_KEY.")
        else:
            # Development/Staging sanity checks
            if self.AUTH_MODE == "oidc" and not (self.OIDC_ISSUER and self.OIDC_CLIENT_ID) and not self.JWT_SECRET_KEY:
                raise RuntimeError("OIDC mode requires either OIDC_ISSUER/OIDC_CLIENT_ID or a valid JWT_SECRET_KEY.")


settings = Settings()
