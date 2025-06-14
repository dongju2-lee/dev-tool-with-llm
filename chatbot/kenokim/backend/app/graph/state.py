"""
LangGraph State Definitions

LangGraph 에이전트 시스템의 상태 정의 모듈입니다.
TypedDict를 사용하여 타입 안전성을 보장합니다.
"""

from typing import Annotated, List, Optional, Dict, Any, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


# ========================================
# 1. UNIFIED GRAPH STATE
# ========================================

class GraphState(TypedDict):
    """
    전체 그래프에서 사용되는 통합 상태
    
    Flow: 사용자 입력 → Supervisor (ReAct + Handoff Tools) → 전문 에이전트 실행
    
    Fields:
        messages: 대화 메시지 목록
        remaining_steps: ReAct 에이전트의 남은 실행 단계 수
        next: 다음 실행할 노드명 (라우팅용)
        transformed_query: 변환된 사용자 쿼리
        task_description: 에이전트에게 전달할 작업 설명
        grafana_data: Grafana 에이전트 결과 데이터
        render_data: 렌더러 에이전트 결과 데이터
        session_context: 세션 컨텍스트 정보
    """
    # 핵심 메시지 관리
    messages: Annotated[List[BaseMessage], add_messages]
    
    # ReAct 에이전트 제어
    remaining_steps: int
    
    # 라우팅 및 플로우 제어
    next: str
    transformed_query: str
    task_description: Optional[str]
    
    # 에이전트별 전용 데이터
    grafana_data: Optional[Dict[str, Any]]
    render_data: Optional[Dict[str, Any]]
    
    # 세션 및 컨텍스트 관리
    session_context: Optional[Dict[str, Any]]


# ========================================
# 2. STATE UTILITY FUNCTIONS
# ========================================

def create_initial_graph_state(user_message: BaseMessage) -> GraphState:
    """GraphState 초기 상태 생성"""
    return GraphState(
        messages=[user_message],
        remaining_steps=10,  # ReAct 에이전트의 기본 최대 실행 단계
        next="",
        transformed_query="",
        task_description=None,
        grafana_data=None,
        render_data=None,
        session_context=None
    )


def update_grafana_data(state: GraphState, data: Dict[str, Any]) -> Dict[str, Any]:
    """Grafana 에이전트 데이터 업데이트"""
    return {"grafana_data": data}


def update_render_data(state: GraphState, data: Dict[str, Any]) -> Dict[str, Any]:
    """렌더러 에이전트 데이터 업데이트"""
    return {"render_data": data}


def update_session_context(state: GraphState, context: Dict[str, Any]) -> Dict[str, Any]:
    """세션 컨텍스트 업데이트"""
    return {"session_context": context} 