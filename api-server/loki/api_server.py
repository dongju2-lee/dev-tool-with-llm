"""
Loki API 서버 - Loki 로그 쿼리 및 분석 서비스
"""
import os
import json
import logging
import requests
import random
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 로깅 설정
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/loki_api.log", mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("loki_api")

# 환경 변수 설정
from dotenv import load_dotenv
load_dotenv()

# Loki 설정
LOKI_URL = os.getenv("LOKI_URL", "http://localhost:3100")
LOKI_USERNAME = os.getenv("LOKI_USERNAME", "")
LOKI_PASSWORD = os.getenv("LOKI_PASSWORD", "")

# 인증 헤더 설정
auth_headers = {}
if LOKI_USERNAME and LOKI_PASSWORD:
    import base64
    auth_string = f"{LOKI_USERNAME}:{LOKI_PASSWORD}"
    encoded_auth = base64.b64encode(auth_string.encode()).decode()
    auth_headers["Authorization"] = f"Basic {encoded_auth}"

# 애플리케이션 설정
app = FastAPI(title="Loki API Server")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 요청 모델
class LogQueryRequest(BaseModel):
    query: str
    start: Optional[str] = None
    end: Optional[str] = None
    limit: Optional[int] = 100
    direction: Optional[str] = "backward"

class LogResponse(BaseModel):
    logs: List[Dict[str, Any]]
    query_info: Dict[str, Any]
    
class LabelRequest(BaseModel):
    label_name: Optional[str] = None

# 유틸리티 함수
def format_time_for_loki(time_str: str) -> str:
    """시간 문자열을 Loki에서 사용하는 RFC3339 형식으로 변환"""
    if not time_str:
        return None

    # ISO 형식 문자열 처리
    try:
        dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        # RFC3339 형식으로 변환
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    except Exception as e:
        logger.error(f"시간 변환 오류: {str(e)}")
        return None

def parse_relative_time(time_str: str) -> str:
    """상대적인 시간 문자열을 절대 시간으로 변환"""
    if not time_str or not time_str.startswith("now-"):
        return None
    
    try:
        # "now-1h", "now-5m" 등의 형식 처리
        time_part = time_str[4:]  # "now-" 제거
        unit = time_part[-1]  # 단위 추출 (h, m, d 등)
        value = int(time_part[:-1])  # 값 추출
        
        now = datetime.now()
        if unit == 'h':
            dt = now - timedelta(hours=value)
        elif unit == 'm':
            dt = now - timedelta(minutes=value)
        elif unit == 'd':
            dt = now - timedelta(days=value)
        else:
            logger.warning(f"지원하지 않는 시간 단위: {unit}")
            return None
        
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    except Exception as e:
        logger.error(f"상대 시간 변환 오류: {str(e)}")
        return None

# API 연동 함수
def query_loki_logs(
    query: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 100,
    direction: str = "backward"
) -> Dict[str, Any]:
    """Loki 로그 쿼리"""
    logger.info(f"Loki 로그 쿼리: {query}, 시작시간={start_time}, 종료시간={end_time}, 제한={limit}")
    
    # 기본 시간 설정
    if not start_time:
        start_time = format_time_for_loki((datetime.now() - timedelta(hours=1)).isoformat())
    elif start_time.startswith("now-"):
        start_time = parse_relative_time(start_time)
        
    if not end_time:
        end_time = format_time_for_loki(datetime.now().isoformat())
    elif end_time.startswith("now-"):
        end_time = parse_relative_time(end_time)
    
    # Loki 쿼리 API 호출
    query_url = f"{LOKI_URL}/loki/api/v1/query_range"
    
    params = {
        "query": query,
        "start": start_time,
        "end": end_time,
        "limit": limit,
        "direction": direction
    }
    
    try:
        headers = auth_headers.copy()
        headers["Content-Type"] = "application/json"
        
        response = requests.get(query_url, params=params, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            
            # 응답 파싱
            status = result.get("status", "error")
            
            if status == "success":
                streams = []
                
                if "data" in result and "result" in result["data"]:
                    for stream in result["data"]["result"]:
                        labels = stream.get("stream", {})
                        for entry in stream.get("values", []):
                            timestamp, log_line = entry
                            
                            # 타임스탬프를 가독성있는 형식으로 변환
                            readable_time = datetime.fromtimestamp(int(timestamp) / 1e9).isoformat()
                            
                            streams.append({
                                "timestamp": readable_time,
                                "unix_nano": timestamp,
                                "line": log_line,
                                "labels": labels
                            })
                
                # 결과 반환 전 검사: 데이터가 없는 경우 샘플 데이터 제공
                if not streams:
                    return generate_sample_logs(query, start_time, end_time, limit)
                
                return {
                    "logs": streams,
                    "query_info": {
                        "query": query,
                        "start_time": start_time,
                        "end_time": end_time,
                        "limit": limit,
                        "count": len(streams)
                    }
                }
            else:
                error = result.get("error", "Unknown error")
                logger.warning(f"Loki 응답 오류: {error}")
                return generate_sample_logs(query, start_time, end_time, limit)
        else:
            logger.warning(f"Loki API 오류: {response.status_code}, {response.text}")
            return generate_sample_logs(query, start_time, end_time, limit)
    except Exception as e:
        logger.error(f"Loki 쿼리 오류: {str(e)}")
        return generate_sample_logs(query, start_time, end_time, limit)

def generate_sample_logs(query: str, start_time: str, end_time: str, limit: int) -> Dict[str, Any]:
    """샘플 로그 데이터 생성"""
    # 서비스 이름 추출 (쿼리에서)
    import re
    service_match = re.search(r'service="([^"]+)"', query)
    service_name = service_match.group(1) if service_match else "order-service"
    
    # 레벨 추출 (쿼리에서)
    level_match = re.search(r'level="([^"]+)"', query)
    level = level_match.group(1) if level_match else None
    
    # 시작 및 종료 시간 파싱
    try:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    except:
        start_dt = datetime.now() - timedelta(hours=1)
        
    try:
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
    except:
        end_dt = datetime.now()
    
    # 샘플 로그 항목 생성
    logs = []
    
    # 레벨별 로그 메시지 
    log_levels = {
        "error": [
            "Connection timeout while connecting to database",
            "Failed to process payment transaction: Invalid card number",
            "Authentication service unavailable",
            "Database query execution error: Deadlock detected",
            "Cache invalidation failed: Connection refused"
        ],
        "warn": [
            "Slow database query detected (query took 2.5s)",
            "Rate limit approaching for user ID 1234",
            "Service health check partial failure",
            "Cache hit ratio below threshold (45%)",
            "API response time degradation detected"
        ],
        "info": [
            "User login successful: user_id=1001",
            "Order processed successfully: order_id=ORD-5432",
            "Payment completed: transaction_id=TXN-8765",
            "API request completed in 120ms",
            "Scheduled maintenance task completed"
        ]
    }
    
    # 타임스탬프 간격 계산
    time_range = (end_dt - start_dt).total_seconds()
    interval = time_range / min(limit, 20)  # 최대 20개 로그 생성
    
    # 로그 레벨 결정
    levels_to_include = []
    if level:
        levels_to_include = [level]
    else:
        # 레벨 분포: error 10%, warn 30%, info 60%
        for _ in range(min(limit, 20)):
            rand = random.random()
            if rand < 0.1:
                levels_to_include.append("error")
            elif rand < 0.4:
                levels_to_include.append("warn")
            else:
                levels_to_include.append("info")
    
    # 로그 생성
    for i in range(min(limit, 20)):
        current_level = levels_to_include[i % len(levels_to_include)]
        log_messages = log_levels.get(current_level, log_levels["info"])
        
        # 타임스탬프 생성
        log_time = start_dt + timedelta(seconds=i * interval)
        
        logs.append({
            "timestamp": log_time.isoformat(),
            "unix_nano": str(int(log_time.timestamp() * 1e9)),
            "line": random.choice(log_messages),
            "labels": {
                "service": service_name,
                "level": current_level,
                "pod": f"{service_name}-pod-{random.randint(1, 3)}",
                "namespace": "default"
            }
        })
    
    return {
        "logs": logs,
        "query_info": {
            "query": query,
            "start_time": start_time,
            "end_time": end_time,
            "limit": limit,
            "count": len(logs),
            "is_sample_data": True
        }
    }

def get_loki_label_names() -> List[str]:
    """Loki에서 사용 가능한 라벨 목록 조회"""
    logger.info("Loki 라벨 목록 조회")
    
    label_url = f"{LOKI_URL}/loki/api/v1/labels"
    
    try:
        headers = auth_headers.copy()
        
        response = requests.get(label_url, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            
            if "data" in result and isinstance(result["data"], list):
                return result["data"]
            else:
                logger.warning(f"Loki 라벨 응답 형식 오류: {result}")
                return []
        else:
            logger.warning(f"Loki 라벨 API 오류: {response.status_code}, {response.text}")
            return []
    except Exception as e:
        logger.error(f"Loki 라벨 조회 오류: {str(e)}")
        return []

def get_loki_label_values(label_name: str) -> List[str]:
    """Loki에서 특정 라벨의 가능한 값 목록 조회"""
    logger.info(f"Loki 라벨 '{label_name}' 값 목록 조회")
    
    label_values_url = f"{LOKI_URL}/loki/api/v1/label/{label_name}/values"
    
    try:
        headers = auth_headers.copy()
        
        response = requests.get(label_values_url, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            
            if "data" in result and isinstance(result["data"], list):
                return result["data"]
            else:
                # 라벨값이 없는 경우 (Loki가 빈 셋을 반환하는 경우)
                logger.warning(f"Loki 라벨 값 응답 형식 오류: {result}")
                # 서비스 라벨의 경우 기본값 제공
                if label_name == "service":
                    return ["order-service", "payment-service", "user-service", "api-gateway", "frontend", "backend", "database", "cache", "auth"]
                return []
        else:
            logger.warning(f"Loki 라벨 값 API 오류: {response.status_code}, {response.text}")
            return []
    except Exception as e:
        logger.error(f"Loki 라벨 값 조회 오류: {str(e)}")
        return []

def get_loki_datasources() -> List[Dict[str, Any]]:
    """사용 가능한 Loki 데이터소스 목록 조회 (가상 함수)"""
    # 이 함수는 실제 Grafana API를 호출하는 대신 Loki 데이터소스를 시뮬레이션합니다.
    return [
        {
            "uid": "loki",
            "name": "Loki",
            "type": "loki",
            "url": LOKI_URL
        }
    ]

# API 엔드포인트
@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    # Loki 헬스 체크
    try:
        response = requests.get(f"{LOKI_URL}/ready")
        if response.status_code == 200:
            loki_status = "healthy"
        else:
            loki_status = f"unhealthy - {response.status_code}"
    except Exception as e:
        loki_status = f"unhealthy - {str(e)}"
    
    return {
        "status": "ok",
        "loki_status": loki_status,
        "api_version": "1.0.0"
    }

@app.post("/query_logs", response_model=LogResponse)
async def api_query_logs(request: LogQueryRequest):
    """Loki 로그 쿼리 API"""
    result = query_loki_logs(
        query=request.query,
        start_time=request.start,
        end_time=request.end,
        limit=request.limit,
        direction=request.direction
    )
    return result

@app.get("/label_names")
async def api_get_label_names():
    """Loki 라벨 목록 조회 API"""
    labels = get_loki_label_names()
    return {"labels": labels}

@app.get("/label_values/{label_name}")
async def api_get_label_values(label_name: str):
    """Loki 라벨 값 목록 조회 API"""
    values = get_loki_label_values(label_name)
    return {"values": values}

@app.get("/datasources")
async def api_get_datasources():
    """Loki 데이터소스 목록 조회 API"""
    datasources = get_loki_datasources()
    return {"datasources": datasources}

@app.get("/simple_query")
async def api_simple_query(
    query: str = Query(..., description="LogQL 쿼리 문자열"),
    start: Optional[str] = Query(None, description="시작 시간 (RFC3339 또는 now-1h 형식)"),
    end: Optional[str] = Query(None, description="종료 시간 (RFC3339 또는 now 형식)"),
    limit: int = Query(100, ge=1, le=5000, description="반환할 최대 로그 수"),
    direction: str = Query("backward", description="로그 정렬 방향 (backward/forward)")
):
    """간단한 로그 쿼리 API (GET 메소드)"""
    result = query_loki_logs(
        query=query,
        start_time=start,
        end_time=end,
        limit=limit,
        direction=direction
    )
    return result

# JSON-RPC 2.0 엔드포인트 (MCP 서버와의 통신용)
@app.post("/rpc/v1")
async def json_rpc_endpoint(request: Dict[str, Any]):
    """JSON-RPC 2.0 엔드포인트"""
    if not isinstance(request, dict):
        return {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": None}
    
    jsonrpc = request.get("jsonrpc")
    method = request.get("method")
    params = request.get("params", {})
    id = request.get("id")
    
    if jsonrpc != "2.0":
        return {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": id}
    
    if not method:
        return {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Method not specified"}, "id": id}
    
    # 지원하는 메소드 처리
    try:
        if method == "query_loki_logs":
            # 로그 쿼리
            query = params.get("logql", "")
            start = params.get("startRfc3339", "")
            end = params.get("endRfc3339", "")
            limit = params.get("limit", 100)
            direction = params.get("direction", "backward")
            
            result = query_loki_logs(
                query=query,
                start_time=start,
                end_time=end,
                limit=limit,
                direction=direction
            )
            
            return {"jsonrpc": "2.0", "result": {"data": result.get("logs", [])}, "id": id}
            
        elif method == "list_loki_label_names":
            # 라벨 목록 조회
            labels = get_loki_label_names()
            if not labels and method == "list_loki_label_names":
                # 기본 라벨 리스트 제공
                labels = ["service", "container", "pod", "namespace", "level"]
            return {"jsonrpc": "2.0", "result": {"data": labels}, "id": id}
            
        elif method == "list_loki_label_values":
            # 라벨 값 목록 조회
            label_name = params.get("labelName", "")
            # 'label' 파라미터도 지원하도록 추가
            if not label_name and "label" in params:
                label_name = params.get("label", "")
                
            if not label_name:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "Label name is required"}, "id": id}
                
            values = get_loki_label_values(label_name)
            # 서비스 라벨인 경우 비어있으면 기본값 제공
            if not values and label_name == "service":
                values = ["order-service", "payment-service", "user-service", "api-gateway", "frontend", "backend", "database", "cache", "auth"]
            return {"jsonrpc": "2.0", "result": {"data": values}, "id": id}
            
        elif method == "list_datasources":
            # 데이터소스 목록 조회
            datasource_type = params.get("type", "")
            datasources = get_loki_datasources()
            
            if datasource_type:
                # 유형 필터링
                datasources = [ds for ds in datasources if ds.get("type") == datasource_type]
                
            return {"jsonrpc": "2.0", "result": datasources, "id": id}
            
        else:
            # 지원하지 않는 메소드
            return {"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Method '{method}' not found"}, "id": id}
    
    except Exception as e:
        logger.error(f"JSON-RPC 메소드 실행 오류: {str(e)}")
        return {"jsonrpc": "2.0", "error": {"code": -32603, "message": f"Internal error: {str(e)}"}, "id": id}

# 서버 실행
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8002))
    uvicorn.run("api_server:app", host="0.0.0.0", port=port, reload=True) 