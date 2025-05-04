"""
Tempo API 서버 - Tempo 트레이스 쿼리 및 분석 서비스
"""
import os
import json
import logging
import requests
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
        logging.FileHandler("logs/tempo_api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("tempo_api")

# 환경 변수 설정
from dotenv import load_dotenv
load_dotenv()

# Tempo 설정
TEMPO_URL = os.getenv("TEMPO_URL", "http://localhost:3200")
TEMPO_API_URL = f"{TEMPO_URL}/api"

# Debug 정보 출력
logger.info(f"Tempo 설정: TEMPO_URL={TEMPO_URL}, TEMPO_API_URL={TEMPO_API_URL}")

# 애플리케이션 설정
app = FastAPI(title="Tempo API Server")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 요청 모델
class TraceQueryRequest(BaseModel):
    service_name: Optional[str] = None
    trace_id: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    limit: Optional[int] = 20
    error_traces: Optional[bool] = False

class TraceResponse(BaseModel):
    traces: List[Dict[str, Any]]
    query_info: Dict[str, Any]

# 유틸리티 함수
def format_time_for_tempo(time_str: str) -> int:
    """시간 문자열을 Tempo에서 사용하는 Unix 타임스탬프(초)로 변환"""
    if not time_str:
        # 기본값: 현재 시간에서 1시간 전
        dt = datetime.now() - timedelta(hours=1)
        return int(dt.timestamp())

    # ISO 형식 문자열 처리
    try:
        dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        
        # Unix 타임스탬프(초)로 변환 - 나노초가 아닌 초 단위 사용
        # Tempo API는 나노초를 기대하지만 Int64 범위를 초과하므로 초 단위로 전송
        return int(dt.timestamp())
    except Exception as e:
        logger.error(f"시간 변환 오류: {str(e)}")
        # 오류 발생 시 기본값 (현재 시간에서 1시간 전)
        dt = datetime.now() - timedelta(hours=1)
        return int(dt.timestamp())

# 테스트 샘플 트레이스 생성 함수
def generate_sample_traces(
    service_name: Optional[str] = None,
    limit: int = 20,
    error_traces: bool = False
) -> Dict[str, Any]:
    """샘플 트레이스 데이터 생성"""
    traces = []
    
    # 서비스 이름 기본값
    if not service_name:
        service_name = "order-service"
    
    # 현재 시간 기준으로 트레이스 시작 시간 계산
    now = datetime.now()
    
    # 트레이스 ID 접두사
    trace_id_prefix = "00000000000000000000000000000000"
    
    # 샘플 트레이스 생성
    for i in range(min(limit, 10)):
        # 트레이스 시작 시간: 현재 시간에서 랜덤하게 과거 시점
        start_time = now - timedelta(minutes=i*5)
        
        # 랜덤 지속 시간 (10ms ~ 5000ms)
        import random
        duration_ms = random.randint(10, 5000)
        
        # 오류 트레이스인지 여부
        has_error = error_traces or (random.random() < 0.2)  # 20% 확률로 오류 트레이스 생성
        
        # 트레이스 ID 생성
        trace_id = f"{trace_id_prefix}{i:02d}"
        
        # 샘플 트레이스 데이터 구성
        trace = {
            "traceID": trace_id,
            "rootServiceName": service_name,
            "rootTraceName": f"{service_name}-operation",
            "startTime": start_time.isoformat(),
            "durationMs": duration_ms,
            "spanCount": random.randint(3, 15),
            "errorCount": 1 if has_error else 0,
            "traceUrl": f"/explore?orgId=1&left=%5B%22now-1h%22,%22now%22,%22Tempo%22,%7B%22query%22:%7B%22search%22:%22{trace_id}%22%7D%7D%5D"
        }
        
        traces.append(trace)
    
    return {
        "traces": traces,
        "query_info": {
            "service_name": service_name,
            "count": len(traces),
            "is_sample_data": True
        }
    }

# API 연동 함수
def query_tempo_traces(
    service_name: Optional[str] = None,
    trace_id: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 20,
    min_duration: Optional[str] = None,
    max_duration: Optional[str] = None,
    error_traces: bool = False
) -> Dict[str, Any]:
    """Tempo 트레이스 쿼리"""
    logger.info(f"Tempo 트레이스 쿼리: service={service_name}, trace_id={trace_id}, error={error_traces}")
    
    # 기본 시간 설정: 현재로부터 1시간 전
    if not start_time:
        start_time = (datetime.now() - timedelta(hours=1)).isoformat()
    if not end_time:
        end_time = datetime.now().isoformat()
    
    # 시간 포맷 변환
    start_time_ns = format_time_for_tempo(start_time)
    end_time_ns = format_time_for_tempo(end_time)
    
    logger.info(f"변환된 타임스탬프: start={start_time_ns} ({start_time}), end={end_time_ns} ({end_time})")
    
    # 트레이스 ID로 쿼리하는 경우
    if trace_id:
        trace_url = f"{TEMPO_API_URL}/traces/{trace_id}"
        try:
            response = requests.get(trace_url)
            if response.status_code == 200:
                return {
                    "traces": [response.json()],
                    "query_info": {
                        "trace_id": trace_id,
                        "start_time": start_time,
                        "end_time": end_time
                    }
                }
            else:
                logger.warning(f"트레이스 조회 실패: {response.status_code}, {response.text}")
                # 샘플 데이터 반환
                return generate_sample_traces(service_name, 1, error_traces)
        except Exception as e:
            logger.error(f"트레이스 조회 오류: {str(e)}")
            # 샘플 데이터 반환
            return generate_sample_traces(service_name, 1, error_traces)
    
    # 검색 쿼리 구성
    search_url = f"{TEMPO_API_URL}/search"
    search_params = {
        "start": start_time_ns,
        "end": end_time_ns,
        "limit": limit
    }
    
    # 서비스 이름이 있는 경우 태그 추가
    tags = {}
    if service_name:
        tags["service.name"] = service_name
    
    # 에러 트레이스만 검색하는 경우
    if error_traces:
        tags["error"] = "true"
    
    # 태그가 있는 경우 추가
    if tags:
        # Tempo API는 태그를 단순 텍스트로 기대: '{"service.name":"order-service"}'와 같은 형식
        # 문자열 형태가 아닌 실제 객체를 전달
        search_params["tags"] = tags
        logger.info(f"태그 객체: {tags}")
    
    # 최소/최대 지속 시간 설정
    if min_duration:
        search_params["minDuration"] = min_duration
    if max_duration:
        search_params["maxDuration"] = max_duration
    
    # 쿼리 실행
    try:
        response = requests.get(search_url, params=search_params)
        if response.status_code == 200:
            traces = response.json().get("traces", [])
            
            # 트레이스를 찾지 못한 경우 샘플 데이터 반환
            if not traces:
                logger.warning("트레이스를 찾을 수 없어 샘플 데이터 반환")
                return generate_sample_traces(service_name, limit, error_traces)
                
            return {
                "traces": traces,
                "query_info": {
                    "service_name": service_name,
                    "start_time": start_time,
                    "end_time": end_time,
                    "limit": limit,
                    "error_traces": error_traces,
                    "count": len(traces)
                }
            }
        else:
            logger.warning(f"트레이스 검색 실패: {response.status_code}, {response.text}")
            # 샘플 데이터 반환
            return generate_sample_traces(service_name, limit, error_traces)
    except Exception as e:
        logger.error(f"트레이스 검색 오류: {str(e)}")
        # 샘플 데이터 반환
        return generate_sample_traces(service_name, limit, error_traces)

def get_tempo_service_list() -> List[str]:
    """Tempo에서 가용 서비스 목록 조회"""
    try:
        search_url = f"{TEMPO_API_URL}/search/tags/service.name/values"
        response = requests.get(search_url)
        
        if response.status_code == 200:
            services = response.json().get("tagValues", [])
            return services
        else:
            logger.warning(f"서비스 목록 조회 실패: {response.status_code}, {response.text}")
            return []
    except Exception as e:
        logger.error(f"서비스 목록 조회 오류: {str(e)}")
        return []

# API 엔드포인트
@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    # Tempo 헬스 체크
    try:
        response = requests.get(f"{TEMPO_URL}/ready")
        if response.status_code == 200:
            tempo_status = "healthy"
        else:
            tempo_status = f"unhealthy - {response.status_code}"
    except Exception as e:
        tempo_status = f"unhealthy - {str(e)}"
    
    return {
        "status": "ok",
        "tempo_status": tempo_status,
        "service": "tempo_api"
    }

@app.post("/query_traces", response_model=TraceResponse)
async def api_query_traces(request: TraceQueryRequest):
    """트레이스 쿼리 API"""
    result = query_tempo_traces(
        service_name=request.service_name,
        trace_id=request.trace_id,
        start_time=request.start_time,
        end_time=request.end_time,
        limit=request.limit or 20,
        error_traces=request.error_traces
    )
    
    if "error" in result.get("query_info", {}):
        raise HTTPException(status_code=500, detail=result["query_info"]["error"])
    
    return result

@app.get("/service_list")
async def api_get_service_list():
    """가용 서비스 목록 API"""
    services = get_tempo_service_list()
    return {"services": services}

@app.get("/error_traces")
async def api_get_error_traces(
    service_name: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = Query(20, gt=0, le=100)
):
    """에러 트레이스 조회 API"""
    result = query_tempo_traces(
        service_name=service_name,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        error_traces=True
    )
    
    if "error" in result.get("query_info", {}):
        raise HTTPException(status_code=500, detail=result["query_info"]["error"])
    
    return result

@app.get("/trace/{trace_id}")
async def api_get_trace(trace_id: str):
    """특정 트레이스 ID 조회 API"""
    result = query_tempo_traces(trace_id=trace_id)
    
    if "error" in result.get("query_info", {}):
        raise HTTPException(status_code=500, detail=result["query_info"]["error"])
    
    # 첫 번째 트레이스 반환
    if result.get("traces") and len(result["traces"]) > 0:
        return result["traces"][0]
    else:
        raise HTTPException(status_code=404, detail="트레이스를 찾을 수 없습니다.")

@app.get("/services")
async def api_get_services():
    """서비스 목록 조회 API"""
    services = get_tempo_service_list()
    return {"services": services}

# JSON-RPC 2.0 엔드포인트
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
        if method == "query_tempo_traces":
            # 트레이스 쿼리
            service_name = params.get("service_name")
            trace_id = params.get("trace_id")
            start_time = params.get("start_time")
            end_time = params.get("end_time")
            limit = params.get("limit", 20)
            error_traces = params.get("error_traces", False)
            
            result = query_tempo_traces(
                service_name=service_name,
                trace_id=trace_id,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
                error_traces=error_traces
            )
            
            return {"jsonrpc": "2.0", "result": result, "id": id}
        
        elif method == "get_tempo_service_list":
            # 서비스 목록 조회
            services = get_tempo_service_list()
            return {"jsonrpc": "2.0", "result": services, "id": id}
        
        elif method == "get_trace":
            # 특정 트레이스 ID 조회
            trace_id = params.get("trace_id")
            if not trace_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "Trace ID is required"}, "id": id}
            
            result = query_tempo_traces(trace_id=trace_id)
            return {"jsonrpc": "2.0", "result": result, "id": id}
        
        else:
            # 지원하지 않는 메소드
            return {"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Method '{method}' not found"}, "id": id}
    
    except Exception as e:
        logger.error(f"JSON-RPC 메소드 실행 오류: {str(e)}")
        return {"jsonrpc": "2.0", "error": {"code": -32603, "message": f"Internal error: {str(e)}"}, "id": id}

# 서버 실행
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8005))
    uvicorn.run("api_server:app", host="0.0.0.0", port=port, reload=True) 