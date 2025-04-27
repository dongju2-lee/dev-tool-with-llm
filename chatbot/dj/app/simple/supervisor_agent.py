import os
import json
from typing import Literal, List, Dict, Any, Optional
from typing_extensions import TypedDict

from langchain_core.messages import SystemMessage, BaseMessage, HumanMessage, AIMessage
from langgraph.graph import MessagesState, END
from langgraph.types import Command
from langchain_google_vertexai import ChatVertexAI
from dotenv import load_dotenv
import requests


from utils.logger_config import setup_logger
from config import *  # Import all constants and configuration values

# 환경 변수 로드
load_dotenv()

# 로거 설정
logger = setup_logger("supervisor_agent", level=LOG_LEVEL)

# 슈퍼바이저에서 관리할 에이전트 멤버 목록
members = ["mcp_agent", "gemini_search_agent"]
# 라우팅 옵션 (멤버 + 종료)
options = members + ["FINISH"]

logger.info(f"슈퍼바이저 에이전트 멤버 목록: {members}")
logger.info(f"라우팅 옵션: {options}")

# 슈퍼바이저 시스템 프롬프트
SYSTEM_PROMPT = """당신은 개발 도구 시스템의 슈퍼바이저 에이전트입니다. 사용자의 요청을 분석하여 적절한 에이전트에 작업을 할당합니다.

당신은 다음 에이전트 중 하나를 선택해야 합니다:
1. gemini_search_agent: 검색 쿼리에 대한 응답을 제공합니다. 일반 지식, 개념 설명, 요약 등의 정보를 제공합니다.
2. mcp_agent: MCP 도구 관리를 담당합니다. 다양한 MCP 도구를 활용하여 사용자 요청을 처리합니다. 현재 mcp_agent tool로는 weather에 대한 mcp가 있습니다

사용자의 요청을 분석하여 다음 중 하나를 선택하세요:
- "mcp_agent": MCP 도구와 관련된 요청인 경우, 현재 mcp_agent tool로는 weather에 대한 mcp가 있습니다
- "gemini_search_agent": 일반적인 정보나 지식에 대해 질문인 경우 (사실 조회, 개념 설명, 요약 등)
- "FINISH": 모든 작업이 완료되어 더 이상 에이전트 호출이 필요 없는 경우

에이전트 선택 기준:
- 사용자가 MCP 도구를 사용하거나 관련 요청을 하는 경우 -> mcp_agent
- 사용자가 일반적인 정보나 지식에 대해 질문하는 경우 -> gemini_search_agent
- 이전 에이전트의 응답만으로 사용자의 요청이 완료된 경우 -> FINISH

중요: 이전 대화 맥락을 반드시 고려하세요. 사용자가 이전 대화와 관련된 질문을 하거나 이전 작업을 이어서 하려는 경우, 그 맥락을 유지하여 적절한 에이전트를 선택해야 합니다.

항상 정확하고 명확한 결정을 내려주세요.
"""

logger.info("슈퍼바이저 시스템 프롬프트 설정 완료")


class Router(TypedDict):
    """다음에 라우팅할 작업자. 필요한 작업자가 없으면 FINISH로 라우팅합니다."""
    next: Literal[*options]


class State(MessagesState):
    """메시지 상태와 다음 라우팅 정보를 포함하는 상태 클래스"""
    next: str


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
    
    async def __call__(self, state: State) -> Command[Literal[*members, "__end__"]]:
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
                    messages.append(SystemMessage(content="위의 대화 맥락을 고려하여, 현재 요청에 가장 적합한 에이전트를 선택하세요."))
            
            # 현재 상태의 메시지 추가
            messages.extend(state["messages"])
            
            # LLM 모델 가져오기
            logger.info("슈퍼바이저 LLM 모델 호출 준비")
            llm = self.initialize()
            
            # 라우팅 결정
            logger.info("슈퍼바이저 라우팅 결정 중...")
            response = llm.with_structured_output(Router).invoke(messages)
            goto = response["next"]
            
            logger.info(f"슈퍼바이저 라우팅 결정 완료: {goto}")
            
            # FINISH인 경우 종료
            if goto == "FINISH":
                logger.info("모든 작업 완료, 대화 종료")
                goto = END
            else:
                logger.info(f"다음 에이전트로 {goto} 선택됨")
            
            # 명령 생성 및 반환
            logger.info(f"슈퍼바이저 에이전트 호출 완료, 다음 경로: {goto}")
            return Command(goto=goto, update={"next": goto})
        
        except Exception as e:
            logger.error(f"슈퍼바이저 에이전트 호출 중 오류 발생: {str(e)}")
            # 오류 발생 시 종료
            return Command(goto=END, update={"next": "ERROR"})


# 슈퍼바이저 에이전트 인스턴스 생성
supervisor_agent = SupervisorAgent()

# supervisor_node 함수는 SupervisorAgent 인스턴스를 호출하는 래퍼 함수
async def supervisor_node(state: State) -> Command[Literal[*members, "__end__"]]:
    """
    슈퍼바이저 노드 함수입니다. SupervisorAgent 인스턴스를 호출합니다.
    
    Args:
        state: 현재 메시지와 상태 정보
        
    Returns:
        다음에 실행할 에이전트 명령
    """
    return await supervisor_agent(state) 