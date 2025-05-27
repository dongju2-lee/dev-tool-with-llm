# k6_mcp_server.py
from typing import List, Dict, Optional
import uuid
import os
import subprocess
import requests
import json
import time
from jinja2 import Template
from mcp.server.fastmcp import FastMCP
from prometheus_api_client import PrometheusConnect
from dotenv import load_dotenv, find_dotenv, set_key
import logging
import pathlib
import sys

# 로깅 설정 추가
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("k6_mcp_server")

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
        "PROMETHEUS_URL": os.getenv("PROMETHEUS_URL"),
        "GRAFANA_URL": os.getenv("GRAFANA_URL"),
        "K6_DASHBOARD_ID": os.getenv("K6_DASHBOARD_ID"),
        "NOTIFICATION_URL": os.getenv("NOTIFICATION_URL"),
        "PROMETHEUS_REMOTE_WRITE": os.getenv("PROMETHEUS_REMOTE_WRITE"),
        "DOCKER_NETWORK": os.getenv("DOCKER_NETWORK"),
        "MICROSERVICE_BASE_URL": os.getenv("MICROSERVICE_BASE_URL"),
        "USER_SERVICE_PORT": os.getenv("USER_SERVICE_PORT"),
        "ORDER_SERVICE_PORT": os.getenv("ORDER_SERVICE_PORT"),
        "RESTAURANT_SERVICE_PORT": os.getenv("RESTAURANT_SERVICE_PORT"),
        "MCP_HOST": os.getenv("MCP_HOST"),
        "MCP_PORT": os.getenv("MCP_PORT"),
        "K6_SCRIPTS_PATH": os.getenv("K6_SCRIPTS_PATH"),
        "DEFAULT_ERROR_THRESHOLD": os.getenv("DEFAULT_ERROR_THRESHOLD"),
        "DEFAULT_API_ENDPOINT": os.getenv("DEFAULT_API_ENDPOINT")
    }
    
    logger.info("======== 환경 설정 ========")
    for key, value in env_vars.items():
        logger.info(f"{key}: {value}")
    logger.info("==========================")

# 환경 설정 로그 출력 - 값 확인을 위해 호출
log_environment_settings()

# .env에서 필수 환경 변수 누락 여부 확인
required_vars = [
    "PROMETHEUS_URL", "GRAFANA_URL", "K6_DASHBOARD_ID", 
    "PROMETHEUS_REMOTE_WRITE", "DOCKER_NETWORK", 
    "MICROSERVICE_BASE_URL", "USER_SERVICE_PORT", 
    "ORDER_SERVICE_PORT", "RESTAURANT_SERVICE_PORT",
    "MCP_HOST", "MCP_PORT"
]

missing_vars = []
for var in required_vars:
    if not os.getenv(var):
        missing_vars.append(var)
        
if missing_vars:
    logger.warning(f"다음 환경 변수가 .env 파일에 누락되었습니다: {', '.join(missing_vars)}")
    logger.warning(".env 파일을 확인하고 필요한 변수를 추가하세요.")

# 환경 변수에서 설정 로드
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL")
GRAFANA_URL = os.getenv("GRAFANA_URL")
K6_DASHBOARD_ID = os.getenv("K6_DASHBOARD_ID")
NOTIFICATION_URL = os.getenv("NOTIFICATION_URL")
DEFAULT_THRESHOLD = float(os.getenv("DEFAULT_ERROR_THRESHOLD", "0.05"))
REMOTE_WRITE_URL = os.getenv("PROMETHEUS_REMOTE_WRITE")
DOCKER_NETWORK = os.getenv("DOCKER_NETWORK")
MICROSERVICE_BASE_URL = os.getenv("MICROSERVICE_BASE_URL")
USER_SERVICE_PORT = os.getenv("USER_SERVICE_PORT")
ORDER_SERVICE_PORT = os.getenv("ORDER_SERVICE_PORT")
RESTAURANT_SERVICE_PORT = os.getenv("RESTAURANT_SERVICE_PORT")

# k6 스크립트 경로 - 상대 경로로 설정
K6_SCRIPTS_PATH = os.getenv("K6_SCRIPTS_PATH", os.path.join(current_dir, "load-test-server"))

# MCP 서버 설정 업데이트
mcp = FastMCP(
    "k6 Load Testing",
    instructions="k6를 사용한 부하 테스트 MCP 서버입니다. API 성능 테스트, 시나리오 테스트, 결과 분석 기능을 제공합니다.",
    host=os.getenv("MCP_HOST"),
    port=int(os.getenv("MCP_PORT", "10001"))
)

# 스크립트 경로가 존재하는지 확인
if not os.path.exists(K6_SCRIPTS_PATH):
    logger.warning(f"k6 스크립트 경로가 존재하지 않습니다: {K6_SCRIPTS_PATH}")
    logger.warning("환경 변수 K6_SCRIPTS_PATH를 설정하여 올바른 경로를 지정해주세요.")

# Prometheus 클라이언트 설정 업데이트
try:
    prom = PrometheusConnect(url=PROMETHEUS_URL)
    logger.info(f"Prometheus 연결 성공: {PROMETHEUS_URL}")
except Exception as e:
    logger.warning(f"Prometheus 연결 실패: {e}")
    prom = None

# 공통 도커 실행 함수
def run_k6_docker(script_file: str, env_vars: Dict, test_id: str) -> Dict:
    """
    도커 컨테이너에서 k6 스크립트를 실행합니다.
    
    Args:
        script_file: 실행할 k6 스크립트 파일 이름
        env_vars: 환경 변수 딕셔너리
        test_id: 테스트 ID
        
    Returns:
        실행 결과 딕셔너리
    """
    # 스크립트 전체 경로
    script_path = os.path.join(K6_SCRIPTS_PATH, script_file)
    
    # 스크립트 파일이 존재하는지 확인
    if not os.path.exists(script_path):
        logger.error(f"스크립트 파일을 찾을 수 없음: {script_path}")
        return {
            "test_id": test_id,
            "status": "failed",
            "script": script_file,
            "error": f"스크립트 파일을 찾을 수 없음: {script_path}"
        }
    
    # 환경 변수 문자열 생성 (-e KEY=VALUE 형식)
    env_str = " ".join([f"-e {k}={v}" for k, v in env_vars.items() if v])
    
    # 도커 네트워크 확인
    docker_network = DOCKER_NETWORK
    if not docker_network:
        docker_network = "bridge"  # 기본 네트워크 사용
        logger.warning(f"DOCKER_NETWORK 환경 변수가 설정되지 않았습니다. 기본 'bridge' 네트워크를 사용합니다.")
    
    # Prometheus Remote Write URL 확인
    prom_rw_url = REMOTE_WRITE_URL
    if not prom_rw_url:
        prom_rw_url = "http://prometheus:9090/api/v1/write"
        logger.warning(f"PROMETHEUS_REMOTE_WRITE 환경 변수가 설정되지 않았습니다. 기본값을 사용합니다: {prom_rw_url}")
    
    # 도커 명령어 구성
    docker_cmd = (
        f"docker run --rm --network={docker_network} "
        f"--name k6-test-{test_id} "
        f"-v {script_path}:/scripts/{script_file} "
        f"-e K6_PROMETHEUS_RW_SERVER_URL={prom_rw_url} "
        f"-e K6_PROMETHEUS_RW_TREND_AS_NATIVE_HISTOGRAM=true "
        f"-e K6_PROMETHEUS_RW_STALE_MARKERS=true "
        f"-e K6_PROMETHEUS_RW_TAG_BLACKLIST=vu,iter,url,group,scenario "
        f"-e TEST_ID={test_id} "
        f"{env_str} "
        f"grafana/k6:latest run -o experimental-prometheus-rw /scripts/{script_file}"
    )
    
    logger.info(f"도커 명령어 실행: {docker_cmd}")
    
    try:
        # 도커 명령어 실행
        result = subprocess.run(
            docker_cmd, 
            shell=True, 
            check=True, 
            capture_output=True, 
            text=True
        )
        logger.info(f"테스트 실행 성공: {test_id}")
        
        # 결과 추출
        output = result.stdout
        
        # Grafana 대시보드 링크 생성
        dashboard_link = None
        if GRAFANA_URL and K6_DASHBOARD_ID:
            dashboard_link = f"{GRAFANA_URL}/d/{K6_DASHBOARD_ID}?orgId=1&var-testid={test_id}"
        
        return {
            "test_id": test_id,
            "status": "completed",
            "script": script_file,
            "output_summary": output.split("\n")[-20:],  # 마지막 20줄만 반환
            "dashboard_link": dashboard_link
        }
        
    except subprocess.CalledProcessError as e:
        logger.error(f"테스트 실행 실패: {e}")
        return {
            "test_id": test_id,
            "status": "failed",
            "script": script_file,
            "error": e.stderr,
            "command": docker_cmd  # 디버깅을 위해 실행된 명령어 포함
        }

@mcp.tool()
async def update_environment_settings(
    prometheus_url: Optional[str] = None,
    grafana_url: Optional[str] = None,
    microservice_base_url: Optional[str] = None,
    docker_network: Optional[str] = None,
    user_service_port: Optional[str] = None,
    order_service_port: Optional[str] = None,
    restaurant_service_port: Optional[str] = None,
    k6_scripts_path: Optional[str] = None
) -> Dict:
    """
    환경 설정을 업데이트합니다.
    
    - prometheus_url: Prometheus 서버 URL
    - grafana_url: Grafana 서버 URL
    - microservice_base_url: 마이크로서비스 기본 URL
    - docker_network: 도커 네트워크 이름
    - user_service_port: 사용자 서비스 포트
    - order_service_port: 주문 서비스 포트
    - restaurant_service_port: 레스토랑 서비스 포트
    - k6_scripts_path: k6 스크립트 디렉토리 경로
    
    이 설정은 .env 파일에 저장되어 서버 재시작 후에도 유지됩니다.
    """
    global PROMETHEUS_URL, GRAFANA_URL, MICROSERVICE_BASE_URL, DOCKER_NETWORK
    global USER_SERVICE_PORT, ORDER_SERVICE_PORT, RESTAURANT_SERVICE_PORT, K6_SCRIPTS_PATH
    
    updated = {}
    
    if prometheus_url:
        set_key(env_file, "PROMETHEUS_URL", prometheus_url)
        PROMETHEUS_URL = prometheus_url
        updated["PROMETHEUS_URL"] = prometheus_url
    
    if grafana_url:
        set_key(env_file, "GRAFANA_URL", grafana_url)
        GRAFANA_URL = grafana_url
        updated["GRAFANA_URL"] = grafana_url
    
    if microservice_base_url:
        set_key(env_file, "MICROSERVICE_BASE_URL", microservice_base_url)
        MICROSERVICE_BASE_URL = microservice_base_url
        updated["MICROSERVICE_BASE_URL"] = microservice_base_url
    
    if docker_network:
        set_key(env_file, "DOCKER_NETWORK", docker_network)
        DOCKER_NETWORK = docker_network
        updated["DOCKER_NETWORK"] = docker_network
    
    if user_service_port:
        set_key(env_file, "USER_SERVICE_PORT", user_service_port)
        USER_SERVICE_PORT = user_service_port
        updated["USER_SERVICE_PORT"] = user_service_port
    
    if order_service_port:
        set_key(env_file, "ORDER_SERVICE_PORT", order_service_port)
        ORDER_SERVICE_PORT = order_service_port
        updated["ORDER_SERVICE_PORT"] = order_service_port
    
    if restaurant_service_port:
        set_key(env_file, "RESTAURANT_SERVICE_PORT", restaurant_service_port)
        RESTAURANT_SERVICE_PORT = restaurant_service_port
        updated["RESTAURANT_SERVICE_PORT"] = restaurant_service_port
    
    if k6_scripts_path:
        # 경로가 존재하는지 확인
        if os.path.exists(k6_scripts_path):
            set_key(env_file, "K6_SCRIPTS_PATH", k6_scripts_path)
            K6_SCRIPTS_PATH = k6_scripts_path
            updated["K6_SCRIPTS_PATH"] = k6_scripts_path
        else:
            return {
                "status": "error",
                "message": f"스크립트 경로가 존재하지 않습니다: {k6_scripts_path}"
            }
    
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
    
    서버에 설정된 환경 변수와 k6 스크립트 경로, 도커 상태 등을 확인하여 반환합니다.
    """
    env_vars = {
        "PROMETHEUS_URL": PROMETHEUS_URL,
        "GRAFANA_URL": GRAFANA_URL,
        "K6_DASHBOARD_ID": K6_DASHBOARD_ID,
        "DOCKER_NETWORK": DOCKER_NETWORK,
        "MICROSERVICE_BASE_URL": MICROSERVICE_BASE_URL,
        "USER_SERVICE_PORT": USER_SERVICE_PORT,
        "ORDER_SERVICE_PORT": ORDER_SERVICE_PORT,
        "RESTAURANT_SERVICE_PORT": RESTAURANT_SERVICE_PORT,
        "K6_SCRIPTS_PATH": K6_SCRIPTS_PATH
    }
    
    # 스크립트 디렉토리 확인
    scripts_exist = os.path.exists(K6_SCRIPTS_PATH)
    script_files = []
    if scripts_exist:
        script_files = [f for f in os.listdir(K6_SCRIPTS_PATH) if f.endswith('.js')]
    
    # 도커 상태 확인
    try:
        docker_result = subprocess.run(
            "docker info", 
            shell=True, 
            check=True, 
            capture_output=True, 
            text=True
        )
        docker_status = "실행 중"
    except subprocess.CalledProcessError:
        docker_status = "실행되지 않음 또는 접근 권한 없음"
    
    # k6 이미지 확인
    try:
        k6_image_result = subprocess.run(
            "docker image ls grafana/k6", 
            shell=True, 
            check=True, 
            capture_output=True, 
            text=True
        )
        k6_image_exists = "grafana/k6" in k6_image_result.stdout
    except subprocess.CalledProcessError:
        k6_image_exists = False
    
    return {
        "환경 변수": env_vars,
        "스크립트 디렉토리 존재": scripts_exist,
        "스크립트 파일": script_files if scripts_exist else "디렉토리가 존재하지 않습니다",
        "도커 상태": docker_status,
        "k6 이미지 존재": k6_image_exists
    }

@mcp.tool()
async def run_chaos_engineering_test(
    vus: int = 10,
    duration: str = "1m",
    payment_fail_percent: int = 30,
    username: str = "user123",
    password: str = "password123",
    menu_id: int = 1,
) -> Dict:
    """
    카오스 엔지니어링 테스트 실행: 결제 실패율을 설정하고 시스템의 복원력을 테스트
    
    - vus: 가상 사용자 수
    - duration: 테스트 지속 시간 (예: "30s", "1m", "5m")
    - payment_fail_percent: 결제 실패율 (%)
    - username: 테스트 사용자 이름
    - password: 테스트 사용자 비밀번호
    - menu_id: 주문할 메뉴 ID
    
    이 테스트는 지정된 결제 실패율로 주문 프로세스의 복원력을 검증합니다.
    결제 실패 시 재고가 자동으로 복구되는지, 시스템 상태가 일관되게 유지되는지 확인합니다.
    """
    test_id = str(uuid.uuid4())
    
    # 환경 변수 설정
    env_vars = {
        "BASE_URL": MICROSERVICE_BASE_URL,
        "USER_SERVICE_PORT": USER_SERVICE_PORT,
        "ORDER_SERVICE_PORT": ORDER_SERVICE_PORT,
        "RESTAURANT_SERVICE_PORT": RESTAURANT_SERVICE_PORT,
        "VUS": str(vus),
        "STEADY_STATE": duration,
        "PAYMENT_FAIL_PERCENT": str(payment_fail_percent),
        "USERNAME": username,
        "PASSWORD": password,
        "MENU_ID": str(menu_id),
        "TEST_ID": test_id
    }
    
    logger.info(f"카오스 엔지니어링 테스트 시작: {test_id}")
    return run_k6_docker("01-chaos-engineering-test.js", env_vars, test_id)

@mcp.tool()
async def run_concurrent_orders_test(
    peak_target: int = 30,
    steady_duration: str = "1m",
    menu_id: int = 1,
    user_count: int = 10,
    max_vus: int = 100,
) -> Dict:
    """
    동시 주문 처리 테스트 실행: 동시에 많은 사용자가 같은 메뉴를 주문할 때의 동시성 제어를 테스트
    
    - peak_target: 초당 최대 요청 수 (초당 주문 수)
    - steady_duration: 최대 부하 지속 시간 (예: "30s", "1m", "5m")
    - menu_id: 주문할 메뉴 ID
    - user_count: 생성할 테스트 사용자 수
    - max_vus: 최대 가상 사용자 수
    
    이 테스트는 동시에 여러 사용자가 같은 메뉴를 주문할 때의 동시성 제어를 검증합니다.
    재고 관리의 일관성과 경쟁 상태 처리를 테스트합니다.
    """
    test_id = str(uuid.uuid4())
    
    # 환경 변수 설정
    env_vars = {
        "BASE_URL": MICROSERVICE_BASE_URL,
        "USER_SERVICE_PORT": USER_SERVICE_PORT,
        "ORDER_SERVICE_PORT": ORDER_SERVICE_PORT,
        "RESTAURANT_SERVICE_PORT": RESTAURANT_SERVICE_PORT,
        "PEAK_TARGET": str(peak_target),
        "STEADY_TARGET": str(peak_target),
        "STEADY_STATE": steady_duration,
        "MENU_ID": str(menu_id),
        "USER_COUNT": str(user_count),
        "MAX_VUS": str(max_vus),
        "TEST_ID": test_id
    }
    
    logger.info(f"동시 주문 테스트 시작: {test_id}")
    return run_k6_docker("02-concurrent-orders-test.js", env_vars, test_id)

@mcp.tool()
async def run_cancel_reorder_test(
    vus: int = 10,
    duration: str = "1m",
    menu_id: int = 1,
    username: str = "user123",
    password: str = "password123",
) -> Dict:
    """
    주문 취소 후 재주문 테스트 실행: 재고 관리의 일관성을 테스트
    
    - vus: 가상 사용자 수
    - duration: 테스트 지속 시간 (예: "30s", "1m", "5m")
    - menu_id: 주문할 메뉴 ID
    - username: 테스트 사용자 이름
    - password: 테스트 사용자 비밀번호
    
    이 테스트는 주문 생성, 취소, 재주문 과정을 반복하며 재고 관리의 일관성을 검증합니다.
    취소된 주문으로 인해 재고가 정확히 복구되는지 확인합니다.
    """
    test_id = str(uuid.uuid4())
    
    # 환경 변수 설정
    env_vars = {
        "BASE_URL": MICROSERVICE_BASE_URL,
        "USER_SERVICE_PORT": USER_SERVICE_PORT,
        "ORDER_SERVICE_PORT": ORDER_SERVICE_PORT,
        "RESTAURANT_SERVICE_PORT": RESTAURANT_SERVICE_PORT,
        "VUS": str(vus),
        "STEADY_STATE": duration,
        "MENU_ID": str(menu_id),
        "USERNAME": username,
        "PASSWORD": password,
        "TEST_ID": test_id
    }
    
    logger.info(f"취소-재주문 테스트 시작: {test_id}")
    return run_k6_docker("03-cancel-reorder-test.js", env_vars, test_id)

@mcp.tool()
async def run_caching_effect_test(
    vus: int = 5,
    duration: str = "1m",
    menu_id: int = 1,
    username: str = "user123",
    password: str = "password123",
) -> Dict:
    """
    캐싱 효과 테스트 실행: Redis 캐싱이 성능에 미치는 영향을 측정
    
    - vus: 가상 사용자 수
    - duration: 테스트 지속 시간 (예: "30s", "1m", "5m")
    - menu_id: 주문할 메뉴 ID
    - username: 테스트 사용자 이름
    - password: 테스트 사용자 비밀번호
    
    이 테스트는 첫 번째 API 호출과 이후 캐시된 호출의 응답 시간을 비교하여 
    Redis 캐싱이 성능에 미치는 영향을 측정합니다.
    """
    test_id = str(uuid.uuid4())
    
    # 환경 변수 설정
    env_vars = {
        "BASE_URL": MICROSERVICE_BASE_URL,
        "USER_SERVICE_PORT": USER_SERVICE_PORT,
        "ORDER_SERVICE_PORT": ORDER_SERVICE_PORT,
        "RESTAURANT_SERVICE_PORT": RESTAURANT_SERVICE_PORT,
        "VUS": str(vus),
        "STEADY_STATE": duration,
        "MENU_ID": str(menu_id),
        "USERNAME": username,
        "PASSWORD": password,
        "TEST_ID": test_id
    }
    
    logger.info(f"캐싱 효과 테스트 시작: {test_id}")
    return run_k6_docker("04-caching-effect-test.js", env_vars, test_id)

@mcp.tool()
async def run_microservice_communication_test(
    vus: int = 5,
    duration: str = "1m",
    username: str = "testuser",
    password: str = "testpass123",
) -> Dict:
    """
    마이크로서비스 간 통신 테스트 실행: 서비스 간 호출 흐름을 테스트
    
    - vus: 가상 사용자 수
    - duration: 테스트 지속 시간 (예: "30s", "1m", "5m")
    - username: 테스트 사용자 이름
    - password: 테스트 사용자 비밀번호
    
    이 테스트는 사용자 인증, 메뉴 조회, 주문 생성 등의 전체 흐름을 통해
    마이크로서비스 간 통신의 안정성을 검증합니다.
    """
    test_id = str(uuid.uuid4())
    
    # 환경 변수 설정
    env_vars = {
        "BASE_URL": MICROSERVICE_BASE_URL,
        "USER_SERVICE_PORT": USER_SERVICE_PORT,
        "ORDER_SERVICE_PORT": ORDER_SERVICE_PORT,
        "RESTAURANT_SERVICE_PORT": RESTAURANT_SERVICE_PORT,
        "VUS": str(vus),
        "STEADY_STATE": duration,
        "DEFAULT_USERNAME": username,
        "DEFAULT_PASSWORD": password,
        "TEST_ID": test_id
    }
    
    logger.info(f"마이크로서비스 통신 테스트 시작: {test_id}")
    return run_k6_docker("05-microservice-communication-test.js", env_vars, test_id)

@mcp.tool()
async def run_load_test(
    endpoint: str,
    vus: int = 10,
    duration: str = "30s",
    method: str = "GET",
    payload: Optional[Dict] = None,
) -> Dict:
    """
    특정 API 엔드포인트 부하 테스트 실행
    
    - endpoint: 테스트할 API 엔드포인트 URL
    - vus: 가상 사용자 수 (동시 사용자 수)
    - duration: 테스트 지속 시간 (예: "30s", "1m", "5m")
    - method: HTTP 메서드 (GET, POST, PUT, DELETE)
    - payload: 요청 본문 데이터 (POST/PUT 요청용)
    
    이 도구는 지정된 엔드포인트에 일정한 부하를 생성하는 기본 테스트를 실행합니다.
    테스트 결과는 Prometheus에 저장되며, 나중에 compare_results로 분석할 수 있습니다.
    """
    test_id = str(uuid.uuid4())
    
    # k6 스크립트 템플릿
    LOAD_TEST_TEMPLATE = """
    import http from 'k6/http';
    import { check, sleep } from 'k6';
    
    export const options = {
      vus: {{ vus }},
      duration: '{{ duration }}',
      thresholds: {
        http_req_duration: ['p(95)<3000'],
        http_req_failed: ['rate<0.1'],
      },
    };
    
    export default function() {
      {% if method|lower == 'get' %}
      const res = http.get('{{ endpoint }}');
      {% elif method|lower == 'post' %}
      const payload = {{ payload|tojson }};
      const res = http.post('{{ endpoint }}', JSON.stringify(payload), {
        headers: { 'Content-Type': 'application/json' },
      });
      {% elif method|lower == 'put' %}
      const payload = {{ payload|tojson }};
      const res = http.put('{{ endpoint }}', JSON.stringify(payload), {
        headers: { 'Content-Type': 'application/json' },
      });
      {% elif method|lower == 'delete' %}
      const res = http.del('{{ endpoint }}');
      {% endif %}
      
      check(res, {
        'status is 2xx': (r) => r.status >= 200 && r.status < 300,
        'response time < 1s': (r) => r.timings.duration < 1000,
      });
      
      sleep(1);
    }
    """
    
    script = Template(LOAD_TEST_TEMPLATE).render({
        "endpoint": endpoint,
        "vus": vus,
        "duration": duration,
        "method": method.lower(),
        "payload": payload or {},
    })
    
    script_path = f"/tmp/{test_id}.js"
    with open(script_path, "w") as f:
        f.write(script)
    
    try:
        # Docker 컨테이너에서 실행
        docker_cmd = (
            f"docker run --rm --network={DOCKER_NETWORK} "
            f"--name k6-load-test-{test_id} "
            f"-v {script_path}:/scripts/load-test.js "
            f"grafana/k6:latest run /scripts/load-test.js"
        )
        
        result = subprocess.run(
            docker_cmd,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        
        # 결과 추출
        output = result.stdout
        
        # Grafana 대시보드 링크 생성
        dashboard_link = None
        if GRAFANA_URL and K6_DASHBOARD_ID:
            dashboard_link = f"{GRAFANA_URL}/d/{K6_DASHBOARD_ID}?orgId=1&var-testid={test_id}"
        
        return {
            "test_id": test_id,
            "status": "completed",
            "endpoint": endpoint,
            "vus": vus,
            "duration": duration,
            "method": method,
            "output_summary": output.split("\n")[-20:],  # 마지막 20줄만 반환
            "dashboard_link": dashboard_link
        }
        
    except subprocess.CalledProcessError as e:
        logger.error(f"테스트 실행 실패: {e}")
        return {
            "test_id": test_id,
            "status": "failed",
            "endpoint": endpoint,
            "error": e.stderr
        }
    finally:
        os.remove(script_path)

@mcp.tool()
async def get_test_results(test_id: str) -> Dict:
    """
    이전에 실행된 테스트의 결과를 조회합니다.
    
    - test_id: 조회할 테스트 ID
    
    이전에 실행된 테스트의 결과 지표를 Prometheus에서 가져와 분석합니다.
    """
    if not prom:
        return {"error": "Prometheus 연결이 구성되지 않았습니다."}
    
    try:
        # Prometheus에서 테스트 결과 조회
        metrics = [
            "k6_http_reqs",
            "k6_http_req_duration_p95",
            "k6_vus",
            "k6_iterations",
            "k6_http_req_failed"
        ]
        
        results = {}
        for metric in metrics:
            query = f'{metric}{{testid="{test_id}"}}'
            result = prom.custom_query(query=query)
            if result:
                results[metric] = result
        
        # Grafana 대시보드 링크 생성
        dashboard_link = None
        if GRAFANA_URL and K6_DASHBOARD_ID:
            dashboard_link = f"{GRAFANA_URL}/d/{K6_DASHBOARD_ID}?orgId=1&var-testid={test_id}"
        
        return {
            "test_id": test_id,
            "metrics": results,
            "dashboard_link": dashboard_link
        }
    except Exception as e:
        logger.error(f"결과 조회 실패: {e}")
        return {
            "test_id": test_id,
            "status": "error",
            "error": str(e)
        }

@mcp.tool()
async def compare_results(test_id1: str, test_id2: str) -> Dict:
    """
    두 테스트 결과를 비교합니다.
    
    - test_id1: 첫 번째 테스트 ID
    - test_id2: 두 번째 테스트 ID
    
    두 테스트의 주요 성능 지표를 비교하여 차이점을 분석합니다.
    """
    if not prom:
        return {"error": "Prometheus 연결이 구성되지 않았습니다."}
    
    try:
        # 비교할 메트릭
        metrics = [
            "k6_http_req_duration_p95",
            "k6_http_req_failed",
            "k6_iterations"
        ]
        
        comparison = {}
        for metric in metrics:
            query1 = f'avg({metric}{{testid="{test_id1}"}})'
            query2 = f'avg({metric}{{testid="{test_id2}"}})'
            
            result1 = prom.custom_query(query=query1)
            result2 = prom.custom_query(query=query2)
            
            if result1 and result2:
                value1 = float(result1[0]['value'][1])
                value2 = float(result2[0]['value'][1])
                diff_pct = ((value2 - value1) / value1) * 100 if value1 != 0 else float('inf')
                
                comparison[metric] = {
                    "test1": value1,
                    "test2": value2,
                    "diff_percent": diff_pct,
                    "improved": diff_pct < 0 if metric.endswith("duration") or metric.endswith("failed") else diff_pct > 0
                }
        
        return {
            "test_id1": test_id1,
            "test_id2": test_id2,
            "comparison": comparison,
            "summary": "테스트 결과 비교가 완료되었습니다."
        }
    except Exception as e:
        logger.error(f"비교 실패: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    print(f"K6 MCP 서버 시작 - 포트: {os.getenv('MCP_PORT', '10001')}")
    print(f".env 파일 위치: {env_file}")
    print(f"k6 스크립트 경로: {K6_SCRIPTS_PATH}")
    mcp.run(transport="sse")
