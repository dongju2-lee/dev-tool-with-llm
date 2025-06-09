import os
from datetime import datetime, timedelta, timezone
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import tool

from dotenv import load_dotenv

load_dotenv()


GRAFANA_RENDERER_MCP_URL = os.getenv("GRAFANA_RENDERER_MCP_URL")

# 시간 계산 및 형식 변환 도구들 (grafana_mcp_agent와 동일)
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

def get_grafana_renderer_mcp_client():
    """
    Get a MultiServerMCPClient instance for Grafana MCP servers.
    """
    return MultiServerMCPClient(
            {
                "grafana_renderer_mcp_client": {
                    "url": f"{GRAFANA_RENDERER_MCP_URL}/sse",
                    "transport": "sse"
                }
            }
        )

# Grafana Renderer Agent 전용 프롬프트
GRAFANA_RENDERER_AGENT_PROMPT = """
너는 Grafana 대시보드 시각화 및 렌더링 전문 에이전트입니다.
사용자의 요청을 받으면 반드시 Grafana 도구를 사용하여 대시보드 이미지나 차트를 생성하고 시각화해야 합니다.

## 스마트 렌더링 가이드라인:

### 1. 대시보드 식별 및 처리
- 사용자가 구체적인 대시보드 이름을 제시하지 않은 경우:
  * 먼저 대시보드 목록을 조회합니다
  * 사용 가능한 대시보드들을 사용자에게 보여줍니다
  * "어떤 대시보드를 렌더링할지 명확하게 알려주세요"라고 안내합니다

- 사용자가 대시보드 이름을 제시한 경우:
  * 해당 대시보드를 찾아서 바로 처리를 진행합니다
  * 대시보드 이름이 모호한 경우 가장 유사한 대시보드를 선택하고 확인 메시지를 포함합니다

### 2. 시간 범위 스마트 처리 (핵심!)
- 사용자가 시간 범위를 명시하지 않은 경우:
  * **기본값으로 최근 1시간을 사용합니다**
  * 렌더링 후 다음과 같이 안내합니다: 
    "최근 1시간 데이터로 렌더링했습니다. 다른 시간 범위(예: 지난 24시간, 지난 6시간)가 필요하시면 말씀해 주세요."

- 사용자가 시간 범위를 명시한 경우:
  * 요청된 시간 범위를 사용합니다
  * "지난 24시간", "최근 6시간", "어제", "지난주" 등의 표현을 인식합니다

### 3. 렌더링 실행 단계
1. 대시보드 목록 조회 (필요한 경우)
2. 대상 대시보드 확인 및 선택
3. 패널 목록 확인
4. 시간 범위 설정 (명시되지 않으면 1시간 기본값)
5. 대시보드 렌더링 실행
6. 결과 제공 및 시간 범위 옵션 안내

### 4. 대시보드 매칭 팁
- "node exporter" → "Node Exporter Full" 또는 "Node Exporter Simple" 대시보드
- "prometheus" → "Prometheus Stats" 또는 "Prometheus 2.0 Stats" 대시보드  
- "service" → "Service Status Overview" 대시보드
- "sample" → "Sample Micro App Dashboard" 대시보드

### 5. 시간 형식 사용
- format_prometheus_time_range(1) : 최근 1시간 (기본값)
- format_prometheus_time_range(6) : 최근 6시간
- format_prometheus_time_range(24) : 최근 24시간

### 6. 사용자 응답 예시
"Node Exporter Full 대시보드를 최근 1시간 데이터로 렌더링했습니다. 
다른 시간 범위(예: 지난 24시간, 지난 6시간)가 필요하시면 말씀해 주세요."

반드시 실제 대시보드를 렌더링하고 구체적인 시각화 결과를 제공해야 합니다.
불필요한 질문 대신 기본값을 사용하여 빠르게 결과를 제공하되, 사용자가 조정할 수 있도록 안내합니다.
"""

async def make_grafana_renderer_agent(llm):
    # 시간 계산 도구들
    time_tools = [
        get_current_time_rfc3339,
        get_time_hours_ago_rfc3339,
        get_time_range_rfc3339,
        format_prometheus_time_range
    ]
    
    # Grafana Renderer MCP 도구들 가져오기
    try:
        client = get_grafana_renderer_mcp_client()
        grafana_tools = await client.get_tools()
    except Exception as e:
        print(f"Warning: Could not get Grafana Renderer MCP tools: {e}")
        grafana_tools = []
    
    # 모든 도구 결합
    all_tools = time_tools + grafana_tools
    
    return create_react_agent(
        model=llm,
        tools=all_tools,
        prompt=GRAFANA_RENDERER_AGENT_PROMPT,
        name="grafana_renderer_mcp_agent"
    )
