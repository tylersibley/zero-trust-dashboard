from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Okta
    okta_domain: str
    okta_api_token: str
    okta_client_id: str = ""
    okta_client_secret: str = ""

    # AWS
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    dynamodb_table_name: str = "zero-trust-events"

    # App
    app_env: str = "development"
    api_port: int = 8000
    log_level: str = "INFO"

    # Risk thresholds
    risk_threshold_high: int = 75
    risk_threshold_medium: int = 40

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def okta_base_url(self) -> str:
        domain = self.okta_domain.rstrip("/")
        if not domain.startswith("https://"):
            domain = f"https://{domain}"
        return domain


@lru_cache()
def get_settings() -> Settings:
    return Settings()
