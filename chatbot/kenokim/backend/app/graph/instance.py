import logging
from datetime import datetime
from typing import Dict, Any, Optional

from langchain_core.messages import HumanMessage

from .agents.enhanced_supervisor import get_enhanced_supervisor_graph

logger = logging.getLogger(__name__)

# LangGraph 표준 패턴: 직접적인 그래프 관리
_app_graph = None



async def get_app_graph():
    """LangGraph 표준 패턴: 컴파일된 그래프를 가져옵니다."""
    global _app_graph
    if _app_graph is None:
        try:
            logger.info("Enhanced LangGraph initialization started...")
            _app_graph = await get_enhanced_supervisor_graph()
            logger.info("Enhanced LangGraph initialization completed.")
        except Exception as e:
            logger.error(f"Failed to initialize Enhanced LangGraph: {str(e)}")
            raise
    return _app_graph


async def process_chat_message(content: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
    """채팅 메시지를 처리합니다."""
    try:
        # 그래프 가져오기
        graph = await get_app_graph()
        
        # 입력 메시지 생성 (LangGraph 표준 형식)
        input_data = {"messages": [HumanMessage(content=content)]}
        
        # 그래프 실행 (LangGraph 표준 방식)
        config = {"configurable": {"thread_id": thread_id}} if thread_id else {}
        result = await graph.ainvoke(input_data, config)
        
        # LangGraph 결과를 그대로 사용 - 마지막 메시지가 최종 응답
        print(result)
        messages = result.get("messages", [])
        if messages:
            last_message = messages[-1]
            response_content = last_message.content if hasattr(last_message, 'content') else "응답을 처리하지 못했습니다."
        else:
            response_content = "응답을 생성하지 못했습니다."
        
        return {
            "content": response_content,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "thread_id": thread_id
            },
            "agent_used": "supervisor",
            "tools_used": []
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
        
        # 입력 메시지 생성 (LangGraph 표준 형식)
        input_data = {"messages": [HumanMessage(content=content)]}
        
        # 그래프 스트림 실행 (LangGraph 표준 방식)
        config = {"configurable": {"thread_id": thread_id}} if thread_id else {}
        
        async for chunk in graph.astream(input_data, config):
            yield chunk
            
    except Exception as e:
        logger.error(f"Error streaming chat message: {str(e)}")
        yield {
            "error": {
                "content": f"스트림 처리 중 오류가 발생했습니다: {str(e)}",
                "metadata": {"error": str(e), "timestamp": datetime.now().isoformat()}
            }
        } 