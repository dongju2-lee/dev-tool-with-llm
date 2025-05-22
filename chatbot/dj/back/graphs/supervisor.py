import logging
import traceback
from langgraph.graph import StateGraph, END, START
from schema.state import DevToolState
from agents.general_agent import get_general_agent
from agents.research_agent import get_research_agent

logger = logging.getLogger("supervisor")
logging.basicConfig(level=logging.INFO)


def router_node(state: DevToolState):
    agent_mode = state.get("agent_mode", "general")
    
    if agent_mode == "general":
        logger.info("일반 에이전트 모드로 라우팅합니다.")
        return {"next": "general"}
    if agent_mode == "research":
        logger.info("장애 분석 에이전트 모드로 라우팅합니다.")
        return {"next": "research"}
    else:
        logger.info(f"알 수 없는 모드 '{agent_mode}'. 일반 모드로 라우팅합니다.")
        return {"next": "general"}

def update(state: DevToolState):
    state["agent_mode"] = "research"
    return state

async def general_node(state: DevToolState):
    logger.info("일반 에이전트 실행 중...")
    try:
        agent = await get_general_agent()
        result = await agent.ainvoke(state)
        logger.info(f"일반 에이전트 실행 완료 result : {result}")
        result = update(result)
        logger.info(f"일반 에이전트 실행 완료 state : {result}")
        return result
    except Exception as e:
        logger.error(f"일반 에이전트 실행 중 오류 발생: {str(e)}")
        logger.error(traceback.format_exc())
        # 에러 발생시 기본 응답 반환
        return {"output": f"죄송합니다. 처리 중 오류가 발생했습니다: {str(e)}"}


async def research_node(state: DevToolState):
    logger.info("장애 분석 에이전트 실행 중...")
    query = state.get("input", "")
    logger.info(f"장애 분석 쿼리: {query[:100]}..." if len(query) > 100 else f"장애 분석 쿼리: {query}")
    
    try:
        # 상태 로깅
        logger.info(f"State 구조: {list(state.keys())}")
        for key, value in state.items():
            logger.info(f"State[{key}] 타입: {type(value).__name__}")
        
        agent = await get_research_agent()
        logger.info("연구 에이전트 가져오기 성공")
        
        # invoke 전 상태 확인
        logger.info(f"Agent 타입: {type(agent).__name__}")
        logger.info("에이전트 호출 시작...")
        
        result = await agent.ainvoke(state)
        
        logger.info("장애 분석 완료. 분석 결과 반환.")
        return result
    except Exception as e:
        error_detail = traceback.format_exc()
        logger.error(f"장애 분석 에이전트 실행 중 오류 발생: {str(e)}")
        logger.error(error_detail)
        
        # 에러 발생시 기본 응답 반환
        return {
            "output": f"장애 분석 중 오류가 발생했습니다. 자세한 내용은 로그를 확인해주세요.\n오류: {str(e)}"
        }

def build_supervisor_graph():
    logger.info("슈퍼바이저 그래프 빌드 시작")
    try:
        sg = StateGraph(DevToolState)
        sg.add_node("router", router_node)
        sg.add_node("general", general_node)
        sg.add_node("research", research_node)

        sg.add_edge(START, "router")

        sg.add_conditional_edges(
            "router",
            lambda state: state.get("agent_mode", "general"),
            {
                "research": "research",
                "general": "general",
            },
        )

        sg.add_edge("research", END)
        sg.add_edge("general", END)
        
        logger.info("슈퍼바이저 그래프 빌드 완료")
        return sg
    except Exception as e:
        logger.error(f"슈퍼바이저 그래프 빌드 중 오류: {str(e)}")
        logger.error(traceback.format_exc())
        raise