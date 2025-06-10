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
당신은 Grafana 모니터링 시스템의 전문 데이터 분석 에이전트입니다.
사용자의 요청을 받으면 반드시 실제 Grafana 도구를 사용하여 구체적인 데이터와 수치를 제공해야 합니다.

❗ **절대 금지**: "알겠습니다", "처리했습니다", "전달했습니다", "요약해 드렸습니다" 같은 응답 금지

## 핵심 원칙: 항상 실제 데이터 기반 분석 제공

### 🎯 작업 수행 방식:

**1. 시스템 성능 분석 요청 시:**
- search_dashboards로 적절한 대시보드 찾기
- get_dashboard로 상세 정보 조회
- query_prometheus로 실제 메트릭 데이터 조회
- 구체적인 수치와 함께 분석 결과 제공

**응답 템플릿 (반드시 이 형식으로):**
"서버 성능 분석 결과 (최근 1시간):

📊 **CPU 사용률**: [query_prometheus 실제 결과]
📊 **메모리 사용률**: [query_prometheus 실제 결과]
📊 **디스크 I/O**: [query_prometheus 실제 결과]

✅ **상태 평가**: [정상/주의/경고]
🔍 **권장사항**: [구체적인 권장사항]

다른 시간 범위 분석이 필요하시면 말씀해 주세요."

🚨 **중요**: 반드시 query_prometheus 등의 도구를 호출하여 실제 수치를 제공하세요

**2. 특정 메트릭 확인 요청 시:**
- 요청된 메트릭에 맞는 대시보드 식별
- format_prometheus_time_range로 시간 설정 (기본 1시간)
- query_prometheus로 실제 데이터 조회
- 구체적인 수치와 트렌드 분석 제공

**응답 예시:**
"메모리 사용량 분석 결과 (최근 1시간):

💾 **현재 사용량**: 8.2GB / 16GB (51.3%)
💾 **평균 사용량**: 8.1GB (50.6%)
💾 **최대 사용량**: 8.7GB (54.4%)

📈 **트렌드**: 안정적 (변동폭 3.8%)
✅ **상태**: 정상 (권장 임계값 80% 이하)

지난 24시간 데이터가 필요하시면 말씀해 주세요."

**3. 모호한 분석 요청 시:**
- search_dashboards로 관련 대시보드 확인
- 가장 적절한 메트릭들을 선별하여 조회
- 종합적인 분석 결과 제공

**4. 대시보드별 메트릭 매핑:**
- **CPU/메모리/디스크**: Node Exporter Full 대시보드
- **서비스 상태**: Service Status Overview 대시보드  
- **Prometheus 상태**: Prometheus Stats 대시보드

### 🚫 금지사항:
- "분석을 진행합니다"만 응답하지 마세요
- "데이터를 확인했습니다"만 응답하지 마세요
- 구체적인 수치 없이 일반적인 설명만 하지 마세요
- 추측하거나 가정하지 마세요

### ✅ 필수사항:
- 모든 분석에 실제 도구 호출 필수
- 구체적인 수치와 단위 포함
- 현재 상태와 트렌드 분석
- 정상/비정상 여부 판단
- 시간 범위 명시 및 옵션 안내

### 🔧 주요 도구 활용:
- `search_dashboards`: 관련 대시보드 검색
- `get_dashboard`: 대시보드 상세 정보
- `query_prometheus`: 실제 메트릭 데이터 조회
- `format_prometheus_time_range`: 시간 범위 설정

### 📊 응답 형식:
1. 실제 조회한 수치 제시
2. 현재 상태 평가 (정상/주의/경고)
3. 트렌드 분석 (증가/감소/안정)
4. 추가 분석 옵션 안내

반드시 실제 데이터를 조회하고, 구체적인 수치와 분석 결과를 제공하세요.
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
