from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_key: str = ""

    # AI APIs
    mistral_api_key: str = ""
    anthropic_api_key: str = ""

    # Feishu
    feishu_webhook_url: str = ""
    feishu_app_id: str = ""
    feishu_app_secret: str = ""

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    max_weekly_rule_adjustments: int = 3
    learning_min_feedback_count: int = 10
    ab_test_min_sample: int = 50

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
