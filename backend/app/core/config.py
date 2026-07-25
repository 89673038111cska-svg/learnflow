from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://learnflow:learnflow_dev_password@localhost:5432/learnflow"
    SECRET_KEY: str = "dev_secret_key_change_in_production"
    MCP_API_TOKEN: str = "dev_mcp_token_change_in_production"
    LLM_BASE_URL: str = "http://192.168.1.64:8317/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "kimi-k3"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    class Config:
        env_file = ".env"


settings = Settings()
