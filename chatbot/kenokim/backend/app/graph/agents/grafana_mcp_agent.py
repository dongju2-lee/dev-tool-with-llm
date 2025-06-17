import os
from datetime import datetime, timedelta, timezone
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import tool

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from ...prompts.prompts import GRAFANA_AGENT_PROMPT
from ...core.config import settings

load_dotenv()

# LLM 초기화
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=settings.gemini_api_key,
    temperature=0
)

GRAFANA_MCP_URL = os.getenv("GRAFANA_MCP_URL")

# 시간 계산 및 형식 변환 도구들
@tool
def get_current_time_rfc3339() -> str:
    """현재 시간을 RFC3339 형식으로 반환합니다."""
    return datetime.now(timezone.utc).isoformat()

@tool
def get_time_hours_ago_rfc3339(hours: int) -> str:
    """지정된 시간 전의 시간을 RFC3339 형식으로 반환합니다.
    
    Args:
        hours: 몇 시간 전인지 (예: 24시간 전이면 24)
    """
    past_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    return past_time.isoformat()

@tool
def get_time_range_rfc3339(hours_ago: int) -> dict:
    """시작 시간과 끝 시간을 RFC3339 형식으로 반환합니다.
    
    Args:
        hours_ago: 몇 시간 전부터 현재까지 (예: 24시간이면 24)
    
    Returns:
        dict: {"start": "시작시간", "end": "끝시간"}
    """
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours_ago)
    
    return {
        "start": start_time.isoformat(),
        "end": end_time.isoformat()
    }

@tool
def format_prometheus_time_range(hours_ago: int) -> dict:
    """Prometheus 쿼리에 사용할 시간 범위를 생성합니다.
    
    Args:
        hours_ago: 몇 시간 전부터 현재까지
        
    Returns:
        dict: Prometheus API에 사용할 시간 파라미터
    """
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours_ago)
    
    return {
        "start": start_time.timestamp(),  # Unix timestamp
        "end": end_time.timestamp(),      # Unix timestamp
        "start_rfc3339": start_time.isoformat(),
        "end_rfc3339": end_time.isoformat(),
        "step": "1h"  # 1시간 간격으로 데이터 수집
    }



async def make_grafana_agent():
    # 시간 계산 도구들
    time_tools = [
        get_current_time_rfc3339,
        get_time_hours_ago_rfc3339,
        get_time_range_rfc3339,
        format_prometheus_time_range
    ]
    
    # Grafana MCP 도구들 가져오기
    try:
        client = MultiServerMCPClient(
            {
                "grafana_mcp_client": {
                    "url": f"{GRAFANA_MCP_URL}/sse",
                    "transport": "sse"
                }
            }
        )
        grafana_tools = await client.get_tools()
    except Exception as e:
        print(f"Warning: Could not get Grafana MCP tools: {e}")
        grafana_tools = []
    
    # 모든 도구 결합
    all_tools = time_tools + grafana_tools
    
    return create_react_agent(
        model=llm,
        tools=all_tools,
        prompt=GRAFANA_AGENT_PROMPT,
        name="grafana_agent"
    )
