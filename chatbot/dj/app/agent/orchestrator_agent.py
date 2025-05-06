"""
오케스트레이터 에이전트 모듈

사용자의 요청을 분석하고 전체적인 작업 흐름을 관리합니다.
요청의 복잡성에 따라 계획 수립이 필요한지 판단하고 작업을 조정합니다.
"""

import os
import json
from typing import Literal, List, Dict, Any, Optional
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.types import Command
from langchain_google_vertexai import ChatVertexAI
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from utils.logger_config import setup_logger
from config import *  # Import all constants and configuration values
from state.base_state import MessagesState, TaskStatus, TaskStep, AgentRequest

# 환경 변수 로드
load_dotenv()

# 로거 설정
logger = setup_logger("orchestrator_agent", level=LOG_LEVEL)

# 시스템 프롬프트
SYSTEM_PROMPT = """당신은 개발 도구 시스템의 오케스트레이터 에이전트입니다. 
사용자의 요청을 분석하고 그 요청을 처리하기 위한 전체적인 흐름을 관리합니다.

당신의 주요 역할:
1. 사용자 요청 분석: 사용자가 어떤 작업을 원하는지 정확히 파악합니다.
2. 계획 필요성 판단: 요청이 복잡하여 상세 계획이 필요한지, 아니면 바로 처리 가능한지 결정합니다.
3. 적절한 에이전트 선택: 요청 처리에 필요한 에이전트를 결정합니다.
4. 작업 조정: 에이전트 간의 작업 흐름을 조정하여 효율적인 처리가 이루어지도록 합니다.
5. 결과 통합 및 검증: 여러 에이전트의 결과를 통합하고 검증하여 일관된 응답을 제공합니다.

당신은 다음 결정을 내려야 합니다:
- 복잡한 작업이라면 "planning"으로 보내 상세 계획 수립
- 날씨 관련 요청은 직접 "weather_agent"로 라우팅
- 단순 검색/조회는 "gemini_search_agent" 또는 "mcp_agent"로 라우팅
- 작업 결과 검증이 필요하면 "validation"으로 라우팅
- 최종 응답을 생성할 때는 "respond"로 라우팅
- 이미 계획이 있다면 다음 단계의 에이전트 호출

모든 결정은 명확한 근거를 바탕으로 해야 합니다.
응답은 항상 한국어로 제공하세요.
"""


class OrchestratorAgent:
    """오케스트레이터 에이전트 클래스"""
    
    def __init__(self):
        """에이전트 초기화"""
        self.llm = None
        
        # 모델 설정 가져오기
        self.model_name = os.environ.get("ORCHESTRATOR_MODEL", "gemini-2.0-flash")
        logger.info(f"오케스트레이터 에이전트 LLM 모델: {self.model_name}")
    
    async def initialize(self):
        """오케스트레이터 에이전트 LLM을 초기화합니다."""
        if self.llm is None:
            logger.info("오케스트레이터 에이전트 초기화 시작")
            
            try:
                # LLM 초기화
                logger.info("LLM 초기화 중...")
                self.llm = ChatVertexAI(
                    model=self.model_name,
                    temperature=0.1,
                    max_output_tokens=8000
                )
                logger.info("LLM 초기화 완료")
                logger.info("오케스트레이터 에이전트 초기화 완료")
            except Exception as e:
                logger.error(f"오케스트레이터 에이전트 초기화 중 오류 발생: {str(e)}")
                raise
        
        return self.llm
    
    async def decide_next_step(self, state: MessagesState) -> str:
        """사용자 요청을 분석하여 다음 단계를 결정합니다.
        
        Args:
            state: 현재 메시지와 상태 정보
            
        Returns:
            다음 단계 (planning, respond, weather_agent, gemini_search_agent 등)
        """
        # 에이전트 인스턴스 가져오기
        llm = await self.initialize()
        
        # 프롬프트 구성
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        
        # 결정을 위한 추가 지시
        messages.append(SystemMessage(content="""
다음 중 가장 적합한 경로를 선택하세요:

1. "planning": 복잡한 작업이 필요하여 상세 계획 수립이 필요한 경우 (여러 단계 또는 여러 에이전트가 필요한 경우)
2. "weather_agent": 날씨 정보 요청을 직접 처리할 경우 (예: "서울 날씨 알려줘")
3. "gemini_search_agent": 간단한 질문이나 정보 검색이 필요한 경우 (예: "파이썬이란?")
4. "mcp_agent": MCP 도구를 직접 사용해야 하는 경우
5. "respond": 간단히 응답만 필요한 경우

참고: 
- 여러 단계가 필요하거나 복잡한 분석이 필요한 경우는 반드시 "planning"을 선택하세요
- 사용자의 요청이 명확하고 단순한 경우에만 직접 특정 에이전트로 라우팅하세요
- 불확실할 경우 "planning"을 선택하는 것이 안전합니다

결정: 
        """))
        
        # LLM 호출
        response = await llm.ainvoke(messages)
        decision = response.content.strip().lower()
        
        # 응답에서 결정 추출
        if "planning" in decision:
            return "planning"
        elif "weather" in decision:
            return "weather_agent"
        elif "gemini" in decision:
            return "gemini_search_agent"
        elif "mcp" in decision:
            return "mcp_agent"
        else:
            return "respond"
    
    async def update_step_status(self, state: MessagesState) -> MessagesState:
        """
        현재 단계 완료 후 상태를 업데이트합니다.
        
        Args:
            state: 현재 메시지와 상태 정보
            
        Returns:
            업데이트된 상태
        """
        # 계획이 있고 현재 단계가 설정되어 있는 경우
        if state.get("plan") and state.get("current_step") is not None:
            plan = state["plan"]
            current_step_idx = state["current_step"]
            
            # 유효한 단계 범위 확인
            if 0 <= current_step_idx < len(plan):
                # 현재 단계 완료 처리
                plan[current_step_idx].status = TaskStatus.completed
                plan[current_step_idx].end_time = datetime.now()
                
                # 다음 단계로 이동
                next_step_idx = current_step_idx + 1
                
                # 업데이트된 상태 반환
                updated_state = dict(state)
                updated_state["plan"] = plan
                updated_state["current_step"] = next_step_idx if next_step_idx < len(plan) else None
                
                # 모든 단계가 완료되었는지 확인
                if next_step_idx >= len(plan):
                    updated_state["status"] = TaskStatus.validating
                else:
                    updated_state["status"] = TaskStatus.executing
                    # 다음 단계 시작 시간 설정
                    plan[next_step_idx].start_time = datetime.now()
                    plan[next_step_idx].status = TaskStatus.executing
                
                logger.info(f"단계 {current_step_idx+1} 완료, 다음 단계: {next_step_idx+1 if next_step_idx < len(plan) else '없음'}")
                return updated_state
        
        # 계획이 없거나 현재 단계 업데이트가 필요 없는 경우
        return state
    
    async def __call__(self, state: MessagesState) -> Command[Literal["planning", "respond", "weather_agent", "gemini_search_agent", "mcp_agent", "validation"]]:
        """
        오케스트레이터 에이전트 호출 메서드입니다.
        
        Args:
            state: 현재 메시지와 상태 정보
            
        Returns:
            다음 에이전트로 이동하는 명령
        """
        try:
            logger.info("오케스트레이터 에이전트 호출 시작")
            
            # 입력 메시지 로깅
            if "messages" in state and state["messages"]:
                last_user_msg = state["messages"][-1].content
                logger.info(f"오케스트레이터 에이전트에 전달된 메시지: '{last_user_msg[:1000]}...'")
            
            # 상태 업데이트 준비
            updated_state = dict(state)
            
            # 단계 1: 계획 실행 상태 확인
            # 이미 계획이 있고 실행 중인 경우
            if "plan" in state and state.get("current_step") is not None:
                # 이전 단계의 에이전트 응답이 있는 경우, 상태 업데이트
                updated_state = await self.update_step_status(state)
                
                # 아직 실행할 단계가 남아있는 경우
                if updated_state.get("current_step") is not None and updated_state["current_step"] < len(updated_state["plan"]):
                    current_step = updated_state["plan"][updated_state["current_step"]]
                    next_agent = current_step.agent
                    
                    logger.info(f"계획 실행 중: 단계 {updated_state['current_step']+1}/{len(updated_state['plan'])}, 다음 에이전트: {next_agent}")
                    
                    # 계획에 따라 다음 에이전트로 이동
                    updated_state["next"] = next_agent
                    updated_state["status"] = TaskStatus.executing
                    return Command(goto=next_agent, update=updated_state)
                
                # 모든 단계가 완료된 경우, 검증으로 이동
                elif "plan" in updated_state and updated_state.get("plan"):
                    logger.info(f"모든 계획 단계 완료, 검증으로 이동")
                    updated_state["next"] = "validation"
                    updated_state["status"] = TaskStatus.validating
                    return Command(goto="validation", update=updated_state)
                
                # 계획은 있지만 모든 단계가 완료되었고 검증도 끝난 경우
                elif updated_state.get("validation_result") is not None:
                    logger.info(f"검증 완료, 응답 생성으로 이동")
                    updated_state["next"] = "respond"
                    updated_state["status"] = TaskStatus.responding
                    return Command(goto="respond", update=updated_state)
            
            # 단계 2: 새로운 요청 처리
            # 이전 단계가 validation이었고, 추가 작업이 필요한 경우 planning으로 다시 보냄
            if state.get("status") == TaskStatus.validating and state.get("validation_result"):
                validation_result = state.get("validation_result")
                if validation_result.missing_information:
                    logger.info("검증 결과 추가 정보 필요, 계획 재수립")
                    updated_state["next"] = "planning"
                    updated_state["status"] = TaskStatus.planning
                    return Command(goto="planning", update=updated_state)
            
            # 단계 3: 요청 분석 및 다음 단계 결정
            next_step = await self.decide_next_step(state)
            logger.info(f"오케스트레이터 결정: {next_step}")
            
            # 상태 업데이트
            if next_step == "planning":
                updated_state["status"] = TaskStatus.planning
            elif next_step == "respond":
                updated_state["status"] = TaskStatus.responding
            else:
                # 직접 전문 에이전트 호출인 경우, 간단한 계획 생성
                # 하나의 단계만 있는 계획 생성
                simple_request = AgentRequest(
                    query=state["messages"][-1].content,
                    context={"original_query": state["messages"][-1].content}
                )
                
                simple_step = TaskStep(
                    description=f"{next_step}를 사용하여 사용자 요청 처리",
                    agent=next_step,
                    status=TaskStatus.planning,
                    request=simple_request,
                    dependencies=[]
                )
                
                # 계획 설정
                updated_state["plan"] = [simple_step]
                updated_state["current_step"] = 0
                updated_state["results"] = {}
                updated_state["status"] = TaskStatus.executing
                
                # 첫 단계 시작 처리
                simple_step.status = TaskStatus.executing
                simple_step.start_time = datetime.now()
            
            updated_state["next"] = next_step
            
            # 다음 단계로 라우팅
            logger.info(f"오케스트레이터 에이전트 작업 완료, {next_step}로 라우팅")
            
            # 메시지 상태 업데이트 후 다음 단계로 이동
            return Command(goto=next_step, update=updated_state)
            
        except Exception as e:
            logger.error(f"오케스트레이터 에이전트 호출 중 오류 발생: {str(e)}")
            error_message = AIMessage(
                content=f"오케스트레이터 에이전트 실행 중 오류가 발생했습니다: {str(e)}",
                name="orchestrator_agent"
            )
            
            error_state = dict(state)
            error_state["messages"] = error_state.get("messages", []) + [error_message]
            error_state["status"] = TaskStatus.failed
            error_state["next"] = "respond"
            
            return Command(
                update=error_state,
                goto="respond"
            )


# 오케스트레이터 에이전트 인스턴스 생성
orchestrator_agent = OrchestratorAgent()

# orchestrator_node 함수는 OrchestratorAgent 인스턴스를 호출하는 래퍼 함수
async def orchestrator_node(state: MessagesState) -> Command[Literal["planning", "respond", "weather_agent", "gemini_search_agent", "mcp_agent", "validation"]]:
    """
    오케스트레이터 노드 함수입니다. OrchestratorAgent 인스턴스를 호출합니다.
    
    Args:
        state: 현재 메시지와 상태 정보
        
    Returns:
        다음 에이전트로 이동하는 명령
    """
    return await orchestrator_agent(state) 