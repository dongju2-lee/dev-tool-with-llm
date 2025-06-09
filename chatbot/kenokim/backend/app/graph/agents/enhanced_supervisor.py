"""
고급 Supervisor: Agent의 메타데이터를 활용한 동적 라우팅
"""

import logging
from langgraph_supervisor import create_supervisor
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph_supervisor.handoff import create_handoff_tool

from .grafana_mcp_agent import make_grafana_agent
from .grafana_renderer_mcp_agent import make_grafana_renderer_agent
from ...core.config import settings
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# init LLM
llm = ChatGoogleGenerativeAI(
    model=settings.gemini_model,
    google_api_key=settings.gemini_api_key,
    temperature=0
)

# Agent 메타데이터 - 실제 Agent 생성과 연동
AGENT_METADATA = {
    "grafana_agent": {
        "factory": make_grafana_agent,
        "description": "Grafana 데이터 분석, 메트릭 조회, 모니터링 정보 제공 전문가",
        "keywords": ["분석", "메트릭", "성능", "상태", "확인", "조회", "로그"],
        "use_cases": [
            "CPU, 메모리, 디스크 사용량 분석",
            "애플리케이션 성능 분석",
            "서비스 상태 모니터링",
            "로그 패턴 분석"
        ]
    },
    "grafana_renderer_mcp_agent": {
        "factory": make_grafana_renderer_agent,
        "description": "Grafana 대시보드 시각화 및 렌더링 전문가",
        "keywords": ["렌더링", "렌더", "보여줘", "시각화", "차트", "대시보드", "스크린샷", "이미지", "목록", "그려줘", "그림"],
        "use_cases": [
            "대시보드 렌더링 및 이미지 생성",
            "대시보드 목록 조회",
            "차트 및 그래프 캡처", 
            "대시보드 스크린샷 생성",
            "시각화 리포트 생성"
        ]
    }
}

def create_enhanced_handoff_tools(agent_metadata: dict) -> list:
    """Agent 메타데이터를 기반으로 더 상세한 handoff tools를 생성합니다."""
    tools = []
    
    for agent_name, metadata in agent_metadata.items():
        # 더 상세한 description으로 handoff tool 생성
        detailed_description = f"""
{metadata['description']}

주요 사용 사례:
{chr(10).join([f'- {use_case}' for use_case in metadata['use_cases']])}

키워드: {', '.join(metadata['keywords'])}
"""
        
        tool = create_handoff_tool(
            agent_name=agent_name,
            description=detailed_description.strip()
        )
        tools.append(tool)
    
    return tools

def generate_dynamic_supervisor_prompt(agent_metadata: dict) -> str:
    """Agent 메타데이터를 기반으로 동적 Supervisor 프롬프트를 생성합니다."""
    
    agent_descriptions = []
    for agent_name, metadata in agent_metadata.items():
        use_cases = "\n    - ".join(metadata["use_cases"])
        keywords = ", ".join(metadata["keywords"])
        
        agent_desc = f"""
{agent_name}: {metadata['description']}
    주요 기능:
    - {use_cases}
    키워드: {keywords}"""
        
        agent_descriptions.append(agent_desc)
    
    return f"""
너는 Grafana 모니터링 시스템의 지능형 Supervisor Agent입니다.
사용자의 요청을 분석하여 가장 적절한 전문 에이전트를 선택합니다.

사용 가능한 전문 에이전트들:
{chr(10).join(agent_descriptions)}

선택 가이드라인:
1. **대시보드 렌더링 요청**: "렌더링", "렌더", "보여줘", "그려줘", "대시보드" + 이름이 포함된 경우 → grafana_renderer_mcp_agent 사용
2. **데이터 분석 요청**: "분석", "확인", "상태", "성능" 등이 포함된 경우 → grafana_agent 사용  
3. **목록 조회**: "목록", "리스트" 등이 포함된 경우 → grafana_renderer_mcp_agent 사용
4. **특정 대시보드 언급**: Node Exporter, Kubernetes 등 구체적 대시보드 이름이 언급되면 → grafana_renderer_mcp_agent 사용
5. 애매한 경우 grafana_renderer_mcp_agent를 기본으로 사용하세요

**중요**: 사용자가 대시보드 렌더링을 요청하면 반드시 해당 에이전트를 호출하여 실제 이미지를 생성해야 합니다.
"""

async def create_enhanced_agents():
    """메타데이터를 기반으로 에이전트들을 생성합니다."""
    agents = []
    
    for agent_name, metadata in AGENT_METADATA.items():
        try:
            agent = await metadata["factory"](llm)
            agents.append(agent)
            logger.info(f"Created agent: {agent_name}")
        except Exception as e:
            logger.error(f"Failed to create agent {agent_name}: {e}")
            raise
    
    return agents

async def create_enhanced_supervisor_graph():
    """향상된 Supervisor 그래프를 생성합니다."""
    try:
        # 1. 에이전트들 생성
        agents = await create_enhanced_agents()
        
        # 2. 커스텀 handoff tools 생성 (선택사항)
        # handoff_tools = create_enhanced_handoff_tools(AGENT_METADATA)
        
        # 3. 동적 프롬프트 생성
        dynamic_prompt = generate_dynamic_supervisor_prompt(AGENT_METADATA)
        
        # 4. Supervisor 그래프 생성
        supervisor_graph_builder = create_supervisor(
            agents=agents,
            model=llm,
            prompt=dynamic_prompt,
            # tools=handoff_tools,  # 커스텀 tools 사용 시
            output_mode='full_history'
        )
        
        logger.info("Enhanced supervisor graph created successfully")
        return supervisor_graph_builder.compile()
        
    except Exception as e:
        logger.error(f"Error creating enhanced supervisor graph: {e}")
        raise

# 전역 변수로 supervisor_graph 저장
_enhanced_supervisor_graph = None

async def get_enhanced_supervisor_graph():
    """향상된 supervisor_graph를 lazy loading으로 가져오기"""
    global _enhanced_supervisor_graph
    if _enhanced_supervisor_graph is None:
        _enhanced_supervisor_graph = await create_enhanced_supervisor_graph()
    return _enhanced_supervisor_graph 