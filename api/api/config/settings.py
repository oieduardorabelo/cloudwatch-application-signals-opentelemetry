import pathlib

import toml
from asgi_correlation_id import CorrelationIdFilter
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from api.config.logger import ProjectNameVersionFilter, logger_create

PROJECT_FOLDER = pathlib.Path(__file__).resolve().parent.parent.parent
PYPROJECT_TOML = toml.loads(open(f"{PROJECT_FOLDER}/pyproject.toml").read())


class Env(BaseSettings):
    APP_ENV: str = Field(default="production")
    APP_NAME: str = Field(default=PYPROJECT_TOML["project"]["name"])
    APP_VERSION: str = Field(default=PYPROJECT_TOML["project"]["version"])

    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)

    LOG_LEVEL: str = Field(default="DEBUG")

    PSQL_DATABASE: str = Field(default=None)
    PSQL_HOST: str = Field(default=None)
    PSQL_PASSWORD: str = Field(default=None)
    PSQL_PORT: str = Field(default=None)
    PSQL_USER: str = Field(default=None)

    QUEUE_ARCHIVE_URL: str = Field(default=None)

    @property
    def is_development(self):
        return self.APP_ENV == "development"

    @property
    def is_production(self):
        return self.APP_ENV == "production"

    model_config = SettingsConfigDict(
        env_file=f"{PROJECT_FOLDER}/api/.env",
        env_file_encoding="utf-8",
    )


env = Env()

logger = logger_create(
    as_json=env.is_production,
    handler_filters=[
        CorrelationIdFilter(default_value="-"),
        ProjectNameVersionFilter(
            project_name=env.APP_NAME,
            project_version=env.APP_VERSION,
        ),
    ],
    logger_level=env.LOG_LEVEL,
    logger_name=env.APP_NAME,
)
