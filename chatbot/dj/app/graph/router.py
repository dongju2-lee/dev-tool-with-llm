"""
라우터 그래프 모듈

이 모듈은 사용자 메시지를 받아 적절한 MCP 서버와 도구를 선택하는 라우터 그래프를 구현합니다.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Tuple, TypedDict, cast

import streamlit as st
from pydantic import BaseModel, Field

# 로깅 설정
logger = logging.getLogger(__name__)

# MCP 래퍼 임포트
from mcp.wrapper import MCPTools

try:
    # LangGraph 라이브러리 임포트 시도
    from langgraph.graph import StateGraph
    from langgraph.prebuilt import ToolNode, create_react_agent
    HAS_LANGGRAPH = True
except ImportError:
    logger.warning("LangGraph 라이브러리를 찾을 수 없습니다. 가상 구현을 사용합니다.")
    HAS_LANGGRAPH = False


class RouterState(TypedDict):
    """라우터 그래프의 상태를 나타내는 데이터 구조"""
    messages: List[Dict[str, Any]]  # 메시지 목록
    selected_server: Optional[str]  # 선택된 MCP 서버
    selected_tool: Optional[str]  # 선택된 도구
    tool_args: Optional[Dict[str, Any]]  # 도구 인수
    result: Optional[Any]  # 도구 실행 결과
    error: Optional[str]  # 오류 메시지


class RouterRequest(BaseModel):
    """라우터 그래프에 대한 요청 모델"""
    message: str = Field(..., description="사용자 메시지")
    session_id: Optional[str] = Field(None, description="세션 ID")


class RouterResponse(BaseModel):
    """라우터 그래프의 응답 모델"""
    response: str = Field(..., description="응답 메시지")
    session_id: str = Field(..., description="세션 ID")
    result: Optional[Any] = Field(None, description="도구 실행 결과")
    error: Optional[str] = Field(None, description="오류 메시지")


class RouterGraph:
    """라우터 그래프 클래스"""
    
    def __init__(self, mcp_tools: MCPTools):
        """
        라우터 그래프 초기화
        
        Args:
            mcp_tools: MCP 도구 관리 객체
        """
        self.mcp_tools = mcp_tools
        self.graph = self._build_graph() if HAS_LANGGRAPH else None
    
    def _build_graph(self):
        """라우터 그래프 구축"""
        if not HAS_LANGGRAPH:
            return None
        
        # 그래프 노드 정의
        def route_request(state: RouterState) -> str:
            """
            사용자 메시지를 분석하고 적절한 MCP 서버와 도구를 선택합니다.
            
            Args:
                state: 라우터 상태
                
            Returns:
                str: 다음 노드 이름
            """
            # 마지막 사용자 메시지 가져오기
            user_message = state["messages"][-1]["content"]
            
            # 이 부분에서 실제 라우팅 로직 구현
            # 간단한 예제: 메시지에 특정 키워드가 있으면 특정 서버/도구 선택
            
            for server_name, server_config in self.mcp_tools.config.items():
                # 여기서는 간단한 키워드 매칭을 사용
                # 실제 구현에서는 임베딩 기반 검색이나 LLM 기반 라우팅 사용 가능
                if server_name.lower() in user_message.lower():
                    state["selected_server"] = server_name
                    # 첫 번째 사용 가능한 도구 선택
                    state["selected_tool"] = f"{server_name}_tool"  # 임시 이름
                    return "call_tool"
            
            # 서버를 찾지 못한 경우 오류 처리
            state["error"] = "적절한 도구를 찾을 수 없습니다."
            return "error"
        
        async def call_tool(state: RouterState) -> str:
            """
            선택된 도구를 호출합니다.
            
            Args:
                state: 라우터 상태
                
            Returns:
                str: 다음 노드 이름
            """
            server_name = state.get("selected_server")
            tool_name = state.get("selected_tool")
            
            if not server_name or not tool_name:
                state["error"] = "서버 또는 도구가 선택되지 않았습니다."
                return "error"
            
            # 실제 도구 이름 추출 (서버 이름 접두사 제거)
            actual_tool_name = tool_name.replace(f"{server_name}_", "")
            
            # 마지막 사용자 메시지에서 도구 인수 추출
            user_message = state["messages"][-1]["content"]
            # 여기서는 간단히 메시지 전체를 쿼리로 사용
            tool_args = {"query": user_message}
            
            try:
                # 도구 실행
                result = await self.mcp_tools.run_tool(server_name, actual_tool_name, tool_args)
                state["result"] = result
                return "format_response"
            except Exception as e:
                state["error"] = f"도구 실행 중 오류 발생: {str(e)}"
                return "error"
        
        def format_response(state: RouterState) -> str:
            """
            도구 실행 결과를 포맷하여 응답을 생성합니다.
            
            Args:
                state: 라우터 상태
                
            Returns:
                str: 다음 노드 이름
            """
            result = state.get("result", {})
            server_name = state.get("selected_server", "unknown")
            tool_name = state.get("selected_tool", "unknown")
            
            # 결과를 텍스트로 변환
            if isinstance(result, str):
                response_text = result
            else:
                try:
                    response_text = json.dumps(result, ensure_ascii=False, indent=2)
                except Exception:
                    response_text = str(result)
            
            # 응답 메시지 생성
            response = {
                "role": "assistant",
                "content": f"서버 '{server_name}'의 도구 '{tool_name}'을(를) 실행한 결과:\n\n{response_text}"
            }
            
            # 메시지 목록에 응답 추가
            state["messages"].append(response)
            return "end"
        
        def handle_error(state: RouterState) -> str:
            """
            오류를 처리하고 오류 메시지를 생성합니다.
            
            Args:
                state: 라우터 상태
                
            Returns:
                str: 다음 노드 이름
            """
            error_message = state.get("error", "알 수 없는 오류가 발생했습니다.")
            
            # 오류 응답 생성
            response = {
                "role": "assistant",
                "content": f"오류: {error_message}"
            }
            
            # 메시지 목록에 오류 응답 추가
            state["messages"].append(response)
            return "end"
        
        # 그래프 구성
        workflow = StateGraph(RouterState)
        
        # 노드 추가
        workflow.add_node("route_request", route_request)
        workflow.add_node("call_tool", call_tool)
        workflow.add_node("format_response", format_response)
        workflow.add_node("error", handle_error)
        
        # 엣지 추가
        workflow.set_entry_point("route_request")
        workflow.add_edge("route_request", "call_tool")
        workflow.add_edge("call_tool", "format_response")
        workflow.add_edge("route_request", "error")
        workflow.add_edge("call_tool", "error")
        
        # 종료 노드 설정
        workflow.add_edge("format_response", "end")
        workflow.add_edge("error", "end")
        
        # 그래프 컴파일
        return workflow.compile()
    
    async def process(self, request: RouterRequest) -> RouterResponse:
        """
        요청을 처리하고 응답을 반환합니다.
        
        Args:
            request: 라우터 요청
            
        Returns:
            RouterResponse: 라우터 응답
        """
        if not HAS_LANGGRAPH:
            # LangGraph 없이 간단한 구현
            return RouterResponse(
                response=f"메시지: {request.message}\n(가상 응답 - LangGraph 필요)",
                session_id=request.session_id or "virtual_session"
            )
        
        # 초기 상태 생성
        state = RouterState(
            messages=[{"role": "user", "content": request.message}],
            selected_server=None,
            selected_tool=None,
            tool_args=None,
            result=None,
            error=None
        )
        
        # 그래프 실행
        try:
            result = await self.graph.ainvoke(state)
            
            # 응답 생성
            messages = result["messages"]
            assistant_messages = [m for m in messages if m["role"] == "assistant"]
            
            if assistant_messages:
                # 마지막 어시스턴트 메시지 사용
                response_text = assistant_messages[-1]["content"]
            else:
                response_text = "응답을 생성할 수 없습니다."
            
            return RouterResponse(
                response=response_text,
                session_id=request.session_id or "session_id",
                result=result.get("result"),
                error=result.get("error")
            )
        except Exception as e:
            logger.error(f"그래프 실행 중 오류 발생: {e}")
            return RouterResponse(
                response=f"오류: {str(e)}",
                session_id=request.session_id or "error_session",
                error=str(e)
            ) 