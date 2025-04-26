"""
Grafana MCP 서버 CLI
"""
import asyncio
import os
import sys
import logging
from typing import List
import typer
from rich.console import Console
from rich.logging import RichHandler
from dotenv import load_dotenv

from . import __version__
from .server import GrafanaMCPServer
from .context import grafana_context
from . import tools

# 타이퍼 앱 생성
app = typer.Typer(help="Grafana MCP 서버")
console = Console()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("mcp-cli")

@app.callback()
def callback():
    """
    Grafana MCP 서버

    Model Context Protocol 서버로 Grafana API와 상호작용합니다.
    """
    # 환경 변수 로드
    load_dotenv()

@app.command()
def version():
    """버전 정보 표시"""
    console.print(f"Grafana MCP 서버 버전: [bold]{__version__}[/]")

@app.command()
def serve(
    transport: str = typer.Option("stdio", help="전송 유형 (stdio 또는 sse)"),
    host: str = typer.Option("localhost", help="SSE 전송을 위한 호스트"),
    port: int = typer.Option(8000, help="SSE 전송을 위한 포트"),
    debug: bool = typer.Option(False, help="디버그 모드 활성화"),
    grafana_url: str = typer.Option(None, help="Grafana URL (기본값: 환경 변수 GRAFANA_URL 또는 http://localhost:3000)"),
    grafana_api_key: str = typer.Option(None, help="Grafana API 키 (기본값: 환경 변수 GRAFANA_API_KEY)"),
    disabled_tools: List[str] = typer.Option(
        [], help="비활성화할 도구 카테고리 (예: dashboard,search)"
    )
):
    """Grafana MCP 서버 실행"""
    # Grafana 컨텍스트 초기화
    grafana_context.initialize(
        url=grafana_url,
        api_key=grafana_api_key,
        debug=debug
    )
    
    if not grafana_context.is_initialized:
        console.print("[bold red]오류:[/] Grafana 클라이언트를 초기화할 수 없습니다. API 키를 확인하세요.")
        raise typer.Exit(1)
    
    # MCP 서버 생성
    server = GrafanaMCPServer("grafana-mcp", __version__)
    
    # 도구 등록
    disabled_categories = set(cat.strip() for cat in disabled_tools)
    
    # 활성화된 카테고리를 기반으로 도구 추가
    if "search" not in disabled_categories:
        tools.search.add_tools(server)
        console.print("- [green]검색 도구 활성화됨[/]")
    else:
        console.print("- [yellow]검색 도구 비활성화됨[/]")
        
    if "dashboard" not in disabled_categories:
        tools.dashboard.add_tools(server)
        console.print("- [green]대시보드 도구 활성화됨[/]")
    else:
        console.print("- [yellow]대시보드 도구 비활성화됨[/]")
    
    # 서버 시작
    if transport == "stdio":
        console.print(f"Grafana MCP 서버를 [bold]STDIO[/] 전송으로 시작 중...")
        # 비동기 실행
        asyncio.run(server.start_stdio())
    elif transport == "sse":
        console.print(f"Grafana MCP 서버를 [bold]SSE[/] 전송으로 시작 중 ([bold]{host}:{port}[/])...")
        server.start_sse(host, port)
    else:
        console.print(f"[bold red]오류:[/] 알 수 없는 전송: {transport}")
        raise typer.Exit(1)

if __name__ == "__main__":
    app() 