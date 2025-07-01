from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PAPERPILOT_", env_file=".env", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8800
    debug: bool = False
    data_dir: str = "./data"
    database_url: str = "sqlite+aiosqlite:///./data/paperpilot.db"
    ollama_url: str = "http://localhost:11434"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    upload_dir: str = "./data/uploads"


settings = Settings()
