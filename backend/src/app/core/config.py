from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PMS_", extra="ignore", hide_input_in_errors=True)

    environment: Literal["local", "test", "staging", "production"] = "local"
    process: Literal["api", "worker", "dispatcher"] = "api"
    database_host: str = "127.0.0.1"
    database_port: int = Field(default=15432, ge=1, le=65535)
    database_name: str = "property_management"
    database_password: SecretStr | None = None
    pool_size: int = Field(default=5, ge=1, le=20)
    database_timeout_seconds: int = Field(default=2, ge=1, le=10)
    redis_host: str = "127.0.0.1"
    redis_port: int = Field(default=16379, ge=1, le=65535)
    redis_password: SecretStr
    queue_name: str = Field(default="pms.events", pattern=r"^[a-zA-Z0-9_.-]{1,100}$")
    dispatch_password: SecretStr | None = None

    @model_validator(mode="after")
    def validate_credentials(self) -> "Settings":
        required = (
            self.dispatch_password if self.process == "dispatcher" else self.database_password
        )
        if required is None:
            raise ValueError("Database credentials are required for the selected process")
        for secret in (required, self.redis_password):
            if len(secret.get_secret_value()) < 24:
                raise ValueError("Generated credentials of at least 24 characters are required")
        return self

    def database_url(self, *, dispatcher: bool = False) -> URL:
        password = self.dispatch_password if dispatcher else self.database_password
        if password is None:
            raise ValueError("Dispatcher credentials are required for dispatch")
        return URL.create(
            "postgresql+psycopg",
            username="pms_dispatcher" if dispatcher else "pms_app",
            password=password.get_secret_value(),
            host=self.database_host,
            port=self.database_port,
            database=self.database_name,
        )

    def broker_url(self) -> str:
        from urllib.parse import quote

        password = quote(self.redis_password.get_secret_value(), safe="")
        return f"redis://:{password}@{self.redis_host}:{self.redis_port}/0"
