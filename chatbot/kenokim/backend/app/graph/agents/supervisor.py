"""
Supervisor Agent for LangGraph

ReAct 패턴 기반 Supervisor 에이전트로 handoff tools와 query transformation tool을 사용하여 
사용자 요청을 분석하고 적절한 전문 에이전트로 작업을 위임합니다.

Flow: 사용자 입력 → Supervisor (ReAct + Tools) → 전문 에이전트
"""

import logging
from typing import Annotated, Literal
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langgraph.prebuilt import create_react_agent, InjectedState
from langchain_core.tools import InjectedToolCallId

from .grafana_mcp_agent import make_grafana_agent
from .grafana_renderer_mcp_agent import make_grafana_renderer_agent
from ...core.config import settings
from ..state import GraphState
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# LLM 초기화
llm = ChatGoogleGenerativeAI(
    model=settings.gemini_model,
    google_api_key=settings.gemini_api_key,
    temperature=0
)

# Query Transformation Tool
@tool
def transform_query(
    original_query: Annotated[str, "변환할 원본 사용자 쿼리"],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> str:
    """
    사용자의 모호하거나 불명확한 쿼리를 Grafana 모니터링 작업에 적합하도록 명확하고 구체적으로 변환합니다.
    
    사용 시기:
    - 사용자 요청이 모호하거나 불분명할 때
    - 구체적인 작업 지시가 필요할 때
    - Grafana 전문 용어로 정제가 필요할 때
    """
    
    logger.info(f"Transforming query: {original_query}")
    
    # Query transformation을 위한 전용 프롬프트
    transformation_prompt = f"""다음 사용자 쿼리를 Grafana 모니터링 시스템에서 처리하기 적합하도록 명확하고 구체적으로 변환해주세요.

원본 쿼리: "{original_query}"

변환 가이드라인:
1. 모호한 표현을 구체적으로 명시
2. Grafana 관련 용어 사용 (대시보드, 패널, 메트릭 등)
3. 작업 의도를 명확하게 표현
4. 한국어로 자연스럽게 작성

변환된 쿼리만 반환하세요 (추가 설명 없이):"""

    try:
        # Query transformation 수행
        response = llm.invoke(transformation_prompt)
        transformed_query = response.content.strip()
        
        logger.info(f"Query transformed: {original_query} -> {transformed_query}")
        
        # State 업데이트를 위한 메시지 생성
        tool_message = ToolMessage(
            content=f"쿼리가 성공적으로 변환되었습니다:\n원본: {original_query}\n변환: {transformed_query}",
            name="transform_query",
            tool_call_id=tool_call_id,
        )
        
        # State에 변환된 쿼리 저장
        current_messages = state.get("messages", [])
        updated_messages = current_messages + [tool_message]
        
        # State 업데이트 (비동기적으로)
        state.update({
            "messages": updated_messages,
            "transformed_query": transformed_query
        })
        
        return transformed_query
        
    except Exception as e:
        logger.error(f"Error in query transformation: {e}")
        error_message = ToolMessage(
            content=f"쿼리 변환 중 오류가 발생했습니다: {str(e)}",
            name="transform_query", 
            tool_call_id=tool_call_id,
        )
        
        current_messages = state.get("messages", [])
        state.update({"messages": current_messages + [error_message]})
        
        return original_query  # 오류 시 원본 쿼리 반환

def create_handoff_tool(agent_name: str, description: str):
    """전문 에이전트로 작업을 위임하는 handoff tool 생성"""
    
    @tool
    def handoff_to_agent(
        task_description: Annotated[str, "해당 에이전트가 수행해야 할 작업에 대한 상세한 설명"],
        state: Annotated[dict, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        """지정된 전문 에이전트로 작업을 위임합니다."""
        
        logger.info(f"Handing off to {agent_name}: {task_description}")
        
        # Tool 실행 결과 메시지 생성
        tool_message = ToolMessage(
            content=f"작업을 {agent_name}에게 성공적으로 위임했습니다: {task_description}",
            name=f"handoff_to_{agent_name}",
            tool_call_id=tool_call_id,
        )
        
        # 현재 메시지에 tool 결과 추가
        messages = state["messages"] + [tool_message]
        
        return Command(
            goto=agent_name,
            graph=Command.PARENT,
            update={
                "messages": messages,
                "next": agent_name,
                "task_description": task_description
            }
        )
    
    # Tool에 이름과 설명 추가
    handoff_to_agent.name = f"handoff_to_{agent_name}"
    handoff_to_agent.__doc__ = description
    return handoff_to_agent

# Handoff tools 생성
handoff_to_grafana_agent = create_handoff_tool(
    agent_name="grafana_agent",
    description="Grafana 데이터 분석, 메트릭 조회, 대시보드 목록 확인이 필요할 때 사용합니다. CPU, 메모리, 성능 분석, 대시보드 정보 조회 등의 작업에 적합합니다."
)

handoff_to_grafana_renderer = create_handoff_tool(
    agent_name="grafana_renderer_mcp_agent", 
    description="Grafana 대시보드를 시각화하고 이미지로 렌더링할 때 사용합니다. 대시보드를 보여주거나, 차트를 그리거나, 스크린샷을 생성하는 작업에 적합합니다."
)

def create_supervisor_agent():
    """ReAct 패턴 기반 Supervisor 에이전트 생성"""
    
    # Supervisor 시스템 프롬프트
    supervisor_prompt = """당신은 Grafana 모니터링 시스템의 지능형 Supervisor입니다.

주요 역할:
1. 사용자 요청 분석 및 쿼리 최적화
2. 적절한 전문 에이전트로 작업 위임
3. 직접 응답이 가능한 간단한 질문 처리

사용 가능한 도구:
1. transform_query: 모호한 사용자 쿼리를 명확하고 구체적으로 변환
2. handoff_to_grafana_agent: Grafana 데이터 분석 및 메트릭 조회 전문가
3. handoff_to_grafana_renderer: Grafana 대시보드 시각화 및 렌더링 전문가

작업 흐름 가이드라인:
1. 사용자 요청이 모호하거나 불분명하면 먼저 transform_query 도구를 사용하여 쿼리를 명확하게 변환
2. 변환된 쿼리(또는 이미 명확한 쿼리)를 바탕으로 적절한 전문가에게 작업 위임:
   - 데이터 분석, 성능 확인, 대시보드 목록 조회 → handoff_to_grafana_agent
   - 대시보드 시각화, 이미지 생성, 렌더링 → handoff_to_grafana_renderer
3. 일반적인 인사나 간단한 질문은 직접 응답

중요 사항:
- 각 에이전트에게 작업을 위임할 때는 반드시 구체적이고 명확한 작업 설명을 제공
- 사용자의 원래 요청과 컨텍스트를 모두 포함하여 에이전트가 완전히 이해할 수 있도록 함
- 쿼리 변환이 필요한지 신중하게 판단하여 불필요한 변환은 피함"""

    # ReAct 에이전트 생성 (모든 tools 포함)
    supervisor_agent = create_react_agent(
        model=llm,
        tools=[transform_query, handoff_to_grafana_agent, handoff_to_grafana_renderer],
        state_schema=GraphState,
        prompt=supervisor_prompt
    )
    
    return supervisor_agent

def router(state: GraphState) -> Literal["grafana_agent", "grafana_renderer_mcp_agent", "END"]:
    """조건부 엣지 라우터 - Command 기반 라우팅"""
    next_node = state.get("next", "END")
    logger.info(f"Router directing to: {next_node}")
    return next_node

async def create_supervisor_graph():
    """ReAct 기반 Supervisor 그래프 생성"""
    try:
        logger.info("Creating ReAct-based supervisor graph with query transformation")
        
        # 전문 에이전트 생성
        grafana_agent = await make_grafana_agent(llm)
        grafana_renderer_agent = await make_grafana_renderer_agent(llm)
        
        # Supervisor ReAct 에이전트 생성
        supervisor_agent = create_supervisor_agent()
        
        # StateGraph 생성
        workflow = StateGraph(GraphState)
        
        # 노드 추가
        workflow.add_node("supervisor", supervisor_agent)
        workflow.add_node("grafana_agent", grafana_agent)
        workflow.add_node("grafana_renderer_mcp_agent", grafana_renderer_agent)
        
        # 엣지 추가
        workflow.add_edge(START, "supervisor")
        
        # 조건부 엣지 - Command 기반 라우팅
        workflow.add_conditional_edges(
            "supervisor",
            router,
            {
                "grafana_agent": "grafana_agent",
                "grafana_renderer_mcp_agent": "grafana_renderer_mcp_agent", 
                "END": END
            }
        )
        
        # 종료 엣지
        workflow.add_edge("grafana_agent", END)
        workflow.add_edge("grafana_renderer_mcp_agent", END)
        
        compiled_graph = workflow.compile()
        logger.info("ReAct-based supervisor graph with query transformation created successfully")
        return compiled_graph
        
    except Exception as e:
        logger.error(f"Error creating supervisor graph: {e}")
        raise

# 싱글톤 패턴으로 그래프 관리
_supervisor_graph = None

async def get_supervisor_graph():
    """supervisor_graph를 lazy loading으로 가져오기"""
    global _supervisor_graph
    
    if _supervisor_graph is None:
        logger.info("Initializing ReAct-based supervisor graph with query transformation")
        _supervisor_graph = await create_supervisor_graph()
    else:
        logger.debug("Returning cached supervisor graph")
    
    return _supervisor_graph 