import os
import io
import requests
from PIL import Image
import base64
from langgraph.graph import StateGraph, START, END

from simple.supervisor_agent import supervisor_node, State
from simple.gemini_search_agent import gemini_search_node
from simple.mcp_agent import mcp_agent_node
from utils.logger_config import setup_logger
from config import *  # Import all constants and configuration values

# 로거 설정'
logger = setup_logger("dev_tool_graph", level=LOG_LEVEL)

# 싱글톤 인스턴스
_graph_instance = None


def get_dev_tool_graph():
    """개발 도구 그래프의 싱글톤 인스턴스를 반환합니다."""
    global _graph_instance
    if _graph_instance is None:
        logger.info("개발 도구 그래프 초기화 시작")
        
        # 그래프 빌더 생성
        builder = StateGraph(State)
        
        # 시작점에서 슈퍼바이저로 연결
        builder.add_edge(START, "supervisor")
        
        # 노드 추가 (제미나이서치와 MCP 에이전트만 사용)
        builder.add_node("supervisor", supervisor_node)
        builder.add_node("gemini_search_agent", gemini_search_node)
        builder.add_node("mcp_agent", mcp_agent_node)
        
        # 각 노드에서 슈퍼바이저로 돌아오는 엣지 추가
        builder.add_edge("gemini_search_agent", "supervisor")
        builder.add_edge("mcp_agent", "supervisor")
        
        # 슈퍼바이저에서 종료로 가는 엣지 추가
        # 그래프 컴파일
        _graph_instance = builder.compile()
        
        logger.info("개발 도구 그래프 초기화 완료")
        
    return _graph_instance


def get_mermaid_graph():
    """개발 도구 그래프의 Mermaid 다이어그램 이미지를 생성합니다."""
    try:
        logger.info("Mermaid 다이어그램 이미지 생성 시작")
        graph = get_dev_tool_graph()
        logger.info(graph.get_graph().draw_mermaid())
        # 타임아웃 없이 기본 호출
        return graph.get_graph().draw_mermaid_png()
    except Exception as e:
        # 오류 발생 시 로그만 남기고 예외 다시 발생시킴
        logger.error(f"Mermaid 다이어그램 생성 실패: {str(e)}")
        raise 