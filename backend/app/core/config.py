
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int = 5432
    DB_NAME: str

    BOT_TOKEN: str
    SECRET_KEY: str
    
    CORS_ORIGINS: list[str] = [
        "https://fletcher-inordinate-leontine.ngrok-free.dev",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000"
    ]
    MAX_INIT_DATA_AGE_SECONDS: int = 300
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    
    @property
    def database_url(self) -> str:
        # Формуємо URL для асинхронного підключення asyncpg
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8")

settings = Settings()