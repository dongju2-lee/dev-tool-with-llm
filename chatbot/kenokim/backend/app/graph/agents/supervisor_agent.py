"""
Supervisor Agent for LangGraph

ReAct 패턴 기반 Supervisor 에이전트로 handoff tools와 query transformation tool을 사용하여 
사용자 요청을 분석하고 적절한 전문 에이전트로 작업을 위임합니다.

Flow: 사용자 입력 → Supervisor (ReAct + Tools) → 전문 에이전트
"""

import logging
from typing import Annotated, Literal, List
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langgraph.prebuilt import create_react_agent, InjectedState
from langchain_core.tools import InjectedToolCallId

from .grafana_mcp_agent import make_grafana_agent
from .grafana_renderer_mcp_agent import make_grafana_renderer_agent

from ..state import GraphState
from ...prompts.prompts import (
    SUPERVISOR_AGENT_PROMPT, 
    QUERY_TRANSFORMATION_PROMPT_TEMPLATE,
    HANDOFF_GRAFANA_AGENT_DESCRIPTION,
    HANDOFF_GRAFANA_RENDERER_DESCRIPTION
)
from ...core.config import settings
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# LLM 초기화
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
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
    transformation_prompt = QUERY_TRANSFORMATION_PROMPT_TEMPLATE.format(
        original_query=original_query
    )

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
    description=HANDOFF_GRAFANA_AGENT_DESCRIPTION
)

handoff_to_grafana_renderer = create_handoff_tool(
    agent_name="grafana_renderer_mcp_agent", 
    description=HANDOFF_GRAFANA_RENDERER_DESCRIPTION
)

def create_supervisor_agent():
    """ReAct 패턴 기반 Supervisor 에이전트 생성"""
    
    # ReAct 에이전트 생성 (모든 tools 포함)
    supervisor_agent = create_react_agent(
        model=llm,
        tools=[transform_query, handoff_to_grafana_agent, handoff_to_grafana_renderer],
        state_schema=GraphState,
        prompt=SUPERVISOR_AGENT_PROMPT
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
        grafana_agent = await make_grafana_agent()
        grafana_renderer_agent = await make_grafana_renderer_agent()
        
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


# ============================================================================
# 대화 히스토리 관리 함수들
# ============================================================================

# 메모리에 저장된 대화 히스토리 (간단한 in-memory 저장소)
_conversation_store = {}

def get_conversation_history(thread_id: str) -> List:
    """특정 thread의 대화 히스토리를 가져옵니다."""
    return _conversation_store.get(thread_id, [])

def clear_conversation_history(thread_id: str) -> bool:
    """특정 thread의 대화 히스토리를 삭제합니다."""
    if thread_id in _conversation_store:
        del _conversation_store[thread_id]
        return True
    return False

def list_active_conversations() -> List[str]:
    """활성 대화 목록을 반환합니다."""
    return list(_conversation_store.keys()) 