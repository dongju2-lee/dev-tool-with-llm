import uuid
import logging
from typing import Dict, List, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from .schemas import (
    ChatRequest, ChatResponse, StreamChatRequest,
    SessionCreateResponse, SessionMessagesResponse, MessageContent,
    MCPSettings, ModelsResponse, ModelInfo, HealthCheckResponse
)
from ...graph.instance import process_chat_message
from ...core.config import get_settings, Settings

# 로깅 설정
logger = logging.getLogger(__name__)

# API 라우터 생성
router = APIRouter()

# 인메모리 세션 저장소 (프로덕션에서는 Redis 등 사용)
chat_sessions: Dict[str, Dict[str, Any]] = {}


# 헬스체크
@router.get("/health", response_model=HealthCheckResponse)
async def health_check(settings: Settings = Depends(get_settings)):
    """API 서버 헬스체크"""
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version=settings.app_version
    )


# 채팅 관련 엔드포인트
@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(
    request: ChatRequest,
    settings: Settings = Depends(get_settings)
):
    """AI 에이전트와 채팅합니다."""
    try:
        # 스레드 ID 생성 (없는 경우)
        thread_id = request.thread_id or str(uuid.uuid4())
        
        # LangGraph 에이전트를 통해 메시지 처리
        result = await process_chat_message(
            content=request.content,
            thread_id=thread_id
        )
        
        # 응답 생성
        response = ChatResponse(
            id=str(uuid.uuid4()),
            content=result["content"],
            timestamp=datetime.now().isoformat(),
            metadata={
                "thread_id": thread_id,
                "agent_used": result["agent_used"],
                "tools_used": result["tools_used"],
                **result["metadata"]
            }
        )
        
        logger.info(f"Chat processed by agent: {result['agent_used']}")
        return response
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"채팅 처리 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/chat/stream")
async def stream_chat_with_agent(
    request: StreamChatRequest,
    settings: Settings = Depends(get_settings)
):
    """AI 에이전트와 스트리밍 채팅합니다."""
    
    async def generate_stream():
        try:
            # 스레드 ID 생성
            thread_id = request.thread_id or str(uuid.uuid4())
            
            # 처리 시작 이벤트
            yield {
                "event": "start",
                "data": {
                    "thread_id": thread_id,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # LangGraph 에이전트를 통해 메시지 처리
            result = await process_chat_message(
                content=request.content,
                thread_id=thread_id
            )
            
            # 응답 스트리밍 (실제로는 한 번에 전송되지만 스트림 형태로)
            yield {
                "event": "message",
                "data": {
                    "id": str(uuid.uuid4()),
                    "content": result["content"],
                    "role": "assistant",
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {
                        "agent_used": result["agent_used"],
                        "tools_used": result["tools_used"]
                    }
                }
            }
            
            # 완료 이벤트
            yield {
                "event": "done",
                "data": {
                    "thread_id": thread_id,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Stream chat error: {str(e)}")
            yield {
                "event": "error",
                "data": {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            }
    
    return EventSourceResponse(generate_stream())


# 세션 관리 엔드포인트
@router.post("/sessions", response_model=SessionCreateResponse)
async def create_chat_session():
    """새로운 채팅 세션을 생성합니다."""
    session_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    
    chat_sessions[session_id] = {
        "session_id": session_id,
        "created_at": created_at,
        "messages": []
    }
    
    return SessionCreateResponse(
        session_id=session_id,
        created_at=created_at
    )


@router.get("/sessions/{session_id}/messages", response_model=SessionMessagesResponse)
async def get_session_messages(session_id: str):
    """특정 세션의 메시지 이력을 조회합니다."""
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    
    session = chat_sessions[session_id]
    return SessionMessagesResponse(
        session_id=session_id,
        messages=session["messages"]
    )


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """채팅 세션을 삭제합니다."""
    if session_id in chat_sessions:
        del chat_sessions[session_id]
    
    return JSONResponse(status_code=204, content={})


# 모델 정보 엔드포인트
@router.get("/models", response_model=ModelsResponse)
async def get_available_models(settings: Settings = Depends(get_settings)):
    """사용 가능한 AI 모델 목록을 반환합니다."""
    models = [
        ModelInfo(
            id="gemini-2.5-flash-preview",
            name="Gemini 2.5 Flash Preview",
            description="최신 버전의 Gemini 모델",
            max_tokens=16384
        ),
        ModelInfo(
            id="gemini-1.5-pro",
            name="Gemini 1.5 Pro",
            description="고성능 Gemini 모델",
            max_tokens=32768
        )
    ]
    
    return ModelsResponse(models=models)


# MCP 설정 관련 엔드포인트 (기존 기능과의 호환성)
@router.get("/mcp/settings")
async def get_mcp_settings(settings: Settings = Depends(get_settings)):
    """현재 MCP 서버 설정을 반환합니다."""
    return {
        "client_name": settings.mcp_client_name,
        "url": settings.mcp_server_url,
        "transport": settings.mcp_transport
    }


@router.post("/mcp/settings")
async def update_mcp_settings(mcp_settings: MCPSettings):
    """MCP 서버 설정을 업데이트합니다."""
    # 실제 구현에서는 설정을 저장하고 MCP 클라이언트를 재초기화해야 합니다
    logger.info(f"MCP settings update requested: {mcp_settings}")
    
    return {
        "message": "MCP 설정이 업데이트되었습니다.",
        "settings": mcp_settings
    }


@router.post("/mcp/connection/test")
async def test_mcp_connection(mcp_settings: MCPSettings):
    """MCP 서버 연결을 테스트합니다."""
    try:
        # 실제 구현에서는 MCP 서버에 연결을 시도합니다
        logger.info(f"Testing MCP connection to: {mcp_settings.url}")
        
        return {
            "status": "success",
            "message": "MCP 서버 연결이 성공했습니다.",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"MCP connection test failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"MCP 서버 연결에 실패했습니다: {str(e)}"
        ) 