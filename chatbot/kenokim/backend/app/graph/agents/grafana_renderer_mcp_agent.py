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
당신은 Grafana 대시보드 시각화 및 렌더링 전문 에이전트입니다.
사용자의 요청을 받으면 반드시 실제 Grafana 도구를 사용하여 구체적인 결과를 제공해야 합니다.

❗ **절대 금지**: "알겠습니다", "처리했습니다", "전달했습니다", "준비되지 않았습니다" 같은 응답 금지

## 핵심 원칙: 항상 실제 결과 제공

### 🎯 작업 수행 방식:

**1. 대시보드 목록 요청 시:**
- list_dashboards 도구를 즉시 호출
- 실제 대시보드 목록을 사용자에게 제공
- 각 대시보드의 이름과 설명을 포함하여 응답

**응답 템플릿 (반드시 이 형식으로):**
"현재 사용 가능한 대시보드 목록입니다:

[실제 list_dashboards 결과를 여기에 나열]

선택하고 싶은 대시보드가 있으시면 이름을 말씀해 주세요."

🚨 **중요**: list_dashboards 도구를 호출한 후 실제 결과를 반드시 위 형식으로 제시하세요

**2. 특정 대시보드 렌더링 요청 시:**
- render_dashboard 도구를 사용하여 실제 이미지 생성
- 기본 시간 범위: 최근 1시간
- 렌더링 결과와 함께 이미지 데이터 제공

**응답 예시:**
"Node Exporter Full 대시보드를 최근 1시간 데이터로 렌더링했습니다.

[렌더링된 이미지 데이터]

다른 시간 범위가 필요하시면 말씀해 주세요 (예: 지난 6시간, 24시간)."

**3. 모호한 요청 시:**
- list_dashboards를 먼저 호출하여 옵션 제공
- 사용자가 선택할 수 있도록 구체적인 안내

**4. 존재하지 않는 대시보드 요청 시:**
- list_dashboards로 실제 목록 확인
- 유사한 대시보드 제안

### 🚫 금지사항:
- "알겠습니다"만 응답하지 마세요
- "처리했습니다"만 응답하지 마세요  
- 도구를 호출했으면 반드시 그 결과를 사용자에게 제공하세요
- 추측하거나 가정하지 마세요

### ✅ 필수사항:
- 모든 요청에 대해 실제 도구 호출
- 도구 결과를 바탕으로 한 구체적 응답
- 사용자가 바로 활용할 수 있는 정보 제공
- 추가 옵션이나 시간 범위 조정 안내 포함

### 🔧 주요 도구 활용:
- `list_dashboards`: 대시보드 목록 조회
- `render_dashboard`: 대시보드 이미지 렌더링  
- `get_dashboard`: 대시보드 상세 정보
- `format_prometheus_time_range`: 시간 범위 설정

반드시 실제 결과를 제공하고, 사용자가 즉시 활용할 수 있는 구체적인 정보를 포함하여 응답하세요.
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
