from app.core.config import Settings


def test_settings_defaults():
    settings = Settings()
    assert settings.PROJECT_NAME == "Selnikel AI"
    assert settings.API_V1_PREFIX == "/api/v1"
    assert settings.EMBEDDING_DIMENSION == 1024
    assert settings.LLM_PROVIDER in ["openai", "ollama"]
    assert "sqlite" in settings.DATABASE_URL or "postgresql" in settings.DATABASE_URL

