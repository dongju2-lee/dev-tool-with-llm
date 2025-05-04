"""
LangGraph 서버 - 로그 분석 및 지원 의사결정 워크플로
"""
import os
import json
import logging
import traceback
from typing import Dict, List, Any, Tuple, Literal, Optional, TypedDict, Annotated, Union
from datetime import datetime, timedelta, timezone
import time
import re
import random
import asyncio
import aiohttp
import hashlib

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import httpx
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.globals import set_debug
from langchain.globals import set_verbose

from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolExecutor, ToolInvocation

import requests

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/langgraph.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("langgraph")

# 환경 변수 설정
from dotenv import load_dotenv
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
API_URL = os.getenv("API_URL", "http://localhost:8002")
# MCP URL 설정
MCP_URL = os.getenv("MCP_URL", "http://loki-mcp:8003")
TEMPO_MCP_URL = os.getenv("TEMPO_MCP_URL", "http://tempo-mcp:8004")
PORT = int(os.getenv("PORT", 8001))
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://grafana:3000")
LOKI_URL = os.getenv("LOKI_URL", "http://loki:3100")

# JSON-RPC 엔드포인트 설정
MCP_RPC_URL = os.getenv("MCP_RPC_URL", "http://loki-mcp:8003")
TEMPO_RPC_URL = os.getenv("TEMPO_RPC_URL", "http://tempo-mcp:8004")
# MCP API URL - JSON-RPC 요청용
MCP_API_URL = os.getenv("MCP_API_URL", "http://loki-mcp:8003")

# Docker 네트워크 정보 로깅
logger.info(f"MCP_API_URL: {MCP_API_URL}")
logger.info(f"TEMPO_RPC_URL: {TEMPO_RPC_URL}")
logger.info(f"MCP_URL: {MCP_URL}")

# FastAPI 앱 설정
app = FastAPI(title="LangGraph 서버 - 로그 분석 및 API 서버 연동 워크플로")

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# LLM 인스턴스 설정
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=GOOGLE_API_KEY,
    temperature=0,
    convert_system_message_to_human=True
)

# == 데이터 모델 ==
class UserQuery(BaseModel):
    user_id: str
    query: str
    context: Optional[Dict[str, Any]] = {}

class QueryResponse(BaseModel):
    response: Dict[str, Any]
    context: Dict[str, Any]

# == 로그 분석 워크플로 상태 ==
class LogAnalysisState(TypedDict):
    user_id: str
    query: str
    intent: str
    parameters: Dict[str, Any]
    log_data: Optional[Dict[str, Any]]
    analysis_results: Optional[Dict[str, Any]]
    trace_data: Optional[Dict[str, Any]]
    response: Optional[str]
    context: Dict[str, Any]
    error: Optional[str]

# == 의도 감지 ==
async def detect_intent(state: LogAnalysisState) -> LogAnalysisState:
    """
    사용자 쿼리에서 의도를 감지합니다.
    """
    user_query = state["user_query"]["text"]
    logger.info(f"의도 감지: 사용자 쿼리 = {user_query}")
    
    # 로그 관련 키워드
    log_keywords = [
        "로그", "log", "logs", "logging", "에러", "error", "warning", "경고", 
        "debug", "디버그", "info", "정보", "출력", "메시지", "message"
    ]
    
    # 트레이스 관련 키워드
    trace_keywords = [
        "트레이스", "trace", "traces", "tracing", "span", "스팬", "추적", 
        "flow", "플로우", "call", "호출", "요청", "request", "chain", "체인"
    ]
    
    # 서비스 상태 관련 키워드
    status_keywords = [
        "상태", "status", "health", "헬스", "alive", "살아있나", "동작", 
        "running", "실행", "작동", "working", "up", "down", "metrics", "메트릭"
    ]
    
    # 키워드 매칭
    log_count = sum(1 for kw in log_keywords if kw.lower() in user_query.lower())
    trace_count = sum(1 for kw in trace_keywords if kw.lower() in user_query.lower())
    status_count = sum(1 for kw in status_keywords if kw.lower() in user_query.lower())
    
    logger.info(f"키워드 매칭: 로그={log_count}, 트레이스={trace_count}, 상태={status_count}")
    
    # 의도 판별
    if log_count > trace_count and log_count > status_count:
        state["detected_intent"] = "LOG_QUERY"
        logger.info("감지된 의도: 로그 쿼리")
    elif trace_count > log_count and trace_count > status_count:
        state["detected_intent"] = "TRACE_QUERY"
        logger.info("감지된 의도: 트레이스 쿼리")
    elif status_count > log_count and status_count > trace_count:
        state["detected_intent"] = "STATUS_QUERY"
        logger.info("감지된 의도: 상태 쿼리")
    else:
        # 기본값은 로그 쿼리
        state["detected_intent"] = "LOG_QUERY"
        logger.info("감지된 의도: 기본값(로그 쿼리)")
    
    return state

# == 파라미터 추출 ==
async def extract_parameters(state: LogAnalysisState) -> LogAnalysisState:
    """사용자 쿼리에서 매개변수를 추출합니다."""
    intent = state["detected_intent"]
    
    # 사용자 쿼리에서 매개변수 추출 시도
    user_query = state["user_query"]["text"]
    
    # 서비스 추출
    service = None
    if "service" in state["parameters"]:
        service = state["parameters"]["service"]
        logger.info(f"사용자 쿼리에서 직접 서비스 추출: {service}")
    else:
        # 지정된 서비스 이름 찾기
        service_pattern = r'(order-service|frontend|backend|database|cache|auth)'
        service_match = re.search(service_pattern, user_query, re.IGNORECASE)
        if service_match:
            service = service_match.group(1).lower()
            logger.info(f"정규식으로 서비스 추출: {service}")
        else:
            # 이미 알려진 서비스 목록 가져오기
            service_values = await get_available_labels()
            logger.info(f"서비스 값 목록: {service_values}")
            
            # 사용자 쿼리에서 서비스 이름 찾기
            matched_services = []
            for svc in service_values:
                if svc.lower() in user_query.lower():
                    matched_services.append(svc)
            
            if matched_services:
                service = matched_services[0]  # 첫 번째 일치하는 서비스 사용
                logger.info(f"사용자 쿼리에서 서비스 매칭: {service}")
            else:
                # 쿼리에서 서비스를 찾을 수 없는 경우 기본값 설정
                service = "order-service"  # 기본값
                logger.info(f"서비스를 찾을 수 없어 기본값 사용: {service}")
    
    # 시간 범위 추출
    time_range_pattern = r'(\d+)\s*(분|시간|일|주|개월|달)'
    time_range_match = re.search(time_range_pattern, user_query)
    
    if time_range_match:
        value = int(time_range_match.group(1))
        unit = time_range_match.group(2)
        
        if unit == "분":
            time_range = f"{value}m"
        elif unit == "시간":
            time_range = f"{value}h"
        elif unit in ["일", "하루"]:
            time_range = f"{value}d"
        elif unit in ["주", "한주"]:
            time_range = f"{value}w"
        elif unit in ["개월", "달", "월"]:
            time_range = f"{value}M"
        else:
            time_range = "1h"  # 기본값
    else:
        # 'N시간 동안', 'N시간 전부터' 등의 패턴
        alt_pattern = r'지난\s+(\d+)\s*(분|시간|일|주|개월|달)'
        alt_match = re.search(alt_pattern, user_query)
        if alt_match:
            value = int(alt_match.group(1))
            unit = alt_match.group(2)
            
            if unit == "분":
                time_range = f"{value}m"
            elif unit == "시간":
                time_range = f"{value}h"
            elif unit in ["일", "하루"]:
                time_range = f"{value}d"
            elif unit in ["주", "한주"]:
                time_range = f"{value}w"
            elif unit in ["개월", "달", "월"]:
                time_range = f"{value}M"
            else:
                time_range = "1h"  # 기본값
        else:
            time_range = "1h"  # 기본값
    
    logger.info(f"추출된 시간 범위: {time_range}")
    
    # 로그 레벨 추출
    level_values = ["error", "warn", "warning", "info", "debug"]
    matched_levels = []
    
    for level in level_values:
        if level.lower() in user_query.lower():
            matched_levels.append(level)
    
    # 한국어 로그 레벨도 처리
    if "오류" in user_query or "에러" in user_query:
        matched_levels.append("error")
    elif "경고" in user_query:
        matched_levels.append("warn")
    elif "정보" in user_query:
        matched_levels.append("info")
    elif "디버그" in user_query:
        matched_levels.append("debug")
    
    # 사용자가 특정 로그 레벨을 지정하지 않았다면 모든 로그 레벨을 가져옴
    level = matched_levels[0] if matched_levels else None
    logger.info(f"추출된 로그 레벨: {level if level else '모든 레벨'}")
    
    # 직접적인 태그 추출 (예: namespace=default)
    tag_pattern = r'(\w+)=(\w+)'
    tags = {}
    for match in re.finditer(tag_pattern, user_query):
        key, value = match.groups()
        tags[key] = value
    
    logger.info(f"추출된 태그: {tags}")
    
    # 매개변수 업데이트
    state["parameters"] = {
        "service": service,
        "timeRange": time_range,
        **tags,
        **state["parameters"]  # 기존 매개변수 유지
    }
    
    # 레벨이 지정된 경우에만 추가
    if level:
        state["parameters"]["level"] = level
    
    return state

# == 라벨 조회 ==
async def get_available_labels():
    """Loki에서 사용 가능한 레이블 목록을 가져옵니다."""
    try:
        logger.info("사용 가능한 레이블 목록 조회")
        
        async with httpx.AsyncClient() as client:
            payload = {
                "jsonrpc": "2.0",
                "method": "get_loki_labels",
                "params": {},
                "id": 1
            }
            
            response = await client.post(
                f"{MCP_URL}/rpc/v1",
                json=payload,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"레이블 목록 조회 오류: {response.status_code}")
                return ["service", "container", "pod", "namespace", "level"]
            
            result = response.json()
            logger.info(f"레이블 목록 응답: {result}")
            
            # JSON-RPC 응답 처리
            if "result" in result:
                result_data = result["result"]
                if isinstance(result_data, dict) and "data" in result_data:
                    data = result_data["data"]
                    if isinstance(data, dict) and "data" in data:
                        labels = data["data"]
                    elif isinstance(data, list):
                        labels = data
                    else:
                        labels = []
                else:
                    labels = result_data if isinstance(result_data, list) else []
                
                if labels:
                    logger.info(f"레이블 {len(labels)}개 찾음: {labels}")
                    return labels
            
            logger.warning("레이블을 찾을 수 없어 기본값을 사용합니다")
            return ["service", "container", "pod", "namespace", "level"]
    except Exception as e:
        logger.error(f"레이블 조회 중 오류: {str(e)}")
        return ["service", "container", "pod", "namespace", "level"]

async def get_label_values(label: str) -> List[str]:
    """지정된 레이블에 대한 값 목록을 가져옵니다."""
    try:
        logger.info(f"레이블 '{label}'에 대한 값 가져오기")
        
        # 요청 파라미터 형식 수정
        payload = {
            "jsonrpc": "2.0",
            "method": "list_loki_label_values",
            "params": {
                "label": label
            },
            "id": 1
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MCP_URL}/rpc/v1",
                json=payload,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"레이블 값 조회 오류: {response.status_code}")
                if label == "service":
                    return ["order-service", "payment-service", "user-service", "api-gateway", "frontend", "backend", "database", "cache", "auth"]
                return []
            
            result = response.json()
            logger.info(f"레이블 값 응답: {result}")
            
            # 다양한 응답 형식 처리 개선
            values = []
            
            # 1. 기본 JSON-RPC 응답 구조
            if "result" in result:
                result_data = result["result"]
                
                # 2. result가 직접 데이터 배열인 경우
                if isinstance(result_data, list):
                    values = result_data
                    logger.info(f"직접 배열 형식 응답: {len(values)} 항목")
                
                # 3. result가 객체이고 data 필드가 있는 경우
                elif isinstance(result_data, dict):
                    if "data" in result_data:
                        data = result_data["data"]
                        
                        # 3.1 data가 직접 배열인 경우
                        if isinstance(data, list):
                            values = data
                            logger.info(f"data 배열 형식 응답: {len(values)} 항목")
                        
                        # 3.2 중첩된 data 구조 (data.data)
                        elif isinstance(data, dict) and "data" in data:
                            nested_data = data["data"]
                            if isinstance(nested_data, list):
                                values = nested_data
                                logger.info(f"중첩 data 형식 응답: {len(values)} 항목")
                
                # 4. 단순 응답 형식인 경우 (status: success만 있는 경우)
                elif isinstance(result_data, dict) and "status" in result_data and result_data["status"] == "success":
                    logger.warning("status:success 형식 응답, 기본값 반환")
                    if label == "service":
                        values = ["order-service", "payment-service", "user-service", "api-gateway", "frontend", "backend", "database", "cache", "auth"]
            
            # 값이 비어있고 서비스 레이블인 경우 기본값 사용
            if not values and label == "service":
                logger.warning("서비스 값을 찾을 수 없어 기본값을 사용합니다.")
                values = ["order-service", "payment-service", "user-service", "api-gateway", "frontend", "backend", "database", "cache", "auth"]
                
            logger.info(f"레이블 '{label}'에 대한 값: {values}")
            return values
    except Exception as e:
        logger.error(f"레이블 값 가져오기 오류: {str(e)}")
        if label == "service":
            return ["order-service", "payment-service", "user-service", "api-gateway", "frontend", "backend", "database", "cache", "auth"]
        return []

async def get_loki_datasource_uid() -> str:
    """MCP 서버에서 Loki 데이터소스 UID를 가져옵니다."""
    try:
        logger.info("Loki 데이터소스 UID 조회 시작")
        
        payload = {
            "jsonrpc": "2.0",
            "method": "list_datasources",
            "params": {
                "type": "loki"
            },
            "id": 1
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MCP_URL}/rpc/v1",
                json=payload,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"데이터소스 조회 오류: {response.status_code}")
                return "loki"
            
            result = response.json()
            logger.info(f"데이터소스 응답: {result}")
            
            # JSON-RPC 응답 처리
            if "result" in result:
                datasources = result["result"]
                for ds in datasources:
                    if isinstance(ds, dict) and ds.get("type") == "loki":
                        uid = ds.get("uid")
                        if uid:
                            logger.info(f"Loki 데이터소스 UID 찾음: {uid}")
                            return uid
            
        logger.warning("Loki 데이터소스를 찾을 수 없어 기본값 사용")
        return "loki"
    except Exception as e:
        logger.error(f"데이터소스 UID 조회 중 오류: {str(e)}")
        return "loki"

# == MCP-Grafana 서버에 로그 쿼리 요청 ==
async def query_logs(
    service_name: str, 
    time_range: Optional[Tuple[datetime, datetime]] = None,
    query_filter: Optional[str] = None,
    state: Optional[LogAnalysisState] = None
) -> List[Dict[str, Any]]:
    """Loki에서 로그를 쿼리합니다."""
    try:
        # 기본 시간 범위: 현재 시간에서 1시간 전까지
        if not time_range:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=1)
        else:
            start_time, end_time = time_range
        
        # 타임스탬프를 문자열 형식으로 변환 (ISO 8601)
        start_ts_str = start_time.isoformat()
        end_ts_str = end_time.isoformat()
        
        # 로그 쿼리 로직
        logger.info(f"로그 쿼리 시작: 서비스={service_name}, 시작={start_time}, 종료={end_time}")
        
        # LLM을 사용하여 LogQL 쿼리 생성 (if state is provided)
        if state:
            try:
                log_query = await generate_logql_query_with_llm(state)
            except Exception as e:
                logger.error(f"LogQL 쿼리 생성 중 오류: {str(e)}")
                # 기본 쿼리 생성
                log_query = f'{{service="{service_name}"}}'
        else:
            # 기본 로그 쿼리를 구성합니다
            log_query = f'{{service="{service_name}"}}'
            
            # 추가 필터가 있으면 필터 연산자 수정
            if query_filter:
                log_query = f'{log_query} |= "{query_filter}"'
        
        logger.info(f"로그 쿼리: {log_query}")
        
        payload = {
            "jsonrpc": "2.0",
            "method": "query_loki",
            "params": {
                "query": log_query,
                "start": start_ts_str,
                "end": end_ts_str,
                "limit": 100
            },
            "id": 1
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MCP_URL}/rpc/v1",
                json=payload,
                timeout=15
            )
            
            if response.status_code != 200:
                logger.error(f"로그 쿼리 오류: {response.status_code}")
                return []
            
            result = response.json()
            logger.debug(f"로그 쿼리 응답: {result}")
            
            # JSON-RPC 응답 처리 로직 개선
            log_entries = []
            
            if "result" in result:
                result_data = result["result"]
                
                # 직접 data 배열을 가진 경우 (신규 API 응답 형식)
                if isinstance(result_data, dict) and "data" in result_data:
                    data = result_data["data"]
                    if isinstance(data, list):
                        # 응답이 이미 로그 항목 리스트인 경우
                        log_entries = data
                        logger.info(f"직접 로그 항목 {len(log_entries)}개 발견")
                    elif isinstance(data, dict) and "data" in data:
                        # 중첩된 data 구조 처리
                        nested_data = data["data"]
                        if isinstance(nested_data, list):
                            log_entries = nested_data
                            logger.info(f"중첩된 로그 항목 {len(log_entries)}개 발견")
            
            if log_entries:
                logger.info(f"로그 항목 {len(log_entries)}개 반환")
                return log_entries
            else:
                logger.warning("로그를 찾을 수 없습니다")
                return []
    except Exception as e:
        logger.error(f"로그 쿼리 중 오류: {str(e)}")
        logger.error(traceback.format_exc())
        return []

def build_logql_query(
    service: Optional[str] = None,
    trace_id: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    LogQL 쿼리를 구성합니다.
    
    매개변수:
        service: 쿼리할 서비스 이름 (선택적)
        trace_id: 트레이스 ID (선택적)
        filters: 추가 필터 조건 (선택적)
        
    반환값:
        구성된 LogQL 쿼리 문자열 또는 None (구성 실패 시)
    """
    # 필터 조건 초기화
    filter_conditions = []
    
    # 서비스 이름으로 필터링
    if service:
        filter_conditions.append(f'service="{service}"')
    
    # 추가 필터 처리
    if filters:
        # 레벨 필터
        if 'level' in filters and filters['level']:
            filter_conditions.append(f'level="{filters["level"]}"')
        
        # 사용자 정의 라벨 필터
        if 'labels' in filters and isinstance(filters['labels'], dict):
            for key, value in filters['labels'].items():
                if key and value:
                    filter_conditions.append(f'{key}="{value}"')
    
    # 필터 조건이 없는 경우
    if not filter_conditions:
        # 서비스와 트레이스 ID가 모두 없는 경우, 기본 필터 사용
        filter_conditions.append('{}')
    
    # 라벨 셀렉터 구성
    label_selector = '{' + ', '.join(filter_conditions) + '}'
    
    # 라인 필터 구성
    line_filters = []
    
    # 트레이스 ID로 필터링
    if trace_id:
        line_filters.append(f'|~ "trace_id.*{trace_id}"')
    
    # 텍스트 검색 필터
    if filters and 'message' in filters and filters['message']:
        message_filter = filters['message'].replace('"', '\\"')
        line_filters.append(f'|~ "{message_filter}"')
    
    # 최종 쿼리 구성
    query = label_selector
    if line_filters:
        query += ' '.join(line_filters)
    
    return query

def to_rfc3339(timestamp_ns: int) -> str:
    """
    나노초 타임스탬프를 RFC3339 형식 문자열로 변환합니다.
    
    매개변수:
        timestamp_ns: 나노초 단위 타임스탬프
        
    반환값:
        RFC3339 형식 문자열
    """
    seconds = timestamp_ns / 1e9
    dt = datetime.utcfromtimestamp(seconds)
    microseconds = int((timestamp_ns % 1e9) / 1e3)
    dt = dt.replace(microsecond=microseconds)
    return dt.isoformat("T") + "Z"

def parse_time_range(time_range: str) -> int:
    """
    문자열 형식의 시간 범위를 초 단위로 변환합니다.
    
    매개변수:
        time_range: 시간 범위 문자열 (예: "1h", "3h", "1d")
        
    반환값:
        경과 시간(초)
    """
    now = time.time()
    
    # '3h'와 같은 간단한 형식 처리
    simple_match = re.match(r'(\d+)([hmd])', time_range, re.IGNORECASE)
    if simple_match:
        value = int(simple_match.group(1))
        unit = simple_match.group(2).lower()
        if unit == 'h':
            seconds = value * 3600
        elif unit == 'm':
            seconds = value * 60
        elif unit == 'd':
            seconds = value * 86400
        else:
            seconds = 3600  # 기본값: 1시간
        return seconds
    
    # "last Xh/m/d" 형식 처리
    last_match = re.match(r'last\s+(\d+)([hmd])', time_range, re.IGNORECASE)
    if last_match:
        value = int(last_match.group(1))
        unit = last_match.group(2).lower()
        if unit == 'h':
            seconds = value * 3600
        elif unit == 'm':
            seconds = value * 60
        elif unit == 'd':
            seconds = value * 86400
        else:
            seconds = 3600
        return seconds
    
    # "now-Xh/m/d" 형식 처리
    now_match = re.match(r'now-(\d+)([hmd])', time_range, re.IGNORECASE)
    if now_match:
        value = int(now_match.group(1))
        unit = now_match.group(2).lower()
        if unit == 'h':
            seconds = value * 3600
        elif unit == 'm':
            seconds = value * 60
        elif unit == 'd':
            seconds = value * 86400
        else:
            seconds = 3600
        return seconds
    
    # 한국어 표현 처리 (예: "3시간", "10분", "2일")
    kr_match = re.match(r'(\d+)(시간|분|일)', time_range)
    if kr_match:
        value = int(kr_match.group(1))
        unit = kr_match.group(2)
        if unit == '시간':
            seconds = value * 3600
        elif unit == '분':
            seconds = value * 60
        elif unit == '일':
            seconds = value * 86400
        else:
            seconds = 3600
        return seconds
    
    # 기본값: 1시간 (3600초)
    return 3600

async def query_traces(
    service_name: str,
    time_range: Optional[Tuple[datetime, datetime]] = None,
    operation_name: Optional[str] = None,
    trace_duration_min: Optional[float] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Tempo에서 트레이스를 쿼리합니다."""
    try:
        # 기본 시간 범위: 현재 시간에서 1시간 전까지
        if not time_range:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=1)
        else:
            start_time, end_time = time_range
        
        # 타임스탬프를 문자열 형식으로 변환 (ISO 8601)
        start_ts_str = start_time.isoformat()
        end_ts_str = end_time.isoformat()
        
        logger.info(f"트레이스 쿼리 시작: 서비스={service_name}, 시작={start_time}, 종료={end_time}")

        # 검색 조건 설정
        search_params = {
            "service": service_name,
            "start": start_ts_str,
            "end": end_ts_str,
            "limit": limit
        }

        # 선택적 파라미터 추가
        if operation_name:
            search_params["operation"] = operation_name
        
        if trace_duration_min is not None:
            search_params["minDuration"] = f"{int(trace_duration_min * 1000000)}ns"
        
        # JSON-RPC 요청 구성
        payload = {
            "jsonrpc": "2.0",
            "method": "query_tempo",
            "params": search_params,
            "id": 1
        }
        
        logger.info(f"트레이스 쿼리 요청: {search_params}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TEMPO_MCP_URL}/rpc/v1",
                json=payload,
                timeout=15
            )
            
            if response.status_code != 200:
                logger.error(f"트레이스 쿼리 오류: {response.status_code}")
                return []
            
            result = response.json()
            logger.info(f"트레이스 쿼리 응답: {result}")
            
            # JSON-RPC 응답 처리
            if "result" in result:
                result_data = result["result"]
                # result_data가 딕셔너리이고 "traces" 필드가 있는 경우 (원래 예상 형식)
                if isinstance(result_data, dict) and "traces" in result_data:
                    traces = result_data["traces"]
                    logger.info(f"트레이스 {len(traces)}개 반환")
                    return traces
                # result_data가 직접 리스트인 경우 (현재 실제 응답 형식)
                elif isinstance(result_data, list):
                    logger.info(f"트레이스 {len(result_data)}개 반환")
                    return result_data
            
            logger.warning("트레이스를 찾을 수 없습니다")
            return []
    except Exception as e:
        logger.error(f"트레이스 쿼리 중 오류: {str(e)}")
        return []

async def async_query_logs(state: LogAnalysisState) -> LogAnalysisState:
    """LogAnalysisState에서 파라미터를 추출하여 로그 쿼리를 실행합니다."""
    # 파라미터 추출
    params = state.get("parameters", {})
    service = params.get("service")
    
    if not service:
        logger.error("로그 쿼리에 서비스 지정이 필요합니다")
        state["log_data"] = None
        return state
    
    # 시간 범위 처리
    time_range = params.get("timeRange", "1h")
    time_range_value = 60  # 기본값: 60분 (1시간)
    
    if isinstance(time_range, str):
        if time_range.endswith("m"):
            time_range_value = int(time_range[:-1])
        elif time_range.endswith("h"):
            time_range_value = int(time_range[:-1]) * 60  # 시간을 분으로 변환
        elif time_range.endswith("d"):
            time_range_value = int(time_range[:-1]) * 60 * 24  # 일을 분으로 변환
    
    # 시간 범위 계산
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=time_range_value)
    
    # LLM 기반 쿼리로 직접 로그 조회
    result = await query_logs(
        service_name=service,
        time_range=(start_time, end_time),
        state=state  # 전체 상태 전달하여 LLM 쿼리 생성
    )
    
    if result:
        logger.info(f"{len(result)}개의 로그 항목을 찾았습니다")
        state["log_data"] = result
        
        # 로그에서 트레이스 ID 추출
        trace_ids = extract_trace_ids_from_logs(result)
        if trace_ids:
            state["extracted_trace_ids"] = trace_ids
            logger.info(f"로그에서 {len(trace_ids)}개의 트레이스 ID를 추출했습니다: {trace_ids[:5]}")
    else:
        logger.warning("로그를 찾을 수 없습니다")
        state["log_data"] = []
    
    return state

def extract_trace_ids_from_logs(logs: List[Dict[str, Any]]) -> List[str]:
    """로그에서 트레이스 ID를 추출합니다."""
    trace_ids = set()
    
    # 정규 표현식 패턴
    # 1. trace_id=HEXSTRING 또는 traceID=HEXSTRING 패턴
    # 2. "traceId":"HEXSTRING" 또는 "trace_id":"HEXSTRING" JSON 패턴
    # 3. 단독 32/64자 16진수 문자열
    patterns = [
        re.compile(r'trace[_-]?id\s*[=:]\s*["\']?([0-9a-f]{16,64})["\']?', re.IGNORECASE),
        re.compile(r'["\']trace[_-]?id["\']\s*:\s*["\']([0-9a-f]{16,64})["\']', re.IGNORECASE),
        re.compile(r'(?<![0-9a-f])([0-9a-f]{32}|[0-9a-f]{64})(?![0-9a-f])')
    ]
    
    for log in logs:
        message = log.get("line", log.get("message", ""))
        
        for pattern in patterns:
            matches = pattern.findall(message)
            for match in matches:
                # 유효한 트레이스 ID인지 검증
                if all(c in "0123456789abcdef" for c in match.lower()):
                    trace_ids.add(match)
    
    return list(trace_ids)

async def async_query_traces(state: LogAnalysisState) -> LogAnalysisState:
    """트레이스 쿼리를 실행합니다."""
    params = state.get("parameters", {})
    service = params.get("service", "order-service")
    
    # 시간 범위 처리
    time_range = params.get("timeRange", "1h")
    seconds = parse_time_range(time_range)
    end_time = datetime.now()
    start_time = end_time - timedelta(seconds=seconds)
    
    # 로그 데이터 확인
    log_data = state.get("log_data", [])
    
    # 트레이스 ID 추출
    trace_ids = set()
    
    # 1. 로그에서 트레이스 ID 추출
    if log_data:
        extracted_ids = extract_trace_ids_from_logs(log_data)
        trace_ids.update(extracted_ids)
        logger.info(f"로그에서 {len(extracted_ids)}개의 트레이스 ID를 추출했습니다: {extracted_ids}")
    
    # 2. 파라미터에서 직접 트레이스 ID 체크
    if params.get("trace_id"):
        trace_ids.add(params.get("trace_id"))
        logger.info(f"파라미터에서 트레이스 ID 추출: {params.get('trace_id')}")
    
    traces = []
    
    # 트레이스 ID가 있으면 해당 ID로 쿼리
    if trace_ids:
        for trace_id in trace_ids:
            logger.info(f"트레이스 ID로 쿼리: {trace_id}")
            trace_result = await query_trace_by_id(trace_id)
            if trace_result:
                traces.extend(trace_result)
    
    # 트레이스 ID가 없거나 결과가 없으면 서비스 기반 쿼리
    if not traces:
        logger.info(f"서비스 기반 트레이스 쿼리: {service}, 시작={start_time}, 종료={end_time}")
        try:
            additional_params = {
                "limit": 10
            }
            
            # 오류 필터
            if params.get("errors") or params.get("error") or params.get("show_errors"):
                additional_params["error_traces"] = True
            
            # 최소/최대 지속 시간
            for param_name, api_param in [("min_duration", "min_duration"), ("max_duration", "max_duration")]:
                if params.get(param_name):
                    additional_params[api_param] = params.get(param_name)
            
            trace_result = await query_traces(
                service_name=service,
                time_range=(start_time, end_time),
                operation_name=params.get("operation"),
                **additional_params
            )
            traces.extend(trace_result)
        except Exception as e:
            logger.error(f"트레이스 쿼리 실행 중 오류: {str(e)}")
    
    # 트레이스가 여전히 없으면 샘플 데이터 생성 고려
    if not traces and log_data:
        logger.warning("실제 트레이스를 찾을 수 없어 로그 기반 샘플 트레이스 생성을 시도합니다")
        # 로그 데이터에서 서비스 및 작업 정보 추출하여 트레이스 생성
        traces = generate_sample_traces_from_logs(log_data, service)
    
    logger.info(f"{len(traces)}개의 트레이스를 찾았습니다")
    state["trace_data"] = traces
    return state

def generate_sample_traces_from_logs(logs: List[Dict[str, Any]], default_service: str) -> List[Dict[str, Any]]:
    """로그 데이터를 기반으로 샘플 트레이스 데이터를 생성합니다."""
    logger.info(f"{len(logs)}개의 로그 항목으로부터 샘플 트레이스 생성")
    
    # 로그에서 서비스 및 엔드포인트 패턴 추출
    service_pattern = re.compile(r'service[=:][\'"]([\w-]+)[\'"]', re.IGNORECASE)
    endpoint_pattern = re.compile(r'(GET|POST|PUT|DELETE|PATCH)\s+(\/[\w\/\-{}]+)', re.IGNORECASE)
    error_pattern = re.compile(r'(error|exception|fail|failed|timeout)', re.IGNORECASE)
    
    traces = []
    processed_logs = 0
    
    # 로그 그룹화 (시간적으로 가까운 로그는 같은 트레이스일 가능성이 높음)
    log_groups = []
    current_group = []
    last_timestamp = None
    
    # 로그 시간순 정렬
    sorted_logs = sorted(logs, key=lambda x: x.get("timestamp", ""))
    
    for log in sorted_logs:
        timestamp = log.get("timestamp", "")
        if not timestamp:
            continue
            
        # 새 그룹 시작 조건: 첫 로그이거나 이전 로그와 시간 차이가 1초 이상
        if not last_timestamp or not current_group:
            current_group = [log]
            last_timestamp = timestamp
        else:
            # 시간 차이 계산 (간단한 문자열 비교로 대체)
            time_diff = abs(timestamp.replace(last_timestamp, ""))
            if time_diff > "1":  # 1초 이상 차이
                if current_group:
                    log_groups.append(current_group)
                current_group = [log]
            else:
                current_group.append(log)
            last_timestamp = timestamp
    
    # 마지막 그룹 추가
    if current_group:
        log_groups.append(current_group)
    
    # 각 로그 그룹에서 트레이스 생성
    for group_idx, log_group in enumerate(log_groups):
        if not log_group:
            continue
            
        # 첫 로그에서 정보 추출
        first_log = log_group[0]
        message = first_log.get("line", first_log.get("message", ""))
        
        # 서비스명 추출, 없으면 기본값 사용
        service_match = service_pattern.search(message)
        span_service = service_match.group(1) if service_match else default_service
        
        # 엔드포인트 추출, 없으면 기본값 사용
        span_endpoint_match = endpoint_pattern.search(message)
        span_operation = span_endpoint_match.group(2) if span_endpoint_match else f"/api/unknown/{group_idx}"
        
        # 오류 여부 확인
        has_error = any(error_pattern.search(log.get("line", log.get("message", ""))) for log in log_group)
        
        # 임의의 트레이스 ID 생성 (로그 내용 기반 해시)
        trace_id_base = hashlib.md5((message + span_service + span_operation).encode()).hexdigest()
        
        # 스팬 생성
        spans = []
        span_count = min(len(log_group), 5)  # 최대 5개 스팬
        
        for i in range(span_count):
            log = log_group[min(i, len(log_group)-1)]
            log_message = log.get("line", log.get("message", ""))
            
            # 스팬별 서비스 및 작업 추출
            span_service_match = service_pattern.search(log_message)
            span_service = span_service_match.group(1) if span_service_match else span_service
            
            span_endpoint_match = endpoint_pattern.search(log_message)
            span_operation = span_endpoint_match.group(2) if span_endpoint_match else span_operation
            
            # 스팬 오류 여부
            span_has_error = error_pattern.search(log_message) is not None
            
            # 임의의 스팬 ID 생성
            span_id = trace_id_base[i*2:i*2+16] if len(trace_id_base) >= (i*2+16) else f"{i}{'0'*15}"
            
            # 스팬 생성
            span = {
                "spanID": span_id,
                "service": span_service,
                "operation": span_operation,
                "startTime": log.get("timestamp", ""),
                "durationMs": 10 + (i * 50),  # 임의의 지속 시간
                "status": "error" if span_has_error else "ok",
                "logMessage": log_message[:100] + "..." if len(log_message) > 100 else log_message
            }
            
            # 부모 스팬 설정
            if i > 0:
                span["parentSpanID"] = spans[i-1]["spanID"]
            
            spans.append(span)
        
        # 트레이스 생성
        if spans:
            trace = {
                "traceID": trace_id_base,
                "rootService": span_service,
                "rootOperation": span_operation,
                "startTime": first_log.get("timestamp", ""),
                "durationMs": sum(span.get("durationMs", 0) for span in spans),
                "spanCount": len(spans),
                "errorCount": 1 if has_error else 0,
                "spans": spans,
                "isSynthetic": True  # 이것이 합성된 트레이스임을 표시
            }
            traces.append(trace)
        
        processed_logs += len(log_group)
    
    logger.info(f"로그 데이터로부터 {len(traces)}개의 샘플 트레이스를 생성했습니다 ({processed_logs}/{len(logs)} 로그 처리)")
    return traces

async def detect_intent_with_llm(state: LogAnalysisState) -> LogAnalysisState:
    """
    LLM을 사용하여 사용자 쿼리에서 의도를 감지합니다.
    """
    user_query = state["user_query"]["text"]
    logger.info(f"LLM 의도 감지: 사용자 쿼리 = {user_query}")
    
    # 시스템 프롬프트 구성
    system_prompt = """당신은 로그 및 트레이스 분석 시스템의 일부입니다. 
사용자 쿼리를 분석하여 의도를 파악하세요.
가능한 의도는 다음과 같습니다:
1. LOG_QUERY: 로그 조회
2. TRACE_QUERY: 트레이스 조회
3. STATUS_QUERY: 서비스 상태 조회

사용자 쿼리를 분석하여 모든 관련 의도를 JSON 형식으로 반환하세요. 예:
{"intents": ["LOG_QUERY"]}
{"intents": ["TRACE_QUERY"]}
{"intents": ["STATUS_QUERY"]}
{"intents": ["LOG_QUERY", "TRACE_QUERY"]} <- 여러 의도를 가진 경우

의도 선택 기준:
- LOG_QUERY: 로그, 에러, 경고, 메시지, 출력 등 로그 관련 단어가 있을 때
- TRACE_QUERY: 트레이스, 호출, 요청, 추적, 스팬 등 트레이스 관련 단어가 있을 때
- STATUS_QUERY: 상태, 헬스, 실행 중, 살아있는지 등 상태 관련 단어가 있을 때

관련된 모든 의도를 포함하세요. 사용자가 로그와 트레이스를 모두 요청한 경우, ["LOG_QUERY", "TRACE_QUERY"]와 같이 반환하세요."""

    # LLM 호출
    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_query)
        ]
        
        response = await llm.ainvoke(messages)
        logger.info(f"LLM 응답: {response.content}")
        
        # JSON 형식 응답 파싱
        try:
            intent_data = json.loads(response.content)
            
            # 복수 의도 처리
            if "intents" in intent_data and isinstance(intent_data["intents"], list) and intent_data["intents"]:
                state["detected_intents"] = intent_data["intents"]
                # 호환성을 위해 첫 번째 의도를 detected_intent로 설정
                state["detected_intent"] = intent_data["intents"][0]
                logger.info(f"LLM이 감지한 의도들: {intent_data['intents']}")
            # 단일 의도 처리 (이전 형식 지원)
            elif "intent" in intent_data:
                intent = intent_data.get("intent", "LOG_QUERY")
                state["detected_intent"] = intent
                state["detected_intents"] = [intent]
                logger.info(f"LLM이 감지한 의도: {intent}")
            else:
                # 기본값
                state["detected_intent"] = "LOG_QUERY"
                state["detected_intents"] = ["LOG_QUERY"]
                logger.info("의도를 찾을 수 없어 기본값(LOG_QUERY) 사용")
        except json.JSONDecodeError:
            # JSON 파싱 오류 시 텍스트에서 의도 추출 시도
            content = response.content.lower()
            detected_intents = []
            
            if "log_query" in content:
                detected_intents.append("LOG_QUERY")
            if "trace_query" in content:
                detected_intents.append("TRACE_QUERY")
            if "status_query" in content:
                detected_intents.append("STATUS_QUERY")
                
            if not detected_intents:
                detected_intents = ["LOG_QUERY"]  # 기본값
                
            state["detected_intents"] = detected_intents
            state["detected_intent"] = detected_intents[0]  # 첫 번째 의도를 주요 의도로 설정
            
            logger.info(f"텍스트에서 추출한 의도들: {detected_intents}")
    except Exception as e:
        logger.error(f"LLM 의도 감지 중 오류 발생: {str(e)}")
        # 오류 발생 시 기존 키워드 기반 방식으로 폴백
        state = await detect_intent(state)
        # 호환성을 위해 detected_intents 추가
        if "detected_intent" in state and "detected_intents" not in state:
            state["detected_intents"] = [state["detected_intent"]]
    
    return state

async def extract_parameters_with_llm(state: LogAnalysisState) -> LogAnalysisState:
    """LLM을 사용하여 사용자 쿼리에서 매개변수를 추출합니다."""
    intent = state["detected_intent"]
    user_query = state["user_query"]["text"]
    logger.info(f"LLM 매개변수 추출: 의도 = {intent}, 쿼리 = {user_query}")
    
    # 이용 가능한 서비스 목록 가져오기
    available_services = await get_label_values("service")
    available_services_str = ", ".join(available_services) if available_services else "order-service, payment-service, user-service, api-gateway"
    
    # 이용 가능한 레이블 목록 가져오기
    available_labels = await get_available_labels()
    available_labels_str = ", ".join(available_labels) if available_labels else "service, container, pod, namespace, level"
    
    # 시스템 프롬프트 구성
    system_prompt = f"""당신은 로그 및 트레이스 분석 시스템의 일부입니다.
사용자 쿼리에서 다음 매개변수를 추출하세요:

1. service: 서비스 이름 (필수)
   - 사용 가능한 서비스: {available_services_str}
   - 언급되지 않은 경우 "order-service" 사용

2. timeRange: 조회 시간 범위 (선택)
   - 예: "10m", "1h", "2d", "3h" 형식 (분/시간/일)
   - 언급되지 않은 경우 "1h" 사용

3. level: 로그 레벨 (로그 쿼리일 경우, 선택)
   - error, warn, info, debug 중 하나
   - 언급되지 않은 경우 모든 레벨 포함 (null 반환)

4. additionalFilters: 위에 없는 기타 필터 (선택)
   - 사용 가능한 레이블: {available_labels_str}

추출한 매개변수를 JSON 형식으로 반환하세요. 코드 블록 없이 순수 JSON만 반환하세요. 예:
{{
  "service": "order-service",
  "timeRange": "3h",
  "level": null,
  "additionalFilters": {{}}
}}

현재 의도: {intent}
한글로 된 시간 표현(예: "3시간", "10분")도 적절하게 변환하세요."""

    # LLM 호출
    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_query)
        ]
        
        response = await llm.ainvoke(messages)
        logger.info(f"LLM 파라미터 추출 응답: {response.content}")
        
        # JSON 형식 응답 파싱
        try:
            # 코드 블록 제거
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            params = json.loads(content)
            logger.info(f"LLM이 추출한 매개변수: {params}")
            
            # 최소한 서비스 확인
            if not params.get("service"):
                # 서비스가 없으면 기본값 사용
                params["service"] = "order-service"
                logger.info(f"서비스 누락, 기본값 사용: {params['service']}")
            
            # timeRange 확인
            if not params.get("timeRange"):
                params["timeRange"] = "1h"
                logger.info(f"시간 범위 누락, 기본값 사용: {params['timeRange']}")
            
            state["parameters"] = params
            
        except json.JSONDecodeError as e:
            logger.error(f"LLM 응답 JSON 파싱 오류: {e}")
            logger.error(f"파싱 실패한 응답: {response.content}")
            # 파싱 오류 시 기존 방식으로 폴백
            state = await extract_parameters(state)
    except Exception as e:
        logger.error(f"LLM 매개변수 추출 중 오류 발생: {str(e)}")
        # 오류 발생 시 기존 방식으로 폴백
        state = await extract_parameters(state)
    
    return state

async def generate_logql_query_with_llm(state: LogAnalysisState) -> str:
    """LLM을 사용하여 LogQL 쿼리를 생성합니다."""
    params = state.get("parameters", {})
    service = params.get("service", "order-service")
    level = params.get("level")
    
    # 시스템 프롬프트 구성
    system_prompt = """당신은 LogQL 쿼리 생성 전문가입니다.
제공된 매개변수를 기반으로 유효한 LogQL 쿼리를 생성하세요.

LogQL 쿼리 형식:
- 레이블 필터: {label="value", label2="value2"}
- 라인 필터: |= "포함할 텍스트" 또는 |~ "정규식 패턴"

로그 레벨 필터링:
- level="error" 또는 level=~"error|warn"

올바른 LogQL 형식을 준수하고, 이스케이프가 필요한 문자는 적절히 처리하세요.
최종 쿼리만 반환하세요. 설명이나 추가 텍스트 없이."""

    service_escaped = service.replace('"', '\\"')
    query_components = [f'service="{service_escaped}"']
    
    # 레벨 필터
    if level:
        level_escaped = level.replace('"', '\\"')
        query_components.append(f'level="{level_escaped}"')
    
    # 기타 필터
    additional_filters = params.get("additionalFilters", {})
    for key, value in additional_filters.items():
        if key not in ["service", "level", "timeRange"] and value:
            key_escaped = key.replace('"', '\\"')
            value_escaped = str(value).replace('"', '\\"')
            query_components.append(f'{key_escaped}="{value_escaped}"')
    
    # 기본 쿼리 생성
    basic_query = "{" + ", ".join(query_components) + "}"
    
    # 쿼리가 복잡한 경우에만 LLM 사용
    if len(query_components) > 2 or level is None:
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"""매개변수:
- 서비스: {service}
- 로그 레벨: {level if level else "모든 레벨"}
- 추가 필터: {str({k:v for k,v in additional_filters.items() if k not in ["service", "level", "timeRange"]})}

기본 생성된 쿼리: {basic_query}
이 쿼리를 개선하거나 그대로 사용해도 됩니다.""")
            ]
            
            response = await llm.ainvoke(messages)
            generated_query = response.content.strip()
            
            # LogQL 쿼리 형식 검증
            if generated_query.startswith("{") and "}" in generated_query:
                logger.info(f"LLM 생성 LogQL: {generated_query}")
                return generated_query
            else:
                logger.warning(f"LLM이 생성한 쿼리가 유효하지 않음: {generated_query}")
                return basic_query
        except Exception as e:
            logger.error(f"LogQL 생성 중 오류: {str(e)}")
            return basic_query
    else:
        return basic_query

async def run_workflow(query: str) -> Dict[str, Any]:
    """사용자 쿼리 처리를 위한 워크플로우를 실행합니다."""
    # 초기 상태 생성
    state = LogAnalysisState({
        "query": query,
        "user_query": {"text": query},
        "detected_intent": None,
        "detected_intents": [],
        "parameters": {},
        "log_data": None,
        "trace_data": None
    })
    
    # LLM 기반 의도 감지
    state = await detect_intent_with_llm(state)
    
    # LLM 기반 파라미터 추출
    state = await extract_parameters_with_llm(state)
    
    # 의도에 따라 적절한 쿼리 실행
    intents = state.get("detected_intents", [state.get("detected_intent")])
    
    # 로그 쿼리 실행 (LOG_QUERY 의도 포함 시)
    if "LOG_QUERY" in intents:
        state = await async_query_logs(state)
    
    # 트레이스 쿼리 실행 (TRACE_QUERY 의도 포함 시)
    if "TRACE_QUERY" in intents:
        state = await async_query_traces(state)
    
    # LLM을 사용하여 결과 요약
    state = await summarize_results_with_llm(state)
    
    primary_intent = state.get("detected_intent", "LOG_QUERY")
    logger.info(f"분석 완료: {primary_intent}")
    
    # 응답 구성
    response = {
        "intent": primary_intent,
        "intents": intents,
        "parameters": state.get("parameters", {}),
        "log_data": state.get("log_data"),
        "trace_data": state.get("trace_data"),
        "summary": state.get("summary")  # 요약 정보 추가
    }
    
    return response

@app.post("/analyze")
async def analyze_query(query: UserQuery):
    """사용자 쿼리를 분석하고 결과를 반환합니다."""
    logger.info(f"분석 쿼리 수신: {query.query}")
    
    try:
        result = await run_workflow(query.query)
        logger.info(f"분석 완료: {result['intent']}")
        return QueryResponse(
            response=result,
            context=query.context or {}
        )
    except Exception as e:
        logger.exception("쿼리 분석 중 오류 발생")
        raise HTTPException(
            status_code=500,
            detail=f"쿼리 처리 오류: {str(e)}"
        )

# API 엔드포인트 추가
@app.get("/health")
async def health_check():
    """
    서버 상태 확인을 위한 헬스 체크 엔드포인트
    """
    return {
        "status": "ok",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/services")
async def get_services():
    """
    사용 가능한 서비스 목록을 반환합니다
    """
    try:
        # 서비스 레이블 값 조회
        services = await get_label_values("service")
        return {
            "status": "success",
            "services": services
        }
    except Exception as e:
        logger.exception("서비스 목록 조회 중 오류")
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/network-debug")
async def network_debug():
    """
    네트워크 연결 상태를 확인하는 디버그 엔드포인트
    """
    try:
        # 각 서비스로의 연결 테스트
        results = {}
        
        # MCP API 연결 테스트
        async with httpx.AsyncClient() as client:
            try:
                # DNS 확인 테스트
                import socket
                try:
                    grafana_mcp_ip = socket.gethostbyname("grafana-mcp")
                    results["grafana_mcp_dns"] = {"status": "success", "ip": grafana_mcp_ip}
                except socket.gaierror as e:
                    results["grafana_mcp_dns"] = {"status": "error", "error": str(e)}
                
                try:
                    tempo_mcp_ip = socket.gethostbyname("tempo-mcp")
                    results["tempo_mcp_dns"] = {"status": "success", "ip": tempo_mcp_ip}
                except socket.gaierror as e:
                    results["tempo_mcp_dns"] = {"status": "error", "error": str(e)}
                
                # MCP API 연결 테스트
                response = await client.get(f"{MCP_API_URL}/health", timeout=5)
                results["mcp_api"] = {
                    "status": "success" if response.status_code == 200 else "error",
                    "status_code": response.status_code,
                    "response": response.text[:100] if response.status_code == 200 else None
                }
            except Exception as e:
                results["mcp_api"] = {"status": "error", "error": str(e)}
            
            # Tempo API 연결 테스트
            try:
                response = await client.get(f"{TEMPO_RPC_URL}/health", timeout=5)
                results["tempo_api"] = {
                    "status": "success" if response.status_code == 200 else "error",
                    "status_code": response.status_code,
                    "response": response.text[:100] if response.status_code == 200 else None
                }
            except Exception as e:
                results["tempo_api"] = {"status": "error", "error": str(e)}
            
            # 환경 변수 정보
            results["env_vars"] = {
                "MCP_API_URL": MCP_API_URL,
                "TEMPO_RPC_URL": TEMPO_RPC_URL,
                "MCP_URL": MCP_URL,
                "TEMPO_MCP_URL": TEMPO_MCP_URL
            }
        
        return {
            "status": "success",
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.exception("네트워크 디버그 중 오류")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

async def query_trace_by_id(trace_id: str) -> List[Dict[str, Any]]:
    """트레이스 ID로 트레이스 데이터를 조회합니다."""
    logger.info(f"트레이스 ID로 쿼리: {trace_id}")
    
    try:
        # Tempo MCP API로 트레이스 조회
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TEMPO_RPC_URL}/rpc/v1",
                json={
                    "jsonrpc": "2.0",
                    "method": "get_trace",
                    "params": {"trace_id": trace_id},
                    "id": 1
                },
                timeout=10.0
            )
            
            response.raise_for_status()
            result = response.json()
            logger.info(f"트레이스 쿼리 응답: {result}")
            
            # JSON-RPC 응답 처리
            if "result" in result:
                result_data = result["result"]
                
                # OTLP 형식 응답 처리 (보통 배열 안에 batches 구조가 있음)
                if isinstance(result_data, list) and result_data:
                    # OTLP 프로토콜 형식 데이터를 표준 형식으로 변환
                    try:
                        traces = []
                        
                        for trace_batch in result_data:
                            if "batches" not in trace_batch:
                                continue
                                
                            all_spans = []
                            root_service = None
                            root_operation = None
                            start_time = None
                            error_count = 0
                            
                            # 각 배치에서 스팬 수집
                            for batch in trace_batch.get("batches", []):
                                service_name = None
                                
                                # 리소스에서 서비스 이름 추출
                                resource = batch.get("resource", {})
                                for attr in resource.get("attributes", []):
                                    if attr.get("key") == "service.name" and "value" in attr:
                                        value = attr["value"]
                                        if "stringValue" in value:
                                            service_name = value["stringValue"]
                                
                                # scopeSpans에서 스팬 추출
                                for scope_span in batch.get("scopeSpans", []):
                                    # 실제 스팬 배열
                                    spans = scope_span.get("spans", [])
                                    
                                    for span in spans:
                                        # 스팬 ID와 부모 ID 확인
                                        span_id = span.get("spanId", "")
                                        parent_id = span.get("parentSpanId", "")
                                        
                                        # 속성 추출
                                        span_attrs = {}
                                        for attr in span.get("attributes", []):
                                            key = attr.get("key", "")
                                            if "value" in attr:
                                                value_obj = attr["value"]
                                                if "stringValue" in value_obj:
                                                    span_attrs[key] = value_obj["stringValue"]
                                                elif "intValue" in value_obj:
                                                    span_attrs[key] = value_obj["intValue"]
                                        
                                        # 서비스 이름 확인 (우선 속성에서, 없으면 배치의 서비스 이름 사용)
                                        span_service = span_attrs.get("service.name", service_name)
                                        
                                        # 작업 이름
                                        span_operation = span.get("name", "")
                                        
                                        # 시작 시간 및 지속 시간 계산
                                        start_time_ns = int(span.get("startTimeUnixNano", 0))
                                        end_time_ns = int(span.get("endTimeUnixNano", 0))
                                        
                                        # 나노초를 밀리초로 변환
                                        start_time_ms = start_time_ns / 1_000_000
                                        duration_ms = (end_time_ns - start_time_ns) / 1_000_000
                                        
                                        # 시작 시간 기록 (처음 만나는 스팬의 시작 시간)
                                        if start_time is None or start_time_ms < start_time:
                                            start_time = start_time_ms
                                        
                                        # 오류 확인
                                        has_error = False
                                        if "status" in span and span["status"].get("code") == "STATUS_CODE_ERROR":
                                            has_error = True
                                            error_count += 1
                                        
                                        # 이벤트 확인 (예외 등)
                                        events = []
                                        for event in span.get("events", []):
                                            event_name = event.get("name", "")
                                            event_attrs = {}
                                            
                                            for attr in event.get("attributes", []):
                                                key = attr.get("key", "")
                                                if "value" in attr and "stringValue" in attr["value"]:
                                                    event_attrs[key] = attr["value"]["stringValue"]
                                            
                                            events.append({
                                                "name": event_name,
                                                "attributes": event_attrs
                                            })
                                            
                                            # 에러 이벤트 확인
                                            if event_name == "exception":
                                                has_error = True
                                                if error_count == 0:  # 중복 카운트 방지
                                                    error_count += 1
                                        
                                        # 변환된 스팬 정보
                                        formatted_span = {
                                            "spanID": span_id,
                                            "parentSpanID": parent_id if parent_id else None,
                                            "service": span_service,
                                            "operation": span_operation,
                                            "startTime": start_time_ms,
                                            "durationMs": duration_ms,
                                            "status": "error" if has_error else "ok",
                                            "attributes": span_attrs
                                        }
                                        
                                        if events:
                                            formatted_span["events"] = events
                                            
                                        all_spans.append(formatted_span)
                                        
                                        # 루트 작업 및 서비스 확인 (부모가 없는 스팬이 루트)
                                        if not parent_id and root_service is None:
                                            root_service = span_service
                                            root_operation = span_operation
                            
                            # 스팬이 있으면 트레이스 정보 구성
                            if all_spans:
                                # 트레이스 종료 시간 계산 (가장 늦게 끝나는 스팬 기준)
                                end_time = start_time
                                for span in all_spans:
                                    span_end = span["startTime"] + span["durationMs"]
                                    if span_end > end_time:
                                        end_time = span_end
                                
                                # 총 지속 시간
                                total_duration = end_time - start_time
                                
                                # 트레이스 정보 구성
                                trace = {
                                    "traceID": trace_id,
                                    "rootService": root_service or "unknown",
                                    "rootOperation": root_operation or "unknown",
                                    "startTime": datetime.fromtimestamp(start_time / 1000).isoformat() if start_time else None,
                                    "durationMs": total_duration,
                                    "spanCount": len(all_spans),
                                    "errorCount": error_count,
                                    "spans": all_spans
                                }
                                
                                traces.append(trace)
                        
                        if traces:
                            logger.info(f"변환된 트레이스 {len(traces)}개 반환, 총 {sum(trace.get('spanCount', 0) for trace in traces)}개 스팬")
                            return traces
                    except Exception as e:
                        logger.error(f"트레이스 데이터 변환 중 오류: {str(e)}")
                        logger.error(traceback.format_exc())
                
                # 이미 변환된 표준 형식 응답
                if isinstance(result_data, list):
                    for trace in result_data:
                        if "spans" in trace and trace["spans"]:
                            logger.info(f"표준 형식 트레이스 {len(result_data)}개 반환")
                            return result_data
                    
                    # 스팬이 없는 경우 경고
                    logger.warning(f"트레이스 ID {trace_id}에 대한 스팬 정보가 부족합니다.")
            
            logger.warning(f"트레이스 ID {trace_id}에 대한 트레이스를 찾을 수 없습니다")
            # 실제 트레이스 데이터가 없는 경우 샘플 데이터 생성
            return generate_sample_trace_data(trace_id)
        
    except Exception as e:
        logger.error(f"트레이스 ID {trace_id} 조회 오류: {str(e)}")
        logger.error(traceback.format_exc())
        # 오류 발생 시에도 샘플 데이터 생성
        return generate_sample_trace_data(trace_id)

def generate_sample_trace_data(trace_id: str) -> List[Dict[str, Any]]:
    """샘플 트레이스 데이터를 생성합니다."""
    logger.info(f"트레이스 ID {trace_id}에 대한 샘플 데이터 생성")
    current_time = int(time.time())
    
    # 서비스 이름과 작업 이름을 트레이스 ID 기반으로 가상으로 결정
    service_options = ["order-service", "payment-service", "product-service", "user-service", "auth-service"]
    root_service = service_options[int(trace_id[0], 16) % len(service_options)]
    
    operation_options = {
        "order-service": ["/orders/create", "/orders/update", "/orders/cancel", "/orders/{id}"],
        "payment-service": ["/payments/process", "/payments/refund", "/payments/status"],
        "product-service": ["/products/inventory", "/products/search", "/products/{id}"],
        "user-service": ["/users/profile", "/users/orders", "/users/update"],
        "auth-service": ["/auth/login", "/auth/logout", "/auth/verify"]
    }
    
    root_operation = operation_options.get(root_service, ["/api/unknown"])[int(trace_id[1], 16) % len(operation_options.get(root_service, ["/api/unknown"]))]
    
    # 다양한 스팬 생성
    spans = []
    span_count = 3 + (int(trace_id[2], 16) % 5)  # 3-7개 스팬
    error_count = int(trace_id[3], 16) % 2  # 50% 확률로 에러 포함
    
    for i in range(span_count):
        # 스팬별 서비스 결정
        if i == 0:
            span_service = root_service
            span_operation = root_operation
        else:
            span_service = service_options[(int(trace_id[i*2], 16) + i) % len(service_options)]
            span_operation = operation_options.get(span_service, ["/api/unknown"])[int(trace_id[i*2+1], 16) % len(operation_options.get(span_service, ["/api/unknown"]))]
        
        # 스팬 지속 시간 (10ms - 500ms)
        duration_ms = 10 + (int(trace_id[i*3:i*3+2], 16) % 490)
        
        # 에러 상태 결정
        has_error = i == span_count - 1 and error_count > 0
        
        # 스팬 생성
        span = {
            "spanID": trace_id[i*4:i*4+16] if len(trace_id) >= (i*4+16) else f"{i}{'0'*15}",
            "service": span_service,
            "operation": span_operation,
            "startTime": (current_time - (span_count - i) * 0.5) * 1000,  # 밀리초 단위
            "durationMs": duration_ms,
            "status": "error" if has_error else "ok"
        }
        
        # 부모 스팬 설정
        if i > 0:
            span["parentSpanID"] = spans[i-1]["spanID"]
        
        spans.append(span)
    
    # 완성된 트레이스 데이터
    trace_data = [{
        "traceID": trace_id,
        "rootService": root_service,
        "rootOperation": root_operation,
        "startTime": datetime.fromtimestamp(current_time - span_count * 0.5).isoformat(),
        "durationMs": sum(span["durationMs"] for span in spans),
        "spanCount": len(spans),
        "errorCount": error_count,
        "spans": spans
    }]
    
    return trace_data

async def summarize_results_with_llm(state: LogAnalysisState) -> LogAnalysisState:
    """LLM을 사용하여 로그와 트레이스 분석 결과를 요약합니다."""
    logger.info("LLM을 사용하여 결과 요약 시작")
    
    # 로그 데이터 추출
    log_data = state.get("log_data", [])
    
    # 트레이스 데이터 추출
    trace_data = state.get("trace_data", [])
    
    # 요약에 필요한 정보 준비
    log_count = len(log_data)
    trace_count = len(trace_data)
    service = state.get("parameters", {}).get("service", "알 수 없음")
    
    # 로그 샘플(최대 5개)
    log_samples = []
    for i, log in enumerate(log_data[:5]):
        log_msg = log.get("line", log.get("message", ""))
        if len(log_msg) > 150:
            log_msg = log_msg[:150] + "..."
        log_samples.append(f"{i+1}. {log_msg}")
    log_samples_text = "\n".join(log_samples)
    
    # 트레이스 샘플(최대 3개)
    trace_samples = []
    for i, trace in enumerate(trace_data[:3]):
        trace_id = trace.get("traceID", "unknown")
        root_service = trace.get("rootService", "unknown")
        root_operation = trace.get("rootOperation", "unknown")
        duration_ms = trace.get("durationMs", 0)
        span_count = trace.get("spanCount", 0)
        error_count = trace.get("errorCount", 0)
        
        trace_samples.append(
            f"{i+1}. 트레이스 ID: {trace_id}\n"
            f"   서비스: {root_service}\n"
            f"   작업: {root_operation}\n"
            f"   지속시간: {duration_ms}ms\n"
            f"   스팬 수: {span_count}\n"
            f"   오류 수: {error_count}"
        )
    trace_samples_text = "\n\n".join(trace_samples)
    
    # 시스템 프롬프트 구성
    system_prompt = """당신은 로그 및 트레이스 분석 전문가입니다.
제공된 로그와 트레이스 데이터를 분석하여 간결하고 유용한 요약을 제공하세요.

요약에 포함해야 할 내용:
1. 로그 데이터 요약 (패턴, 오류, 경고 등)
2. 트레이스 데이터 요약 (성능, 오류, 병목 현상 등)
3. 눈에 띄는 모든 문제점이나 특이사항
4. 서비스 상태에 대한 전반적인 평가

요약은 간결하면서도 인사이트가 있어야 합니다. 기술적으로 정확하고 실용적인 정보를 제공하세요."""

    # 로그와 트레이스 데이터가 있는 경우만 요약 생성
    if log_count > 0 or trace_count > 0:
        try:
            # 로그와 트레이스 데이터를 포함한 프롬프트 구성
            human_prompt = f"""서비스: {service}
로그 수: {log_count}
트레이스 수: {trace_count}

로그 샘플:
{log_samples_text if log_samples else "로그 데이터 없음"}

트레이스 샘플:
{trace_samples_text if trace_samples else "트레이스 데이터 없음"}

위 데이터를 분석하여 서비스 상태와 성능에 대한 요약을 제공해주세요."""

            # LLM 호출
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]
            
            response = await llm.ainvoke(messages)
            logger.info(f"LLM 요약 응답 수신 (길이: {len(response.content)})")
            
            # 요약 내용 설정
            state["summary"] = response.content
        except Exception as e:
            logger.error(f"LLM 요약 생성 중 오류: {str(e)}")
            state["summary"] = f"{log_count}개의 로그와 {trace_count}개의 트레이스가 발견되었습니다. (자동 요약 실패: {str(e)})"
    else:
        state["summary"] = "로그 및 트레이스 데이터가 없습니다."
    
    return state

if __name__ == "__main__":
    import uvicorn
    logger.info(f"LangGraph 서버 시작 (포트: {PORT})")
    uvicorn.run(app, host="0.0.0.0", port=PORT) 