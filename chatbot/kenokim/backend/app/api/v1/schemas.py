from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class MessageContent(BaseModel):
    """메시지 내용 모델"""
    content: str = Field(..., description="메시지 내용")
    role: str = Field(default="user", description="메시지 역할 (user, assistant)")
    type: str = Field(default="text", description="메시지 타입")
    timestamp: Optional[str] = Field(default=None, description="메시지 생성 시간")
    id: Optional[str] = Field(default=None, description="메시지 고유 ID")


class ChatRequest(BaseModel):
    """채팅 요청 스키마"""
    content: str = Field(..., description="사용자 메시지 내용")
    thread_id: Optional[str] = Field(default=None, description="대화 스레드 ID")
    model_settings: Optional[Dict[str, Any]] = Field(
        default={"model": "gemini-2.5-flash-preview", "timeout_seconds": 60},
        description="모델 설정"
    )


class ChatResponse(BaseModel):
    """채팅 응답 스키마"""
    id: str = Field(..., description="메시지 고유 ID")
    role: str = Field(default="assistant", description="응답 역할")
    content: str = Field(..., description="응답 내용")
    type: str = Field(default="text", description="응답 타입")
    timestamp: str = Field(..., description="응답 생성 시간")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="추가 메타데이터")


class StreamChatRequest(BaseModel):
    """스트리밍 채팅 요청 스키마"""
    content: str = Field(..., description="사용자 메시지 내용")
    thread_id: Optional[str] = Field(default=None, description="대화 스레드 ID")
    model_settings: Optional[Dict[str, Any]] = Field(
        default={"model": "gemini-2.5-flash-preview", "timeout_seconds": 60},
        description="모델 설정"
    )


class SessionCreateResponse(BaseModel):
    """세션 생성 응답 스키마"""
    session_id: str = Field(..., description="생성된 세션 ID")
    created_at: str = Field(..., description="세션 생성 시간")


class SessionMessagesResponse(BaseModel):
    """세션 메시지 조회 응답 스키마"""
    session_id: str = Field(..., description="세션 ID")
    messages: List[MessageContent] = Field(..., description="메시지 목록")


class MCPSettings(BaseModel):
    """MCP 서버 설정 스키마"""
    client_name: str = Field(..., description="MCP 클라이언트 이름")
    url: str = Field(..., description="MCP 서버 URL")
    transport: str = Field(default="sse", description="전송 방식")


class ModelInfo(BaseModel):
    """모델 정보 스키마"""
    id: str = Field(..., description="모델 ID")
    name: str = Field(..., description="모델 이름")
    description: str = Field(..., description="모델 설명")
    max_tokens: int = Field(..., description="최대 토큰 수")


class ModelsResponse(BaseModel):
    """모델 목록 응답 스키마"""
    models: List[ModelInfo] = Field(..., description="사용 가능한 모델 목록")


class HealthCheckResponse(BaseModel):
    """헬스체크 응답 스키마"""
    status: str = Field(..., description="서비스 상태")
    timestamp: str = Field(..., description="체크 시간")
    version: str = Field(..., description="API 버전") 