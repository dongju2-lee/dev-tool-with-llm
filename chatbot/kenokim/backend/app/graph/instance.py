"""
LangGraph Instance Management Module

이 모듈은 LangGraph 기반 Grafana 모니터링 챗봇의 핵심 인스턴스 관리를 담당합니다.
- 그래프 초기화 및 관리
- 채팅 메시지 처리 (일반/스트리밍)
- 대화 히스토리 관리
- 이미지 데이터 처리 유틸리티
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
import base64
import uuid

from langchain_core.messages import HumanMessage, ToolMessage

from .agents.supervisor_agent import (
    get_supervisor_graph, 
    get_conversation_history, 
    clear_conversation_history, 
    list_active_conversations
)

logger = logging.getLogger(__name__)

# ============================================================================
# 1. 전역 상태 관리
# ============================================================================

# LangGraph 표준 패턴: 직접적인 그래프 관리
_app_graph = None


# ============================================================================
# 2. 유틸리티 함수들
# ============================================================================

def generate_thread_id() -> str:
    """새로운 thread_id를 생성합니다."""
    return str(uuid.uuid4())


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


# ============================================================================
# 3. 그래프 관리
# ============================================================================

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


# ============================================================================
# 4. 채팅 메시지 처리
# ============================================================================

async def process_chat_message(content: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
    """채팅 메시지를 처리합니다. (대화 저장 기능 포함)"""
    try:
        # thread_id가 없으면 새로 생성
        if not thread_id:
            thread_id = generate_thread_id()
            logger.info(f"Generated new thread_id: {thread_id}")
        
        # 그래프 가져오기
        graph = await get_app_graph()
        
        # 입력 메시지 생성 (LangGraph 표준 형식)
        input_data = {"messages": [HumanMessage(content=content)]}
        
        # 그래프 실행 (대화 저장을 위한 config 설정)
        config = {"configurable": {"thread_id": thread_id}}
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
            "tools_used": [],
            "thread_id": thread_id  # 클라이언트가 사용할 수 있도록 thread_id 반환
        }
        
        # 이미지 데이터가 있으면 별도로도 포함
        if image_data:
            result_data["image_data"] = image_data
        
        logger.info(f"Message processed successfully for thread {thread_id}")
        return result_data
        
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        return {
            "content": f"메시지 처리 중 오류가 발생했습니다: {str(e)}",
            "metadata": {"error": str(e), "timestamp": datetime.now().isoformat()},
            "agent_used": "error",
            "tools_used": [],
            "thread_id": thread_id
        }


async def stream_chat_message(content: str, thread_id: Optional[str] = None):
    """채팅 메시지를 스트림으로 처리합니다. (대화 저장 기능 포함)"""
    try:
        # thread_id가 없으면 새로 생성
        if not thread_id:
            thread_id = generate_thread_id()
            logger.info(f"Generated new thread_id for streaming: {thread_id}")
        
        # 그래프 가져오기
        graph = await get_app_graph()
        
        # 입력 메시지 생성 (LangGraph 표준 형식)
        input_data = {"messages": [HumanMessage(content=content)]}
        
        # 그래프 스트림 실행 (대화 저장을 위한 config 설정)
        config = {"configurable": {"thread_id": thread_id}}
        
        # thread_id를 첫 번째 청크로 전송
        yield {"thread_id": thread_id, "type": "thread_info"}
        
        async for chunk in graph.astream(input_data, config):
            yield chunk
            
    except Exception as e:
        logger.error(f"Error streaming chat message: {str(e)}")
        yield {
            "error": {
                "content": f"스트림 처리 중 오류가 발생했습니다: {str(e)}",
                "metadata": {"error": str(e), "timestamp": datetime.now().isoformat()},
                "thread_id": thread_id
            }
        }


# ============================================================================
# 5. 대화 히스토리 관리
# ============================================================================

async def get_thread_history(thread_id: str) -> Dict[str, Any]:
    """특정 thread의 대화 히스토리를 조회합니다."""
    try:
        messages = get_conversation_history(thread_id)
        
        # 메시지를 사용자 친화적 형태로 변환
        formatted_messages = []
        for msg in messages:
            if hasattr(msg, 'type') and hasattr(msg, 'content'):
                formatted_messages.append({
                    "type": msg.type,
                    "content": msg.content,
                    "timestamp": getattr(msg, 'timestamp', None)
                })
        
        return {
            "thread_id": thread_id,
            "message_count": len(formatted_messages),
            "messages": formatted_messages,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error retrieving thread history: {str(e)}")
        return {
            "thread_id": thread_id,
            "error": str(e),
            "message_count": 0,
            "messages": []
        }


async def delete_thread_history(thread_id: str) -> Dict[str, Any]:
    """특정 thread의 대화 히스토리를 삭제합니다."""
    try:
        success = clear_conversation_history(thread_id)
        
        return {
            "thread_id": thread_id,
            "deleted": success,
            "message": "대화 히스토리가 성공적으로 삭제되었습니다." if success else "삭제할 대화 히스토리를 찾을 수 없습니다.",
            "deleted_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error deleting thread history: {str(e)}")
        return {
            "thread_id": thread_id,
            "deleted": False,
            "error": str(e),
            "message": "대화 히스토리 삭제 중 오류가 발생했습니다."
        }


async def list_all_conversations() -> Dict[str, Any]:
    """모든 활성 대화 목록을 조회합니다."""
    try:
        thread_ids = list_active_conversations()
        
        # 각 thread의 기본 정보 수집
        conversations = []
        for thread_id in thread_ids:
            messages = get_conversation_history(thread_id)
            if messages:
                first_message = messages[0] if messages else None
                last_message = messages[-1] if messages else None
                
                conversations.append({
                    "thread_id": thread_id,
                    "message_count": len(messages),
                    "first_message_preview": first_message.content[:100] + "..." if first_message and hasattr(first_message, 'content') and len(first_message.content) > 100 else (first_message.content if first_message and hasattr(first_message, 'content') else ""),
                    "last_message_preview": last_message.content[:100] + "..." if last_message and hasattr(last_message, 'content') and len(last_message.content) > 100 else (last_message.content if last_message and hasattr(last_message, 'content') else "")
                })
        
        return {
            "total_conversations": len(conversations),
            "conversations": conversations,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error listing conversations: {str(e)}")
        return {
            "total_conversations": 0,
            "conversations": [],
            "error": str(e)
        } 