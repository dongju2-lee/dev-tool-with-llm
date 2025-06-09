from typing import List, Literal
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field

from ..state import AgentState
from ...core.config import settings


class RouteQuery(BaseModel):
    """라우팅 결정을 위한 스키마"""
    next: Literal["grafana_agent", "grafana_renderer_mcp_agent", "FINISH"] = Field(
        description="다음에 호출할 에이전트를 선택합니다"
    )
    reasoning: str = Field(
        description="선택한 에이전트의 이유를 설명합니다"
    )


def create_supervisor_node():
    """Supervisor 노드를 생성합니다."""
    
    # Gemini 모델 초기화
    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.1
    )
    
    # 구조화된 출력을 위해 Pydantic 모델 바인딩
    structured_llm = llm.with_structured_output(RouteQuery)
    
    # Supervisor 프롬프트 템플릿
    system_prompt = """당신은 Grafana 모니터링 시스템 전문 AI 어시스턴트의 Supervisor입니다.
사용자의 요청을 분석하여 가장 적절한 Grafana 전문 에이전트에게 작업을 위임해야 합니다.

사용 가능한 에이전트:
1. **grafana_agent**: 
   - Grafana 대시보드 데이터 조회 및 분석
   - 메트릭 쿼리 및 데이터 분석
   - 알람 설정 및 모니터링 데이터 확인
   - 시스템 상태 및 성능 데이터 분석
   - 대시보드 설정 및 관리

2. **grafana_renderer_mcp_agent**: 
   - Grafana 대시보드 시각화 및 렌더링
   - 차트, 그래프 이미지 생성
   - 대시보드 스크린샷 및 리포트 생성
   - 시각적 모니터링 자료 제작

3. **FINISH**: 
   - 작업이 완료되었거나 더 이상 처리할 내용이 없을 때

**에이전트 선택 가이드:**
- 사용자가 데이터 조회, 분석, 설정을 원한다면 → grafana_agent
- 사용자가 차트, 이미지, 시각화를 원한다면 → grafana_renderer_mcp_agent
- Grafana 관련이 아닌 요청은 적절히 안내 후 → FINISH

사용자의 요청을 신중히 분석하고, 가장 적절한 에이전트를 선택하세요.
선택 이유도 함께 제공해야 합니다."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        ("human", "위 대화를 바탕으로 다음에 호출할 에이전트를 선택하세요: {current_input}")
    ])
    
    # Supervisor 체인 생성
    supervisor_chain = prompt | structured_llm
    
    def supervisor_node(state: AgentState) -> AgentState:
        """Supervisor 노드 실행 함수"""
        try:
            # metadata 초기화 확인
            if "metadata" not in state:
                state["metadata"] = {}
            
            # current_input 확인 및 설정
            current_input = state.get("current_input", "")
            if not current_input and "messages" in state and state["messages"]:
                # messages에서 마지막 사용자 메시지 추출
                last_human_msg = None
                for msg in reversed(state["messages"]):
                    if hasattr(msg, 'type') and msg.type == 'human':
                        last_human_msg = msg
                        break
                current_input = last_human_msg.content if last_human_msg else "안녕하세요"
            
            # LLM을 통해 라우팅 결정
            result = supervisor_chain.invoke({
                "messages": state["messages"],
                "current_input": current_input
            })
            
            # 상태 업데이트
            state["next"] = result.next
            state["current_agent"] = "supervisor"
            state["metadata"]["supervisor_reasoning"] = result.reasoning
            
            # FINISH가 선택되면 직접 응답 생성
            if result.next == "FINISH":
                state["is_finished"] = True
                
                # 직접 응답 메시지 생성
                from langchain_core.messages import AIMessage
                finish_response = AIMessage(
                    content=f"안녕하세요! 저는 LangGraph AI 어시스턴트입니다.\n\n{result.reasoning}\n\n구체적인 질문이나 요청사항이 있으시면 언제든 말씀해 주세요. 다양한 주제에 대해 도움을 드릴 수 있습니다."
                )
                state["messages"].append(finish_response)
            
            return state
            
        except Exception as e:
            # 에러 발생 시 metadata 초기화 확인
            if "metadata" not in state:
                state["metadata"] = {}
                
            # 에러 발생 시 기본값으로 FINISH 선택
            state["next"] = "FINISH"
            state["current_agent"] = "supervisor"
            state["is_finished"] = True
            state["metadata"]["error"] = f"Supervisor error: {str(e)}"
            
            # 에러 시에도 응답 메시지 생성
            from langchain_core.messages import AIMessage
            error_response = AIMessage(
                content=f"죄송합니다. 처리 중 오류가 발생했습니다: {str(e)}\n\n다시 시도해 주시거나 다른 질문을 해주세요."
            )
            state["messages"].append(error_response)
            
            return state
    
    return supervisor_node 