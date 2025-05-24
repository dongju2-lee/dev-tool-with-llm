import logging
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # With external dependencies like Valkey
    integration_mode: bool = True

    # Including LLM calls from VertexAI
    llm_enabled: bool = True

    gcp_project_id: str = "gen-lang-client-0449310391"
    gcp_vertexai_location: str = "asia-northeast1"
    model_name: str = "gemini-2.0-flash"

    langfuse_enabled: bool = False
    langfuse_secret_key: str = ""
    langfuse_public_key: str = ""
    langfuse_host: str = ""

    log_level: int = logging.INFO

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        logging.getLogger("agent_server").setLevel(self.log_level)


settings = Settings()