# loki_tempo_mcp_server.py
from typing import List, Dict, Optional, Any
import os
import requests
import json
import time
from datetime import datetime, timedelta
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv, find_dotenv, set_key
import logging
import pathlib
import urllib.parse
import base64

# 로깅 설정 추가
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("loki_tempo_mcp_server")

# 현재 파일 위치 확인 및 경로 설정
current_dir = pathlib.Path(__file__).parent.absolute()
env_file = os.path.join(current_dir, '.env')

# .env 파일 로드 - 먼저 실행해야 함
logger.info(f".env 파일 로드: {env_file}")
load_dotenv(dotenv_path=env_file)

# 환경 변수 출력 함수
def log_environment_settings():
    """
    현재 설정된 환경 변수 값을 로그에 기록합니다.
    """
    env_vars = {
        "LOKI_URL": os.getenv("LOKI_URL"),
        "TEMPO_URL": os.getenv("TEMPO_URL"),
        "GRAFANA_URL": os.getenv("GRAFANA_URL"),
        "LOKI_DASHBOARD_ID": os.getenv("LOKI_DASHBOARD_ID"),
        "TEMPO_DASHBOARD_ID": os.getenv("TEMPO_DASHBOARD_ID"),
        "MCP_HOST": os.getenv("MCP_HOST"),
        "MCP_PORT": os.getenv("MCP_PORT"),
        "DEFAULT_LOG_LIMIT": os.getenv("DEFAULT_LOG_LIMIT"),
        "DEFAULT_TRACE_LIMIT": os.getenv("DEFAULT_TRACE_LIMIT"),
        "DEFAULT_TIME_RANGE": os.getenv("DEFAULT_TIME_RANGE"),
        "LOKI_AUTH_USER": os.getenv("LOKI_AUTH_USER"),
        "LOKI_AUTH_PASSWORD": os.getenv("LOKI_AUTH_PASSWORD"),
        "TEMPO_AUTH_USER": os.getenv("TEMPO_AUTH_USER"),
        "TEMPO_AUTH_PASSWORD": os.getenv("TEMPO_AUTH_PASSWORD")
    }
    
    logger.info("======== 환경 설정 ========")
    for key, value in env_vars.items():
        # 비밀번호는 마스킹 처리
        if "PASSWORD" in key and value:
            logger.info(f"{key}: ***masked***")
        else:
            logger.info(f"{key}: {value}")
    logger.info("==========================")

# 환경 설정 로그 출력 - 값 확인을 위해 호출
log_environment_settings()

# .env에서 필수 환경 변수 누락 여부 확인
required_vars = ["LOKI_URL", "TEMPO_URL", "MCP_HOST", "MCP_PORT"]

missing_vars = []
for var in required_vars:
    if not os.getenv(var):
        missing_vars.append(var)
        
if missing_vars:
    logger.warning(f"다음 환경 변수가 .env 파일에 누락되었습니다: {', '.join(missing_vars)}")
    logger.warning(".env 파일을 확인하고 필요한 변수를 추가하세요.")

# 환경 변수에서 설정 로드
LOKI_URL = os.getenv("LOKI_URL", "http://localhost:3100")
TEMPO_URL = os.getenv("TEMPO_URL", "http://localhost:3200")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
LOKI_DASHBOARD_ID = os.getenv("LOKI_DASHBOARD_ID")
TEMPO_DASHBOARD_ID = os.getenv("TEMPO_DASHBOARD_ID")
DEFAULT_LOG_LIMIT = int(os.getenv("DEFAULT_LOG_LIMIT", "100"))
DEFAULT_TRACE_LIMIT = int(os.getenv("DEFAULT_TRACE_LIMIT", "20"))
DEFAULT_TIME_RANGE = os.getenv("DEFAULT_TIME_RANGE", "1h")

# 인증 정보
LOKI_AUTH_USER = os.getenv("LOKI_AUTH_USER")
LOKI_AUTH_PASSWORD = os.getenv("LOKI_AUTH_PASSWORD")
TEMPO_AUTH_USER = os.getenv("TEMPO_AUTH_USER")
TEMPO_AUTH_PASSWORD = os.getenv("TEMPO_AUTH_PASSWORD")

# MCP 서버 설정
mcp = FastMCP(
    "Loki & Tempo Observability",
    instructions="Loki와 Tempo를 사용한 관찰성(Observability) MCP 서버입니다. 로그 쿼리, 추적 검색, 분석 기능을 제공합니다.",
    host=os.getenv("MCP_HOST", "0.0.0.0"),
    port=int(os.getenv("MCP_PORT", "10002"))
)

# 테스트 도구 추가
@mcp.tool()
async def test_tool() -> str:
    """간단한 테스트 도구입니다."""
    return "MCP 서버가 정상적으로 작동합니다!"

# 파라미터 검증 헬퍼 함수
def validate_and_fix_query(query: Any, function_name: str = "unknown") -> str:
    """
    query 파라미터를 검증하고 올바른 형태로 변환합니다.
    
    Args:
        query: 입력된 query 파라미터
        function_name: 함수명 (로깅용)
        
    Returns:
        검증된 문자열 쿼리
    """
    try:
        # 파라미터 타입 로깅
        logger.info(f"{function_name}: 입력된 query 타입: {type(query)}, 값: {query}")
        
        # 딕셔너리인 경우 더 구체적인 기본값으로 변경
        if isinstance(query, dict):
            logger.warning(f"{function_name}: query 파라미터가 딕셔너리로 전달됨. 기본 쿼리 사용.")
            if function_name.startswith("query_logs") or function_name.startswith("analyze_logs"):
                return '{job=~".+"}'  # 모든 job 라벨을 가진 로그
            else:
                return '{}'  # Tempo는 빈 쿼리 허용
        
        # None인 경우 기본값으로 변경
        if query is None:
            logger.warning(f"{function_name}: query 파라미터가 None. 기본 쿼리 사용.")
            if function_name.startswith("query_logs") or function_name.startswith("analyze_logs"):
                return '{job=~".+"}'
            else:
                return '{}'
        
        # 문자열이 아닌 경우 문자열로 변환
        if not isinstance(query, str):
            str_query = str(query)
            logger.warning(f"{function_name}: query 파라미터 타입 변환: {type(query)} → str, 결과: '{str_query}'")
            return str_query if str_query else ('{job=~".+"}' if function_name.startswith("query_logs") else '{}')
        
        # 빈 문자열이거나 "{}"인 경우 더 구체적인 기본값으로 변경
        if not query or not query.strip() or query.strip() == '{}':
            logger.warning(f"{function_name}: query 파라미터가 빈 문자열 또는 {{}}. 기본 쿼리 사용.")
            if function_name.startswith("query_logs") or function_name.startswith("analyze_logs"):
                return '{job=~".+"}'  # 모든 job 라벨을 가진 로그
            else:
                return '{}'  # Tempo는 빈 쿼리 허용
        
        # 정상적인 문자열인 경우
        logger.info(f"{function_name}: 정상적인 query 파라미터: '{query}'")
        return query
        
    except Exception as e:
        logger.error(f"{function_name}: query 파라미터 처리 중 오류 발생: {e}")
        if function_name.startswith("query_logs") or function_name.startswith("analyze_logs"):
            return '{job=~".+"}'
        else:
            return '{}'

# 시간 범위 파싱 함수 - 수정된 버전
def parse_time_range(time_range: str) -> tuple:
    """
    시간 범위 문자열을 파싱하여 시작/종료 시간을 반환합니다.
    
    Args:
        time_range: "1h", "24h", "7d" 등의 상대적 시간 또는 ISO 형식의 절대 시간
        
    Returns:
        (start_time, end_time) 튜플 (나노초 단위)
    """
    try:
        now = datetime.now()
        
        # 입력값 검증 및 정규화
        if not isinstance(time_range, str):
            time_range = str(time_range)
        
        time_range = time_range.strip()
        
        # 상대적 시간 처리
        if time_range.endswith('m'):
            minutes = int(time_range[:-1])
            start = now - timedelta(minutes=minutes)
        elif time_range.endswith('h'):
            hours = int(time_range[:-1])
            start = now - timedelta(hours=hours)
        elif time_range.endswith('d'):
            days = int(time_range[:-1])
            start = now - timedelta(days=days)
        else:
            # ISO 형식으로 파싱 시도
            try:
                start = datetime.fromisoformat(time_range)
            except:
                # 기본값: 1시간 전
                logger.warning(f"시간 범위 파싱 실패: {time_range}, 기본값 1h 사용")
                start = now - timedelta(hours=1)
        
        # 나노초 단위로 변환 (Loki와 Tempo 모두 나노초 사용)
        start_ns = int(start.timestamp() * 1_000_000_000)
        end_ns = int(now.timestamp() * 1_000_000_000)
        
        logger.info(f"시간 범위 파싱 완료: {time_range} -> {start_ns} ~ {end_ns} (나노초)")
        return start_ns, end_ns
        
    except Exception as e:
        logger.error(f"시간 범위 파싱 오류: {e}, 기본값 사용")
        # 오류 시 기본값 반환 (1시간 전부터 현재까지)
        now = datetime.now()
        start = now - timedelta(hours=1)
        start_ns = int(start.timestamp() * 1_000_000_000)
        end_ns = int(now.timestamp() * 1_000_000_000)
        return start_ns, end_ns

# HTTP 요청 헬퍼 함수
def make_request(url: str, method: str = "GET", params: Dict = None, 
                headers: Dict = None, auth_user: str = None, auth_password: str = None) -> Dict:
    """
    HTTP 요청을 만들고 응답을 반환합니다.
    
    Args:
        url: 요청 URL
        method: HTTP 메서드
        params: 쿼리 파라미터
        headers: 헤더
        auth_user: 인증 사용자명
        auth_password: 인증 비밀번호
        
    Returns:
        응답 딕셔너리
    """
    try:
        # Basic Auth 설정
        auth = None
        if auth_user and auth_password:
            auth = (auth_user, auth_password)
        
        # 헤더 설정
        if headers is None:
            headers = {}
        
        # 요청 실행
        if method == "GET":
            response = requests.get(url, params=params, headers=headers, auth=auth, timeout=30)
        else:
            response = requests.request(method, url, params=params, headers=headers, auth=auth, timeout=30)
        
        response.raise_for_status()
        
        # JSON 응답 파싱
        try:
            return response.json()
        except:
            return {"text": response.text}
            
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP 요청 실패: {e}")
        # 응답 내용 로깅
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"응답 내용: {e.response.text}")
        return {"error": str(e)}

@mcp.tool()
async def update_environment_settings(
    loki_url: Optional[str] = None,
    tempo_url: Optional[str] = None,
    grafana_url: Optional[str] = None,
    loki_dashboard_id: Optional[str] = None,
    tempo_dashboard_id: Optional[str] = None,
    default_log_limit: Optional[int] = None,
    default_trace_limit: Optional[int] = None,
    default_time_range: Optional[str] = None,
    loki_auth_user: Optional[str] = None,
    loki_auth_password: Optional[str] = None,
    tempo_auth_user: Optional[str] = None,
    tempo_auth_password: Optional[str] = None
) -> Dict:
    """
    환경 설정을 업데이트합니다.
    
    - loki_url: Loki 서버 URL
    - tempo_url: Tempo 서버 URL
    - grafana_url: Grafana 서버 URL
    - loki_dashboard_id: Loki 대시보드 ID
    - tempo_dashboard_id: Tempo 대시보드 ID
    - default_log_limit: 기본 로그 조회 제한
    - default_trace_limit: 기본 트레이스 조회 제한
    - default_time_range: 기본 시간 범위 (예: "1h", "24h", "7d")
    - loki_auth_user: Loki 인증 사용자명
    - loki_auth_password: Loki 인증 비밀번호
    - tempo_auth_user: Tempo 인증 사용자명
    - tempo_auth_password: Tempo 인증 비밀번호
    
    이 설정은 .env 파일에 저장되어 서버 재시작 후에도 유지됩니다.
    """
    global LOKI_URL, TEMPO_URL, GRAFANA_URL, LOKI_DASHBOARD_ID, TEMPO_DASHBOARD_ID
    global DEFAULT_LOG_LIMIT, DEFAULT_TRACE_LIMIT, DEFAULT_TIME_RANGE
    global LOKI_AUTH_USER, LOKI_AUTH_PASSWORD, TEMPO_AUTH_USER, TEMPO_AUTH_PASSWORD
    
    updated = {}
    
    if loki_url:
        set_key(env_file, "LOKI_URL", loki_url)
        LOKI_URL = loki_url
        updated["LOKI_URL"] = loki_url
    
    if tempo_url:
        set_key(env_file, "TEMPO_URL", tempo_url)
        TEMPO_URL = tempo_url
        updated["TEMPO_URL"] = tempo_url
    
    if grafana_url:
        set_key(env_file, "GRAFANA_URL", grafana_url)
        GRAFANA_URL = grafana_url
        updated["GRAFANA_URL"] = grafana_url
    
    if loki_dashboard_id:
        set_key(env_file, "LOKI_DASHBOARD_ID", loki_dashboard_id)
        LOKI_DASHBOARD_ID = loki_dashboard_id
        updated["LOKI_DASHBOARD_ID"] = loki_dashboard_id
    
    if tempo_dashboard_id:
        set_key(env_file, "TEMPO_DASHBOARD_ID", tempo_dashboard_id)
        TEMPO_DASHBOARD_ID = tempo_dashboard_id
        updated["TEMPO_DASHBOARD_ID"] = tempo_dashboard_id
    
    if default_log_limit is not None:
        set_key(env_file, "DEFAULT_LOG_LIMIT", str(default_log_limit))
        DEFAULT_LOG_LIMIT = default_log_limit
        updated["DEFAULT_LOG_LIMIT"] = default_log_limit
    
    if default_trace_limit is not None:
        set_key(env_file, "DEFAULT_TRACE_LIMIT", str(default_trace_limit))
        DEFAULT_TRACE_LIMIT = default_trace_limit
        updated["DEFAULT_TRACE_LIMIT"] = default_trace_limit
    
    if default_time_range:
        set_key(env_file, "DEFAULT_TIME_RANGE", default_time_range)
        DEFAULT_TIME_RANGE = default_time_range
        updated["DEFAULT_TIME_RANGE"] = default_time_range
    
    if loki_auth_user:
        set_key(env_file, "LOKI_AUTH_USER", loki_auth_user)
        LOKI_AUTH_USER = loki_auth_user
        updated["LOKI_AUTH_USER"] = loki_auth_user
    
    if loki_auth_password:
        set_key(env_file, "LOKI_AUTH_PASSWORD", loki_auth_password)
        LOKI_AUTH_PASSWORD = loki_auth_password
        updated["LOKI_AUTH_PASSWORD"] = "***masked***"
    
    if tempo_auth_user:
        set_key(env_file, "TEMPO_AUTH_USER", tempo_auth_user)
        TEMPO_AUTH_USER = tempo_auth_user
        updated["TEMPO_AUTH_USER"] = tempo_auth_user
    
    if tempo_auth_password:
        set_key(env_file, "TEMPO_AUTH_PASSWORD", tempo_auth_password)
        TEMPO_AUTH_PASSWORD = tempo_auth_password
        updated["TEMPO_AUTH_PASSWORD"] = "***masked***"
    
    # 환경 설정 다시 로그로 출력
    log_environment_settings()
    
    if updated:
        return {
            "status": "success",
            "message": "환경 설정이 업데이트되었습니다.",
            "updated": updated
        }
    else:
        return {
            "status": "info",
            "message": "업데이트할 설정이 없습니다."
        }

@mcp.tool()
async def check_environment() -> Dict:
    """
    현재 환경 설정을 확인합니다.
    
    서버에 설정된 환경 변수와 Loki/Tempo 연결 상태를 확인하여 반환합니다.
    """
    env_vars = {
        "LOKI_URL": LOKI_URL,
        "TEMPO_URL": TEMPO_URL,
        "GRAFANA_URL": GRAFANA_URL,
        "LOKI_DASHBOARD_ID": LOKI_DASHBOARD_ID,
        "TEMPO_DASHBOARD_ID": TEMPO_DASHBOARD_ID,
        "DEFAULT_LOG_LIMIT": DEFAULT_LOG_LIMIT,
        "DEFAULT_TRACE_LIMIT": DEFAULT_TRACE_LIMIT,
        "DEFAULT_TIME_RANGE": DEFAULT_TIME_RANGE,
        "LOKI_AUTH_USER": LOKI_AUTH_USER,
        "LOKI_AUTH_PASSWORD": "***masked***" if LOKI_AUTH_PASSWORD else None,
        "TEMPO_AUTH_USER": TEMPO_AUTH_USER,
        "TEMPO_AUTH_PASSWORD": "***masked***" if TEMPO_AUTH_PASSWORD else None
    }
    
    # Loki 연결 상태 확인
    try:
        loki_ready = make_request(f"{LOKI_URL}/ready", auth_user=LOKI_AUTH_USER, auth_password=LOKI_AUTH_PASSWORD)
        loki_status = "연결됨" if not loki_ready.get("error") else f"오류: {loki_ready.get('error')}"
    except Exception as e:
        loki_status = f"연결 실패: {str(e)}"
    
    # Tempo 연결 상태 확인
    try:
        tempo_ready = make_request(f"{TEMPO_URL}/status", auth_user=TEMPO_AUTH_USER, auth_password=TEMPO_AUTH_PASSWORD)
        tempo_status = "연결됨" if not tempo_ready.get("error") else f"오류: {tempo_ready.get('error')}"
    except Exception as e:
        tempo_status = f"연결 실패: {str(e)}"
    
    return {
        "환경 변수": env_vars,
        "Loki 상태": loki_status,
        "Tempo 상태": tempo_status,
        "Grafana 대시보드": {
            "Loki": f"{GRAFANA_URL}/d/{LOKI_DASHBOARD_ID}" if GRAFANA_URL and LOKI_DASHBOARD_ID else "미설정",
            "Tempo": f"{GRAFANA_URL}/d/{TEMPO_DASHBOARD_ID}" if GRAFANA_URL and TEMPO_DASHBOARD_ID else "미설정"
        }
    }

@mcp.tool()
async def query_logs(
    query: str = '{job=~".+"}',
    time_range: str = "1h",
    limit: int = 100,
    direction: str = "backward",
    service: Optional[str] = None,
    level: Optional[str] = None
) -> Dict[str, Any]:
    """
    Loki에서 로그를 쿼리합니다.
    
    **쿼리 예제**:
    - 모든 로그: '{job=~".+"}'
    - 특정 서비스: '{service="api-gateway"}'
    - 특정 컨테이너: '{container="nginx"}'
    - 여러 조건 조합: '{service="api-gateway", level="error"}'
    - 텍스트 필터링: '{service="api-gateway"} |= "error"'
    - 정규식 필터링: '{service="api-gateway"} |~ "error|warn"'
    
    **파라미터**:
    - query: LogQL 쿼리 문자열 (기본값: '{job=~".+"}' - 모든 로그)
    - time_range: 시간 범위 (예: "5m", "1h", "24h", "7d")
    - limit: 반환할 로그 수 제한 (기본값: 100)
    - direction: 검색 방향 ("forward" 또는 "backward")
    - service: 특정 서비스 필터 (쿼리에 자동 추가)
    - level: 로그 레벨 필터 (예: "error", "warn", "info")
    
    **반환값**: 로그 엔트리 리스트와 메타데이터
    """
    
    # 🔧 파라미터 검증 및 정규화
    query = validate_and_fix_query(query, "query_logs")
    
    # 기본값 설정
    if not time_range:
        time_range = DEFAULT_TIME_RANGE
    if limit is None:
        limit = DEFAULT_LOG_LIMIT
    
    # 시간 범위 파싱
    start_ns, end_ns = parse_time_range(time_range)
    
    # 쿼리 구성
    if service:
        if query == '{job=~".+"}':
            query = f'{{service="{service}"}}'
        else:
            # 기존 쿼리에 service 레이블 추가
            query = query.rstrip('}') + f', service="{service}"}}'
    
    if level:
        query += f' |= "{level}"'
    
    # Loki API 호출
    params = {
        "query": query,
        "start": str(start_ns),  # 나노초를 문자열로
        "end": str(end_ns),      # 나노초를 문자열로
        "limit": limit,
        "direction": direction
    }
    
    logger.info(f"Loki 쿼리 실행: {query} (파라미터: {params})")
    result = make_request(
        f"{LOKI_URL}/loki/api/v1/query_range",
        params=params,
        auth_user=LOKI_AUTH_USER,
        auth_password=LOKI_AUTH_PASSWORD
    )
    
    if result.get("error"):
        logger.error(f"Loki API 오류: {result['error']}")
        return {
            "status": "error",
            "error": result["error"],
            "query": query,
            "hint": "쿼리 구문을 확인하세요. 예: '{service=\"api-gateway\"}' 또는 '{job=\"varlogs\"}'"
        }
    
    # 결과 처리
    logs = []
    if result.get("data", {}).get("result"):
        for stream in result["data"]["result"]:
            stream_labels = stream.get("stream", {})
            for value in stream.get("values", []):
                timestamp_ns, log_line = value
                logs.append({
                    "timestamp": datetime.fromtimestamp(int(timestamp_ns) / 1000000000).isoformat(),
                    "labels": stream_labels,
                    "log": log_line
                })
    
    # Grafana 대시보드 링크 생성
    dashboard_link = None
    if GRAFANA_URL and LOKI_DASHBOARD_ID:
        encoded_query = urllib.parse.quote(query)
        dashboard_link = f"{GRAFANA_URL}/d/{LOKI_DASHBOARD_ID}?orgId=1&var-query={encoded_query}"
    
    logger.info(f"로그 쿼리 완료: {len(logs)}개 로그 반환")
    
    return {
        "status": "success",
        "query": query,
        "time_range": time_range,
        "log_count": len(logs),
        "logs": logs,
        "dashboard_link": dashboard_link
    }

@mcp.tool()
async def search_traces(
    service_name: Optional[str] = None,
    operation_name: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
    min_duration: Optional[str] = None,
    max_duration: Optional[str] = None,
    time_range: str = "1h",
    limit: int = 20
) -> Dict:
    """
    Tempo에서 트레이스를 검색합니다.
    
    **예제**:
    - 특정 서비스의 모든 트레이스: service_name="api-gateway"
    - 에러 트레이스: tags={"error": "true", "http.status_code": "500"}
    - 느린 트레이스: min_duration="1s"
    - 특정 작업: operation_name="GET /users"
    
    **파라미터**:
    - service_name: 서비스 이름으로 필터링
    - operation_name: 오퍼레이션 이름으로 필터링
    - tags: 태그로 필터링 (딕셔너리 형태)
    - min_duration: 최소 지속 시간 (예: "100ms", "1s", "5s")
    - max_duration: 최대 지속 시간 (예: "5s", "1m")
    - time_range: 시간 범위 (예: "5m", "1h", "24h", "7d")
    - limit: 반환할 트레이스 수 제한 (기본값: 20)
    
    **반환값**: 검색된 트레이스 정보
    """
    # 기본값 설정
    if not time_range:
        time_range = DEFAULT_TIME_RANGE
    if limit is None:
        limit = DEFAULT_TRACE_LIMIT
    
    # 시간 범위 파싱
    start_ns, end_ns = parse_time_range(time_range)
    
    # TraceQL 쿼리 구성
    conditions = []
    
    if service_name:
        conditions.append(f'resource.service.name="{service_name}"')
    
    if operation_name:
        conditions.append(f'name="{operation_name}"')
    
    if tags and isinstance(tags, dict):
        for key, value in tags.items():
            # 속성 키에 점(.)이 포함되어 있으면 그대로 사용
            if '.' in key:
                conditions.append(f'{key}="{value}"')
            else:
                conditions.append(f'.{key}="{value}"')
    
    if min_duration:
        conditions.append(f'duration>{min_duration}')
    
    if max_duration:
        conditions.append(f'duration<{max_duration}')
    
    # 쿼리 조합
    if conditions:
        query = "{" + " && ".join(conditions) + "}"
    else:
        query = "{}"
    
    # Tempo Search API 호출
    params = {
        "q": query,
        "start": str(int(start_ns // 1_000_000_000)),  # 나노초를 초로 변환하여 문자열로
        "end": str(int(end_ns // 1_000_000_000)),      # 나노초를 초로 변환하여 문자열로
        "limit": limit
    }
    
    logger.info(f"Tempo 트레이스 검색: {query}")
    result = make_request(
        f"{TEMPO_URL}/api/search",
        params=params,
        auth_user=TEMPO_AUTH_USER,
        auth_password=TEMPO_AUTH_PASSWORD
    )
    
    if result.get("error"):
        return {
            "status": "error",
            "error": result["error"],
            "query": query,
            "hint": "TraceQL 쿼리 구문을 확인하세요. 예: {resource.service.name=\"api-gateway\"}"
        }
    
    # 결과 처리
    traces = []
    for trace in result.get("traces", []):
        trace_info = {
            "trace_id": trace.get("traceID"),
            "root_service": trace.get("rootServiceName"),
            "root_trace_name": trace.get("rootTraceName"),
            "start_time": datetime.fromtimestamp(trace.get("startTimeUnixNano", 0) / 1000000000).isoformat(),
            "duration_ms": trace.get("durationMs"),
            "span_count": len(trace.get("spanSet", {}).get("spans", [])) if trace.get("spanSet") else 0
        }
        
        # 스팬 세트에서 서비스 목록 추출
        if trace.get("spanSet", {}).get("spans"):
            services = set()
            for span in trace["spanSet"]["spans"]:
                for attr in span.get("attributes", []):
                    if attr["key"] == "service.name":
                        services.add(attr["value"]["stringValue"])
            trace_info["services"] = list(services)
        
        traces.append(trace_info)
    
    # Grafana 대시보드 링크 생성
    dashboard_link = None
    if GRAFANA_URL and TEMPO_DASHBOARD_ID:
        dashboard_link = f"{GRAFANA_URL}/d/{TEMPO_DASHBOARD_ID}?orgId=1"
    
    return {
        "status": "success",
        "query": query,
        "time_range": time_range,
        "trace_count": len(traces),
        "traces": traces,
        "dashboard_link": dashboard_link
    }

@mcp.tool()
async def get_trace_details(trace_id: str) -> Dict:
    """
    특정 트레이스의 상세 정보를 조회합니다.
    
    **파라미터**:
    - trace_id: 조회할 트레이스 ID (예: "a1b2c3d4e5f6")
    
    **반환값**: 트레이스 ID로 전체 스팬 트리와 각 스팬의 상세 정보
    """
    # Tempo API 호출
    logger.info(f"트레이스 상세 조회: {trace_id}")
    result = make_request(
        f"{TEMPO_URL}/api/traces/{trace_id}",
        auth_user=TEMPO_AUTH_USER,
        auth_password=TEMPO_AUTH_PASSWORD
    )
    
    if result.get("error"):
        return {
            "status": "error",
            "error": result["error"],
            "trace_id": trace_id,
            "hint": "트레이스 ID가 올바른지 확인하세요."
        }
    
    # 트레이스 정보 추출
    batches = result.get("batches", [])
    spans = []
    services = set()
    
    for batch in batches:
        resource = batch.get("resource", {})
        service_name = None
        
        # 서비스 이름 추출
        for attr in resource.get("attributes", []):
            if attr["key"] == "service.name":
                service_name = attr["value"]["stringValue"]
                services.add(service_name)
                break
        
        # 스팬 정보 추출
        for span in batch.get("scopeSpans", []):
            for s in span.get("spans", []):
                span_info = {
                    "span_id": s["spanId"],
                    "parent_span_id": s.get("parentSpanId"),
                    "name": s["name"],
                    "service": service_name,
                    "start_time": datetime.fromtimestamp(int(s["startTimeUnixNano"]) / 1000000000).isoformat(),
                    "end_time": datetime.fromtimestamp(int(s["endTimeUnixNano"]) / 1000000000).isoformat(),
                    "duration_ms": (int(s["endTimeUnixNano"]) - int(s["startTimeUnixNano"])) / 1000000,
                    "status": s.get("status", {})
                }
                
                # 속성 추출
                attributes = {}
                for attr in s.get("attributes", []):
                    key = attr["key"]
                    value = attr["value"]
                    # 값 타입에 따라 처리
                    if "stringValue" in value:
                        attributes[key] = value["stringValue"]
                    elif "intValue" in value:
                        attributes[key] = value["intValue"]
                    elif "boolValue" in value:
                        attributes[key] = value["boolValue"]
                
                span_info["attributes"] = attributes
                spans.append(span_info)
    
    # 스팬 트리 구성
    root_spans = [s for s in spans if not s.get("parent_span_id")]
    
    # Grafana 대시보드 링크 생성
    dashboard_link = None
    if GRAFANA_URL and TEMPO_DASHBOARD_ID:
        dashboard_link = f"{GRAFANA_URL}/d/{TEMPO_DASHBOARD_ID}?orgId=1&var-traceId={trace_id}"
    
    return {
        "status": "success",
        "trace_id": trace_id,
        "services": list(services),
        "span_count": len(spans),
        "root_spans": len(root_spans),
        "spans": spans,
        "dashboard_link": dashboard_link
    }

@mcp.tool()
async def analyze_logs_pattern(
    query: str = '{job=~".+"}',
    time_range: str = "1h",
    pattern_type: str = "simple"
) -> Dict[str, Any]:
    """
    로그 패턴을 분석하여 가장 빈번한 패턴을 찾습니다.
    
    **참고**: Loki의 pattern 기능이 지원되지 않는 경우 간단한 패턴 분석을 수행합니다.
    
    **파라미터**:
    - query: LogQL 쿼리 문자열 (예: '{service="api-gateway"}')
    - time_range: 시간 범위 (예: "5m", "1h", "24h")
    - pattern_type: "simple" (기본) 또는 "loki" (Loki pattern 사용)
    
    **반환값**: 패턴 분석 결과
    """
    
    # 🔧 파라미터 검증 및 정규화
    query = validate_and_fix_query(query, "analyze_logs_pattern")
    
    # 기본값 설정
    if not time_range:
        time_range = DEFAULT_TIME_RANGE
    
    # 시간 범위 파싱
    start_ns, end_ns = parse_time_range(time_range)
    
    # 먼저 일반 로그를 가져옴
    params = {
        "query": query,
        "start": str(start_ns),
        "end": str(end_ns),
        "limit": 1000
    }
    
    logger.info(f"로그 패턴 분석을 위한 로그 조회: {query}")
    result = make_request(
        f"{LOKI_URL}/loki/api/v1/query_range",
        params=params,
        auth_user=LOKI_AUTH_USER,
        auth_password=LOKI_AUTH_PASSWORD
    )
    
    if result.get("error"):
        logger.error(f"로그 조회 API 오류: {result['error']}")
        return {
            "status": "error",
            "error": result["error"],
            "query": query,
            "hint": "쿼리 구문을 확인하세요. 예: '{service=\"api-gateway\"}'"
        }
    
    # 패턴 집계
    pattern_counts = {}
    total_logs = 0
    
    if result.get("data", {}).get("result"):
        for stream in result["data"]["result"]:
            for value in stream.get("values", []):
                _, log_line = value
                total_logs += 1
                
                # 간단한 패턴 추출
                import re
                pattern = log_line
                
                # 타임스탬프 정규화
                pattern = re.sub(r'\b\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}[\.\d]*[Z\+\-\d:]*\b', '<TIMESTAMP>', pattern)
                # UUID 정규화
                pattern = re.sub(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', '<UUID>', pattern, flags=re.IGNORECASE)
                # IP 주소 정규화
                pattern = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '<IP>', pattern)
                # 큰 숫자 정규화 (3자리 이상)
                pattern = re.sub(r'\b\d{3,}\b', '<NUMBER>', pattern)
                # 16진수 정규화
                pattern = re.sub(r'\b0x[0-9a-f]+\b', '<HEX>', pattern, flags=re.IGNORECASE)
                
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
    
    # 상위 패턴 정렬
    top_patterns = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # 결과 구성
    patterns = []
    for pattern, count in top_patterns:
        percentage = (count / total_logs * 100) if total_logs > 0 else 0
        patterns.append({
            "pattern": pattern[:200] + "..." if len(pattern) > 200 else pattern,
            "count": count,
            "percentage": round(percentage, 2)
        })
    
    logger.info(f"로그 패턴 분석 완료: 총 {total_logs}개 로그, {len(pattern_counts)}개 고유 패턴")
    
    return {
        "status": "success",
        "query": query,
        "time_range": time_range,
        "total_logs": total_logs,
        "unique_patterns": len(pattern_counts),
        "top_patterns": patterns,
        "pattern_type": "simple"  # Loki pattern이 실패하면 simple 사용
    }

@mcp.tool()
async def get_service_metrics(
    service_name: str,
    time_range: str = "1h",
    operation: Optional[str] = None
) -> Dict:
    """
    특정 서비스의 트레이스 메트릭을 조회합니다.
    
    **파라미터**:
    - service_name: 서비스 이름 (예: "api-gateway", "order-service")
    - time_range: 시간 범위 (예: "5m", "1h", "24h")
    - operation: 특정 오퍼레이션으로 필터링 (선택사항)
    
    **반환값**: 서비스의 평균 응답 시간, 에러율, 처리량 등의 메트릭
    """
    # 기본값 설정
    if not time_range:
        time_range = DEFAULT_TIME_RANGE
    
    # 시간 범위 파싱
    start_ns, end_ns = parse_time_range(time_range)
    
    # TraceQL 쿼리 구성
    query = f'{{resource.service.name="{service_name}"'
    if operation:
        query += f' && name="{operation}"'
    query += '}'
    
    # Tempo Search API 호출
    params = {
        "q": query,
        "start": str(int(start_ns // 1_000_000_000)),  # 나노초를 초로 변환
        "end": str(int(end_ns // 1_000_000_000)),      # 나노초를 초로 변환
        "limit": 1000  # 메트릭 계산을 위해 더 많은 트레이스 가져오기
    }
    
    logger.info(f"서비스 메트릭 조회: {service_name}")
    result = make_request(
        f"{TEMPO_URL}/api/search",
        params=params,
        auth_user=TEMPO_AUTH_USER,
        auth_password=TEMPO_AUTH_PASSWORD
    )
    
    if result.get("error"):
        return {
            "status": "error",
            "error": result["error"],
            "service": service_name,
            "hint": "서비스 이름이 올바른지 확인하세요."
        }
    
    # 메트릭 계산
    traces = result.get("traces", [])
    if not traces:
        return {
            "status": "success",
            "service": service_name,
            "message": "해당 기간에 트레이스가 없습니다.",
            "metrics": {
                "total_traces": 0,
                "error_count": 0,
                "error_rate": 0
            }
        }
    
    durations = []
    error_count = 0
    operations = {}
    
    for trace in traces:
        duration = trace.get("durationMs", 0)
        durations.append(duration)
        
        # 에러 확인 (간단한 휴리스틱)
        if trace.get("rootTraceName", "").lower().find("error") >= 0:
            error_count += 1
        
        # 오퍼레이션별 집계
        op_name = trace.get("rootTraceName", "unknown")
        if op_name not in operations:
            operations[op_name] = {"count": 0, "total_duration": 0}
        operations[op_name]["count"] += 1
        operations[op_name]["total_duration"] += duration
    
    # 통계 계산
    durations.sort()
    total_traces = len(traces)
    
    metrics = {
        "service": service_name,
        "time_range": time_range,
        "total_traces": total_traces,
        "error_count": error_count,
        "error_rate": round(error_count / total_traces * 100, 2) if total_traces > 0 else 0,
        "latency": {
            "min": min(durations) if durations else 0,
            "max": max(durations) if durations else 0,
            "avg": round(sum(durations) / len(durations), 2) if durations else 0,
            "p50": durations[int(len(durations) * 0.5)] if durations else 0,
            "p95": durations[int(len(durations) * 0.95)] if durations else 0,
            "p99": durations[int(len(durations) * 0.99)] if durations else 0
        },
        "operations": []
    }
    
    # 오퍼레이션별 메트릭
    for op_name, op_stats in operations.items():
        metrics["operations"].append({
            "name": op_name,
            "count": op_stats["count"],
            "avg_duration": round(op_stats["total_duration"] / op_stats["count"], 2)
        })
    
    # 오퍼레이션을 호출 횟수로 정렬
    metrics["operations"].sort(key=lambda x: x["count"], reverse=True)
    
    # Grafana 대시보드 링크 생성
    dashboard_link = None
    if GRAFANA_URL and TEMPO_DASHBOARD_ID:
        dashboard_link = f"{GRAFANA_URL}/d/{TEMPO_DASHBOARD_ID}?orgId=1&var-service={service_name}"
    
    metrics["dashboard_link"] = dashboard_link
    
    return {
        "status": "success",
        "metrics": metrics
    }

@mcp.tool()
async def correlate_logs_and_traces(
    trace_id: Optional[str] = None,
    time_window: str = "5m",
    service: Optional[str] = None
) -> Dict:
    """
    로그와 트레이스를 상관 분석합니다.
    
    **파라미터**:
    - trace_id: 특정 트레이스 ID (제공시 해당 트레이스와 관련된 로그 찾기)
    - time_window: 검색할 시간 범위 (예: "5m", "30m", "1h")
    - service: 특정 서비스로 필터링
    
    **반환값**: 트레이스 ID를 기반으로 관련 로그를 찾거나, 시간대별로 로그와 트레이스를 매칭
    """
    results = {
        "status": "success",
        "correlations": []
    }
    
    if trace_id:
        # 특정 트레이스에 대한 로그 찾기
        logger.info(f"트레이스 {trace_id}에 대한 로그 검색")
        
        # 트레이스 상세 정보 가져오기
        trace_details = await get_trace_details(trace_id)
        if trace_details.get("status") != "success":
            return {
                "status": "error",
                "error": "트레이스를 찾을 수 없습니다.",
                "trace_id": trace_id
            }
        
        # 트레이스의 시간 범위 추출
        spans = trace_details.get("spans", [])
        if not spans:
            return {
                "status": "error",
                "error": "트레이스에 스팬이 없습니다.",
                "trace_id": trace_id
            }
        
        # 모든 스팬의 시작/종료 시간 찾기
        start_times = [datetime.fromisoformat(s["start_time"]) for s in spans]
        end_times = [datetime.fromisoformat(s["end_time"]) for s in spans]
        
        trace_start = min(start_times)
        trace_end = max(end_times)
        
        # 시간 범위를 조금 넓혀서 로그 검색
        search_start = trace_start - timedelta(seconds=5)
        search_end = trace_end + timedelta(seconds=5)
        
        # 로그 쿼리 구성
        log_query = f'{{}} |= "{trace_id}"'
        if service:
            log_query = f'{{service="{service}"}} |= "{trace_id}"'
        
        # 로그 검색
        search_start_ns = int(search_start.timestamp() * 1_000_000_000)
        search_end_ns = int(search_end.timestamp() * 1_000_000_000)
        
        log_params = {
            "query": log_query,
            "start": str(search_start_ns),
            "end": str(search_end_ns),
            "limit": 1000
        }
        
        log_result = make_request(
            f"{LOKI_URL}/loki/api/v1/query_range",
            params=log_params,
            auth_user=LOKI_AUTH_USER,
            auth_password=LOKI_AUTH_PASSWORD
        )
        
        # 결과 처리
        correlated_logs = []
        if log_result.get("data", {}).get("result"):
            for stream in log_result["data"]["result"]:
                for value in stream.get("values", []):
                    timestamp_ns, log_line = value
                    correlated_logs.append({
                        "timestamp": datetime.fromtimestamp(int(timestamp_ns) / 1000000000).isoformat(),
                        "log": log_line,
                        "labels": stream.get("stream", {})
                    })
        
        results["correlations"].append({
            "trace_id": trace_id,
            "trace_duration_ms": trace_details.get("spans", [{}])[0].get("duration_ms", 0),
            "services": trace_details.get("services", []),
            "log_count": len(correlated_logs),
            "logs": correlated_logs[:10]  # 처음 10개만 반환
        })
        
    else:
        # 시간 기반 상관 분석
        logger.info(f"시간 기반 로그-트레이스 상관 분석: {time_window}")
        
        # 최근 에러 트레이스 찾기
        traces_result = await search_traces(
            tags={"error": "true"},
            time_range=time_window,
            limit=10
        )
        
        if traces_result.get("status") == "success" and traces_result.get("traces"):
            for trace in traces_result["traces"][:5]:  # 처음 5개 트레이스만
                # 각 트레이스에 대한 로그 찾기
                correlation = await correlate_logs_and_traces(
                    trace_id=trace["trace_id"],
                    time_window=time_window,
                    service=service
                )
                
                if correlation.get("status") == "success" and correlation.get("correlations"):
                    results["correlations"].extend(correlation["correlations"])
    
    results["correlation_count"] = len(results["correlations"])
    results["time_window"] = time_window
    
    return results

@mcp.tool()
async def export_data(
    data_type: str,
    query: str = None,
    time_range: str = "1h",
    format: str = "json",
    output_file: Optional[str] = None
) -> Dict[str, Any]:
    """
    로그나 트레이스 데이터를 내보냅니다.
    
    **파라미터**:
    - data_type: "logs" 또는 "traces"
    - query: 검색 쿼리 문자열 (logs: LogQL, traces: 서비스명)
    - time_range: 시간 범위 (예: "5m", "1h", "24h")
    - format: 출력 형식 ("json" 또는 "csv")
    - output_file: 저장할 파일 경로 (선택사항)
    
    **예제**:
    - 로그 내보내기: data_type="logs", query='{service="api-gateway"}'
    - 트레이스 내보내기: data_type="traces", query="api-gateway"
    
    **반환값**: 내보내기 결과
    """
    import csv
    import io
    
    results = []
    
    if data_type == "logs":
        # 로그 데이터 가져오기
        if not query:
            query = '{job=~".+"}'
        
        log_result = await query_logs(
            query=query,
            time_range=time_range,
            limit=10000  # 더 많은 데이터 가져오기
        )
        
        if log_result.get("status") != "success":
            return log_result
        
        results = log_result.get("logs", [])
        
    elif data_type == "traces":
        # 트레이스 데이터 가져오기
        service_name = query if query else None
        trace_result = await search_traces(
            service_name=service_name,
            time_range=time_range,
            limit=1000
        )
        
        if trace_result.get("status") != "success":
            return trace_result
        
        results = trace_result.get("traces", [])
        
    else:
        return {
            "status": "error",
            "error": "data_type은 'logs' 또는 'traces'여야 합니다."
        }
    
    # 형식에 따라 변환
    if format == "csv":
        if not results:
            return {
                "status": "error",
                "error": "내보낼 데이터가 없습니다."
            }
        
        # CSV 변환
        output = io.StringIO()
        if data_type == "logs":
            fieldnames = ["timestamp", "log", "service", "level", "container"]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for log in results:
                row = {
                    "timestamp": log["timestamp"],
                    "log": log["log"],
                    "service": log["labels"].get("service", ""),
                    "level": log["labels"].get("level", ""),
                    "container": log["labels"].get("container", "")
                }
                writer.writerow(row)
        else:  # traces
            fieldnames = ["trace_id", "service", "operation", "duration_ms", "start_time"]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for trace in results:
                row = {
                    "trace_id": trace["trace_id"],
                    "service": trace["root_service"],
                    "operation": trace["root_trace_name"],
                    "duration_ms": trace["duration_ms"],
                    "start_time": trace["start_time"]
                }
                writer.writerow(row)
        
        export_data = output.getvalue()
    else:  # json
        export_data = json.dumps(results, indent=2)
    
    # 파일로 저장 (선택사항)
    if output_file:
        try:
            with open(output_file, 'w') as f:
                f.write(export_data)
            
            return {
                "status": "success",
                "message": f"데이터가 {output_file}에 저장되었습니다.",
                "record_count": len(results),
                "format": format,
                "file_size": len(export_data)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"파일 저장 실패: {str(e)}"
            }
    
    return {
        "status": "success",
        "data": export_data if len(export_data) < 10000 else export_data[:10000] + "... (truncated)",
        "record_count": len(results),
        "format": format,
        "total_size": len(export_data)
    }

if __name__ == "__main__":
    print(f"Loki & Tempo MCP 서버 시작 - 포트: {os.getenv('MCP_PORT', '10002')}")
    print(f".env 파일 위치: {env_file}")
    print(f"Loki URL: {LOKI_URL}")
    print(f"Tempo URL: {TEMPO_URL}")
    print("🚀 MCP 서버 시작 중...")
    
    mcp.run(transport="sse")