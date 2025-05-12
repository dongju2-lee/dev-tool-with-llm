"""
슈퍼바이저 에이전트 모듈

사용자 요청을 분석하여 적절한 에이전트로 라우팅합니다.
"""

import os
import json
from typing import Literal, List, Dict, Any, Optional
from datetime import datetime

from langchain_core.messages import SystemMessage, BaseMessage, HumanMessage, AIMessage
from langgraph.graph import END
from langgraph.types import Command
from langchain_google_vertexai import ChatVertexAI
from dotenv import load_dotenv
import requests

from state.base_state import MessagesState, TaskStatus, AgentRequest, AgentResponse
from utils.logger_config import setup_logger
from config import *  # Import all constants and configuration values

# 환경 변수 로드
load_dotenv()

# 로거 설정
logger = setup_logger("supervisor_agent", level=LOG_LEVEL)

# 슈퍼바이저에서 관리할 에이전트 멤버 목록 (주로 orchestrator, 필요시 FINISH만 사용)
members = ["orchestrator"]
# 라우팅 옵션 (멤버 + 종료)
options = members + ["FINISH"]

logger.info(f"슈퍼바이저 에이전트 멤버 목록: {members}")
logger.info(f"라우팅 옵션: {options}")

# 슈퍼바이저 시스템 프롬프트
SYSTEM_PROMPT = """당신은 개발 도구 시스템의 슈퍼바이저 에이전트입니다. 사용자의 요청을 분석하여 다음 단계를 결정합니다.

중요: 모든 실질적인 사용자 요청은 "orchestrator"로 라우팅해야 합니다. orchestrator는 작업 계획 수립 및 적절한 전문 에이전트 호출을 담당합니다.

당신의 역할은 다음 두 가지 결정 중 하나를 내리는 것입니다:
1. "orchestrator": 대부분의 사용자 요청은 이쪽으로 라우팅해야 합니다. 단순한 질문이라도 일관된 처리를 위해 orchestrator로 보냅니다.
2. "FINISH": 대화를 종료해야 하는 경우에만 선택합니다. 사용자가 명시적으로 대화 종료를 요청하거나, 에러가 발생했거나, 더 이상 처리할 내용이 없을 때만 사용합니다.

항상 정확하고 명확한 결정을 내려주세요.
"""

logger.info("슈퍼바이저 시스템 프롬프트 설정 완료")


class Router:
    """다음에 라우팅할 작업자. 필요한 작업자가 없으면 FINISH로 라우팅합니다."""
    next: Literal[tuple(options)]


class SessionManager:
    """세션 관리 클래스"""
    
    def __init__(self):
        self.session_api_url = os.environ.get("SESSION_API_URL", "http://localhost:8000")
    
    def get_recent_messages(self, session_id: str, max_messages: int = 10) -> List[BaseMessage]:
        """현재 세션에서 최근 대화 내용을 가져옵니다.
        
        Args:
            session_id: 세션 ID
            max_messages: 가져올 최대 메시지 수
            
        Returns:
            최근 대화 메시지 리스트
        """
        try:
            # 세션 매니저 API를 직접 호출
            response = requests.get(f"{self.session_api_url}/sessions/{session_id}")
            
            if response.status_code != 200:
                logger.warning(f"세션 {session_id} 조회 실패: 상태 코드 {response.status_code}")
                return []
            
            session_data = response.json()
            
            if not session_data or "messages" not in session_data or not session_data["messages"]:
                logger.warning(f"세션 {session_id}에서 메시지를 찾을 수 없습니다.")
                return []
            
            # 최근 메시지 선택 (최대 max_messages개)
            all_messages = session_data["messages"]
            recent_messages = all_messages[-min(max_messages, len(all_messages)):]
            
            # BaseMessage 객체로 변환
            result_messages = []
            for msg in recent_messages:
                msg_type = msg.get("type")
                content = msg.get("content", "")
                
                if msg_type == "HumanMessage":
                    result_messages.append(HumanMessage(content=content))
                elif msg_type == "AIMessage":
                    result_messages.append(AIMessage(content=content))
            
            logger.info(f"세션 {session_id}에서 {len(result_messages)}개의 최근 메시지를 가져왔습니다.")
            return result_messages
        except Exception as e:
            logger.error(f"세션 메시지 가져오기 중 오류 발생: {str(e)}")
            return []


class SupervisorAgent:
    """슈퍼바이저 에이전트 클래스"""
    
    def __init__(self):
        """에이전트 초기화"""
        self.llm = None
        self.session_manager = SessionManager()
        
        # 모델 설정 가져오기
        self.model_name = os.environ.get("SUPERVISOR_MODEL", "gemini-2.0-flash")
        logger.info(f"슈퍼바이저 LLM 모델: {self.model_name}")
    
    def initialize(self):
        """슈퍼바이저 LLM을 초기화합니다."""
        if self.llm is None:
            try:
                logger.info("슈퍼바이저 LLM 초기화 중...")
                self.llm = ChatVertexAI(
                    model=self.model_name,
                    temperature=0.1,
                    max_output_tokens=8000
                )
                logger.info("슈퍼바이저 LLM 초기화 완료")
            except Exception as e:
                logger.error(f"슈퍼바이저 LLM 초기화 중 오류 발생: {str(e)}")
                raise
        
        return self.llm
    
    def log_messages(self, messages: List[BaseMessage]) -> None:
        """메시지 목록의 내용을 로그로 남깁니다."""
        logger.info(f"총 {len(messages)}개의 메시지가 있습니다")
        
        # 마지막 메시지 로깅
        if messages:
            last_idx = len(messages) - 1
            last_msg = messages[last_idx]
            
            if hasattr(last_msg, "type"):
                msg_type = last_msg.type
            else:
                msg_type = "unknown"
                
            if hasattr(last_msg, "content"):
                content = last_msg.content
                logger.info(f"마지막 메시지(타입: {msg_type}): '{content[:1000]}...'")
    
    async def __call__(self, state: MessagesState) -> Command[Literal[*members, "__end__"]]:
        """
        슈퍼바이저 에이전트 호출 메서드입니다.
        현재 상태에 따라 다음에 실행할 에이전트를 결정합니다.
        
        Args:
            state: 현재 메시지와 상태 정보
            
        Returns:
            다음에 실행할 에이전트 명령
        """
        try:
            logger.info("슈퍼바이저 에이전트 호출 시작")
            
            # 메시지 상태 로깅
            if "messages" in state:
                self.log_messages(state["messages"])
            
            # 현재 메시지에서 세션 ID 추출
            session_id = None
            if "messages" in state and state["messages"] and hasattr(state["messages"][-1], "additional_kwargs"):
                session_id = state["messages"][-1].additional_kwargs.get("session_id")
                logger.info(f"세션 ID 추출: {session_id}")
            
            # 시스템 메시지 준비
            messages = [SystemMessage(content=SYSTEM_PROMPT)]
            
            # 세션에서 최근 대화 내용 가져오기
            if session_id:
                logger.info(f"세션 {session_id}에서 최근 대화 내용을 가져옵니다.")
                session_messages = self.session_manager.get_recent_messages(session_id, 10)
                
                if session_messages:
                    # 최근 세션 메시지 추가 (컨텍스트로 사용)
                    messages.append(SystemMessage(content="다음은 현재 세션의 최근 대화 내용입니다. 이 맥락을 고려하여 판단하세요:"))
                    messages.extend(session_messages)
                    messages.append(SystemMessage(content="위의 대화 맥락을 고려하여, 다음 단계를 결정하세요."))
            
            # 현재 상태의 메시지 추가
            messages.extend(state["messages"])
            
            # LLM 모델 가져오기
            logger.info("슈퍼바이저 LLM 모델 호출 준비")
            llm = self.initialize()
            
            # 라우팅 결정
            logger.info("슈퍼바이저 라우팅 결정 중...")
            
            # 대부분의 경우 오케스트레이터로 라우팅 (종료 요청이 아니면)
            is_end_request = False
            
            # 종료 요청 확인 (사용자가 명시적으로 종료를 요청한 경우)
            if "messages" in state and state["messages"]:
                last_message = state["messages"][-1].content.lower()
                end_phrases = ["종료", "중단", "그만", "끝", "quit", "exit", "stop", "bye", "goodbye"]
                is_end_request = any(phrase in last_message for phrase in end_phrases) and len(last_message) < 30
            
            # 종료 요청이면 FINISH, 그 외에는 orchestrator
            goto = "FINISH" if is_end_request else "orchestrator"
            
            # 일반적인 경우 LLM으로 라우팅 결정
            if not is_end_request:
                # 간단한 쿼리로 라우팅 결정
                messages.append(SystemMessage(content="""
사용자의 메시지를 확인하고 다음 중 하나를 선택하세요:
1. "orchestrator": 대부분의 사용자 요청
2. "FINISH": 명시적인 종료 요청이나 더 이상 처리할 내용이 없는 경우

결정: 
                """))
                
                response = llm.with_structured_output(Router).invoke(messages)
                goto = response.next
            
            logger.info(f"슈퍼바이저 라우팅 결정 완료: {goto}")
            
            # 상태 업데이트 준비
            updated_state = dict(state)
            updated_state["status"] = TaskStatus.planning
            
            # 의도 파싱 (간단한 형태로)
            intent_data = {
                "agent": goto,
                "determined_at": datetime.now().isoformat(),
                "confidence": "high"
            }
            updated_state["parsed_intent"] = intent_data
            
            # FINISH인 경우 종료
            if goto == "FINISH":
                logger.info("모든 작업 완료, 대화 종료")
                goto = END
                updated_state["status"] = TaskStatus.completed
            else:
                logger.info(f"다음 에이전트로 {goto} 선택됨")
            
            # 명령 생성 및 반환
            logger.info(f"슈퍼바이저 에이전트 호출 완료, 다음 경로: {goto}")
            return Command(goto=goto, update={**updated_state, "next": goto})
        
        except Exception as e:
            logger.error(f"슈퍼바이저 에이전트 호출 중 오류 발생: {str(e)}")
            # 오류 발생 시 종료
            return Command(goto=END, update={"next": "ERROR", "status": TaskStatus.failed})


# 슈퍼바이저 에이전트 인스턴스 생성
supervisor_agent = SupervisorAgent()

# supervisor_node 함수는 SupervisorAgent 인스턴스를 호출하는 래퍼 함수
async def supervisor_node(state: MessagesState) -> Command[Literal[*members, "__end__"]]:
    """
    슈퍼바이저 노드 함수입니다. SupervisorAgent 인스턴스를 호출합니다.
    
    Args:
        state: 현재 메시지와 상태 정보
        
    Returns:
        다음에 실행할 에이전트 명령
    """
    return await supervisor_agent(state) 