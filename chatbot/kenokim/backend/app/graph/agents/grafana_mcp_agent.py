import os
from datetime import datetime, timedelta, timezone
from typing import List
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

from dotenv import load_dotenv
from ..mcp.grafana_client import get_grafana_mcp_client
from ...core.config import settings

load_dotenv()

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

# Grafana Agent 전용 프롬프트
GRAFANA_AGENT_PROMPT = """
너는 Grafana 모니터링 시스템의 전문 데이터 분석 에이전트입니다.
사용자의 요청을 받으면 반드시 Grafana 도구를 사용하여 실제 데이터를 조회하고 분석해야 합니다.

- 가장 먼저, 대시보드 목록을 조회해야 합니다.
  - 어떤 대시보드 목록이 있고, 어떤 대시보드를 읽을 것인지 명확하게 반환해야 합니다.

- 어떤 대시보드 목록이 있는지 확인하고, 적절한 대시보드를 선택합니다.
- 그 후, 그 대시보드에서 패널 목록을 확인하고, 적절한 패널을 확인합니다.
- 그 패널을 확인하여, 사용자가 원하는 정보를 반환합니다.
- 사용자에게 전달하는 시간은 한국시간 기준으로 해 주세요.

해당 패널에서 데이터를 조회할 때 올바른 시간 형식을 사용합니다.

대시보드 관련 팁:
- ~~서비스에서 등등 정보를 보려면, 'Service Status Overview' 대시보드를 확인하세요.
- ~~CPU, memory 시스템 ... 등등 시스템 정보를 보려면 'Node Exporter '로 시작하는 대시보드를 확인하세요. 

시간 관련 팁:
- "최근 24시간" = format_prometheus_time_range(24) 사용
- "지난 1시간" = format_prometheus_time_range(1) 사용
- Prometheus 쿼리에는 Unix timestamp 또는 RFC3339 형식 사용

반드시 실제 데이터를 조회하고 구체적인 수치를 제공해야 합니다.
"""

async def make_grafana_agent(llm):
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
        prompt=GRAFANA_AGENT_PROMPT
    )
