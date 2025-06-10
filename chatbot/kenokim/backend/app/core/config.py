import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """애플리케이션 설정을 관리하는 클래스"""
    
    # API 설정
    app_name: str = "DevOps AI Assistant API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Google Gemini API 설정
    gemini_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    gemini_model: str = "gemini-2.0-flash"
    
    # MCP 서버 설정
    mcp_client_name: str = Field(default="devops-assistant", alias="MCP_CLIENT_NAME")
    mcp_server_url: str = Field(default="http://localhost:8000/sse", alias="MCP_SERVER_URL")
    mcp_transport: str = Field(default="sse", alias="MCP_TRANSPORT")
    
    # Grafana MCP 서버 설정
    grafana_mcp_url: str = Field(default="http://localhost:8091", alias="GRAFANA_MCP_URL")
    grafana_renderer_mcp_url: str = Field(default="http://localhost:8090", alias="GRAFANA_RENDERER_MCP_URL")
    
    # LangSmith 설정 (옵션)
    langsmith_tracing: Optional[str] = Field(default=None, alias="LANGSMITH_TRACING")
    langsmith_endpoint: Optional[str] = Field(default=None, alias="LANGSMITH_ENDPOINT")
    langsmith_api_key: Optional[str] = Field(default=None, alias="LANGSMITH_API_KEY")
    langsmith_project: Optional[str] = Field(default=None, alias="LANGSMITH_PROJECT")
    
    # FastAPI 서버 설정
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    
    # CORS 설정
    allowed_origins: list[str] = ["*"]
    allowed_methods: list[str] = ["*"]
    allowed_headers: list[str] = ["*"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 전역 설정 인스턴스
settings = Settings()


def get_settings() -> Settings:
    """설정 인스턴스를 반환하는 의존성 주입 함수"""
    return settings 