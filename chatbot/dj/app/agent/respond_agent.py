"""
응답 에이전트 모듈

사용자 쿼리에 대한 최종 응답을 생성하고 형식을 지정합니다.
검증 결과를 통합하고 응답을 개선하여 사용자가 이해하기 쉽고 도움이 되는 응답을 제공합니다.
"""

import os
from typing import Literal, Dict, Any, Optional, List
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_google_vertexai import ChatVertexAI
from langgraph.types import Command
from dotenv import load_dotenv

from utils.logger_config import setup_logger
from config import *  # Import all constants and configuration values
from state.base_state import MessagesState, TaskStatus, ValidationResult, AgentResponse

# 환경 변수 로드
load_dotenv()

# 로거 설정
logger = setup_logger("respond_agent", level=LOG_LEVEL)

# 시스템 프롬프트
SYSTEM_PROMPT = """당신은 개발 도구 시스템의 응답 에이전트입니다. 
사용자 쿼리에 대한 최종 응답을 생성하고 형식을 지정하는 것이 당신의 역할입니다.

응답 작성 지침:
1. 정확성: 모든 정보가 정확하고 오류가 없는지 확인하세요.
2. 완전성: 사용자의 질문에 완전히 답변했는지 확인하세요.
3. 명확성: 응답이 명확하고 이해하기 쉬운지 확인하세요.
4. 구조화: 응답을 논리적으로 구조화하여 사용자가 쉽게 이해할 수 있도록 하세요.
5. 제안 사항: 추가 정보나 관련 작업에 대한 제안을 포함하세요.

응답에는 다음 요소를 포함해야 합니다:
- 요약: 핵심 정보를 간결하게 요약합니다.
- 세부 정보: 필요한 세부 정보를 명확하게 제공합니다.
- 다음 단계: 적절한 경우 사용자가 취할 수 있는 다음 단계를 제안합니다.

응답은 항상 한국어로 제공하세요.
"""


class RespondAgent:
    """응답 에이전트 클래스"""
    
    def __init__(self):
        """에이전트 초기화"""
        self.llm = None
        
        # 모델 설정 가져오기
        self.model_name = os.environ.get("RESPOND_MODEL", "gemini-2.0-flash")
        logger.info(f"응답 에이전트 LLM 모델: {self.model_name}")
    
    async def initialize(self):
        """응답 에이전트 LLM을 초기화합니다."""
        if self.llm is None:
            logger.info("응답 에이전트 초기화 시작")
            
            try:
                # LLM 초기화
                logger.info("LLM 초기화 중...")
                self.llm = ChatVertexAI(
                    model=self.model_name,
                    temperature=0.2,
                    max_output_tokens=8000
                )
                logger.info("LLM 초기화 완료")
                logger.info("응답 에이전트 초기화 완료")
            except Exception as e:
                logger.error(f"응답 에이전트 초기화 중 오류 발생: {str(e)}")
                raise
        
        return self.llm
    
    async def generate_response(self, state: MessagesState) -> str:
        """
        사용자 쿼리에 대한 최종 응답을 생성합니다.
        
        Args:
            state: 현재 메시지와 상태 정보
            
        Returns:
            생성된 응답 문자열
        """
        # 에이전트 인스턴스 가져오기
        llm = await self.initialize()
        
        # 응답 생성에 필요한 정보 가져오기
        user_request = state.get("original_query", "")
        results = state.get("results", {})
        plan = state.get("plan", [])
        validation_result = state.get("validation_result", None)
        
        if not user_request or not results:
            logger.warning("응답 생성에 필요한 데이터가 충분하지 않습니다.")
            return "죄송합니다, 요청을 처리하는 데 필요한 정보가 부족합니다. 다시 질문해 주시겠어요?"
        
        # 응답 프롬프트 구성
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"사용자 요청: {user_request}")
        ]
        
        # 수집한 결과 추가
        messages.append(SystemMessage(content="다음은 각 단계에서 수집한 결과입니다:"))
        
        for step_idx, step in enumerate(plan):
            if step_idx in results and results[step_idx] and results[step_idx].get("response"):
                step_result = results[step_idx]["response"]
                messages.append(
                    HumanMessage(
                        content=f"단계 {step_idx+1}: {step.description}\n결과: {step_result.content if hasattr(step_result, 'content') else step_result}"
                    )
                )
        
        # 검증 결과 추가
        if validation_result:
            completeness = validation_result.completeness
            feedback = validation_result.feedback
            
            messages.append(
                SystemMessage(
                    content=f"""
검증 결과:
- 완전성 점수: {completeness}/10
- 피드백: {feedback}
                    """
                )
            )
        
        # 응답 생성 지침 추가
        messages.append(
            SystemMessage(content="""
위 정보를 바탕으로 사용자 요청에 대한 최종 응답을 생성하세요. 다음 사항을 고려하세요:
1. 명확하고 정확한 응답을 제공하세요.
2. 논리적으로 정보를 구조화하세요.
3. 사용자의 원래 질문에 완전히 답변하세요.
4. 필요한 경우 추가 정보나 다음 단계를 제안하세요.
5. 응답은 항상 한국어로 작성하세요.
            """)
        )
        
        # LLM 호출
        try:
            response = await llm.ainvoke(messages)
            generated_response = response.content
            
            logger.info(f"생성된 응답: \n{generated_response[:200]}...")
            return generated_response
            
        except Exception as e:
            logger.error(f"응답 생성 중 오류 발생: {str(e)}")
            return f"죄송합니다, 응답을 생성하는 중에 오류가 발생했습니다: {str(e)}"
    
    async def __call__(self, state: MessagesState) -> Command[Literal["orchestrator"]]:
        """
        응답 에이전트 호출 메서드입니다.
        
        Args:
            state: 현재 메시지와 상태 정보
            
        Returns:
            오케스트레이터로 돌아가는 명령
        """
        try:
            logger.info("응답 에이전트 호출 시작")
            
            # 현재 상태 업데이트
            updated_state = dict(state)
            updated_state["status"] = TaskStatus.responding
            
            # 응답 생성
            response_text = await self.generate_response(state)
            
            # 응답 메시지 생성
            response_message = AIMessage(
                content=response_text,
                name="respond_agent"
            )
            
            # 상태 업데이트
            updated_state["messages"] = updated_state.get("messages", []) + [response_message]
            updated_state["final_response"] = response_text
            updated_state["status"] = TaskStatus.completed
            updated_state["next"] = "orchestrator"
            
            logger.info("응답 에이전트 작업 완료")
            
            # 오케스트레이터로 돌아가기
            return Command(
                update=updated_state,
                goto="orchestrator"
            )
            
        except Exception as e:
            logger.error(f"응답 에이전트 호출 중 오류 발생: {str(e)}")
            error_message = AIMessage(
                content=f"응답 에이전트 실행 중 오류가 발생했습니다: {str(e)}",
                name="respond_agent"
            )
            
            error_state = dict(state)
            error_state["messages"] = error_state.get("messages", []) + [error_message]
            error_state["status"] = TaskStatus.failed
            error_state["next"] = "orchestrator"
            
            return Command(
                update=error_state,
                goto="orchestrator"
            )


# 응답 에이전트 인스턴스 생성
respond_agent = RespondAgent()

# respond_node 함수는 RespondAgent 인스턴스를 호출하는 래퍼 함수
async def respond_node(state: MessagesState) -> Command[Literal["orchestrator"]]:
    """
    응답 노드 함수입니다. RespondAgent 인스턴스를 호출합니다.
    
    Args:
        state: 현재 메시지와 상태 정보
        
    Returns:
        오케스트레이터로 돌아가는 명령
    """
    return await respond_agent(state) 