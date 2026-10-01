"""Configuration settings for the application.

Defines environment variables and computed properties for database connection.
"""

from pydantic import PostgresDsn, computed_field
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "Python Template"
    API_STR: str = "/api"
    ROOT_PATH: str = "/proxy/8000"

    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    TOKEN_TYPE: str = "bearer"  # noqa : S105

    POSTGRES_HOST: str
    POSTGRES_DATABASE: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_PORT: int

    @computed_field
    def postgres_dsn(self) -> PostgresDsn:
        """Compute postgres url from variables.

        :return: The postgres url as data source name
        """
        return MultiHostUrl.build(
            scheme="postgresql",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DATABASE,
        )


settings = Settings()
