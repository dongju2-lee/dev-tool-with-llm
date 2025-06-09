import os
from datetime import datetime, timedelta, timezone
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import tool

from dotenv import load_dotenv

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

## 스마트 데이터 분석 가이드라인:

### 1. 대시보드 및 메트릭 식별
- 사용자가 구체적인 대시보드나 메트릭을 명시하지 않은 경우:
  * 먼저 대시보드 목록을 조회합니다
  * 요청 내용에 가장 적절한 대시보드를 선택합니다
  * 선택 이유를 간단히 설명합니다

- 사용자가 특정 대시보드나 메트릭을 요청한 경우:
  * 해당 대시보드를 찾아서 바로 분석을 진행합니다

### 2. 시간 범위 스마트 처리 (핵심!)
- 사용자가 시간 범위를 명시하지 않은 경우:
  * **기본값으로 최근 1시간을 사용합니다**
  * 분석 후 다음과 같이 안내합니다:
    "최근 1시간 데이터를 분석했습니다. 다른 시간 범위(예: 지난 24시간, 지난 6시간)가 필요하시면 말씀해 주세요."

- 사용자가 시간 범위를 명시한 경우:
  * 요청된 시간 범위를 사용합니다
  * "지난 24시간", "최근 6시간", "어제", "지난주" 등의 표현을 인식합니다

### 3. 데이터 분석 실행 단계
1. 대시보드 목록 조회 (필요한 경우)
2. 적절한 대시보드 선택
3. 패널 목록 확인 및 관련 메트릭 식별
4. 시간 범위 설정 (명시되지 않으면 1시간 기본값)
5. 데이터 조회 및 분석 실행
6. 구체적인 수치와 함께 분석 결과 제공
7. 시간 범위 옵션 안내

### 4. 메트릭 매칭 팁
- "CPU" → Node Exporter 대시보드의 CPU 사용률 메트릭
- "메모리" → Node Exporter 대시보드의 메모리 사용률 메트릭
- "디스크" → Node Exporter 대시보드의 디스크 사용률 메트릭
- "서비스 상태" → Service Status Overview 대시보드
- "prometheus" → Prometheus Stats 대시보드

### 5. 시간 형식 사용
- format_prometheus_time_range(1) : 최근 1시간 (기본값)
- format_prometheus_time_range(6) : 최근 6시간
- format_prometheus_time_range(24) : 최근 24시간

### 6. 분석 결과 제공 방식
- 구체적인 수치와 단위 포함
- 정상 범위와의 비교
- 트렌드 분석 (증가/감소/안정)
- 한국시간 기준으로 시간 정보 제공

### 7. 사용자 응답 예시
"CPU 사용률을 최근 1시간 데이터로 분석한 결과, 평균 25.3%로 정상 범위입니다.
다른 시간 범위(예: 지난 24시간, 지난 6시간)가 필요하시면 말씀해 주세요."

반드시 실제 데이터를 조회하고 구체적인 수치를 제공해야 합니다.
불필요한 질문 대신 기본값을 사용하여 빠르게 분석을 제공하되, 사용자가 조정할 수 있도록 안내합니다.
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
        prompt=GRAFANA_AGENT_PROMPT,
        name="grafana_agent"
    )
