
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DB_USER: str = "taxi"
    DB_PASSWORD: str = "local_password"
    DB_HOST: str = "db"
    DB_PORT: int = 5432
    DB_NAME: str = "taxi_local"
    DATABASE_URL: str | None = None

    BOT_TOKEN: str
    SECRET_KEY: str
    
    CORS_ORIGINS: list[str] = [
        "https://fletcher-inordinate-leontine.ngrok-free.dev",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000"
    ]
    MAX_INIT_DATA_AGE_SECONDS: int = 86400
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    
    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()