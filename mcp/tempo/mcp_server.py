"""
Tempo MCP 서버 - Model Context Protocol 및 API 서버 연결 서비스
"""
import os
import json
import logging
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
import httpx
import re

from fastapi import FastAPI, HTTPException, Request, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# 로깅 설정
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/tempo_mcp.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("tempo_mcp")

# 환경 변수 설정
from dotenv import load_dotenv
load_dotenv()

# API URL 설정
LANGGRAPH_URL = os.getenv("LANGGRAPH_URL", "http://localhost:8001")
TEMPO_API_URL = os.getenv("TEMPO_API_URL", "http://localhost:8005")

# 애플리케이션 설정
app = FastAPI(title="Tempo MCP 서버")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 요청/응답 모델
class QueryRequest(BaseModel):
    query: str
    context: Dict[str, Any] = Field(default_factory=dict)

class QueryResponse(BaseModel):
    response: str
    context: Dict[str, Any]
    
class LogQueryRequest(BaseModel):
    logql_query: str
    time_range: str

class TraceQueryRequest(BaseModel):
    trace_id: Optional[str] = None
    service_name: Optional[str] = None
    error_traces: Optional[bool] = False
    time_period: Optional[str] = "1h"

# MCP Context 모델
class MCPContext(BaseModel):
    """MCP 컨텍스트 관리 모델"""
    messages: List[Dict[str, str]] = Field(default_factory=list)
    trace_ids: List[str] = Field(default_factory=list)
    services: List[str] = Field(default_factory=list)
    last_query_time: Optional[str] = None
    
    def add_message(self, role: str, content: str):
        """메시지 추가"""
        self.messages.append({"role": role, "content": content})
        self.last_query_time = datetime.now().isoformat()
    
    def add_trace_id(self, trace_id: str):
        """트레이스 ID 추가"""
        if trace_id not in self.trace_ids:
            self.trace_ids.append(trace_id)
    
    def add_service(self, service: str):
        """서비스 추가"""
        if service not in self.services:
            self.services.append(service)

# API 연동 함수
async def call_langgraph_api(query: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph API 호출"""
    logger.info(f"LangGraph API 호출: {query[:50]}...")
    
    request_data = {
        "query": query,
        "context": context
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{LANGGRAPH_URL}/api/query",
                json=request_data
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"LangGraph 응답 수신: {len(str(result))} 바이트")
                return result
            else:
                error_msg = f"LangGraph API 오류: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise HTTPException(status_code=response.status_code, detail=error_msg)
    except httpx.RequestError as e:
        error_msg = f"LangGraph 연결 오류: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

async def call_tempo_api_jsonrpc(method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Tempo API를 JSON-RPC 2.0 프로토콜을 사용해 호출"""
    logger.info(f"Tempo API 호출 (JSON-RPC): {method}")
    
    jsonrpc_request = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": int(time.time() * 1000)  # 타임스탬프 기반 ID
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{TEMPO_API_URL}/rpc/v1",
                json=jsonrpc_request
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # JSON-RPC 응답 확인
                if "error" in result:
                    error = result["error"]
                    error_msg = f"Tempo API JSON-RPC 오류: {error.get('code')} - {error.get('message')}"
                    logger.error(error_msg)
                    raise HTTPException(status_code=500, detail=error_msg)
                
                logger.info(f"Tempo API 응답 수신: {len(str(result))} 바이트")
                return result.get("result", {})
            else:
                error_msg = f"Tempo API 오류: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise HTTPException(status_code=response.status_code, detail=error_msg)
    except httpx.RequestError as e:
        error_msg = f"Tempo API 연결 오류: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

async def query_traces(context: MCPContext, trace_request: TraceQueryRequest) -> Dict[str, Any]:
    """트레이스 쿼리"""
    logger.info(f"트레이스 쿼리: {trace_request}")
    
    # 트레이스 ID가 있는 경우 직접 조회
    if trace_request.trace_id:
        trace_result = await call_tempo_api_jsonrpc("get_trace", {
            "trace_id": trace_request.trace_id
        })
        
        # 컨텍스트 업데이트
        context.add_trace_id(trace_request.trace_id)
        
        return {
            "result": f"트레이스 {trace_request.trace_id} 조회 결과",
            "traces": trace_result.get("traces", []),
            "context": context.dict()
        }
    
    # 시간 변환
    now = datetime.now()
    start_time = None
    
    if trace_request.time_period == "15m":
        start_time = (now - timedelta(minutes=15)).isoformat()
    elif trace_request.time_period == "30m":
        start_time = (now - timedelta(minutes=30)).isoformat()
    elif trace_request.time_period == "1h":
        start_time = (now - timedelta(hours=1)).isoformat()
    elif trace_request.time_period == "3h":
        start_time = (now - timedelta(hours=3)).isoformat()
    elif trace_request.time_period == "6h":
        start_time = (now - timedelta(hours=6)).isoformat()
    elif trace_request.time_period == "12h":
        start_time = (now - timedelta(hours=12)).isoformat()
    elif trace_request.time_period == "24h":
        start_time = (now - timedelta(hours=24)).isoformat()
    else:
        # 기본값: 1시간
        start_time = (now - timedelta(hours=1)).isoformat()
    
    end_time = now.isoformat()
    
    # JSON-RPC 파라미터 구성
    params = {
        "service_name": trace_request.service_name,
        "start_time": start_time,
        "end_time": end_time,
        "limit": 20,
        "error_traces": trace_request.error_traces
    }
    
    # Tempo API 호출
    trace_result = await call_tempo_api_jsonrpc("query_tempo_traces", params)
    
    # 컨텍스트 업데이트
    for trace in trace_result.get("traces", []):
        if trace.get("traceID"):
            context.add_trace_id(trace.get("traceID"))
    
    if trace_request.service_name:
        context.add_service(trace_request.service_name)
    
    return {
        "result": f"트레이스 조회 결과",
        "traces": trace_result.get("traces", []),
        "context": context.dict()
    }

async def get_service_list() -> List[str]:
    """가용 서비스 목록 조회"""
    try:
        return await call_tempo_api_jsonrpc("get_tempo_service_list")
    except Exception as e:
        logger.error(f"서비스 목록 조회 오류: {str(e)}")
        return []

# API 엔드포인트
@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    services_status = {}
    
    # LangGraph 상태 확인
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{LANGGRAPH_URL}/health")
            if response.status_code == 200:
                services_status["langgraph"] = "정상"
            else:
                services_status["langgraph"] = f"오류 - {response.status_code}"
    except Exception as e:
        services_status["langgraph"] = f"연결 오류 - {str(e)}"
    
    # Tempo API 상태 확인
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{TEMPO_API_URL}/health")
            if response.status_code == 200:
                services_status["tempo_api"] = "정상"
            else:
                services_status["tempo_api"] = f"오류 - {response.status_code}"
    except Exception as e:
        services_status["tempo_api"] = f"연결 오류 - {str(e)}"
    
    # 전체 상태 반환
    all_services_ok = all(status == "정상" for status in services_status.values())
    return {
        "status": "정상" if all_services_ok else "일부 서비스 오류",
        "timestamp": datetime.now().isoformat(),
        "services": services_status
    }

@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """쿼리 처리 엔드포인트"""
    # 컨텍스트 가져오기 또는 초기화
    context = request.context.get("mcp_context", {})
    mcp_context = MCPContext(**context) if context else MCPContext()
    
    # 사용자 쿼리 저장
    mcp_context.add_message("user", request.query)
    
    # LangGraph로 쿼리 전달
    try:
        result = await call_langgraph_api(request.query, request.context)
        response_text = result.get("response", "응답을 받지 못했습니다.")
        
        # 응답 저장
        mcp_context.add_message("assistant", response_text)
        
        # 컨텍스트 업데이트
        result["context"]["mcp_context"] = mcp_context.dict()
        
        return {
            "response": response_text,
            "context": result.get("context", {})
        }
    except Exception as e:
        logger.error(f"쿼리 처리 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"쿼리 처리 오류: {str(e)}")

@app.post("/api/tempo/query_traces")
async def api_query_traces(request: TraceQueryRequest, context: Dict[str, Any] = {}):
    """트레이스 쿼리 엔드포인트"""
    # 컨텍스트 가져오기 또는 초기화
    mcp_context_data = context.get("mcp_context", {})
    mcp_context = MCPContext(**mcp_context_data) if mcp_context_data else MCPContext()
    
    # 트레이스 쿼리 실행
    result = await query_traces(mcp_context, request)
    
    return result

@app.get("/api/tempo/trace/{trace_id}")
async def api_get_trace(trace_id: str, context: Dict[str, Any] = {}):
    """특정 트레이스 조회 엔드포인트"""
    # 컨텍스트 가져오기 또는 초기화
    mcp_context_data = context.get("mcp_context", {})
    mcp_context = MCPContext(**mcp_context_data) if mcp_context_data else MCPContext()
    
    # 트레이스 ID 컨텍스트에 추가
    mcp_context.add_trace_id(trace_id)
    
    # 트레이스 조회
    trace_result = await call_tempo_api_jsonrpc("get_trace", {
        "trace_id": trace_id
    })
    
    return {
        "result": f"트레이스 {trace_id} 조회 결과",
        "trace": trace_result,
        "context": mcp_context.dict()
    }

@app.get("/api/tempo/services")
async def api_get_services(context: Dict[str, Any] = {}):
    """서비스 목록 조회 엔드포인트"""
    # 컨텍스트 가져오기 또는 초기화
    mcp_context_data = context.get("mcp_context", {})
    mcp_context = MCPContext(**mcp_context_data) if mcp_context_data else MCPContext()
    
    # 서비스 목록 조회
    services_result = await get_service_list()
    
    # 서비스 목록 컨텍스트에 추가
    for service in services_result:
        mcp_context.add_service(service)
    
    return {
        "result": "서비스 목록 조회 결과",
        "services": services_result,
        "context": mcp_context.dict()
    }

@app.get("/api/tempo/context")
async def api_get_context(context: Dict[str, Any] = {}):
    """현재 컨텍스트 조회 엔드포인트"""
    # 컨텍스트 가져오기 또는 초기화
    mcp_context_data = context.get("mcp_context", {})
    mcp_context = MCPContext(**mcp_context_data) if mcp_context_data else MCPContext()
    
    return {
        "result": "현재 컨텍스트",
        "context": mcp_context.dict()
    }

@app.post("/api/tempo/context")
async def api_update_context(context: Dict[str, Any]):
    """컨텍스트 업데이트 엔드포인트"""
    # 컨텍스트 가져오기 또는 초기화
    mcp_context_data = context.get("mcp_context", {})
    mcp_context = MCPContext(**mcp_context_data) if mcp_context_data else MCPContext()
    
    return {
        "result": "컨텍스트 업데이트 완료",
        "context": mcp_context.dict()
    }

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
    
    # 초기 컨텍스트 생성
    if "mcp_context" in params:
        mcp_context = MCPContext(**params["mcp_context"])
    else:
        mcp_context = MCPContext()
    
    # 지원하는 메소드 처리
    try:
        if method == "query_tempo":
            # 트레이스 쿼리
            service = params.get("service", "")
            start = params.get("start", "")
            end = params.get("end", "")
            limit = params.get("limit", 20)
            error_only = params.get("error_only", False)
            
            # 트레이스 쿼리 요청 구성
            trace_request = TraceQueryRequest(
                service_name=service,
                error_traces=error_only,
                time_period="1h"  # 기본값
            )
            
            # 실제 트레이스 조회 함수 호출
            logger.info(f"트레이스 쿼리: trace_id={None} service_name={service} error_traces={error_only} time_period='1h'")
            
            # 트레이스 API에 전달할 파라미터
            api_params = {
                "service_name": service,
                "error_traces": error_only,
                "limit": limit
            }
            
            # 시간값이 있는 경우 추가 (ISO 형식으로 변환)
            if start:
                api_params["start_time"] = start
            if end:
                api_params["end_time"] = end
            
            # Tempo API 호출
            result = await call_tempo_api_jsonrpc("query_tempo_traces", api_params)
            
            # 컨텍스트 업데이트: 서비스 추가
            if service:
                mcp_context.add_service(service)
            
            # 트레이스 ID 추출 및 컨텍스트 업데이트
            traces = result.get("traces", [])
            for trace in traces:
                if "traceID" in trace:
                    mcp_context.add_trace_id(trace["traceID"])
            
            return {"jsonrpc": "2.0", "result": traces, "id": id}
        
        elif method == "get_tempo_service_list" or method == "list_services":
            # 서비스 목록 조회
            services = await get_service_list()
            return {"jsonrpc": "2.0", "result": services, "id": id}
        
        elif method == "get_trace":
            # 특정 트레이스 ID 조회
            trace_id = params.get("trace_id")
            if not trace_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "Trace ID is required"}, "id": id}
            
            # 트레이스 쿼리 요청 구성
            trace_request = TraceQueryRequest(trace_id=trace_id)
            
            # API 호출 파라미터
            api_params = {"trace_id": trace_id}
            
            # Tempo API 호출
            result = await call_tempo_api_jsonrpc("get_trace", api_params)
            
            # 컨텍스트 업데이트
            mcp_context.add_trace_id(trace_id)
            
            return {"jsonrpc": "2.0", "result": result.get("traces", []), "id": id}
        
        else:
            # 지원하지 않는 메소드
            return {"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Method '{method}' not found"}, "id": id}
    
    except Exception as e:
        logger.error(f"JSON-RPC 메소드 실행 오류: {str(e)}", exc_info=True)
        return {"jsonrpc": "2.0", "error": {"code": -32603, "message": f"Internal error: {str(e)}"}, "id": id}

# 서버 실행
if __name__ == "__main__":
    import uvicorn
    PORT = int(os.getenv("TEMPO_MCP_PORT", 8004))
    logger.info(f"Tempo MCP 서버 시작: 포트={PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT) 