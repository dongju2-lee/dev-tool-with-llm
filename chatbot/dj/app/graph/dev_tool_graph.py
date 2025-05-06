"""
개발 도구 그래프 모듈

이 모듈은 개발 도구 챗봇을 위한 LangGraph 워크플로우를 정의합니다.
다양한 에이전트 노드들이 서로 상호작용하는 방식을 구성합니다.
"""

import os
from datetime import datetime
from typing import Dict, Any, List, Union, Tuple, Annotated, Literal
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
# from langgraph.prebuilt import ToolExecutor
from langgraph.graph import StateGraph, END
from langgraph.types import Command

# 에이전트 노드들 임포트
from agent.supervisor_agent import supervisor_node
from agent.orchestrator_agent import orchestrator_node
from agent.planning_agent import planning_node
from agent.validation_agent import validation_node
from agent.respond_agent import respond_node
from agent.weather_agent import weather_agent_node
from agent.gemini_search_agent import gemini_search_node
from agent.mcp_agent import mcp_agent_node

# 상태 클래스 임포트
from state.base_state import MessagesState, TaskStatus, TaskStep, ValidationResult, AgentRequest, AgentResponse

from utils.logger_config import setup_logger
from config import *  # 상수 및 구성 값 임포트

# 환경 변수 로드
load_dotenv()

# 로거 설정
logger = setup_logger("dev_tool_graph", level=LOG_LEVEL)


class DevToolGraph:
    """
    개발 도구 LangGraph 클래스
    
    이 클래스는 다양한 에이전트 노드를 연결하는 그래프를 생성하고 관리합니다.
    """
    
    def __init__(self):
        """
        DevToolGraph 인스턴스를 초기화합니다.
        """
        self.graph = None
        self.graph_state = None
        
    async def build(self) -> None:
        """
        그래프를 빌드하고 초기화합니다.
        """
        logger.info("개발 도구 그래프 빌드 시작")
        
        try:
            # 그래프 생성
            self.graph = await build_graph()
            logger.info("개발 도구 그래프 성공적으로 빌드됨")
            
            # 상태 초기화
            self.reset_state()
            
        except Exception as e:
            logger.error(f"그래프 빌드 중 오류 발생: {str(e)}")
            raise
    
    def reset_state(self) -> None:
        """
        그래프 상태를 재설정합니다.
        """
        logger.info("그래프 상태 재설정")
        self.graph_state = {
            "messages": [],
            "original_query": "",
            "parsed_intent": None,
            "plan": None,
            "current_step": None,
            "results": {},
            "validation_result": None,
            "final_response": None,
            "conversation_context": {},
            "status": TaskStatus.planning,
            "next": None
        }
    
    async def invoke(self, message: str) -> List[BaseMessage]:
        """
        사용자 메시지로 그래프를 호출합니다.
        
        Args:
            message: 사용자 입력 메시지
            
        Returns:
            응답 메시지 목록
        """
        if not self.graph:
            await self.build()
        
        # 메시지를 상태에 추가
        human_message = HumanMessage(content=message)
        
        if "messages" not in self.graph_state:
            self.graph_state = {
                "messages": [human_message],
                "original_query": message,
                "parsed_intent": None,
                "plan": None,
                "current_step": None,
                "results": {},
                "validation_result": None,
                "final_response": None,
                "conversation_context": {},
                "status": TaskStatus.planning,
                "next": None
            }
        else:
            self.graph_state["messages"].append(human_message)
            self.graph_state["original_query"] = message
            self.graph_state["status"] = TaskStatus.planning
        
        # 그래프 실행
        logger.info(f"그래프 호출 시작. 메시지: '{message[:50]}...'")
        
        try:
            # 그래프 실행
            result = await self.graph.ainvoke(self.graph_state)
            
            # 응답 메시지 추출
            if "messages" in result:
                new_messages = result["messages"][len(self.graph_state.get("messages", [])):]
                
                # 상태 업데이트
                self.graph_state = result
                
                # 상태 업데이트 후 상태 정보 로깅
                logger.info(f"그래프 호출 완료. {len(new_messages)} 개의 새 메시지 받음")
                logger.info(f"현재 상태: {self.graph_state.get('status', TaskStatus.planning)}")
                
                if self.graph_state.get("final_response"):
                    logger.info("최종 응답이 생성되었습니다.")
                
                return new_messages
            else:
                logger.warning("그래프 응답에 메시지가 없음")
                return []
                
        except Exception as e:
            logger.error(f"그래프 호출 중 오류 발생: {str(e)}")
            
            # 오류 메시지 생성
            error_message = AIMessage(content=f"처리 중 오류가 발생했습니다: {str(e)}")
            return [error_message]


async def build_graph() -> StateGraph:
    """
    에이전트 노드를 연결하는 LangGraph를 구축합니다.
    
    Returns:
        구성된 StateGraph 인스턴스
    """
    logger.info("그래프 구축 시작")
    
    # 그래프 생성
    builder = StateGraph(MessagesState)
    
    # 노드 추가
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("planning", planning_node)
    builder.add_node("validation", validation_node)
    builder.add_node("respond", respond_node)
    builder.add_node("weather_agent", weather_agent_node)
    builder.add_node("gemini_search_agent", gemini_search_node)
    builder.add_node("mcp_agent", mcp_agent_node)
    
    # 엣지 정의 - 시작점은 슈퍼바이저
    builder.set_entry_point("supervisor")
    
    # 슈퍼바이저 노드 연결 (주로 orchestrator와 END로만 연결)
    builder.add_conditional_edges(
        "supervisor",
        lambda state: state.get("next", END),
        {
            "orchestrator": lambda state: state.get("next") == "orchestrator",
            END: lambda state: state.get("next") == END,
        }
    )
    
    # 오케스트레이터 노드 연결 (다양한 에이전트로 라우팅)
    builder.add_conditional_edges(
        "orchestrator",
        lambda state: state.get("next", "planning"),
        {
            "planning": lambda state: state.get("next") == "planning",
            "weather_agent": lambda state: state.get("next") == "weather_agent",
            "gemini_search_agent": lambda state: state.get("next") == "gemini_search_agent",
            "mcp_agent": lambda state: state.get("next") == "mcp_agent",
            "validation": lambda state: state.get("next") == "validation",
            "respond": lambda state: state.get("next") == "respond",
            END: lambda state: state.get("next") == END,
        }
    )
    
    # 계획 노드 연결 (항상 orchestrator로 돌아감)
    builder.add_edge("planning", "orchestrator")
    
    # 전문 에이전트들은 항상 orchestrator로 돌아감
    builder.add_edge("weather_agent", "orchestrator")
    builder.add_edge("gemini_search_agent", "orchestrator")
    builder.add_edge("mcp_agent", "orchestrator")
    
    # 검증 노드 연결 (주로 respond, 필요시 orchestrator로 돌아감)
    builder.add_conditional_edges(
        "validation",
        lambda state: state.get("next", "respond"),
        {
            "respond": lambda state: state.get("next") == "respond",
            "orchestrator": lambda state: state.get("next") == "orchestrator",
        }
    )
    
    # 응답 노드는 그래프의 종료점
    builder.add_edge("respond", END)
    
    # 그래프 컴파일
    graph = builder.compile()
    logger.info("그래프 구축 완료")
    
    return graph 