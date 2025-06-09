import logging
from langgraph_supervisor import create_supervisor
from langchain_google_genai import ChatGoogleGenerativeAI

from .grafana_mcp_agent import make_grafana_agent
from .grafana_renderer_mcp_agent import make_grafana_renderer_agent
from ...core.config import settings
from dotenv import load_dotenv

load_dotenv()

# 로깅 설정
logger = logging.getLogger(__name__)

# init LLM
llm = ChatGoogleGenerativeAI(
    model=settings.gemini_model,
    google_api_key=settings.gemini_api_key,
    temperature=0
)

# Agent 설정 정보
AGENT_CONFIGS = {
    "grafana_agent": {
        "description": "Grafana 데이터 분석, 메트릭 조회, 모니터링 정보 제공 전문가",
        "capabilities": [
            "시스템 메트릭 분석 (CPU, 메모리, 디스크)",
            "애플리케이션 성능 분석 (응답시간, 에러율)",
            "HTTP 상태 코드 분석 (2xx, 4xx, 5xx)",
            "서비스 상태 및 가용성 확인",
            "로그 분석 및 패턴 감지",
            "대시보드 데이터 조회 및 분석"
        ]
    },
    "grafana_renderer_mcp_agent": {
        "description": "Grafana 대시보드 시각화 및 렌더링 전문가",
        "capabilities": [
            "대시보드 이미지, 차트 캡처, 시각화",
            "대시보드 목록 조회 및 정보 제공",
            "대시보드 스크린샷 및 리포트 생성",
            "패널별 개별 이미지 렌더링"
        ]
    }
}

def generate_supervisor_prompt(agent_configs: dict) -> str:
    """Agent 설정 정보를 기반으로 Supervisor 프롬프트를 자동 생성합니다."""
    
    agent_descriptions = []
    for agent_name, config in agent_configs.items():
        capabilities = "\n  * ".join(config["capabilities"])
        agent_desc = f"{agent_name}: {config['description']}\n  * {capabilities}"
        agent_descriptions.append(agent_desc)
    
    return f"""
너는 Grafana 모니터링 시스템의 Supervisor Agent입니다.
사용자의 요청을 분석하고 적절한 전문 에이전트에게 작업을 배분하는 역할을 담당합니다.

사용 가능한 전문 에이전트들:

{chr(10).join(agent_descriptions)}

대시보드 관련 요청이 오면 반드시 알맞는 agent에게 위임하여 처리하세요.
다른 agent에게 명령을 전달한 경우, 반드시 사용자에게는 agent가 반환한 결과를 제공해야 합니다. 
반드시, "...에게 전달하여 분석하도록 하겠습니다. 분석 결과를 받는 대로 즉시 알려드리겠습니다." 이런 응답은 하지 마세요.
분석 결과를 반드시 반환해야 합니다.

사용자의 요청을 신중히 분석하고, 가장 적절한 에이전트를 선택하세요.
"""

# 자동 생성된 Supervisor 프롬프트
SUPERVISOR_PROMPT = generate_supervisor_prompt(AGENT_CONFIGS)

# Supervisor 그래프
logger.info("Creating supervisor graph...")

async def create_agents():
    """모든 에이전트를 비동기적으로 생성합니다."""
    try:
        grafana_agent = await make_grafana_agent(llm)
        grafana_renderer_agent = await make_grafana_renderer_agent(llm)
        return [grafana_agent, grafana_renderer_agent]
    except Exception as e:
        logger.error(f"Error creating agents: {e}")
        raise

async def create_supervisor_graph():
    """Supervisor 그래프를 비동기적으로 생성합니다."""
    try:
        agents = await create_agents()
        
        # create_supervisor는 StateGraph를 반환
        supervisor_graph_builder = create_supervisor(
            agents=agents,
            model=llm,
            prompt=SUPERVISOR_PROMPT,
            output_mode='full_history'
        )
        logger.info("Supervisor graph created successfully")
        
        # StateGraph를 컴파일
        compiled_graph = supervisor_graph_builder.compile()
        return compiled_graph
        
    except Exception as e:
        logger.error(f"Error creating supervisor graph: {e}")
        raise

# 전역 변수로 supervisor_graph 저장
_supervisor_graph = None

async def get_supervisor_graph():
    """supervisor_graph를 lazy loading으로 가져오기"""
    global _supervisor_graph
    if _supervisor_graph is None:
        _supervisor_graph = await create_supervisor_graph()
    return _supervisor_graph

# LangGraph 표준 패턴: 직접 그래프 반환
async def get_graph():
    """LangGraph 표준 패턴: 컴파일된 그래프를 직접 반환"""
    return await get_supervisor_graph()

# 이전 코드와의 호환성을 위한 함수들
def create_supervisor_node():
    """이전 코드와의 호환성을 위한 함수 - 더 이상 사용하지 않음"""
    logger.warning("create_supervisor_node() is deprecated. Use get_graph() instead.")
    return None
