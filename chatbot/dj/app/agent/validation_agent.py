"""
검증 에이전트 모듈

생성된 결과의 정확성, 완전성 및 품질을 검증합니다.
사용자 요청과 제공된 정보 간의 일관성을 확인하고 필요한 개선사항을 제안합니다.
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
from state.base_state import MessagesState, TaskStatus, ValidationResult, AgentResponse, TaskStep

# 환경 변수 로드
load_dotenv()

# 로거 설정
logger = setup_logger("validation_agent", level=LOG_LEVEL)

# 시스템 프롬프트
SYSTEM_PROMPT = """당신은 개발 도구 시스템의 검증 에이전트입니다. 
생성된 결과의 정확성, 완전성 및 품질을 검증하는 것이 당신의 역할입니다.

검증 기준:
1. 완전성: 사용자의 질문에 충분히 답변했는가?
2. 정확성: 제공된 정보가 정확한가?
3. 품질: 응답이 명확하고 구조화되어 있는가?
4. 일관성: 응답이 사용자의 질문과 일치하는가?

생성된 결과를 검토하고, 다음을 제공해야 합니다:
1. 완전성, 정확성, 품질, 일관성에 대한 1-10 점수 평가
2. 개선이 필요한 부분에 대한 구체적인 피드백
3. 필요한 경우 추가 정보나 수정 사항 제안

응답은 항상 한국어로 제공하세요.
"""


class ValidationAgent:
    """검증 에이전트 클래스"""
    
    def __init__(self):
        """에이전트 초기화"""
        self.llm = None
        
        # 모델 설정 가져오기
        self.model_name = os.environ.get("VALIDATION_MODEL", "gemini-1.5-pro")
        logger.info(f"검증 에이전트 LLM 모델: {self.model_name}")
    
    async def initialize(self):
        """검증 에이전트 LLM을 초기화합니다."""
        if self.llm is None:
            logger.info("검증 에이전트 초기화 시작")
            
            try:
                # LLM 초기화
                logger.info("LLM 초기화 중...")
                self.llm = ChatVertexAI(
                    model=self.model_name,
                    temperature=0.1,
                    max_output_tokens=4000
                )
                logger.info("LLM 초기화 완료")
                logger.info("검증 에이전트 초기화 완료")
            except Exception as e:
                logger.error(f"검증 에이전트 초기화 중 오류 발생: {str(e)}")
                raise
        
        return self.llm
    
    async def validate_results(self, state: MessagesState) -> ValidationResult:
        """
        계획 단계에서 생성된 결과를 검증합니다.
        
        Args:
            state: 현재 메시지와 상태 정보
            
        Returns:
            검증 결과
        """
        # 에이전트 인스턴스 가져오기
        llm = await self.initialize()
        
        # 검증할 결과 가져오기
        user_request = state.get("original_query", "")
        results = state.get("results", {})
        plan = state.get("plan", [])
        
        if not user_request or not results:
            logger.warning("검증할 데이터가 충분하지 않습니다.")
            return ValidationResult(
                completeness=5,
                feedback="검증할 충분한 데이터가 없습니다.",
                missing_information=True,
                suggested_agents=["planning_agent"]
            )
        
        # 검증 프롬프트 구성
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"사용자 요청: {user_request}"),
            SystemMessage(content="다음은 각 단계에서 생성된 결과입니다:")
        ]
        
        # 각 단계 결과 추가
        for step_idx, step in enumerate(plan):
            if step_idx in results and results[step_idx] and results[step_idx].get("response"):
                step_result = results[step_idx]["response"]
                messages.append(
                    HumanMessage(
                        content=f"단계 {step_idx+1}: {step.description}\n결과: {step_result.content if hasattr(step_result, 'content') else step_result}"
                    )
                )
        
        # 검증 수행 요청
        messages.append(
            SystemMessage(content="""
검증을 수행하고 다음 형식으로 결과를 제공하세요:

완전성 점수: [1-10]
정확성 점수: [1-10]
품질 점수: [1-10]
일관성 점수: [1-10]

피드백: [구체적인 피드백 및 개선 사항]

필요한 추가 정보: [필요한 경우 추가 정보 명시, 없으면 '없음']

제안된 에이전트: [추가 정보 수집을 위해 호출해야 할 에이전트, 없으면 '없음']
            """)
        )
        
        # 검증 호출
        try:
            response = await llm.ainvoke(messages)
            validation_text = response.content
            
            # 검증 결과 파싱
            logger.info(f"검증 결과 텍스트: \n{validation_text}")
            
            # 점수 및 피드백 파싱
            completeness = self._extract_score(validation_text, "완전성")
            accuracy = self._extract_score(validation_text, "정확성")
            quality = self._extract_score(validation_text, "품질")
            consistency = self._extract_score(validation_text, "일관성")
            
            # 평균 점수 계산
            avg_score = (completeness + accuracy + quality + consistency) / 4
            
            # 피드백 추출
            feedback = self._extract_text(validation_text, "피드백:")
            if not feedback:
                feedback = self._extract_text(validation_text, "피드백")
            
            # 필요한 추가 정보 확인
            missing_info_text = self._extract_text(validation_text, "필요한 추가 정보:")
            if not missing_info_text:
                missing_info_text = self._extract_text(validation_text, "필요한 추가 정보")
            
            missing_information = missing_info_text.lower() not in ["없음", "없습니다", "no", "none"]
            
            # 제안된 에이전트 추출
            suggested_agents_text = self._extract_text(validation_text, "제안된 에이전트:")
            if not suggested_agents_text:
                suggested_agents_text = self._extract_text(validation_text, "제안된 에이전트")
            
            suggested_agents = []
            if suggested_agents_text.lower() not in ["없음", "없습니다", "no", "none"]:
                for agent in ["weather_agent", "mcp_agent", "gemini_search_agent"]:
                    if agent in suggested_agents_text.lower():
                        suggested_agents.append(agent)
            
            # 검증 결과 객체 생성
            validation_result = ValidationResult(
                completeness=completeness,
                feedback=feedback,
                missing_information=missing_information,
                suggested_agents=suggested_agents
            )
            
            logger.info(f"검증 평균 점수: {avg_score:.1f}/10")
            logger.info(f"검증 피드백: {feedback}")
            
            return validation_result
        
        except Exception as e:
            logger.error(f"검증 중 오류 발생: {str(e)}")
            # 오류 발생 시 기본 검증 결과 반환
            return ValidationResult(
                completeness=5,
                feedback=f"검증 과정에서 오류가 발생했습니다: {str(e)}",
                missing_information=True,
                suggested_agents=["planning_agent"]
            )
    
    def _extract_score(self, text: str, score_type: str) -> int:
        """검증 텍스트에서 점수를 추출합니다."""
        try:
            import re
            pattern = rf"{score_type} 점수: *(\d+)"
            match = re.search(pattern, text)
            if match:
                return int(match.group(1))
            
            # 다른 형식 시도
            pattern = rf"{score_type}: *(\d+)"
            match = re.search(pattern, text)
            if match:
                return int(match.group(1))
                
            return 5  # 기본값
        except Exception:
            return 5  # 예외 발생 시 기본값
    
    def _extract_text(self, text: str, prefix: str) -> str:
        """검증 텍스트에서 특정 섹션을 추출합니다."""
        try:
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if prefix in line:
                    # 해당 줄에서 접두사 제거하고 텍스트 추출
                    result = line.split(prefix, 1)[1].strip()
                    
                    # 만약 다음 줄이 있고 비어있지 않으면 더 많은 내용이 있을 수 있음
                    j = i + 1
                    while j < len(lines) and not any(marker in lines[j] for marker in ["완전성", "정확성", "품질", "일관성", "피드백", "필요한 추가 정보", "제안된 에이전트"]):
                        result += " " + lines[j].strip()
                        j += 1
                    
                    return result.strip()
            return ""
        except Exception:
            return ""
    
    async def __call__(self, state: MessagesState) -> Command[Literal["orchestrator"]]:
        """
        검증 에이전트 호출 메서드입니다.
        
        Args:
            state: 현재 메시지와 상태 정보
            
        Returns:
            오케스트레이터로 돌아가는 명령
        """
        try:
            logger.info("검증 에이전트 호출 시작")
            
            # 현재 단계 가져오기
            current_step_idx = state.get("current_step", None)
            plan = state.get("plan", [])
            
            if current_step_idx is not None and 0 <= current_step_idx < len(plan):
                # 현재 단계 상태 업데이트
                current_step = plan[current_step_idx]
                current_step.status = TaskStatus.validating
            
            # 검증 수행
            validation_result = await self.validate_results(state)
            
            # 검증 메시지 생성
            validation_message = AIMessage(
                content=f"검증 결과:\n\n"
                        f"완전성: {validation_result.completeness}/10\n"
                        f"피드백: {validation_result.feedback}\n"
                        f"{'추가 정보 필요: 예' if validation_result.missing_information else '추가 정보 필요: 아니오'}",
                name="validation_agent"
            )
            
            # 현재 단계 완료 처리
            if current_step_idx is not None and 0 <= current_step_idx < len(plan):
                plan[current_step_idx].status = TaskStatus.completed
                plan[current_step_idx].end_time = datetime.now()
            
            # 상태 업데이트 준비
            updated_state = dict(state)
            updated_state["messages"] = updated_state.get("messages", []) + [validation_message]
            updated_state["validation_result"] = validation_result
            updated_state["status"] = TaskStatus.responding
            updated_state["next"] = "respond"
            
            logger.info("검증 에이전트 작업 완료, 응답 에이전트로 이동")
            
            # 응답 에이전트로 이동
            return Command(
                update=updated_state,
                goto="respond"
            )
            
        except Exception as e:
            logger.error(f"검증 에이전트 호출 중 오류 발생: {str(e)}")
            error_message = AIMessage(
                content=f"검증 에이전트 실행 중 오류가 발생했습니다: {str(e)}",
                name="validation_agent"
            )
            
            error_state = dict(state)
            error_state["messages"] = error_state.get("messages", []) + [error_message]
            error_state["status"] = TaskStatus.failed
            error_state["next"] = "respond"
            
            return Command(
                update=error_state,
                goto="respond"
            )


# 검증 에이전트 인스턴스 생성
validation_agent = ValidationAgent()

# validation_node 함수는 ValidationAgent 인스턴스를 호출하는 래퍼 함수
async def validation_node(state: MessagesState) -> Command[Literal["orchestrator", "respond"]]:
    """
    검증 노드 함수입니다. ValidationAgent 인스턴스를 호출합니다.
    
    Args:
        state: 현재 메시지와 상태 정보
        
    Returns:
        응답 에이전트로 이동하는 명령
    """
    return await validation_agent(state) 