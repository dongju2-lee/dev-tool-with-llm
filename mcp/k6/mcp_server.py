# k6_mcp_server.py
from typing import List, Dict, Optional
import uuid
import os
import subprocess
import requests
from jinja2 import Template
from mcp.server.fastmcp import FastMCP
from prometheus_api_client import PrometheusConnect
from dotenv import load_dotenv
import logging
import json

# 환경 변수 로드 코드 추가
load_dotenv()

# 환경 변수에서 설정 로드
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
K6_DASHBOARD_ID = os.getenv("K6_DASHBOARD_ID", "k6-load-testing")
NOTIFICATION_URL = os.getenv("NOTIFICATION_URL", "")
DEFAULT_THRESHOLD = float(os.getenv("DEFAULT_ERROR_THRESHOLD", "0.1"))
REMOTE_WRITE_URL = os.getenv("PROMETHEUS_REMOTE_WRITE", "http://prometheus:9090/api/v1/write")

# 로깅 설정 추가
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("k6_mcp_server")

# MCP 서버 설정 업데이트
mcp = FastMCP(
    "k6 Load Testing",
    instructions="k6를 사용한 부하 테스트 MCP 서버입니다. API 성능 테스트, 시나리오 테스트, 결과 분석 기능을 제공합니다.",
    host=os.getenv("MCP_HOST", "0.0.0.0"),
    port=int(os.getenv("MCP_PORT", "8000"))
)

# Prometheus 클라이언트 설정 업데이트
try:
    prom = PrometheusConnect(url=PROMETHEUS_URL)
    logger.info(f"Prometheus 연결 성공: {PROMETHEUS_URL}")
except Exception as e:
    logger.warning(f"Prometheus 연결 실패: {e}")
    prom = None

# k6 스크립트 템플릿
LOAD_TEST_TEMPLATE = """
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
    scenarios: {
        main_scenario: {
            executor: 'constant-vus',
            vus: {{vus}},
            duration: '{{duration}}',
        },
    },
    ext: {
        prometheus: {
            endpoint: "{{prometheus_endpoint}}",
            tlsConfig: {
                insecureSkipTLSVerify: true
            }
        }
    }
};

export default function () {
    const res = http.{{method}}('{{endpoint}}'{% if payload %}, JSON.stringify({{payload}}){% endif %});
    check(res, { 'status is 200': (r) => r.status === 200 });
    sleep(1);
}
"""

# 스테이지 기반 k6 스크립트 템플릿
STAGED_LOAD_TEST_TEMPLATE = """
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
    scenarios: {
        staged_scenario: {
            executor: 'ramping-vus',
            stages: [
                {% for stage in stages %}
                {
                    duration: '{{stage.duration}}',
                    target: {{stage.target_vus}}
                }{% if not loop.last %},{% endif %}
                {% endfor %}
            ],
        },
    },
    ext: {
        prometheus: {
            endpoint: "{{prometheus_endpoint}}",
            tlsConfig: {
                insecureSkipTLSVerify: true
            }
        }
    }
};

export default function () {
    const res = http.{{method}}('{{endpoint}}'{% if payload %}, JSON.stringify({{payload}}){% endif %});
    check(res, { 'status is 200': (r) => r.status === 200 });
    sleep({{sleep_time}});
}
"""

@mcp.tool()
async def run_load_test(
    endpoint: str,
    vus: int = 10,
    duration: str = "1m",
    method: str = "GET",
    payload: Optional[Dict] = None
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
    
    script = Template(LOAD_TEST_TEMPLATE).render({
        "endpoint": endpoint,
        "vus": vus,
        "duration": duration,
        "method": method.lower(),
        "payload": payload,
        "prometheus_endpoint": REMOTE_WRITE_URL
    })
    
    script_path = f"/tmp/{test_id}.js"
    with open(script_path, "w") as f:
        f.write(script)
    
    try:
        subprocess.run(
            ["k6", "run", script_path],
            check=True,
            capture_output=True
        )
    except subprocess.CalledProcessError as e:
        return {"error": e.stderr.decode()}
    finally:
        os.remove(script_path)
    
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
        "dashboard_link": dashboard_link
    }

@mcp.tool()
async def compare_results(
    test_id: str,
    metrics: List[str] = None,
    compare_with: List[str] = None
) -> Dict:
    """
    과거 테스트 결과 비교 및 성능 분석
    
    - test_id: 분석할 테스트 ID
    - metrics: 분석할 메트릭 목록 (기본값: ['http_req_duration', 'http_reqs', 'http_req_failed'])
    - compare_with: 비교할 다른 테스트 ID 목록 (선택 사항)
    
    반환 결과에는 다음 정보가 포함됩니다:
    - 최대 TPS (초당 트랜잭션 수)
    - 평균 응답 시간
    - 에러율
    - p95, p99 응답 시간 (95%, 99% 백분위)
    - 시간별 성능 트렌드
    - Grafana 대시보드 링크 (설정된 경우)
    """
    if metrics is None:
        metrics = ['http_req_duration', 'http_reqs', 'http_req_failed']
    
    test_results = {}
    
    # 테스트 ID 목록 (비교 대상 포함)
    all_test_ids = [test_id]
    if compare_with:
        all_test_ids.extend(compare_with)
    
    # Prometheus에서 각 메트릭 조회
    for current_test_id in all_test_ids:
        test_results[current_test_id] = {}
        
        # 메트릭별 데이터 수집
        for metric in metrics:
            full_metric = f'k6_{metric}'
            query_result = prom.custom_query(
                f'{full_metric}{{test_id="{current_test_id}"}}'
            )
            
            if query_result and len(query_result) > 0:
                # 메트릭 값 처리
                values = [float(point[1]) for point in query_result[0].get('values', [])]
                test_results[current_test_id][metric] = {
                    'avg': sum(values) / len(values) if values else 0,
                    'max': max(values) if values else 0,
                    'min': min(values) if values else 0,
                    'values': values
                }
    
    # 결과 분석 및 계산
    analysis = {}
    for current_test_id, results in test_results.items():
        # 기본 메트릭이 수집된 경우에만 계산
        if all(metric in results for metric in ['http_reqs', 'http_req_duration', 'http_req_failed']):
            # TPS 계산 (http_reqs 메트릭이 초당 요청 수를 의미)
            max_tps = results['http_reqs']['max']
            
            # 에러율 계산
            error_rate = 0
            if 'http_req_failed' in results:
                error_values = results['http_req_failed']['values']
                if error_values:
                    error_rate = sum(error_values) / len(error_values)
            
            # 응답 시간 통계
            response_times = results['http_req_duration']['values']
            response_times.sort()
            
            p95 = response_times[int(len(response_times) * 0.95)] if response_times else 0
            p99 = response_times[int(len(response_times) * 0.99)] if response_times else 0
            
            analysis[current_test_id] = {
                'max_tps': max_tps,
                'avg_response_time': results['http_req_duration']['avg'],
                'error_rate': error_rate,
                'p95_response_time': p95,
                'p99_response_time': p99
            }
    
    # Grafana 대시보드 링크 생성 (환경 변수에 설정된 경우)
    grafana_url = GRAFANA_URL
    dashboard_id = K6_DASHBOARD_ID
    
    dashboard_link = None
    if grafana_url and dashboard_id:
        # Grafana 시간 범위 설정 (테스트 시작 시간부터 +1시간)
        test_time = prom.custom_query(
            f'k6_http_reqs_first_timestamp{{test_id="{test_id}"}}'
        )
        
        if test_time and len(test_time) > 0:
            try:
                start_time = int(float(test_time[0]['value'][1]))
                end_time = start_time + 3600  # 1시간 추가
                
                dashboard_link = (
                    f"{grafana_url}/d/{dashboard_id}?orgId=1&from={start_time}000"
                    f"&to={end_time}000&var-testid={test_id}"
                )
            except (IndexError, KeyError, ValueError):
                pass
    
    return {
        "test_id": test_id,
        "compared_with": compare_with,
        "metrics": metrics,
        "analysis": analysis,
        "dashboard_link": dashboard_link
    }

@mcp.tool()
async def generate_from_openapi(swagger_url: str) -> str:
    """Swagger/OpenAPI 문서 파싱하여 스크립트 생성"""
    try:
        result = subprocess.run(
            ['openapi2k6', '-o', 'output.js', swagger_url],
            capture_output=True,
            text=True,
            check=True
        )
        with open('output.js') as f:
            return f.read()
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def execute_scenario(
    steps: List[Dict],
    vus: int = 10,
    duration: str = "5m"
) -> Dict:
    """
    시나리오 기반 테스트 실행 
    - steps: 테스트 단계 목록, 각 단계는 다음 형식의 딕셔너리:
        {
            "description": "단계 설명",
            "method": "GET/POST/PUT/DELETE",
            "endpoint": "호출할 URL",
            "payload": {"key": "value"} (선택 사항),
            "check": "응답 검증 조건",
            "delay": 지연 시간(초)(선택 사항)
        }
    - vus: 동시 가상 사용자 수 (모든 단계에 동일하게 적용)
    - duration: 전체 테스트 지속 시간 (모든 단계에 동일한 부하)
    
    주의: 이 함수는 테스트 기간 동안 일정한 부하만 지원합니다.
    시간별로 다른 부하 프로필이 필요한 경우 execute_staged_scenario를 사용하세요.
    """
    scenario_id = str(uuid.uuid4())
    
    scenario_script = f"""
    import http from 'k6/http';
    import {{ check, sleep }} from 'k6';
    
    export const options = {{
        vus: {vus},
        duration: '{duration}'
    }};
    
    export default function () {{
        {"".join([
            f'''
            // Step {i+1}: {step['description']}
            let res{i} = http.{step['method'].lower()}('{step['endpoint']}'{', JSON.stringify('+str(step['payload'])+')' if step.get('payload') else ''});
            check(res{i}, {{ '{step['check']}': (r) => r.status === 200 }});
            sleep({step.get('delay', 1)});
            ''' 
            for i, step in enumerate(steps)
        ])}
    }}
    """
    
    script_path = f"/tmp/{scenario_id}.js"
    with open(script_path, "w") as f:
        f.write(scenario_script)
    
    subprocess.run(["k6", "run", script_path], check=True)
    os.remove(script_path)
    
    return {"status": "completed", "scenario_id": scenario_id}

@mcp.tool()
async def execute_staged_scenario(
    endpoint: str,
    stages: List[Dict],
    method: str = "GET",
    payload: Optional[Dict] = None,
    sleep_time: float = 1.0
) -> Dict:
    """
    단계별 부하 프로필을 적용한 고급 시나리오 테스트 실행
    - endpoint: 테스트할 API 엔드포인트
    - stages: 각 단계별 설정 목록, 각 단계는 다음 형식의 딕셔너리:
        {
            "duration": "단계 지속 시간(예: '5m', '30s')",
            "target_vus": 목표 가상 사용자 수(예: 10, 50, 100)
        }
    - method: HTTP 메서드(GET, POST, PUT, DELETE)
    - payload: 요청 본문 데이터(선택 사항)
    - sleep_time: 요청 간 대기 시간(초)
    
    예시:
    stages = [
        {"duration": "5m", "target_vus": 10},   # 처음 5분간 10명의 VU로 부하
        {"duration": "10m", "target_vus": 50},  # 다음 10분간 50명으로 증가
        {"duration": "5m", "target_vus": 0}     # 마지막 5분간 0명으로 감소(정리)
    ]
    
    이 함수는 시간에 따라 가상 사용자 수를 점진적으로 변경하는 부하 테스트를 실행합니다.
    각 단계는 이전 단계에서 지정한 VU 수에서 목표 VU 수까지 점진적으로 변경됩니다.
    """
    test_id = str(uuid.uuid4())
    
    # 단계 유효성 검사
    if not stages or not all(isinstance(s, dict) and "duration" in s and "target_vus" in s for s in stages):
        return {"error": "모든 단계에는 'duration'과 'target_vus' 필드가 필요합니다"}
    
    script = Template(STAGED_LOAD_TEST_TEMPLATE).render({
        "endpoint": endpoint,
        "stages": stages,
        "method": method.lower(),
        "payload": payload,
        "sleep_time": sleep_time,
        "prometheus_endpoint": REMOTE_WRITE_URL
    })
    
    script_path = f"/tmp/{test_id}_staged.js"
    with open(script_path, "w") as f:
        f.write(script)
    
    try:
        result = subprocess.run(
            ["k6", "run", script_path],
            check=True,
            capture_output=True,
            text=True
        )
        
        # 결과 요약 정보 추출
        output = result.stdout
        summary_lines = [line for line in output.split('\n') if "iterations" in line or "http_reqs" in line]
        summary = "\n".join(summary_lines) if summary_lines else "결과 요약을 찾을 수 없습니다"
        
        return {
            "status": "completed",
            "test_id": test_id,
            "stages_count": len(stages),
            "total_duration": sum(
                int(s["duration"].replace("m", "")) * 60 if "m" in s["duration"] else
                int(s["duration"].replace("s", ""))
                for s in stages if isinstance(s["duration"], str)
            ),
            "summary": summary
        }
    except subprocess.CalledProcessError as e:
        return {"error": e.stderr, "test_id": test_id}
    finally:
        os.remove(script_path)

@mcp.tool()
async def auth_test(
    auth_endpoint: str,
    auth_payload: Dict,
    test_endpoint: str,
    vus: int = 10,
    duration: str = "5m"
) -> Dict:
    """인증이 필요한 API 테스트"""
    test_id = str(uuid.uuid4())
    
    auth_script = f"""
    import http from 'k6/http';
    import {{ check, sleep }} from 'k6';
    
    export const options = {{
        vus: {vus},
        duration: '{duration}'
    }};
    
    export default function () {{
        // Authentication
        const authRes = http.post('{auth_endpoint}', JSON.stringify({auth_payload}));
        const token = authRes.json('token');
        
        // Main Test
        const res = http.get('{test_endpoint}', {{
            headers: {{ 'Authorization': `Bearer ${{token}}` }}
        }});
        check(res, {{ 'status is 200': (r) => r.status === 200 }});
        sleep(1);
    }}
    """
    
    script_path = f"/tmp/{test_id}_auth.js"
    with open(script_path, "w") as f:
        f.write(auth_script)
    
    subprocess.run(["k6", "run", script_path], check=True)
    os.remove(script_path)
    
    return {"test_id": test_id}

@mcp.tool()
async def monitor_test(
    test_config: Dict,
    alert_thresholds: Dict = None,
    notification_channels: List[str] = None,
    notification_message: str = None
) -> Dict:
    """
    테스트 실행 및 실패 시 자동 알림
    
    - test_config: run_load_test 또는 execute_staged_scenario에 전달할 설정
    - alert_thresholds: 알림 임계값 설정 (예: {'error_rate': 0.05, 'response_time': 500})
    - notification_channels: 알림 채널 목록 ('slack', 'webhook' 지원)
    - notification_message: 알림에 포함할 추가 메시지
    
    설정된 임계값을 초과하면 지정된 채널로 알림을 발송합니다.
    """
    logger.info(f"모니터링 테스트 시작: {test_config.get('endpoint', '')}")
    
    # 기본값 설정
    if alert_thresholds is None:
        alert_thresholds = {'error_rate': DEFAULT_THRESHOLD, 'response_time': 1000}
    
    if notification_channels is None:
        notification_channels = ['webhook']
    
    # 테스트 실행 (test_config에 함수명이 없으면 run_load_test 사용)
    if 'function' in test_config and test_config['function'] == 'execute_staged_scenario':
        # test_config에서 함수명을 제거하고 나머지 매개변수만 전달
        function_params = {k: v for k, v in test_config.items() if k != 'function'}
        test_result = await execute_staged_scenario(**function_params)
    else:
        # function 키 제거 (있는 경우)
        function_params = {k: v for k, v in test_config.items() if k != 'function'}
        test_result = await run_load_test(**function_params)
    
    # 테스트 실패 또는 오류 발생 시
    if 'error' in test_result:
        alert_data = {
            "alert_type": "TEST_ERROR",
            "test_id": test_result.get("test_id", "unknown"),
            "error": test_result["error"],
            "test_config": test_config,
            "message": notification_message or "테스트 실행 중 오류가 발생했습니다."
        }
        
        await send_alerts(alert_data, notification_channels)
        return test_result
    
    # 테스트 성공했지만 메트릭 임계값 초과 여부 확인
    test_id = test_result.get("test_id")
    if not test_id:
        return test_result
    
    # Prometheus에서 메트릭 조회
    metrics_to_check = {
        'error_rate': f'k6_http_req_failed{{test_id="{test_id}"}}',
        'response_time': f'k6_http_req_duration{{test_id="{test_id}"}}'
    }
    
    alerts = []
    
    for metric_name, query in metrics_to_check.items():
        if not prom:
            logger.warning("Prometheus 연결 실패로 메트릭 조회를 건너뜁니다.")
            continue
            
        try:
            metric_result = prom.custom_query(query)
            
            if metric_result and len(metric_result) > 0:
                values = [float(point[1]) for point in metric_result[0].get('values', [])]
                if values:
                    avg_value = sum(values) / len(values)
                    threshold = alert_thresholds.get(metric_name, 0)
                    
                    if avg_value > threshold:
                        alerts.append({
                            "metric": metric_name,
                            "value": avg_value,
                            "threshold": threshold
                        })
        except Exception as e:
            logger.error(f"메트릭 조회 실패: {e}")
    
    # 알림이 필요한 경우
    if alerts:
        alert_data = {
            "alert_type": "THRESHOLD_EXCEEDED",
            "test_id": test_id,
            "alerts": alerts,
            "test_config": test_config,
            "grafana_link": test_result.get("dashboard_link"),
            "message": notification_message or "테스트 임계값이 초과되었습니다."
        }
        
        await send_alerts(alert_data, notification_channels)
        
        # 테스트 결과에 알림 정보 추가
        test_result["alerts"] = alerts
    
    return test_result

# 알림 발송 헬퍼 함수 추가
async def send_alerts(alert_data: Dict, channels: List[str]):
    """알림 채널별로 알림 발송"""
    for channel in channels:
        if channel == 'webhook':
            # Webhook으로 알림 발송
            if NOTIFICATION_URL:
                try:
                    response = requests.post(
                        NOTIFICATION_URL,
                        json=alert_data,
                        timeout=5
                    )
                    if response.status_code >= 400:
                        logger.error(f"Webhook 알림 발송 실패: HTTP {response.status_code}")
                    else:
                        logger.info(f"Webhook 알림 발송 성공")
                except Exception as e:
                    logger.error(f"Webhook 알림 발송 오류: {e}")
            else:
                logger.warning("NOTIFICATION_URL이 설정되지 않아 webhook 알림을 건너뜁니다.")
        
        elif channel == 'slack':
            # Slack으로 알림 발송
            slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
            if slack_webhook:
                try:
                    # Slack 메시지 포맷 구성
                    message = {
                        "blocks": [
                            {
                                "type": "header",
                                "text": {
                                    "type": "plain_text",
                                    "text": f"⚠️ K6 테스트 알림: {alert_data['alert_type']}"
                                }
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": alert_data.get('message', '테스트 알림')
                                }
                            }
                        ]
                    }
                    
                    # 알림 유형에 따라 메시지 내용 추가
                    if alert_data['alert_type'] == 'THRESHOLD_EXCEEDED':
                        alerts_text = "\n".join([
                            f"• *{a['metric']}*: {a['value']:.4f} (임계값: {a['threshold']})"
                            for a in alert_data.get('alerts', [])
                        ])
                        
                        message["blocks"].append({
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*초과된 메트릭:*\n{alerts_text}"
                            }
                        })
                        
                        # Grafana 링크가 있으면 추가
                        if alert_data.get('grafana_link'):
                            message["blocks"].append({
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"<{alert_data['grafana_link']}|Grafana에서 결과 보기>"
                                }
                            })
                    
                    elif alert_data['alert_type'] == 'TEST_ERROR':
                        message["blocks"].append({
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*오류 메시지:*\n```{alert_data.get('error', '알 수 없는 오류')}```"
                            }
                        })
                    
                    response = requests.post(
                        slack_webhook,
                        json=message,
                        timeout=5
                    )
                    if response.status_code >= 400:
                        logger.error(f"Slack 알림 발송 실패: HTTP {response.status_code}")
                    else:
                        logger.info(f"Slack 알림 발송 성공")
                except Exception as e:
                    logger.error(f"Slack 알림 발송 오류: {e}")
            else:
                logger.warning("SLACK_WEBHOOK_URL이 설정되지 않아 Slack 알림을 건너뜁니다.")

# URL 검증 및 분석 도구 추가
@mcp.tool()
async def validate_url(
    url: str,
    check_methods: List[str] = None,
    headers: Dict = None
) -> Dict:
    """
    URL 유효성 검증 및 기본 분석
    
    - url: 검증할 URL
    - check_methods: 테스트할 HTTP 메서드 목록 (기본값: ["GET"])
    - headers: 요청 헤더 (선택 사항)
    
    이 기능은 테스트 전에 URL이 유효한지 확인하고, 기본적인 응답 시간 및
    가용성 정보를 제공합니다. 부하 테스트 전 사전 검증용으로 사용합니다.
    """
    if check_methods is None:
        check_methods = ["GET"]
    
    if headers is None:
        headers = {}
    
    results = {}
    
    for method in check_methods:
        try:
            logger.info(f"{method} 요청으로 URL 검증 중: {url}")
            
            # HTTP 메서드별 요청 수행
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, headers=headers, timeout=10)
            elif method == "PUT":
                response = requests.put(url, headers=headers, timeout=10)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                results[method] = {"error": f"지원하지 않는 HTTP 메서드: {method}"}
                continue
            
            # 응답 분석
            results[method] = {
                "status_code": response.status_code,
                "response_time_ms": response.elapsed.total_seconds() * 1000,
                "content_type": response.headers.get("Content-Type"),
                "content_length": len(response.content),
                "is_success": 200 <= response.status_code < 300
            }
            
        except requests.Timeout:
            results[method] = {"error": "요청 시간 초과"}
        except requests.ConnectionError:
            results[method] = {"error": "연결 오류 (서버에 연결할 수 없음)"}
        except Exception as e:
            results[method] = {"error": str(e)}
    
    # 종합 결과
    all_success = all(
        result.get("is_success", False) 
        for result in results.values() 
        if "is_success" in result
    )
    
    return {
        "url": url,
        "is_valid": all_success,
        "methods_tested": check_methods,
        "results": results
    }

# HTTP 메서드별 간편 테스트 함수 추가
@mcp.tool()
async def run_http_method_test(
    url: str,
    methods: List[str] = None,
    vus: int = 10,
    duration: str = "30s",
    payload: Optional[Dict] = None
) -> Dict:
    """
    HTTP 메서드별 성능 비교 테스트
    
    - url: 테스트할 URL
    - methods: 테스트할 HTTP 메서드 목록 (기본값: ["GET", "POST"])
    - vus: 가상 사용자 수
    - duration: 각 메서드별 테스트 지속 시간
    - payload: POST/PUT 요청에 사용할 데이터 (선택 사항)
    
    이 도구는 동일한 URL에 대해 여러 HTTP 메서드의 성능을 비교합니다.
    각 메서드별로 별도의 테스트를 실행하고 결과를 비교합니다.
    """
    if methods is None:
        methods = ["GET", "POST"]
    
    # URL 유효성 먼저 검증
    validation = await validate_url(url, methods)
    if not validation["is_valid"]:
        return {
            "error": "URL 검증 실패",
            "validation_results": validation
        }
    
    # 각 메서드별로 테스트 실행
    results = {}
    test_ids = {}
    
    for method in methods:
        logger.info(f"{method} 메서드 테스트 시작: {url}")
        
        test_result = await run_load_test(
            endpoint=url,
            vus=vus,
            duration=duration,
            method=method,
            payload=payload if method in ["POST", "PUT"] else None
        )
        
        test_ids[method] = test_result.get("test_id")
        results[method] = test_result
    
    # 결과 비교 분석
    comparison = await compare_results(
        test_id=test_ids[methods[0]],
        compare_with=[test_ids[m] for m in methods[1:]]
    )
    
    return {
        "url": url,
        "methods_tested": methods,
        "test_ids": test_ids,
        "comparison": comparison
    }

# 사용자 정의 k6 스크립트 실행 기능 추가
@mcp.tool()
async def run_custom_script(
    script_content: str,
    script_vars: Dict = None,
    script_name: str = None
) -> Dict:
    """
    사용자 정의 k6 스크립트 실행
    
    - script_content: 실행할 k6 스크립트 JavaScript 코드
    - script_vars: 스크립트에 전달할 변수 (선택 사항)
    - script_name: 스크립트 파일명 (지정하지 않으면 자동 생성)
    
    이 도구는 미리 정의된 템플릿 대신 사용자가 제공한 k6 스크립트를
    직접 실행합니다. 복잡한 테스트 시나리오나 사용자 정의 기능이 필요한
    경우 유용합니다.
    
    예시:
    ```javascript
    import http from 'k6/http';
    import { check, sleep } from 'k6';
    
    export const options = {
        vus: 10,
        duration: '30s'
    };
    
    export default function() {
        const res = http.get('https://test.k6.io');
        check(res, { 'status is 200': (r) => r.status === 200 });
        sleep(1);
    }
    ```
    """
    test_id = str(uuid.uuid4())
    
    if script_name is None:
        script_name = f"custom_script_{test_id[:8]}"
    
    # 스크립트 변수 처리
    if script_vars:
        # 변수 선언 코드 생성
        vars_code = "\n".join([f"const {k} = {json.dumps(v)};" for k, v in script_vars.items()])
        
        # 스크립트 시작 부분에 변수 선언 추가
        import_end = script_content.find("export")
        if import_end == -1:
            # export가 없으면 스크립트 맨 앞에 추가
            script_content = vars_code + "\n\n" + script_content
        else:
            # import와 export 사이에 변수 선언 추가
            script_content = script_content[:import_end] + "\n" + vars_code + "\n\n" + script_content[import_end:]
    
    # 스크립트 파일 저장
    script_path = f"/tmp/{script_name}.js"
    with open(script_path, "w") as f:
        f.write(script_content)
    
    try:
        logger.info(f"사용자 정의 스크립트 실행: {script_name}")
        
        # 스크립트 실행
        result = subprocess.run(
            ["k6", "run", script_path],
            check=True,
            capture_output=True,
            text=True
        )
        
        # 결과 파싱
        output = result.stdout
        
        # 결과에서 주요 메트릭 추출
        import re
        
        metrics = {}
        patterns = {
            "http_reqs": r"http_reqs\s*:\s*(\d+)",
            "http_req_duration_avg": r"http_req_duration\s*\{.*avg=([\d\.]+)ms",
            "http_req_duration_p95": r"http_req_duration\s*\{.*p\(95\)=([\d\.]+)ms",
            "iterations": r"iterations\s*:\s*(\d+)",
            "vus": r"vus\s*:\s*(\d+)",
            "data_received": r"data_received\s*:\s*([\d\.]+\s*\w+)",
            "data_sent": r"data_sent\s*:\s*([\d\.]+\s*\w+)"
        }
        
        for metric, pattern in patterns.items():
            match = re.search(pattern, output)
            if match:
                metrics[metric] = match.group(1)
        
        return {
            "test_id": test_id,
            "status": "completed",
            "script_name": script_name,
            "output_summary": output.split("running", 1)[1] if "running" in output else output,
            "metrics": metrics
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"스크립트 실행 실패: {e}")
        return {
            "test_id": test_id,
            "status": "failed",
            "script_name": script_name,
            "error": e.stderr
        }
    finally:
        # 스크립트 파일 삭제
        os.remove(script_path)

if __name__ == "__main__":
    print(f"K6 MCP 서버 시작 - 포트: {os.getenv('MCP_PORT', '8000')}")
    mcp.run(transport="sse")
