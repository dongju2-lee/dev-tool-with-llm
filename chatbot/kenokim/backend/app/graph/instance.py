import logging
from datetime import datetime
from typing import Dict, Any, Optional

from langchain_core.messages import HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .state import AgentState
from .agents.supervisor import create_supervisor_node
from ..core.config import settings

logger = logging.getLogger(__name__)

# 전역 그래프 인스턴스
_app_graph = None


class AgentGraphBuilder:
    """에이전트 그래프를 구성하는 클래스입니다."""
    
    def __init__(self):
        self.model = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=0.1
        )
        
    def _create_simple_agent(self, name: str, prompt: str):
        """간단한 텍스트 기반 에이전트를 생성합니다."""
        def agent_node(state: AgentState) -> AgentState:
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
                
                # 모델에 요청
                messages = [HumanMessage(content=prompt + "\n\n사용자 요청: " + current_input)]
                response = self.model.invoke(messages)
                
                # 응답 메시지 추가
                ai_message = AIMessage(content=response.content)
                state["messages"].append(ai_message)
                
                # 상태 업데이트
                state["current_agent"] = name
                state["next"] = "FINISH"
                state["is_finished"] = True
                state["metadata"]["agent_used"] = name
                
                return state
                
            except Exception as e:
                logger.error(f"Error in {name}: {str(e)}")
                
                # metadata 초기화 확인
                if "metadata" not in state:
                    state["metadata"] = {}
                
                error_message = AIMessage(
                    content=f"{name} 처리 중 오류가 발생했습니다: {str(e)}"
                )
                state["messages"].append(error_message)
                state["current_agent"] = name
                state["next"] = "FINISH"
                state["is_finished"] = True
                state["metadata"]["error"] = f"{name} error: {str(e)}"
                return state
        
        return agent_node
    
    def build(self):
        """StateGraph를 구성하고 반환합니다."""
        
        # 그래프 생성
        graph = StateGraph(AgentState)
        
        # 노드 추가
        supervisor_node = create_supervisor_node()
        graph.add_node("supervisor", supervisor_node)
        
        # 간단한 에이전트들 생성
        grafana_prompt = """당신은 Grafana 모니터링 시스템 전문 AI 어시스턴트입니다.
사용자의 Grafana 관련 질문에 대해 전문적이고 도움이 되는 답변을 제공하세요.
대시보드, 메트릭, 알람, 데이터 소스 등 Grafana의 모든 기능에 대해 안내할 수 있습니다."""

        grafana_renderer_prompt = """당신은 Grafana 대시보드 시각화 및 렌더링 전문 AI 어시스턴트입니다.
대시보드 이미지 생성, 차트 렌더링, 시각화 최적화 등에 대해 전문적인 조언을 제공하세요."""

        graph.add_node("grafana_agent", self._create_simple_agent("grafana_agent", grafana_prompt))
        graph.add_node("grafana_renderer_agent", self._create_simple_agent("grafana_renderer_agent", grafana_renderer_prompt))
        
        # 라우팅 함수
        def route_to_next(state: AgentState) -> str:
            """다음 노드를 결정하는 라우팅 함수"""
            next_node = state.get("next")
            if next_node == "FINISH" or state.get("is_finished", False):
                return END
            return next_node or END
        
        # 엣지 추가
        graph.add_edge(START, "supervisor")
        graph.add_conditional_edges(
            "supervisor",
            route_to_next,
            {
                "grafana_agent": "grafana_agent",
                "grafana_renderer_agent": "grafana_renderer_agent",
                END: END
            }
        )
        graph.add_edge("grafana_agent", END)
        graph.add_edge("grafana_renderer_agent", END)
        
        # 체크포인터 추가 (메모리 기능)
        checkpointer = MemorySaver()
        
        # 그래프 컴파일
        compiled_graph = graph.compile(checkpointer=checkpointer)
        
        logger.info("LangGraph compiled successfully with Supervisor pattern")
        return compiled_graph


async def get_app_graph():
    """앱 그래프를 가져옵니다 (싱글톤 패턴)."""
    global _app_graph
    if _app_graph is None:
        try:
            logger.info("LangGraph initialization started...")
            builder = AgentGraphBuilder()
            _app_graph = builder.build()
            logger.info("LangGraph initialization completed.")
        except Exception as e:
            logger.error(f"Failed to initialize LangGraph: {str(e)}")
            raise
    
    return _app_graph


async def process_chat_message(content: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
    """채팅 메시지를 처리합니다."""
    try:
        # 그래프 가져오기
        graph = await get_app_graph()
        
        # 상태 초기화 - 모든 필드를 명시적으로 설정
        initial_state: AgentState = {
            "messages": [HumanMessage(content=content)],
            "current_input": content,
            "next": None,
            "current_agent": None,
            "is_finished": False,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "thread_id": thread_id
            },
            "thread_id": thread_id
        }
        
        # 그래프 실행
        config = {"configurable": {"thread_id": thread_id}} if thread_id else {}
        result = await graph.ainvoke(initial_state, config)
        
        # 결과에서 마지막 AI 메시지 추출
        ai_messages = [msg for msg in result["messages"] if hasattr(msg, 'content') and msg.type == 'ai']
        final_response = ai_messages[-1].content if ai_messages else "응답을 생성하지 못했습니다."
        
        return {
            "content": final_response,
            "metadata": result.get("metadata", {}),
            "agent_used": result.get("current_agent", "unknown"),
            "tools_used": result.get("metadata", {}).get("used_tools", [])
        }
        
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        return {
            "content": f"메시지 처리 중 오류가 발생했습니다: {str(e)}",
            "metadata": {"error": str(e), "timestamp": datetime.now().isoformat()},
            "agent_used": "error",
            "tools_used": []
        }


async def stream_chat_message(content: str, thread_id: Optional[str] = None):
    """채팅 메시지를 스트림으로 처리합니다."""
    try:
        # 그래프 가져오기
        graph = await get_app_graph()
        
        # 상태 초기화
        initial_state: AgentState = {
            "messages": [HumanMessage(content=content)],
            "current_input": content,
            "next": None,
            "current_agent": None,
            "is_finished": False,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "thread_id": thread_id
            },
            "thread_id": thread_id
        }
        
        # 그래프 스트림 실행
        config = {"configurable": {"thread_id": thread_id}} if thread_id else {}
        
        async for chunk in graph.astream(initial_state, config):
            yield chunk
            
    except Exception as e:
        logger.error(f"Error streaming chat message: {str(e)}")
        yield {
            "error": {
                "content": f"스트림 처리 중 오류가 발생했습니다: {str(e)}",
                "metadata": {"error": str(e), "timestamp": datetime.now().isoformat()}
            }
        } 