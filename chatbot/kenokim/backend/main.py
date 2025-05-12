import os
import uuid
import json
import asyncio
import logging
import traceback
from typing import Dict, List, Any
from datetime import datetime
from pydantic import BaseModel

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

import uvicorn
from dotenv import load_dotenv

# mcp_client_agent 모듈 가져오기
from mcp_client_agent import make_graph
from langchain_core.messages import HumanMessage

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MCP 클라이언트 설정을 위한 변수 초기화
MCP_SETTINGS = {
    "client_name": os.getenv("MCP_CLIENT_NAME", "mcp-server-test"),
    "url": os.getenv("MCP_SERVER_URL", "http://localhost:8000/sse"),
    "transport": os.getenv("MCP_TRANSPORT", "sse")
}

# Google API 키 설정
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", os.getenv("GEMINI_API_KEY", ""))

# 사용 가능한 모델 목록
AVAILABLE_MODELS = [
    {
        "id": "gemini-2.5-flash-preview-04-17",
        "name": "Gemini 2.5 Flash Preview",
        "description": "최신 버전의 Gemini 모델",
        "max_tokens": 16384
    }
]

# 클래스 정의: 세션 관리
class ChatSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now().isoformat()
        self.messages = []
        
    def add_message(self, message: Dict):
        """메시지를 세션에 추가합니다."""
        if "id" not in message:
            message["id"] = str(uuid.uuid4())
        if "timestamp" not in message:
            message["timestamp"] = datetime.now().isoformat()
        self.messages.append(message)
        return message
    
    def to_dict(self):
        """세션을 딕셔너리로 변환합니다."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "messages": self.messages
        }

# 인메모리 세션 저장소
chat_sessions = {}

# 모델 정의: 요청 및 응답 스키마
class MessageRequest(BaseModel):
    content: str
    model_config: Dict[str, Any] = {"model": "gemini-2.5-flash-preview-04-17", "timeout_seconds": 60}

class MCPSettings(BaseModel):
    client_name: str
    url: str
    transport: str = "sse"

# FastAPI 앱 생성
app = FastAPI(title="채팅 백엔드 API", 
              description="Streamlit 채팅 프론트엔드를 위한 백엔드 API",
              version="1.0.0")

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 출처 허용 (프로덕션에서는 구체적인 출처로 제한해야 함)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {"message": "챗봇 백엔드 API에 오신 것을 환영합니다."}

## 채팅 세션 API ##

@app.post("/api/chat/sessions")
async def create_chat_session():
    """새로운 채팅 세션을 생성합니다."""
    session_id = str(uuid.uuid4())
    chat_sessions[session_id] = ChatSession(session_id)
    return {
        "session_id": session_id,
        "created_at": chat_sessions[session_id].created_at
    }

@app.get("/api/chat/sessions/{session_id}/messages")
async def get_chat_messages(session_id: str):
    """특정 세션의 메시지 이력을 조회합니다."""
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    
    return {
        "session_id": session_id,
        "messages": chat_sessions[session_id].messages
    }

@app.delete("/api/chat/sessions/{session_id}")
async def delete_chat_session(session_id: str):
    """채팅 세션을 삭제합니다."""
    if session_id in chat_sessions:
        del chat_sessions[session_id]
    return JSONResponse(status_code=204, content={})

@app.post("/api/chat/sessions/{session_id}/messages")
async def send_message(session_id: str, message_request: MessageRequest):
    """메시지를 전송하고 응답을 받습니다."""
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    
    # 사용자 메시지 저장
    session = chat_sessions[session_id]
    user_message = {
        "role": "user",
        "type": "text",
        "content": message_request.content
    }
    session.add_message(user_message)
    
    try:
        # MCP 서버에 메시지 전송
        response = await call_mcp_server(
            message_request.content, 
            session.messages, 
            message_request.model_config
        )
        logger.info(f"MCP 서버 result 응답: {response}")
        
        # 응답 처리 및 저장
        processed_response = process_mcp_response(response)
        
        return processed_response
            
    except Exception as e:
        logger.error(f"메시지 처리 중 오류 발생: {str(e)}")
        logger.error(traceback.format_exc())
        error_message = {
            "role": "assistant",
            "type": "text",
            "content": f"죄송합니다. 응답을 생성하는 중 오류가 발생했습니다: {str(e)}"
        }
        session.add_message(error_message)
        return error_message

@app.post("/api/chat/sessions/{session_id}/messages/stream")
async def stream_message(session_id: str, message_request: MessageRequest):
    """메시지를 전송하고 응답을 스트리밍 방식으로 받습니다."""
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    
    # 사용자 메시지 저장
    session = chat_sessions[session_id]
    user_message = {
        "role": "user",
        "type": "text", 
        "content": message_request.content
    }
    session.add_message(user_message)
    
    return EventSourceResponse(stream_mcp_response(session_id, message_request))

async def stream_mcp_response(session_id: str, message_request: MessageRequest):
    """MCP 서버 응답을 스트리밍합니다."""
    session = chat_sessions[session_id]
    current_text = ""
    
    # 처리 시작 이벤트
    yield {
        "event": "thinking",
        "data": json.dumps({"status": "processing"})
    }
    
    try:
        # MCP 서버와 통신
        response = await call_mcp_server(
            message_request.content, 
            session.messages, 
            message_request.model_config
        )
        
        # 응답 처리
        processed_response = process_mcp_response(response)
        
        # 응답 시작 이벤트
        yield {
            "event": "message_start",
            "data": json.dumps({"status": "start"})
        }
        
        # 응답 타입에 따른 처리
        if isinstance(processed_response, list):
            for item in processed_response:
                if item["type"] == "text":
                    # 텍스트 메시지 스트리밍 (단어 단위)
                    words = item["content"].split()
                    for word in words:
                        current_text += word + " "
                        await asyncio.sleep(0.05)  # 의도적 지연
                        yield {
                            "event": "message_text",
                            "data": json.dumps({"text": word + " "})
                        }
                    
                    # 텍스트 메시지 저장
                    item["role"] = "assistant"
                    session.add_message(item)
                
                elif item["type"] == "image":
                    # 이미지 메시지 이벤트
                    yield {
                        "event": "message_image",
                        "data": json.dumps({
                            "data": item["content"],
                            "caption": item.get("caption", "")
                        })
                    }
                    
                    # 이미지 메시지 저장
                    item["role"] = "assistant"
                    session.add_message(item)
        else:
            if processed_response["type"] == "text":
                # 텍스트 메시지 스트리밍 (단어 단위)
                words = processed_response["content"].split()
                for word in words:
                    current_text += word + " "
                    await asyncio.sleep(0.05)  # 의도적 지연
                    yield {
                        "event": "message_text",
                        "data": json.dumps({"text": word + " "})
                    }
                
                # 텍스트 메시지 저장
                processed_response["role"] = "assistant"
                session.add_message(processed_response)
            
            elif processed_response["type"] == "image":
                # 이미지 메시지 이벤트
                yield {
                    "event": "message_image",
                    "data": json.dumps({
                        "data": processed_response["content"],
                        "caption": processed_response.get("caption", "")
                    })
                }
                
                # 이미지 메시지 저장
                processed_response["role"] = "assistant"
                session.add_message(processed_response)
        
        # 메시지 종료 이벤트
        yield {
            "event": "message_end",
            "data": json.dumps({"status": "complete"})
        }
        
    except asyncio.TimeoutError:
        # 타임아웃 처리
        timeout_seconds = message_request.model_config.get("timeout_seconds", 60)
        yield {
            "event": "timeout",
            "data": json.dumps({
                "message": f"응답 생성 시간이 {timeout_seconds}초를 초과했습니다."
            })
        }
        
        # 채팅 세션에 메시지 저장
        session.add_message({
            "role": "assistant",
            "type": "text",
            "content": f"응답 생성 시간이 {timeout_seconds}초를 초과했습니다."
        })
        
    except Exception as e:
        # 오류 처리
        logger.error(f"스트리밍 응답 생성 중 오류: {str(e)}")
        logger.error(traceback.format_exc())
        yield {
            "event": "error",
            "data": json.dumps({
                "message": f"오류가 발생했습니다: {str(e)}"
            })
        }
        
        # 채팅 세션에 메시지 저장
        session.add_message({
            "role": "assistant",
            "type": "text",
            "content": f"오류가 발생했습니다: {str(e)}"
        })

async def call_mcp_server(content: str, history: List[Dict], model_config: Dict):
    """MCP 서버에 요청을 보내고 응답을 받습니다."""
    logger.info(f"MCP 서버 호출: content={content[:30]}..., model_config={model_config}")
    
    # 설정 가져오기
    client_name = MCP_SETTINGS.get("client_name", "mcp-server-test")
    url = MCP_SETTINGS.get("url", "http://localhost:8000/sse")
    transport = MCP_SETTINGS.get("transport", "sse")
    timeout_seconds = model_config.get("timeout_seconds", 60)
    model_name = model_config.get("model", "gemini-2.0-flash")
    
    # 이력에서 사용자 메시지만 추출
    user_messages = []
    for msg in history:
        if msg["role"] == "user" and msg.get("type", "text") == "text":
            user_messages.append(HumanMessage(content=msg["content"]))
    
    try:
        # mcp_client_agent에서 가져온 make_graph 함수를 사용하여 에이전트 생성
        async with make_graph(client_name, url, transport) as agent:
            # 마지막 메시지 제외 (이미 추가됨)
            messages = user_messages[:-1] if user_messages else []
            
            # 현재 쿼리 추가
            messages.append(HumanMessage(content=content))
            
            # 에이전트 호출 (타임아웃 처리)
            try:
                result = await asyncio.wait_for(
                    agent.ainvoke({"messages": messages}),
                    timeout=timeout_seconds
                )
                # LangGraph ReAct 에이전트 응답 로깅
                try:
                    # AddableValuesDict나 다른 형태의 결과 처리
                    if hasattr(result, "get") and callable(result.get) and result.get("messages"):
                        # 메시지 리스트에서 AIMessage 타입 찾기
                        for msg in result.get("messages"):
                            if hasattr(msg, "__class__") and msg.__class__.__name__ == "AIMessage":
                                if hasattr(msg, "content"):
                                    logger.info(f"AI 응답 내용: {str(msg.content)}")
                                if hasattr(msg, "tool_calls") and msg.tool_calls:
                                    logger.info(f"도구 호출: {str(msg.tool_calls)}")
                    elif isinstance(result, str):
                        logger.info(f"문자열 응답: {result[:200]}")
                    else:
                        logger.info(f"응답 타입: {type(result)}")
                except Exception as e:
                    logger.info(f"응답 로깅 실패: {str(e)}")
                return result
            except asyncio.TimeoutError:
                return f"요청 시간이 {timeout_seconds}초를 초과했습니다. 좀 더 간단한 질문을 해보세요."
    
    except Exception as e:
        logger.error(f"MCP 서버 호출 오류: {str(e)}")
        logger.error(traceback.format_exc())
        return f"MCP 서버 호출 중 오류가 발생했습니다: {str(e)}"

def process_mcp_response(response):
    """MCP 서버의 응답을 처리합니다."""
    logger.info(f"MCP 응답 처리: {type(response)}")
    
    # 문자열 응답 처리
    if isinstance(response, str):
        # 여러 줄의 응답을 별도 메시지로 분리
        sections = response.split("\n\n")
        if len(sections) > 1:
            return [{"type": "text", "content": section.strip()} for section in sections if section.strip()]
        return {
            "type": "text",
            "content": response
        }
    
    # 이미지 응답 처리
    if isinstance(response, dict) and "type" in response and response["type"] == "image":
        return {
            "type": "image",
            "content": response["content"],
            "caption": response.get("caption", "")
        }
    
    # LangGraph ReAct 에이전트 응답 처리
    results = []
    
    # AddableValuesDict 또는 일반 Dict 처리
    if hasattr(response, "get") and callable(response.get):
        # AIMessage가 포함된 메시지 배열 처리
        if response.get("messages"):
            for msg in response.get("messages"):
                # AIMessage 객체 처리
                if hasattr(msg, "__class__") and msg.__class__.__name__ == "AIMessage":
                    # 메시지 내용 추출
                    if hasattr(msg, "content") and msg.content:
                        # 내용에서 여러 단락을 별도 메시지로 분리
                        content_str = str(msg.content)
                        paragraphs = [p.strip() for p in content_str.split("\n\n") if p.strip()]
                        
                        for paragraph in paragraphs:
                            results.append({
                                "type": "text",
                                "content": paragraph
                            })
                    
                    # 도구 호출 결과 처리
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            # 이미지 도구 결과 처리
                            if "content_type" in tool_call.get("args", {}) and "image" in tool_call["args"]["content_type"]:
                                if "data" in tool_call["args"]:
                                    results.append({
                                        "type": "image",
                                        "content": tool_call["args"]["data"],
                                        "caption": tool_call["args"].get("message", "")
                                    })
                
                # ToolMessage 객체 처리
                elif hasattr(msg, "__class__") and (msg.__class__.__name__ == "ToolMessage" or "ToolMessage" in str(msg.__class__.__name__)):
                    if hasattr(msg, "content"):
                        content = str(msg.content)
                        # 도구 결과가 JSON인지 확인
                        try:
                            tool_data = eval(content)
                            if isinstance(tool_data, dict):
                                if "content_type" in tool_data and "image" in tool_data["content_type"]:
                                    # 이미지 처리
                                    if "data" in tool_data:
                                        results.append({
                                            "type": "image",
                                            "content": tool_data["data"],
                                            "caption": tool_data.get("message", "")
                                        })
                                else:
                                    # 일반 JSON 결과
                                    tool_result = f"도구 결과: {json.dumps(tool_data, ensure_ascii=False, indent=2)}"
                                    results.append({
                                        "type": "text",
                                        "content": tool_result
                                    })
                        except:
                            # Base64 이미지 체크
                            if content.startswith('iVBOR') and len(content) > 1000:
                                results.append({
                                    "type": "image",
                                    "content": content,
                                    "caption": f"도구 결과 이미지" + (f" - {msg.name}" if hasattr(msg, "name") else "")
                                })
                            # 일반 텍스트 도구 결과
                            elif not content.startswith("Error"):
                                tool_name = msg.name if hasattr(msg, "name") else "도구"
                                paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
                                
                                for paragraph in paragraphs:
                                    results.append({
                                        "type": "text",
                                        "content": paragraph
                                    })
                            # 에러 메시지
                            else:
                                results.append({
                                    "type": "text",
                                    "content": f"도구 호출 오류: {content}"
                                })
    
    # 결과가 없으면 원본 응답을 문자열로 변환
    if not results:
        return {
            "type": "text",
            "content": str(response)
        }
    
    # 결과가 하나면 그대로 반환
    if len(results) == 1:
        return results[0]
    
    # 여러 결과가 있으면 배열로 반환
    return results

## MCP 서버 설정 API ##

@app.get("/api/mcp/settings")
async def get_mcp_settings():
    """저장된 MCP 서버 설정을 조회합니다."""
    return MCP_SETTINGS

@app.post("/api/mcp/settings")
async def save_mcp_settings(settings: MCPSettings):
    """MCP 서버 연결 설정을 저장합니다."""
    global MCP_SETTINGS
    MCP_SETTINGS = settings.dict()
    return {
        "status": "success",
        "saved_at": datetime.now().isoformat()
    }

@app.post("/api/mcp/connection/test")
async def test_mcp_connection(settings: MCPSettings):
    """MCP 서버 연결을 테스트합니다."""
    try:
        # mcp_client_agent의 make_graph 함수를 사용하여 연결 테스트
        async with make_graph(
            settings.client_name, 
            settings.url,
            settings.transport
        ) as agent:
            if agent:
                return {
                    "status": "success",
                    "message": f"MCP 서버({settings.url})에 성공적으로 연결되었습니다."
                }
            else:
                return {
                    "status": "error",
                    "message": "연결은 되었으나 에이전트를 생성할 수 없습니다."
                }
    except Exception as e:
        logger.error(f"MCP 서버 연결 테스트 중 오류: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": f"MCP 서버 연결 실패: {str(e)}"
        }

## 모델 정보 API ##

@app.get("/api/models")
async def get_models():
    """사용 가능한 모델 목록을 조회합니다."""
    return {
        "models": AVAILABLE_MODELS
    }

# 서버 실행 설정
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True) 