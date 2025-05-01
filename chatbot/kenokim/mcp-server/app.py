from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn
import uuid
from datetime import datetime
import time
import random

app = FastAPI(title="MCP 서버", description="모델 컨텍스트 프로토콜(MCP) 서버")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 메시지 모델
class Message(BaseModel):
    message: str
    thread_id: Optional[str] = None
    context: Optional[List[Dict[str, Any]]] = None
    stream: Optional[bool] = False

# 간단한 메모리 저장소 (실제로는 데이터베이스를 사용할 것)
threads = {}
messages = {}

# 시작 시간 기록
start_time = time.time()

@app.get("/")
def read_root():
    return {"message": "MCP 서버가 실행 중입니다"}

@app.get("/status")
def get_status():
    """서버 상태 확인 엔드포인트"""
    return {
        "status": "online",
        "version": "0.1.0",
        "uptime": int(time.time() - start_time)
    }

@app.post("/chat")
async def chat(message_data: Message, request: Request):
    """채팅 메시지 처리 엔드포인트"""
    # 스레드 ID가 없으면 새로 생성
    thread_id = message_data.thread_id or str(uuid.uuid4())
    
    # 스레드 정보 저장/업데이트
    if thread_id not in threads:
        threads[thread_id] = {
            "created_at": datetime.now().isoformat(),
            "metadata": {}
        }
    
    # 메시지 ID 생성 및 저장
    message_id = str(uuid.uuid4())
    message_obj = {
        "id": message_id,
        "role": "user",
        "content": message_data.message,
        "created_at": datetime.now().isoformat()
    }
    
    if thread_id not in messages:
        messages[thread_id] = []
    
    messages[thread_id].append(message_obj)
    
    # 응답 생성 (실제로는 LLM을 호출할 것)
    response_options = [
        "안녕하세요! 무엇을 도와드릴까요?",
        "좋은 질문이네요. 더 자세히 알려주시겠어요?",
        "흥미로운 주제입니다. 어떤 측면에 관심이 있으신가요?",
        "도움이 필요하시면 언제든지 물어보세요!",
        f"'{message_data.message}'에 대한 답변을 준비 중입니다..."
    ]
    
    response_content = random.choice(response_options)
    
    # 응답 저장
    response_obj = {
        "id": str(uuid.uuid4()),
        "role": "assistant",
        "content": response_content,
        "created_at": datetime.now().isoformat()
    }
    
    messages[thread_id].append(response_obj)
    
    # 스트리밍이 아닌 경우 바로 응답
    if not message_data.stream:
        return {
            "content": response_content,
            "thread_id": thread_id
        }
    
    # 스트리밍 응답은 구현 예정
    return {
        "content": response_content,
        "thread_id": thread_id
    }

@app.get("/threads")
def get_threads():
    """모든 스레드 목록 조회"""
    return {"threads": [{"thread_id": tid, **info} for tid, info in threads.items()]}

@app.post("/threads")
def create_thread(metadata: Optional[Dict[str, Any]] = None):
    """새 스레드 생성"""
    thread_id = str(uuid.uuid4())
    threads[thread_id] = {
        "created_at": datetime.now().isoformat(),
        "metadata": metadata or {}
    }
    messages[thread_id] = []
    
    return {
        "thread_id": thread_id,
        "created_at": threads[thread_id]["created_at"],
        "metadata": threads[thread_id]["metadata"]
    }

@app.get("/threads/{thread_id}/messages")
def get_thread_messages(thread_id: str):
    """특정 스레드의 메시지 조회"""
    if thread_id not in threads:
        raise HTTPException(status_code=404, detail="스레드를 찾을 수 없습니다")
    
    return {"messages": messages.get(thread_id, [])}

@app.post("/tools/execute")
def execute_tool(tool_request: Dict[str, Any]):
    """도구 실행 엔드포인트"""
    tool_name = tool_request.get("tool_name")
    parameters = tool_request.get("parameters", {})
    
    # 실제 도구 실행 로직은 구현 예정
    return {
        "result": f"도구 '{tool_name}'가 파라미터 {parameters}로 실행되었습니다 (더미 응답)",
        "status": "success"
    }

# 직접 실행 시 사용
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 