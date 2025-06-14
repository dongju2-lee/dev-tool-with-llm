import logging
from datetime import datetime
from typing import Dict, Any, Optional
import base64

from langchain_core.messages import HumanMessage, ToolMessage

from .agents.supervisor import get_supervisor_graph

logger = logging.getLogger(__name__)

# LangGraph 표준 패턴: 직접적인 그래프 관리
_app_graph = None


def _extract_image_data(messages) -> Optional[str]:
    """메시지에서 Base64 이미지 데이터를 추출합니다."""
    try:
        for message in messages:
            if hasattr(message, 'content') and isinstance(message, ToolMessage):
                content = message.content
                if isinstance(content, str) and content.startswith('iVBORw0KGgo'):
                    # PNG Base64 데이터인지 확인
                    try:
                        decoded = base64.b64decode(content[:100])
                        if decoded.startswith(b'\x89PNG'):
                            # 유효한 PNG 이미지 데이터를 data URL 형태로 반환
                            return f"data:image/png;base64,{content}"
                    except Exception:
                        pass
        return None
    except Exception as e:
        logger.error(f"Error extracting image data: {str(e)}")
        return None


def _process_final_response(content: str, image_data: Optional[str]) -> str:
    """최종 응답을 처리하여 이미지 데이터를 포함시킵니다."""
    if image_data and "[렌더링된 이미지 데이터]" in content:
        # 플레이스홀더를 실제 이미지 데이터로 교체
        return content.replace("[렌더링된 이미지 데이터]", f"![Dashboard Image]({image_data})")
    return content


async def get_app_graph():
    """LangGraph 표준 패턴: 컴파일된 그래프를 가져옵니다."""
    global _app_graph
    if _app_graph is None:
        try:
            logger.info("LangGraph initialization started...")
            _app_graph = await get_supervisor_graph()
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
        
        # 입력 메시지 생성 (LangGraph 표준 형식)
        input_data = {"messages": [HumanMessage(content=content)]}
        
        # 그래프 실행 (LangGraph 표준 방식)
        config = {"configurable": {"thread_id": thread_id}} if thread_id else {}
        result = await graph.ainvoke(input_data, config)
        
        # 메시지에서 이미지 데이터 추출
        messages = result.get("messages", [])
        image_data = _extract_image_data(messages)
        
        # 최종 응답 처리
        if messages:
            last_message = messages[-1]
            response_content = last_message.content if hasattr(last_message, 'content') else "응답을 처리하지 못했습니다."
            
            # 이미지 데이터가 있으면 응답에 포함
            response_content = _process_final_response(response_content, image_data)
        else:
            response_content = "응답을 생성하지 못했습니다."
        
        result_data = {
            "content": response_content,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "thread_id": thread_id,
                "original_response": result
            },
            "agent_used": "supervisor",
            "tools_used": []
        }
        
        # 이미지 데이터가 있으면 별도로도 포함
        if image_data:
            result_data["image_data"] = image_data
        
        return result_data
        
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