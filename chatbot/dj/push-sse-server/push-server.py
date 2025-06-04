"""
SSE 기반 푸시 알림 서버
음성 처리 결과 및 실시간 알림을 클라이언트에 전송
FastAPI 기반 Server-Sent Events
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

# 로그 디렉토리 생성
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "push_server.log"

# 로그 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 서버 시작 로그
logger.info("=" * 50)
logger.info("SSE 푸시 알림 서버 시작")
logger.info(f"로그 파일: {log_file}")
logger.info("=" * 50)

app = FastAPI(title="SSE 푸시 알림 서버", description="실시간 알림을 위한 Server-Sent Events 서버")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경에서는 모든 origin 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 연결된 클라이언트들을 저장할 딕셔너리
connected_clients: Dict[str, asyncio.Queue] = {}

# 알림 메시지 모델
class NotificationMessage(BaseModel):
    type: str  # 알림 타입 (info, success, warning, error, voice_status)
    title: str  # 알림 제목
    message: str  # 알림 내용
    data: dict = None  # 추가 데이터
    timestamp: str = None

class VoiceStatusMessage(BaseModel):
    type: str = "voice_status"
    status: str  # idle, recording, processing, speaking
    message: str = ""
    data: dict = None

class BroadcastMessage(BaseModel):
    message: NotificationMessage

def create_sse_message(data: dict) -> str:
    """SSE 형식의 메시지 생성"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

async def add_client(client_id: str) -> asyncio.Queue:
    """새 클라이언트 연결 추가"""
    queue = asyncio.Queue()
    connected_clients[client_id] = queue
    logger.info(f"클라이언트 연결됨: {client_id} (총 {len(connected_clients)}개)")
    
    # 연결 환영 메시지 전송
    welcome_msg = {
        "type": "connection",
        "title": "연결 성공",
        "message": "SSE 연결이 성공적으로 설정되었습니다.",
        "timestamp": datetime.now().isoformat(),
        "data": {"client_id": client_id}
    }
    await queue.put(create_sse_message(welcome_msg))
    
    return queue

async def remove_client(client_id: str):
    """클라이언트 연결 제거"""
    if client_id in connected_clients:
        del connected_clients[client_id]
        logger.info(f"클라이언트 연결 해제됨: {client_id} (총 {len(connected_clients)}개)")

async def broadcast_to_all(message: dict):
    """모든 연결된 클라이언트에게 메시지 브로드캐스트"""
    if not connected_clients:
        logger.warning("연결된 클라이언트가 없습니다.")
        return
    
    sse_message = create_sse_message(message)
    disconnected_clients = []
    
    for client_id, queue in connected_clients.items():
        try:
            await queue.put(sse_message)
            logger.debug(f"메시지 전송 완료: {client_id}")
        except Exception as e:
            logger.error(f"클라이언트 {client_id}에게 메시지 전송 실패: {e}")
            disconnected_clients.append(client_id)
    
    # 연결이 끊어진 클라이언트 제거
    for client_id in disconnected_clients:
        await remove_client(client_id)
    
    logger.info(f"브로드캐스트 완료: {len(connected_clients)}개 클라이언트")

async def send_to_client(client_id: str, message: dict):
    """특정 클라이언트에게 메시지 전송"""
    if client_id not in connected_clients:
        logger.warning(f"클라이언트 {client_id}가 연결되어 있지 않습니다.")
        return False
    
    try:
        sse_message = create_sse_message(message)
        await connected_clients[client_id].put(sse_message)
        logger.info(f"메시지 전송 완료: {client_id}")
        return True
    except Exception as e:
        logger.error(f"클라이언트 {client_id}에게 메시지 전송 실패: {e}")
        await remove_client(client_id)
        return False

@app.get("/health")
async def health_check():
    """서버 상태 확인"""
    return {
        "status": "healthy",
        "connected_clients": len(connected_clients),
        "server_time": datetime.now().isoformat()
    }

@app.get("/events/{client_id}")
async def stream_events(client_id: str, request: Request):
    """SSE 스트림 엔드포인트"""
    logger.info(f"SSE 연결 요청: {client_id}")
    
    # 클라이언트 추가
    queue = await add_client(client_id)
    
    async def event_generator():
        try:
            while True:
                # 클라이언트 연결 상태 확인
                if await request.is_disconnected():
                    logger.info(f"클라이언트 연결 끊어짐: {client_id}")
                    break
                
                try:
                    # 큐에서 메시지 대기 (타임아웃 30초)
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield message
                except asyncio.TimeoutError:
                    # 연결 유지를 위한 heartbeat 전송
                    heartbeat = create_sse_message({
                        "type": "heartbeat",
                        "timestamp": datetime.now().isoformat()
                    })
                    yield heartbeat
                    
        except Exception as e:
            logger.error(f"SSE 스트림 오류 ({client_id}): {e}")
        finally:
            await remove_client(client_id)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )

@app.post("/notify/broadcast")
async def broadcast_notification(message: BroadcastMessage):
    """모든 클라이언트에게 알림 브로드캐스트"""
    try:
        # 타임스탬프 추가
        notification = message.message.dict()
        if not notification.get("timestamp"):
            notification["timestamp"] = datetime.now().isoformat()
        
        await broadcast_to_all(notification)
        
        return {
            "success": True,
            "message": "브로드캐스트 완료",
            "clients_count": len(connected_clients)
        }
    except Exception as e:
        logger.error(f"브로드캐스트 오류: {e}")
        raise HTTPException(status_code=500, detail=f"브로드캐스트 실패: {str(e)}")

@app.post("/notify/{client_id}")
async def send_notification(client_id: str, message: NotificationMessage):
    """특정 클라이언트에게 알림 전송"""
    try:
        # 타임스탬프 추가
        notification = message.dict()
        if not notification.get("timestamp"):
            notification["timestamp"] = datetime.now().isoformat()
        
        success = await send_to_client(client_id, notification)
        
        if success:
            return {
                "success": True,
                "message": f"클라이언트 {client_id}에게 알림 전송 완료"
            }
        else:
            raise HTTPException(status_code=404, detail=f"클라이언트 {client_id}를 찾을 수 없습니다")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"알림 전송 오류: {e}")
        raise HTTPException(status_code=500, detail=f"알림 전송 실패: {str(e)}")

@app.post("/voice/status")
async def update_voice_status(status_message: VoiceStatusMessage):
    """음성 상태 업데이트 브로드캐스트"""
    try:
        # 타임스탬프 추가
        notification = status_message.dict()
        notification["timestamp"] = datetime.now().isoformat()
        
        await broadcast_to_all(notification)
        
        logger.info(f"음성 상태 업데이트: {status_message.status} - {status_message.message}")
        
        return {
            "success": True,
            "message": "음성 상태 업데이트 완료",
            "status": status_message.status
        }
    except Exception as e:
        logger.error(f"음성 상태 업데이트 오류: {e}")
        raise HTTPException(status_code=500, detail=f"음성 상태 업데이트 실패: {str(e)}")

@app.get("/clients")
async def get_connected_clients():
    """연결된 클라이언트 목록 조회"""
    return {
        "connected_clients": list(connected_clients.keys()),
        "count": len(connected_clients)
    }

# 테스트용 엔드포인트들
@app.post("/test/info")
async def test_info_notification():
    """테스트: 정보 알림"""
    message = NotificationMessage(
        type="info",
        title="정보 알림",
        message="이것은 테스트 정보 알림입니다.",
        data={"test": True}
    )
    await broadcast_to_all(message.dict())
    return {"message": "정보 알림 전송 완료"}

@app.post("/test/success")
async def test_success_notification():
    """테스트: 성공 알림"""
    message = NotificationMessage(
        type="success",
        title="성공!",
        message="작업이 성공적으로 완료되었습니다.",
        data={"result": "success"}
    )
    await broadcast_to_all(message.dict())
    return {"message": "성공 알림 전송 완료"}

@app.post("/test/warning")
async def test_warning_notification():
    """테스트: 경고 알림"""
    message = NotificationMessage(
        type="warning",
        title="주의",
        message="주의가 필요한 상황입니다.",
        data={"level": "warning"}
    )
    await broadcast_to_all(message.dict())
    return {"message": "경고 알림 전송 완료"}

@app.post("/test/error")
async def test_error_notification():
    """테스트: 오류 알림"""
    message = NotificationMessage(
        type="error",
        title="오류 발생",
        message="시스템에서 오류가 발생했습니다.",
        data={"error_code": "TEST_ERROR"}
    )
    await broadcast_to_all(message.dict())
    return {"message": "오류 알림 전송 완료"}

if __name__ == '__main__':
    logger.info("SSE 푸시 알림 서버를 시작합니다...")
    logger.info("서버 주소: http://localhost:8505")
    logger.info("SSE 엔드포인트: http://localhost:8505/events/{client_id}")
    logger.info("종료하려면 Ctrl+C를 누르세요.")
    
    uvicorn.run(
        "push-server:app",  # 문자열로 앱 지정
        host="0.0.0.0", 
        port=8505, 
        reload=True,
        log_level="info",
        access_log=True
    )
