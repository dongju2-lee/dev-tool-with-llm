from fastapi import FastAPI, HTTPException, BackgroundTasks
import uvicorn
import random
import time
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging
import os
from datetime import datetime

# 로그 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("load-test-server")

# FastAPI 애플리케이션 생성
app = FastAPI(
    title="K6 Load Test Server",
    description="K6로 부하 테스트를 위한 샘플 API 서버",
    version="1.0.0"
)

# 데이터 모델 정의
class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    tax: Optional[float] = None

class User(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None

# 메모리 저장소
items_db = {}
users_db = {}
request_log = []

# 랜덤 지연 처리 함수
async def random_delay():
    # 20%의 확률로 큰 지연 발생 (3~8초)
    if random.random() < 0.2:
        delay_time = random.uniform(3.0, 8.0)
        logger.info(f"큰 지연 발생: {delay_time:.2f}초")
    else:
        # 80%의 확률로 작은 지연 발생 (0.1~1초)
        delay_time = random.uniform(0.1, 1.0)
        logger.info(f"작은 지연 발생: {delay_time:.2f}초")
    
    await asyncio.sleep(delay_time)

# 요청 로그 저장
def log_request(path: str, method: str, status_code: int):
    request_log.append({
        "timestamp": datetime.now().isoformat(),
        "path": path,
        "method": method,
        "status_code": status_code
    })
    # 로그 크기 제한 (최대 1000개)
    if len(request_log) > 1000:
        request_log.pop(0)

# API 엔드포인트 구현
@app.get("/", tags=["Root"])
async def root():
    """
    루트 엔드포인트: 서버가 살아있는지 확인
    """
    log_request("/", "GET", 200)
    return {"message": "K6 Load Test Server is running"}

@app.get("/items", tags=["Items"])
async def get_items(skip: int = 0, limit: int = 10):
    """
    아이템 목록 조회 API
    - skip: 건너뛸 아이템 수
    - limit: 반환할 최대 아이템 수
    """
    log_request("/items", "GET", 200)
    items_list = list(items_db.values())
    return items_list[skip : skip + limit]

@app.post("/items", tags=["Items"], status_code=201)
async def create_item(item: Item):
    """
    새 아이템 생성 API
    """
    item_id = str(len(items_db) + 1)
    items_db[item_id] = {
        "id": item_id,
        "name": item.name,
        "description": item.description,
        "price": item.price,
        "tax": item.tax
    }
    log_request("/items", "POST", 201)
    return {"id": item_id, **items_db[item_id]}

@app.get("/items/{item_id}", tags=["Items"])
async def get_item(item_id: str):
    """
    특정 아이템 조회 API
    """
    if item_id not in items_db:
        log_request(f"/items/{item_id}", "GET", 404)
        raise HTTPException(status_code=404, detail="Item not found")
    
    log_request(f"/items/{item_id}", "GET", 200)
    return items_db[item_id]

@app.post("/users", tags=["Users"], status_code=201)
async def create_user(user: User):
    """
    새 사용자 생성 API
    """
    if user.username in users_db:
        log_request("/users", "POST", 400)
        raise HTTPException(status_code=400, detail="Username already exists")
    
    users_db[user.username] = {
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name
    }
    log_request("/users", "POST", 201)
    return users_db[user.username]

@app.get("/users/{username}", tags=["Users"])
async def get_user(username: str, background_tasks: BackgroundTasks):
    """
    특정 사용자 조회 API (랜덤 지연 발생)
    """
    # 백그라운드에서 랜덤 지연 처리
    background_tasks.add_task(random_delay)
    
    if username not in users_db:
        log_request(f"/users/{username}", "GET", 404)
        raise HTTPException(status_code=404, detail="User not found")
    
    log_request(f"/users/{username}", "GET", 200)
    return users_db[username]

@app.get("/stats", tags=["Admin"])
async def get_stats():
    """
    서버 통계 정보 조회 API
    """
    log_request("/stats", "GET", 200)
    return {
        "items_count": len(items_db),
        "users_count": len(users_db),
        "request_count": len(request_log),
        "recent_requests": request_log[-10:] if request_log else []
    }

# 시작 메시지 및 초기 데이터 생성
@app.on_event("startup")
async def startup_event():
    # 초기 샘플 데이터 생성
    logger.info("서버 시작 중...")
    
    # 샘플 아이템 생성
    sample_items = [
        {"name": "노트북", "description": "고성능 개발용 노트북", "price": 1500000.0, "tax": 150000.0},
        {"name": "모니터", "description": "32인치 4K 모니터", "price": 450000.0, "tax": 45000.0},
        {"name": "키보드", "description": "기계식 키보드", "price": 120000.0, "tax": 12000.0},
        {"name": "마우스", "description": "무선 마우스", "price": 45000.0, "tax": 4500.0},
        {"name": "헤드폰", "description": "노이즈 캔슬링 헤드폰", "price": 350000.0, "tax": 35000.0}
    ]
    
    for i, item_data in enumerate(sample_items, 1):
        item_id = str(i)
        items_db[item_id] = {"id": item_id, **item_data}
    
    # 샘플 사용자 생성
    sample_users = [
        {"username": "user1", "email": "user1@example.com", "full_name": "사용자 1"},
        {"username": "user2", "email": "user2@example.com", "full_name": "사용자 2"},
        {"username": "admin", "email": "admin@example.com", "full_name": "관리자"}
    ]
    
    for user_data in sample_users:
        users_db[user_data["username"]] = user_data
    
    logger.info(f"초기 데이터 생성 완료: {len(items_db)} 아이템, {len(users_db)} 사용자")

if __name__ == "__main__":
    # 환경 변수에서 호스트와 포트 가져오기
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    
    logger.info(f"서버 시작: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
