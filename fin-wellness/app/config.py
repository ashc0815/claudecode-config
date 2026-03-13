from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # AI
    anthropic_api_key: str = ""

    # Local database
    db_path: str = "fin_wellness.db"

    # App
    app_env: str = "development"
    log_level: str = "INFO"

    # Privacy: encryption key for optional cloud backup
    backup_encryption_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
