"""
Loki MCP 서버 - Model Context Protocol 및 API 서버 연결 서비스
"""
import os
import json
import logging
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
import httpx

from fastapi import FastAPI, HTTPException, Request, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# 로깅 설정
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/loki_mcp.log", mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("loki_mcp")

# 환경 변수 설정
from dotenv import load_dotenv
load_dotenv()

# API URL 설정
LANGGRAPH_URL = os.getenv("LANGGRAPH_URL", "http://localhost:8001")
LOKI_API_URL = os.getenv("LOKI_API_URL", "http://localhost:8002")

# 애플리케이션 설정
app = FastAPI(title="Loki MCP 서버")

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
    limit: int = 100

# MCP Context 모델
class MCPContext(BaseModel):
    """MCP 컨텍스트 관리 모델"""
    messages: List[Dict[str, str]] = Field(default_factory=list)
    services: List[str] = Field(default_factory=list)
    queries: List[str] = Field(default_factory=list)
    last_query_time: Optional[str] = None
    
    def add_message(self, role: str, content: str):
        """메시지 추가"""
        self.messages.append({"role": role, "content": content})
        self.last_query_time = datetime.now().isoformat()
    
    def add_query(self, query: str):
        """쿼리 추가"""
        if query not in self.queries:
            self.queries.append(query)
    
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

async def call_loki_api_jsonrpc(method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Loki API를 JSON-RPC 2.0 프로토콜을 사용해 호출"""
    logger.info(f"Loki API 호출 (JSON-RPC): {method}")
    
    jsonrpc_request = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": int(time.time() * 1000)  # 타임스탬프 기반 ID
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{LOKI_API_URL}/rpc/v1",
                json=jsonrpc_request
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # JSON-RPC 응답 확인
                if "error" in result:
                    error = result["error"]
                    error_msg = f"Loki API JSON-RPC 오류: {error.get('code')} - {error.get('message')}"
                    logger.error(error_msg)
                    raise HTTPException(status_code=500, detail=error_msg)
                
                logger.info(f"Loki API 응답 수신: {len(response.content)} 바이트")
                return result.get("result", {})
            else:
                error_msg = f"Loki API 오류: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise HTTPException(status_code=response.status_code, detail=error_msg)
    except httpx.RequestError as e:
        error_msg = f"Loki API 연결 오류: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

async def query_logs(context: MCPContext, query_request: LogQueryRequest) -> Dict[str, Any]:
    """로그 쿼리"""
    logger.info(f"로그 쿼리: {query_request}")
    
    # 시간 변환
    time_range = query_request.time_range
    
    # 시간 처리
    now = datetime.now()
    start_time = None
    end_time = now.isoformat()
    
    if time_range.startswith("last_"):
        # "last_15m", "last_1h" 등의 형식 처리
        value_unit = time_range[5:]
        unit = value_unit[-1]
        try:
            value = int(value_unit[:-1])
            
            if unit == 'h':
                start_time = (now - timedelta(hours=value)).isoformat()
            elif unit == 'm':
                start_time = (now - timedelta(minutes=value)).isoformat()
            elif unit == 'd':
                start_time = (now - timedelta(days=value)).isoformat()
            else:
                # 기본값: 1시간
                start_time = (now - timedelta(hours=1)).isoformat()
        except ValueError:
            # 기본값: 1시간
            start_time = (now - timedelta(hours=1)).isoformat()
    else:
        # 기본값: 1시간
        start_time = (now - timedelta(hours=1)).isoformat()
    
    # Loki API 호출
    params = {
        "logql": query_request.logql_query,
        "startRfc3339": start_time,
        "endRfc3339": end_time,
        "limit": query_request.limit
    }
    
    logs = await call_loki_api_jsonrpc("query_loki_logs", params)
    
    # 쿼리 컨텍스트에 추가
    context.add_query(query_request.logql_query)
    
    return {
        "result": f"로그 쿼리 결과 ({len(logs)} 항목)",
        "logs": logs,
        "context": context.dict()
    }

async def get_loki_datasource_uid() -> str:
    """Loki 데이터소스 UID 가져오기"""
    try:
        datasources = await call_loki_api_jsonrpc("list_datasources", {"type": "loki"})
        
        if datasources and len(datasources) > 0:
            return datasources[0].get("uid", "loki")
        
        return "loki"  # 기본값
    except Exception as e:
        logger.error(f"Loki 데이터소스 UID 조회 오류: {str(e)}")
        return "loki"  # 기본값

async def get_label_names() -> List[str]:
    """Loki 라벨 목록 가져오기"""
    try:
        return await call_loki_api_jsonrpc("list_loki_label_names")
    except Exception as e:
        logger.error(f"Loki 라벨 목록 조회 오류: {str(e)}")
        return []

async def get_label_values(label_name: str) -> List[str]:
    """Loki 라벨 값 목록 가져오기"""
    try:
        result = await call_loki_api_jsonrpc("list_loki_label_values", {"label": label_name})
        
        # 응답 데이터 구조 처리
        if isinstance(result, dict) and "data" in result:
            data = result["data"]
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "data" in data:
                return data["data"]
        
        # 응답이 비어있거나 다른 형식인 경우 기본값 제공
        if label_name == "service":
            logger.info("서비스 라벨 값이 비어있어 기본값 반환")
            return ["order-service", "payment-service", "user-service", "api-gateway"]
        return []
    except Exception as e:
        logger.error(f"Loki 라벨 값 목록 조회 오류: {str(e)}")
        if label_name == "service":
            return ["order-service", "payment-service", "user-service", "api-gateway"]
        return []

# API 엔드포인트
@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    # Loki API 헬스 체크
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{LOKI_API_URL}/health")
            if response.status_code == 200:
                loki_api_status = "healthy"
            else:
                loki_api_status = f"unhealthy - {response.status_code}"
    except Exception as e:
        loki_api_status = f"unhealthy - {str(e)}"
    
    # LangGraph API 헬스 체크
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{LANGGRAPH_URL}/health")
            if response.status_code == 200:
                langgraph_status = "healthy"
            else:
                langgraph_status = f"unhealthy - {response.status_code}"
    except Exception as e:
        langgraph_status = f"unhealthy - {str(e)}"
    
    return {
        "status": "ok",
        "loki_api_status": loki_api_status,
        "langgraph_status": langgraph_status,
        "api_version": "1.0.0"
    }

@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """LangGraph API 쿼리 엔드포인트"""
    context = request.context
    
    # 사용자 메시지 컨텍스트에 추가
    if "mcp_context" not in context:
        context["mcp_context"] = MCPContext().dict()
    
    mcp_context = MCPContext(**context["mcp_context"])
    mcp_context.add_message("user", request.query)
    
    # LangGraph API 호출
    result = await call_langgraph_api(request.query, context)
    
    # LangGraph 응답 컨텍스트에 추가
    mcp_context.add_message("system", result.get("response", ""))
    
    # 업데이트된 컨텍스트 저장
    result["context"]["mcp_context"] = mcp_context.dict()
    
    return result

@app.post("/api/loki/query_logs")
async def api_query_logs(request: LogQueryRequest, context: Dict[str, Any] = {}):
    """로그 쿼리 API"""
    # MCP 컨텍스트 생성 또는 가져오기
    if "mcp_context" not in context:
        mcp_context = MCPContext()
    else:
        mcp_context = MCPContext(**context["mcp_context"])
    
    return await query_logs(mcp_context, request)

@app.get("/api/loki/datasource_uid")
async def api_get_datasource_uid(context: Dict[str, Any] = {}):
    """Loki 데이터소스 UID 가져오기"""
    datasource_uid = await get_loki_datasource_uid()
    return {"datasource_uid": datasource_uid}

@app.get("/api/loki/label_names")
async def api_get_label_names(context: Dict[str, Any] = {}):
    """Loki 라벨 목록 가져오기"""
    labels = await get_label_names()
    return {"labels": labels}

@app.get("/api/loki/label_values/{label_name}")
async def api_get_label_values(label_name: str, context: Dict[str, Any] = {}):
    """Loki 라벨 값 목록 가져오기"""
    values = await get_label_values(label_name)
    return {"values": values}

@app.get("/api/loki/context")
async def api_get_context(context: Dict[str, Any] = {}):
    """MCP 컨텍스트 가져오기"""
    if "mcp_context" not in context:
        mcp_context = MCPContext().dict()
    else:
        mcp_context = context["mcp_context"]
    
    return {"context": mcp_context}

@app.post("/api/loki/context")
async def api_update_context(context: Dict[str, Any]):
    """MCP 컨텍스트 업데이트"""
    return {"context": context}

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
        if method == "list_datasources":
            # 데이터소스 목록 조회
            datasource_type = params.get("type", "")
            datasources = await call_loki_api_jsonrpc("list_datasources", {"type": datasource_type})
            return {"jsonrpc": "2.0", "result": datasources, "id": id}
        
        elif method == "list_loki_label_names" or method == "get_loki_labels":
            # 라벨 목록 조회
            datasource_uid = params.get("datasourceUid", "")
            labels = await get_label_names()
            return {"jsonrpc": "2.0", "result": {"data": labels}, "id": id}
        
        elif method == "list_loki_label_values" or method == "get_loki_label_values":
            # 라벨 값 목록 조회
            datasource_uid = params.get("datasourceUid", "")
            label_name = params.get("labelName", "")
            label = params.get("label", "")
            
            # label_name 또는 label 파라미터 사용
            label_to_use = label_name if label_name else label
            
            if not label_to_use:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "Label name is required"}, "id": id}
            
            values = await get_label_values(label_to_use)
            return {"jsonrpc": "2.0", "result": {"data": values}, "id": id}
        
        elif method == "query_loki_logs" or method == "query_loki":
            # 로그 쿼리
            datasource_uid = params.get("datasourceUid", "")
            logql = params.get("logql", "")
            query = params.get("query", "")  # 대체 파라미터
            start = params.get("startRfc3339", "") or params.get("start", "")
            end = params.get("endRfc3339", "") or params.get("end", "")
            limit = params.get("limit", 100)
            direction = params.get("direction", "backward")
            
            # logql 또는 query 파라미터 사용
            query_to_use = logql if logql else query
            
            api_params = {
                "logql": query_to_use,
                "startRfc3339": start,
                "endRfc3339": end,
                "limit": limit,
                "direction": direction
            }
            
            logs = await call_loki_api_jsonrpc("query_loki_logs", api_params)
            return {"jsonrpc": "2.0", "result": logs, "id": id}
        
        else:
            # 지원하지 않는 메소드
            return {"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Method '{method}' not found"}, "id": id}
    
    except Exception as e:
        logger.error(f"JSON-RPC 메소드 실행 오류: {str(e)}")
        return {"jsonrpc": "2.0", "error": {"code": -32603, "message": f"Internal error: {str(e)}"}, "id": id}

# 서버 실행
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8003))
    uvicorn.run("mcp_server:app", host="0.0.0.0", port=port, reload=True) 