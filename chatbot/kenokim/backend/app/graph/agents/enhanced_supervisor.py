"""
고급 Supervisor: LangGraph를 사용한 직접 구현
"""

import logging
from typing import Annotated, Literal, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END

from .grafana_mcp_agent import make_grafana_agent
from .grafana_renderer_mcp_agent import make_grafana_renderer_agent
from ...core.config import settings
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# State 정의
class SupervisorState(TypedDict):
    messages: Annotated[list[BaseMessage], "The messages in the conversation"]
    next: Annotated[str, "The next agent to route to"]

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

# Supervisor 노드 함수
def supervisor_node(state: SupervisorState) -> SupervisorState:
    """Supervisor가 다음 agent를 결정합니다."""
    messages = state["messages"]
    
    # 마지막 메시지 가져오기
    last_message = messages[-1] if messages else None
    if not last_message or not hasattr(last_message, 'content'):
        return {"messages": messages, "next": "END"}
    
    content = last_message.content.lower()
    
    # 간단한 라우팅 로직
    if any(keyword in content for keyword in ["대시보드", "목록", "렌더링", "렌더", "보여줘", "시각화", "차트", "스크린샷", "이미지", "그려줘"]):
        next_agent = "grafana_renderer_mcp_agent"
    elif any(keyword in content for keyword in ["분석", "성능", "상태", "확인", "메트릭", "메모리", "cpu", "디스크", "사용량", "모니터링"]):
        next_agent = "grafana_agent"
    else:
        # 일반적인 요청은 직접 응답
        supervisor_prompt = generate_dynamic_supervisor_prompt(AGENT_METADATA)
        response = llm.invoke([
            {"role": "system", "content": supervisor_prompt},
            {"role": "user", "content": last_message.content}
        ])
        
        new_message = AIMessage(content=response.content, name="supervisor")
        return {"messages": messages + [new_message], "next": "END"}
    
    return {"messages": messages, "next": next_agent}

def router(state: SupervisorState) -> Literal["grafana_agent", "grafana_renderer_mcp_agent", "END"]:
    """다음 노드를 결정하는 라우터"""
    return state["next"]

def generate_dynamic_supervisor_prompt(agent_metadata: dict) -> str:
    """Agent 메타데이터를 기반으로 동적 Supervisor 프롬프트를 생성합니다."""
    
    return f"""
당신은 Grafana 모니터링 시스템의 Supervisor입니다. 
사용자 요청을 분석하고 적절한 전문 에이전트에게 작업을 전달한 후, 그 결과를 사용자에게 제대로 전달하세요.

**핵심 책임**:
1. 요청 분석 및 적절한 에이전트 선택
2. 전문 에이전트 결과를 사용자에게 완전히 전달
3. 구체적이고 유용한 응답 보장

**전문 에이전트 선택 기준**:

🎨 **grafana_renderer_mcp_agent** 사용 시:
- "대시보드", "목록", "렌더링", "렌더", "보여줘", "시각화"  
- 구체적 대시보드 이름 (Node Exporter, Prometheus Stats 등)
- "이미지", "차트", "스크린샷" 관련

📊 **grafana_agent** 사용 시:
- "분석", "성능", "상태", "확인", "메트릭"
- "메모리", "CPU", "디스크", "사용량"
- "모니터링", "로그", "패턴" 관련

**결과 전달 원칙**:
✅ **해야 할 일**:
- 전문 에이전트의 완전한 응답을 그대로 전달
- 구체적인 데이터나 목록이 있으면 모두 포함
- 사용자가 바로 활용할 수 있는 정보 제공

❌ **하지 말아야 할 일**:
- "전달했습니다"만 응답
- "처리 완료"만 응답
- 전문 에이전트 결과 요약하거나 생략
- 추상적이거나 모호한 응답

**응답 방식**:
- **일반 인사**: 직접 친근하게 응답
- **도움 요청**: 기능 목록 간단히 안내
- **Grafana 요청**: 전문 에이전트 호출 → 완전한 결과 전달

**성공적인 응답 예시**:
사용자: "대시보드 목록 보여줘"
→ grafana_renderer_mcp_agent 호출
→ 에이전트 결과: "현재 7개 대시보드... (상세 목록)"
→ 사용자에게 그대로 전달

**실패하는 응답 예시**:
- "대시보드 목록을 전달했습니다" ❌
- "처리가 완료되었습니다" ❌
- "알겠습니다" ❌
- "요약해 드렸습니다" ❌

⚠️ **추가 규칙**:
- 만약 전문 에이전트가 빈약한 응답을 했다면, 다시 전달하여 구체적인 결과를 요청하세요
- 전문 에이전트의 응답에 실제 데이터가 없으면 "더 구체적인 정보를 요청해 주세요"라고 안내하세요
- 절대 "알겠습니다", "처리했습니다" 같은 빈약한 응답을 그대로 전달하지 마세요

다른 agent에게 명령을 전달한 경우, 반드시 사용자에게는 agent가 반환한 결과를 제공해야 합니다. 
반드시, "...에게 전달하여 분석하도록 하겠습니다. 분석 결과를 받는 대로 즉시 알려드리겠습니다." 이런 응답은 하지 마세요.
agent 의 결과를 반드시 반환해야 합니다.

전문 에이전트가 제공한 구체적이고 상세한 결과를 반드시 사용자에게 완전히 전달하세요.
과거의 chat history 에 필요한 정보가 있는 경우 반드시 포함하여 사용자에게 전달하세요.
"""



async def create_enhanced_supervisor_graph():
    """향상된 Supervisor 그래프를 생성합니다."""
    try:
        # 1. 에이전트들 생성
        grafana_agent = await make_grafana_agent(llm)
        grafana_renderer_agent = await make_grafana_renderer_agent(llm)
        
        # 2. StateGraph 생성
        workflow = StateGraph(SupervisorState)
        
        # 3. 노드 추가
        workflow.add_node("supervisor", supervisor_node)
        workflow.add_node("grafana_agent", grafana_agent)
        workflow.add_node("grafana_renderer_mcp_agent", grafana_renderer_agent)
        
        # 4. 엣지 추가
        workflow.add_edge(START, "supervisor")
        workflow.add_conditional_edges(
            "supervisor",
            router,
            {
                "grafana_agent": "grafana_agent",
                "grafana_renderer_mcp_agent": "grafana_renderer_mcp_agent",
                "END": END
            }
        )
        workflow.add_edge("grafana_agent", END)
        workflow.add_edge("grafana_renderer_mcp_agent", END)
        
        logger.info("Enhanced supervisor graph created successfully")
        return workflow.compile()
        
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