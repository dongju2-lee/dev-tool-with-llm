"""
메인 애플리케이션 모듈

이 모듈은 FastAPI를 사용하여 챗봇 애플리케이션의 REST API를 정의합니다.
"""

import os
import asyncio
import time
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from graph import DevToolGraph
from utils.logger_config import setup_logger
from config import *

# 환경 변수 로드
load_dotenv()

# 로거 설정
logger = setup_logger("app", level=LOG_LEVEL)

# 그래프 인스턴스 생성
graph_instance = DevToolGraph()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 라이프사이클 관리
    """
    # 시작 시 실행
    logger.info("애플리케이션 시작")
    try:
        # 그래프 초기 구축
        await graph_instance.build()
        logger.info("그래프 초기화 완료")
    except Exception as e:
        logger.error(f"시작 이벤트 처리 중 오류 발생: {str(e)}")
    
    yield
    
    # 종료 시 실행
    logger.info("애플리케이션 종료")

# FastAPI 앱 생성
app = FastAPI(
    title="개발 도구 챗봇 API",
    description="다양한 개발 도구 에이전트를 통합한 다중 에이전트 챗봇 API",
    version="0.1.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 요청/응답 모델 정의
class ChatMessage(BaseModel):
    """채팅 메시지 모델"""
    role: str = Field(..., description="메시지 발신자의 역할 (user 또는 assistant)")
    content: str = Field(..., description="메시지 내용")
    name: Optional[str] = Field(None, description="메시지 발신자의 이름 (선택 사항)")
    
class ChatRequest(BaseModel):
    """채팅 요청 모델"""
    message: str = Field(..., description="사용자 입력 메시지")
    conversation_id: Optional[str] = Field(None, description="대화 ID (선택 사항)")
    
class ChatResponse(BaseModel):
    """채팅 응답 모델"""
    conversation_id: str = Field(..., description="대화 ID")
    messages: List[ChatMessage] = Field(default_factory=list, description="응답 메시지 목록")
    created_at: float = Field(..., description="응답 생성 시간 (유닉스 타임스탬프)")


@app.get("/")
async def root():
    """
    애플리케이션 상태를 확인하는 엔드포인트
    """
    return {"status": "online", "service": "dev-tool-chatbot"}


@app.get("/status")
async def status():
    """
    애플리케이션 상태 정보를 제공하는 엔드포인트
    """
    return {
        "status": "online",
        "service": "dev-tool-chatbot",
        "version": "0.1.0",
        "timestamp": time.time()
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    채팅 메시지를 처리하는 엔드포인트
    
    Args:
        request: 채팅 요청 객체
        
    Returns:
        채팅 응답 객체
    """
    try:
        logger.info(f"채팅 요청 수신: '{request.message[:50]}...'")
        start_time = time.time()
        
        # 그래프 호출
        responses = await graph_instance.invoke(request.message)
        
        # 응답 변환
        chat_messages = []
        for msg in responses:
            role = "assistant"
            if hasattr(msg, "name") and msg.name:
                name = msg.name
            else:
                name = None
                
            chat_messages.append(
                ChatMessage(
                    role=role,
                    content=msg.content,
                    name=name
                )
            )
        
        # 응답 생성
        conversation_id = request.conversation_id or f"conv_{int(time.time())}"
        response = ChatResponse(
            conversation_id=conversation_id,
            messages=chat_messages,
            created_at=time.time()
        )
        
        elapsed_time = time.time() - start_time
        logger.info(f"채팅 응답 생성 완료. 소요 시간: {elapsed_time:.2f}초")
        
        return response
        
    except Exception as e:
        logger.error(f"채팅 처리 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"채팅 처리 중 오류 발생: {str(e)}")


@app.post("/reset")
async def reset_conversation():
    """
    대화 상태를 재설정하는 엔드포인트
    """
    try:
        logger.info("대화 상태 재설정 요청")
        
        # 그래프 상태 재설정
        graph_instance.reset_state()
        
        return {"status": "success", "message": "대화 상태가 재설정되었습니다."}
        
    except Exception as e:
        logger.error(f"대화 상태 재설정 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"대화 상태 재설정 중 오류 발생: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    # Uvicorn 서버 시작 - 포트 8001로 변경
    port = int(os.environ.get("PORT", 8051))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=True
    ) 