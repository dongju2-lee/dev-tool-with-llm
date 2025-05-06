"""
플래닝 에이전트 모듈

사용자의 요청을 분석하고 그 요청을 효율적으로 처리하기 위한 상세 계획을 수립합니다.
복잡한 작업을 작은 단계로 분해하고 각 단계에 적절한 에이전트를 할당합니다.
"""

import os
import json
from typing import Literal, List, Dict, Any, Optional
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
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
logger = setup_logger("planning_agent", level=LOG_LEVEL)

# 시스템 프롬프트
SYSTEM_PROMPT = """당신은 개발 도구 시스템의 계획 수립 에이전트입니다. 
사용자의 요청을 분석하고 그 요청을 효율적으로 처리하기 위한 상세 계획을 수립합니다.

당신의 주요 역할:
1. 사용자 요청 분석: 사용자가 요청한 작업의 핵심 요소를 파악합니다.
2. 작업 분해: 복잡한 요청을 작은 단계들로 분해합니다.
3. 에이전트 할당: 각 단계에 적합한 에이전트를 할당합니다.
4. 의존성 관리: 단계 간의 의존성을 파악하여 순서를 결정합니다.

사용 가능한 에이전트:
1. weather_agent: 날씨 정보를 제공합니다.
2. mcp_agent: 다양한 MCP 도구를 활용합니다.
3. gemini_search_agent: 일반 검색 정보를 제공합니다.

계획 수립 지침:
- 각 단계는 명확하고 구체적이어야 합니다.
- 각 단계에는 적절한 에이전트를 할당해야 합니다.
- 단계 간의 의존성을 고려하여 실행 순서를 결정해야 합니다.
- 계획은 사용자 요청을 완벽하게 처리할 수 있도록 포괄적이어야 합니다.

응답은 항상 한국어로 제공하세요.
"""


class PlanningAgent:
    """플래닝 에이전트 클래스"""
    
    def __init__(self):
        """에이전트 초기화"""
        self.llm = None
        
        # 모델 설정 가져오기
        self.model_name = os.environ.get("PLANNING_MODEL", "gemini-2.0-flash")
        logger.info(f"플래닝 에이전트 LLM 모델: {self.model_name}")
    
    async def initialize(self):
        """플래닝 에이전트 LLM을 초기화합니다."""
        if self.llm is None:
            logger.info("플래닝 에이전트 초기화 시작")
            
            try:
                # LLM 초기화
                logger.info("LLM 초기화 중...")
                self.llm = ChatVertexAI(
                    model=self.model_name,
                    temperature=0.1,
                    max_output_tokens=8000
                )
                logger.info("LLM 초기화 완료")
                logger.info("플래닝 에이전트 초기화 완료")
            except Exception as e:
                logger.error(f"플래닝 에이전트 초기화 중 오류 발생: {str(e)}")
                raise
        
        return self.llm
    
    async def create_plan(self, state: MessagesState) -> List[TaskStep]:
        """사용자 요청을 분석하여 실행 계획을 생성합니다.
        
        Args:
            state: 현재 메시지와 상태 정보
            
        Returns:
            태스크 단계 목록
        """
        # 에이전트 인스턴스 가져오기
        llm = await self.initialize()
        
        # 프롬프트 구성
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        
        # 계획 생성을 위한 추가 지시
        messages.append(SystemMessage(content="""
요청을 처리하기 위한 단계별 계획을 작성하세요. 다음 형식을 사용하세요:

1. [첫 번째 단계 설명] - 담당 에이전트: [에이전트 이름]
2. [두 번째 단계 설명] - 담당 에이전트: [에이전트 이름]
3. ...

각 단계는 명확하고 구체적이어야 하며, 적절한 에이전트를 할당해야 합니다.
가능한 에이전트: weather_agent, mcp_agent, gemini_search_agent
        """))
        
        # LLM 호출
        response = await llm.ainvoke(messages)
        plan_text = response.content
        
        # 텍스트 형식의 계획을 TaskStep 객체 목록으로 변환
        steps = []
        for line in plan_text.split('\n'):
            line = line.strip()
            if not line or not any(c.isdigit() for c in line):
                continue
                
            try:
                # 단계 번호 추출
                step_num = 0
                for c in line:
                    if c.isdigit():
                        step_num = int(c)
                        break
                
                # 담당 에이전트 추출
                agent = None
                if "weather_agent" in line.lower():
                    agent = "weather_agent"
                elif "mcp_agent" in line.lower():
                    agent = "mcp_agent"
                elif "gemini_search_agent" in line.lower():
                    agent = "gemini_search_agent"
                else:
                    # 기본값
                    agent = "gemini_search_agent"
                
                # 단계 설명 추출 (번호와 에이전트 정보 제외)
                description = line
                for prefix in [f"{step_num}.", f"{step_num}:"]:
                    if description.startswith(prefix):
                        description = description[len(prefix):].strip()
                        break
                
                # 에이전트 정보 제거
                for agent_marker in [
                    "- 담당 에이전트:",
                    "- 담당:",
                    "담당 에이전트:",
                    "담당:",
                    "에이전트:"
                ]:
                    if agent_marker in description:
                        description = description.split(agent_marker)[0].strip()
                
                # 기본 요청 생성
                agent_request = AgentRequest(
                    query=description,
                    context={"original_query": state.get("original_query", "")}
                )
                
                # TaskStep 생성
                step = TaskStep(
                    description=description,
                    agent=agent,
                    status=TaskStatus.planning,
                    request=agent_request,
                    dependencies=[i for i in range(step_num-1)]  # 이전 단계에 대한 의존성 추가
                )
                steps.append(step)
            except Exception as e:
                logger.error(f"계획 단계 파싱 중 오류: {str(e)}, 라인: {line}")
        
        logger.info(f"생성된 계획: {len(steps)}개 단계")
        for i, step in enumerate(steps):
            logger.info(f"  단계 {i+1}: {step.description} (담당: {step.agent})")
        
        return steps
    
    async def __call__(self, state: MessagesState) -> Command[Literal["orchestrator"]]:
        """
        플래닝 에이전트 호출 메서드입니다.
        
        Args:
            state: 현재 메시지와 상태 정보
            
        Returns:
            오케스트레이터로 돌아가는 명령
        """
        try:
            logger.info("플래닝 에이전트 호출 시작")
            
            # 입력 메시지 로깅
            if "messages" in state and state["messages"]:
                last_user_msg = state["messages"][-1].content
                logger.info(f"플래닝 에이전트에 전달된 메시지: '{last_user_msg[:1000]}...'")
            
            # 상태 업데이트 준비
            updated_state = dict(state)
            updated_state["status"] = TaskStatus.planning
            
            # 계획 생성
            plan = await self.create_plan(state)
            
            # 계획 요약 메시지 생성
            plan_summary = "계획이 생성되었습니다:\n\n"
            for i, step in enumerate(plan):
                plan_summary += f"{i+1}. {step.description} (담당: {step.agent})\n"
            
            # 계획 메시지 생성
            planning_message = HumanMessage(
                content=plan_summary,
                name="planning_agent"
            )
            
            # 첫 번째 단계 시작 시간 설정
            if plan:
                plan[0].start_time = datetime.now()
                plan[0].status = TaskStatus.executing
            
            # 상태 업데이트
            updated_state["messages"] = updated_state.get("messages", []) + [planning_message]
            updated_state["plan"] = plan
            updated_state["current_step"] = 0 if plan else None
            updated_state["status"] = TaskStatus.executing
            updated_state["next"] = "orchestrator"
            
            logger.info("플래닝 에이전트 작업 완료, 오케스트레이터로 반환")
            
            # 오케스트레이터로 돌아가기
            return Command(
                update=updated_state,
                goto="orchestrator"
            )
            
        except Exception as e:
            logger.error(f"플래닝 에이전트 호출 중 오류 발생: {str(e)}")
            error_message = HumanMessage(
                content=f"플래닝 에이전트 실행 중 오류가 발생했습니다: {str(e)}",
                name="planning_agent"
            )
            
            error_state = dict(state)
            error_state["messages"] = error_state.get("messages", []) + [error_message]
            error_state["status"] = TaskStatus.failed
            error_state["next"] = "orchestrator"
            
            return Command(
                update=error_state,
                goto="orchestrator"
            )


# 플래닝 에이전트 인스턴스 생성
planning_agent = PlanningAgent()

# planning_node 함수는 PlanningAgent 인스턴스를 호출하는 래퍼 함수
async def planning_node(state: MessagesState) -> Command[Literal["orchestrator"]]:
    """
    플래닝 노드 함수입니다. PlanningAgent 인스턴스를 호출합니다.
    
    Args:
        state: 현재 메시지와 상태 정보
        
    Returns:
        오케스트레이터로 돌아가는 명령
    """
    return await planning_agent(state) 