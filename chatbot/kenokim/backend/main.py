from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import sys
import uuid
import asyncio
import logging
import traceback
from contextlib import asynccontextmanager
import uvicorn

# 환경 변수 및 로깅 설정
from dotenv import load_dotenv
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(current_dir))  # Add parent directory

# MCP 클라이언트 임포트
from mcp_client_agent import make_graph
from langchain_core.messages import HumanMessage

# 앱 초기화
app = FastAPI(title="슬라임 챗봇 API", description="Streamlit 챗봇을 위한 FastAPI 백엔드")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경에서는 모든 Origin 허용, 프로덕션에서는 제한 필요
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 요청 스키마 정의
class ChatRequest(BaseModel):
    query: str
    thread_id: str
    history: List[Dict[str, Any]]
    mcp_client_name: str = "mcp-server-test"
    mcp_server_url: str = "http://localhost:8000/sse"
    mcp_transport: str = "sse"
    timeout_seconds: int = 60

class ConnectionTestRequest(BaseModel):
    mcp_client_name: str = "mcp-server-test"
    mcp_server_url: str = "http://localhost:8000/sse"
    mcp_transport: str = "sse"

# 응답 스키마 정의
class ChatResponse(BaseModel):
    response: Any
    status: str

class ConnectionTestResponse(BaseModel):
    status: str
    message: str

# 대화 이력 저장소 (실제로는 데이터베이스를 사용할 것)
chat_histories = {}

@app.get("/")
async def read_root():
    return {"status": "healthy", "message": "슬라임 챗봇 API가 실행 중입니다."}

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """사용자 메시지에 대한 응답을 생성합니다."""
    try:
        # 응답 생성
        result = await get_mcp_response(
            request.query,
            request.history,
            request.mcp_client_name,
            request.mcp_server_url,
            request.mcp_transport,
            request.timeout_seconds
        )
        
        # 대화 이력 저장 (실제로는 데이터베이스에 저장)
        if request.thread_id not in chat_histories:
            chat_histories[request.thread_id] = []
            
        chat_histories[request.thread_id] = request.history
        
        return result
    except Exception as e:
        logger.error(f"채팅 처리 오류: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/connection_test", response_model=ConnectionTestResponse)
async def test_connection(request: ConnectionTestRequest):
    """MCP 서버 연결을 테스트합니다."""
    try:
        result = await connection_test(
            request.mcp_client_name,
            request.mcp_server_url,
            request.mcp_transport
        )
        
        if result:
            return ConnectionTestResponse(status="success", message=f"MCP 서버 연결 성공: {request.mcp_server_url}")
        else:
            return ConnectionTestResponse(status="error", message=f"MCP 서버 연결 실패: {request.mcp_server_url}")
    except Exception as e:
        logger.error(f"연결 테스트 오류: {str(e)}")
        logger.error(traceback.format_exc())
        return ConnectionTestResponse(status="error", message=f"연결 테스트 오류: {str(e)}")

async def connection_test(client_name, server_url, transport):
    """MCP 서버 연결을 테스트하는 함수"""
    try:
        async with make_graph(client_name, server_url, transport) as agent:
            return True
    except Exception as e:
        logger.error(f"MCP 서버 연결 오류: {str(e)}")
        logger.error(traceback.format_exc())
        return False

async def get_mcp_response(query, history, client_name, server_url, transport, timeout_seconds=60):
    """MCP 에이전트를 통해 응답을 생성하는 함수"""
    try:
        # make_graph 함수를 사용하여 에이전트 생성
        async with make_graph(client_name, server_url, transport) as agent:
            # 메시지 형식 변환
            messages = []
            for msg in history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
            
            # 현재 쿼리 추가
            messages.append(HumanMessage(content=query))
            
            # 에이전트 호출 (타임아웃 처리 추가)
            try:
                result = await asyncio.wait_for(
                    agent.ainvoke({"messages": messages}),
                    timeout=timeout_seconds
                )
                return {
                    "response": result,
                    "status": "success"
                }
            except asyncio.TimeoutError:
                return {
                    "response": f"요청 시간이 {timeout_seconds}초를 초과했습니다. 좀 더 간단한 질문을 해보세요.",
                    "status": "timeout"
                }
    except Exception as e:
        logger.error(f"MCP 응답 생성 오류: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "response": f"오류가 발생했습니다: {str(e)}",
            "status": "error"
        }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 