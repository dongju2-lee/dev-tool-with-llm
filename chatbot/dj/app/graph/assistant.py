"""
어시스턴트 그래프 모듈

이 모듈은 사용자 메시지를 받아 적절한 에이전트와 도구를 사용하여 응답을 생성하는 그래프를 구현합니다.
"""

import asyncio
import json
import logging
import os
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
    from langchain_google_vertexai import ChatVertexAI
    HAS_LANGGRAPH = True
except ImportError:
    logger.warning("LangGraph 라이브러리를 찾을 수 없습니다. 가상 구현을 사용합니다.")
    HAS_LANGGRAPH = False

# 라우터 그래프 임포트
from graph.router import RouterRequest, RouterResponse, RouterGraph


class AssistantState(TypedDict):
    """어시스턴트 그래프의 상태를 나타내는 데이터 구조"""
    messages: List[Dict[str, Any]]  # 메시지 목록
    intermediate_steps: List[Tuple[Any, Any]]  # 중간 단계(도구 호출 및 결과) 목록
    session_id: Optional[str]  # 세션 ID
    result: Optional[Any]  # 최종 결과
    error: Optional[str]  # 오류 메시지


class AssistantRequest(BaseModel):
    """어시스턴트 그래프에 대한 요청 모델"""
    message: str = Field(..., description="사용자 메시지")
    session_id: Optional[str] = Field(None, description="세션 ID")


class AssistantResponse(BaseModel):
    """어시스턴트 그래프의 응답 모델"""
    response: str = Field(..., description="응답 메시지")
    session_id: str = Field(..., description="세션 ID")
    error: Optional[str] = Field(None, description="오류 메시지")


class AssistantGraph:
    """어시스턴트 그래프 클래스"""
    
    def __init__(self, mcp_tools: MCPTools):
        """
        어시스턴트 그래프 초기화
        
        Args:
            mcp_tools: MCP 도구 관리 객체
        """
        self.mcp_tools = mcp_tools
        self.router_graph = RouterGraph(mcp_tools)
        self.graph = self._build_graph() if HAS_LANGGRAPH else None
    
    def _build_graph(self):
        """어시스턴트 그래프 구축"""
        if not HAS_LANGGRAPH:
            return None
        
        # LLM 초기화
        llm = None
        try:
            # 환경 변수에서 설정 가져오기
            model_name = os.environ.get("LLM_MODEL_NAME", "gemini-1.5-pro-001")
            project = os.environ.get("GOOGLE_CLOUD_PROJECT")
            region = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")
            
            # 로그에 설정 정보 출력
            logger.info(f"Vertex AI 설정 - 모델: {model_name}, 프로젝트: {project}, 리전: {region}")
            
            # VertexAI LLM 초기화
            llm = ChatVertexAI(
                model=model_name,
                temperature=0.1,
                max_output_tokens=8000,
                project=project,
                location=region
            )
            logger.info(f"ChatVertexAI 모델 '{model_name}'이(가) 성공적으로 초기화되었습니다.")
        except Exception as e:
            logger.error(f"LLM 초기화 오류: {e}", exc_info=True)
        
        # 그래프 노드 정의
        async def analyze_request(state: AssistantState) -> Dict[str, Any]:
            """
            사용자 메시지를 분석하고 라우팅 결정합니다.
            
            Args:
                state: 어시스턴트 상태
                
            Returns:
                Dict[str, Any]: 업데이트된 상태 또는 다음 노드 결정
            """
            # 메시지가 없는 경우 오류 처리
            if not state["messages"]:
                state["error"] = "메시지가 비어 있습니다."
                return {"next": "handle_error"}
            
            # 마지막 사용자 메시지 가져오기
            for msg in reversed(state["messages"]):
                if msg["role"] == "user":
                    user_message = msg["content"]
                    break
            else:
                state["error"] = "사용자 메시지를 찾을 수 없습니다."
                return {"next": "handle_error"}
            
            # 도구 사용이 필요한지 판단
            # 실제 구현에서는 LLM을 사용하여 더 정교한 판단 가능
            if "도구" in user_message or "tool" in user_message.lower():
                return {"next": "call_router"}
            else:
                return {"next": "generate_response"}
        
        async def call_router(state: AssistantState) -> Dict[str, Any]:
            """
            라우터 그래프를 호출하여 적절한 도구를 선택하고 실행합니다.
            
            Args:
                state: 어시스턴트 상태
                
            Returns:
                Dict[str, Any]: 업데이트된 상태
            """
            # 마지막 사용자 메시지 가져오기
            for msg in reversed(state["messages"]):
                if msg["role"] == "user":
                    user_message = msg["content"]
                    break
            else:
                state["error"] = "사용자 메시지를 찾을 수 없습니다."
                return {"next": "handle_error"}
            
            # 라우터 요청 생성
            router_request = RouterRequest(
                message=user_message,
                session_id=state.get("session_id")
            )
            
            try:
                # 라우터 호출
                router_response = await self.router_graph.process(router_request)
                
                # 응답 처리
                if router_response.error:
                    state["error"] = router_response.error
                    return {"next": "handle_error"}
                
                # 응답 추가
                state["messages"].append({
                    "role": "assistant",
                    "content": router_response.response
                })
                
                # 세션 ID 업데이트
                state["session_id"] = router_response.session_id
                
                return {"next": "end"}
            except Exception as e:
                state["error"] = f"라우터 호출 중 오류 발생: {str(e)}"
                return {"next": "handle_error"}
        
        async def generate_response(state: AssistantState) -> Dict[str, Any]:
            """
            LLM을 사용하여 응답을 생성합니다.
            
            Args:
                state: 어시스턴트 상태
                
            Returns:
                Dict[str, Any]: 업데이트된 상태
            """
            if not llm:
                state["error"] = "LLM이 초기화되지 않았습니다."
                return {"next": "handle_error"}
            
            try:
                # LLM으로 응답 생성
                response = await llm.ainvoke(state["messages"])
                
                # 응답 추가
                state["messages"].append({
                    "role": "assistant",
                    "content": response.content
                })
                
                return {"next": "end"}
            except Exception as e:
                state["error"] = f"응답 생성 중 오류 발생: {str(e)}"
                return {"next": "handle_error"}
        
        def handle_error(state: AssistantState) -> Dict[str, Any]:
            """
            오류를 처리하고 오류 메시지를 생성합니다.
            
            Args:
                state: 어시스턴트 상태
                
            Returns:
                Dict[str, Any]: 업데이트된 상태
            """
            error_message = state.get("error", "알 수 없는 오류가 발생했습니다.")
            
            # 오류 응답 생성
            state["messages"].append({
                "role": "assistant",
                "content": f"오류: {error_message}"
            })
            
            return {"next": "end"}
        
        # 어시스턴트 그래프 구성
        workflow = StateGraph(AssistantState)
        
        # 노드 추가
        workflow.add_node("analyze_request", analyze_request)
        workflow.add_node("call_router", call_router)
        workflow.add_node("generate_response", generate_response)
        workflow.add_node("handle_error", handle_error)
        
        # 조건부 엣지 추가
        workflow.set_entry_point("analyze_request")
        
        # analyze_request에서 분기
        workflow.add_conditional_edges(
            "analyze_request",
            lambda x: x["next"],
            {
                "call_router": "call_router",
                "generate_response": "generate_response",
                "handle_error": "handle_error"
            }
        )
        
        # call_router에서 분기
        workflow.add_conditional_edges(
            "call_router",
            lambda x: x["next"],
            {
                "end": "end",
                "handle_error": "handle_error"
            }
        )
        
        # generate_response에서 분기
        workflow.add_conditional_edges(
            "generate_response",
            lambda x: x["next"],
            {
                "end": "end",
                "handle_error": "handle_error"
            }
        )
        
        # error에서 end로
        workflow.add_edge("handle_error", "end")
        
        # 그래프 컴파일
        return workflow.compile()
    
    async def process(self, request: AssistantRequest) -> AssistantResponse:
        """
        요청을 처리하고 응답을 반환합니다.
        
        Args:
            request: 어시스턴트 요청
            
        Returns:
            AssistantResponse: 어시스턴트 응답
        """
        if not HAS_LANGGRAPH:
            # LangGraph 없이 간단한 구현
            return AssistantResponse(
                response=f"메시지: {request.message}\n(가상 응답 - LangGraph 필요)",
                session_id=request.session_id or "virtual_session"
            )
        
        # 초기 상태 생성
        state = AssistantState(
            messages=[{"role": "user", "content": request.message}],
            intermediate_steps=[],
            session_id=request.session_id,
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
            
            return AssistantResponse(
                response=response_text,
                session_id=result.get("session_id") or request.session_id or "session_id",
                error=result.get("error")
            )
        except Exception as e:
            logger.error(f"그래프 실행 중 오류 발생: {e}")
            return AssistantResponse(
                response=f"오류: {str(e)}",
                session_id=request.session_id or "error_session",
                error=str(e)
            ) 