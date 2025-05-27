from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import subprocess
import json
import os
import uvicorn
import random
import time
import uuid
import logging
import sys

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('mcp_server.log', encoding='utf-8', mode='w')  # mode='w'로 변경하여 로그 파일 초기화
    ]
)

# 루트 로거 설정
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

# MCP 서버 로거 설정
logger = logging.getLogger('mcp_server')
logger.setLevel(logging.DEBUG)

# 로그 핸들러 추가
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# 파일 핸들러 추가
file_handler = logging.FileHandler('mcp_server.log', encoding='utf-8', mode='w')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

logger.info("="*50)
logger.info("MCP 서버 시작")
logger.info("="*50)

logger.info("FastAPI application initialization in progress...")
app = FastAPI()

# 시뮬레이션에 사용할 대시보드 데이터 (grafana_server.py에서 이동)
logger.info("Loading Grafana dashboard simulation data...")
grafana_dashboards = ["cpu-usage-dashboard", "memory-usage-dashboard", "pod-count-dashboard"]
grafana_datasources = ["Prometheus", "Loki", "Tempo"]

# 시뮬레이션에 사용할 ArgoCD 애플리케이션 데이터 (argocd_server.py에서 이동)
logger.info("Loading ArgoCD application simulation data...")
argocd_applications = [
    {"name": "user-service", "status": "Healthy"},
    {"name": "restaurant-service", "status": "Healthy"},
    {"name": "order-service", "status": "Healthy"},
    {"name": "payment-service", "status": "Healthy"},
    {"name": "delivery-service", "status": "Healthy"},
    {"name": "notification-service", "status": "Healthy"}
]

# 시뮬레이션에 사용할 GitHub PR 데이터 (github_server.py에서 이동)
logger.info("Loading GitHub PR simulation data...")
github_prs_data = [
    {
        "id": 101,
        "title": "사용자 인증 기능 개선",
        "author": "developer1",
        "branch": "feature/auth-improvement",
        "status": "open",
        "created_at": "2023-05-10T09:30:00Z",
        "updated_at": "2023-05-10T14:20:00Z",
        "comments": 5,
        "approved": False
    },
    {
        "id": 102,
        "title": "주문 서비스 성능 최적화",
        "author": "developer2",
        "branch": "perf/order-service",
        "status": "open",
        "created_at": "2023-05-11T10:15:00Z",
        "updated_at": "2023-05-11T16:45:00Z",
        "comments": 8,
        "approved": False
    },
    {
        "id": 103,
        "title": "레스토랑 검색 API 추가",
        "author": "developer3",
        "branch": "feature/restaurant-search",
        "status": "open",
        "created_at": "2023-05-12T08:20:00Z",
        "updated_at": "2023-05-12T13:10:00Z",
        "comments": 3,
        "approved": False
    }
]

# k6 테스트 결과 저장을 위한 딕셔너리 (k6_server.py에서 이동)
logger.info("Initializing test result storage...")
test_results = {}

class Command(BaseModel):
    command: str
    args: List[str] = []

# k6 성능 테스트 실행을 위한 요청 모델
class K6TestRequest(BaseModel):
    service_name: str
    virtual_users: int = 10
    duration: str = "30s"

# k6 테스트 결과 비교를 위한 요청 모델
class K6CompareRequest(BaseModel):
    test_id1: str
    test_id2: str

# Get Kubernetes configuration from environment
KUBERNETES_SERVICE_HOST = os.getenv("KUBERNETES_SERVICE_HOST", "192.168.45.100")
KUBERNETES_SERVICE_PORT = os.getenv("KUBERNETES_SERVICE_PORT", "6443")
KUBECONFIG = os.path.join(os.path.expanduser("~"), ".kube", "config")

def check_kubectl_config():
    """Check if kubectl is properly configured"""
    logger.info("Checking kubectl configuration...")
    try:
        # Check if kubeconfig exists
        if not os.path.exists(KUBECONFIG):
            logger.error(f"Error: kubeconfig not found at {KUBECONFIG}")
            return False
            
        # Check if kubectl is available
        result = subprocess.run(
            ["which", "kubectl"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logger.error("Error: kubectl is not installed")
            return False
            
        # Check if kubectl can connect to cluster
        result = subprocess.run(
            ["kubectl", "config", "view", "--minify"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Error checking kubectl config: {result.stderr}")
            return False
            
        # Try to get cluster info
        result = subprocess.run(
            ["kubectl", "cluster-info"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Error connecting to cluster: {result.stderr}")
            # Try to fix the server address
            subprocess.run(
                ["kubectl", "config", "set-cluster", "kubernetes", f"--server=https://{KUBERNETES_SERVICE_HOST}:{KUBERNETES_SERVICE_PORT}"],
                capture_output=True,
                text=True
            )
            return False
            
        logger.info("kubectl configuration is valid")
        return True
        
    except Exception as e:
        logger.error(f"Error checking kubectl config: {str(e)}")
        return False

def start_kubectl_proxy():
    """Start kubectl proxy in background"""
    logger.info("Starting kubectl proxy...")
    try:
        # First check kubectl configuration
        if not check_kubectl_config():
            return False
            
        # Kill any existing kubectl proxy process
        subprocess.run(["pkill", "-f", "kubectl proxy"], capture_output=True)
        time.sleep(1)  # Wait for process to be killed
        
        # Start new kubectl proxy with timeout
        proxy_process = subprocess.Popen(
            ["kubectl", "proxy", "--port=8002", "--address=0.0.0.0", "--accept-hosts=.*", "--accept-paths=.*"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for proxy to start with timeout
        start_time = time.time()
        while time.time() - start_time < 5:  # 5 second timeout
            try:
                result = subprocess.run(
                    ["curl", "-s", "http://localhost:8002/version"],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                if result.returncode == 0:
                    logger.info("kubectl proxy started successfully")
                    return True
            except subprocess.TimeoutExpired:
                pass
            time.sleep(0.5)
        
        # If we get here, proxy didn't start in time
        logger.error("Timeout waiting for kubectl proxy to start")
        proxy_process.terminate()
        return False
            
    except Exception as e:
        logger.error(f"Error starting kubectl proxy: {str(e)}")
        return False

@app.post("/execute")
async def execute_command(command: Command):
    logger.info(f"Executing command: {command.command} with args: {command.args}")
    try:
        # Execute the command
        result = subprocess.run(
            [command.command] + command.args,
            capture_output=True,
            text=True
        )
        logger.info(f"Command execution completed. Return code: {result.returncode}")
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except Exception as e:
        logger.error(f"Error executing command: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/services")
async def get_services():
    logger.info("Fetching list of available services...")
    # Get list of available services
    services = {
        "k6": {
            "description": "Load testing service",
            "endpoints": ["/k6/start", "/k6/stop", "/k6/status"]
        },
        "github": {
            "description": "GitHub integration service",
            "endpoints": ["/github/webhook", "/github/status"]
        },
        "grafana": {
            "description": "Monitoring service",
            "endpoints": ["/grafana/dashboards", "/grafana/alerts"]
        },
        "argocd": {
            "description": "GitOps service",
            "endpoints": ["/argocd/applications", "/argocd/sync"]
        }
    }
    logger.info(f"Total {len(services)} services found")
    return services

@app.get("/status")
async def get_status():
    logger.info("Checking status of all services...")
    # Get status of all services
    status = {}
    for service in ["k6", "github", "grafana", "argocd"]:
        try:
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True
            )
            status[service] = service in result.stdout
            logger.info(f"Service {service} status: {status[service]}")
        except Exception as e:
            logger.error(f"Error checking service status: {str(e)}")
            status[service] = False
    return status

# Kubernetes API endpoints
@app.post("/k8s/list_nodes")
async def list_nodes():
    logger.info("="*50)
    logger.info("[Kubernetes] 노드 목록 조회 시작")
    logger.info("="*50)
    try:
        logger.info("[Kubernetes] kubectl 설정 확인 중...")
        result = subprocess.run(["kubectl", "config", "view"], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"[Kubernetes] kubectl 설정 오류: {result.stderr}")
            return {"success": False, "error": "kubectl 설정이 올바르지 않습니다."}
        logger.info("[Kubernetes] kubectl 설정 정상")

        logger.info("[Kubernetes] 노드 정보 조회 중...")
        result = subprocess.run(["kubectl", "get", "nodes", "-o", "json"], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"[Kubernetes] 노드 조회 오류: {result.stderr}")
            return {"success": False, "error": "노드 정보를 가져오는데 실패했습니다."}
        
        logger.info("[Kubernetes] 노드 정보 파싱 중...")
        nodes_data = json.loads(result.stdout)
        logger.info(f"[Kubernetes] 원본 노드 데이터: {json.dumps(nodes_data, indent=2, ensure_ascii=False)}")
        
        nodes = []
        for node in nodes_data.get("items", []):
            logger.info(f"[Kubernetes] 노드 처리 중: {node['metadata']['name']}")
            
            # 노드 상태 확인
            status = "Ready" if any(condition["type"] == "Ready" and condition["status"] == "True" 
                                  for condition in node["status"]["conditions"]) else "NotReady"
            
            # CPU 및 메모리 정보 추출
            cpu_capacity = node["status"]["capacity"]["cpu"]
            memory_capacity = node["status"]["capacity"]["memory"]
            
            # 노드 정보 구성
            node_info = {
                "name": node["metadata"]["name"],
                "status": status,
                "cpu": cpu_capacity,
                "memory": memory_capacity,
                "age": node["metadata"]["creationTimestamp"],
                "labels": node["metadata"].get("labels", {}),
                "taints": node["spec"].get("taints", []),
                "addresses": node["status"].get("addresses", []),
                "conditions": [
                    {
                        "type": condition["type"],
                        "status": condition["status"],
                        "reason": condition.get("reason", ""),
                        "message": condition.get("message", "")
                    }
                    for condition in node["status"]["conditions"]
                ]
            }
            nodes.append(node_info)
            logger.info(f"[Kubernetes] 노드 정보 추가 완료: {json.dumps(node_info, indent=2, ensure_ascii=False)}")
        
        # 노드 상태 통계 계산
        total_nodes = len(nodes)
        ready_nodes = sum(1 for n in nodes if n["status"] == "Ready")
        
        logger.info(f"[Kubernetes] 총 {total_nodes}개 노드 처리 완료")
        logger.info(f"[Kubernetes] 노드 상태 통계:")
        logger.info(f"  - Ready 상태: {ready_nodes}개")
        logger.info(f"  - NotReady 상태: {total_nodes - ready_nodes}개")
        
        # 각 노드의 상세 정보 로깅
        for node in nodes:
            logger.info(f"\n[Kubernetes] 노드 상세 정보: {node['name']}")
            logger.info(f"  - 상태: {node['status']}")
            logger.info(f"  - CPU: {node['cpu']}")
            logger.info(f"  - 메모리: {node['memory']}")
            logger.info(f"  - 생성 시간: {node['age']}")
            logger.info(f"  - 라벨: {json.dumps(node['labels'], ensure_ascii=False)}")
            logger.info(f"  - 테인트: {json.dumps(node['taints'], ensure_ascii=False)}")
            logger.info("  - 주소:")
            for addr in node['addresses']:
                logger.info(f"    - {addr['type']}: {addr['address']}")
            logger.info("  - 상태 조건:")
            for condition in node['conditions']:
                logger.info(f"    - {condition['type']}: {condition['status']}")
                if condition['reason']:
                    logger.info(f"      이유: {condition['reason']}")
                if condition['message']:
                    logger.info(f"      메시지: {condition['message']}")
        
        return {
            "success": True,
            "data": {
                "nodes": nodes,
                "total_nodes": total_nodes,
                "ready_nodes": ready_nodes,
                "not_ready_nodes": total_nodes - ready_nodes,
                "status_summary": {
                    "total": total_nodes,
                    "ready": ready_nodes,
                    "not_ready": total_nodes - ready_nodes
                }
            }
        }
    except Exception as e:
        logger.error(f"[Kubernetes] 예외 발생: {str(e)}")
        return {"success": False, "error": str(e)}

@app.post("/k8s/list_pods")
async def list_pods():
    logger.info("="*50)
    logger.info("[Kubernetes] 파드 목록 조회 시작")
    logger.info("="*50)
    try:
        logger.info("[Kubernetes] kubectl 설정 확인 중...")
        result = subprocess.run(["kubectl", "config", "view"], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"[Kubernetes] kubectl 설정 오류: {result.stderr}")
            return {"success": False, "error": "kubectl 설정이 올바르지 않습니다."}
        logger.info("[Kubernetes] kubectl 설정 정상")

        logger.info("[Kubernetes] 파드 정보 조회 중...")
        result = subprocess.run(
            ["kubectl", "get", "pods", "-A", "-o", "json"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logger.error(f"[Kubernetes] 파드 조회 오류: {result.stderr}")
            return {"success": False, "error": "파드 정보를 가져오는데 실패했습니다."}
        
        logger.info("[Kubernetes] 파드 정보 파싱 중...")
        pods_data = json.loads(result.stdout)
        logger.info(f"[Kubernetes] 원본 파드 데이터: {json.dumps(pods_data, indent=2, ensure_ascii=False)}")
        
        pods = []
        for pod in pods_data.get("items", []):
            logger.info(f"[Kubernetes] 파드 처리 중: {pod['metadata']['name']}")
            
            # 파드 상태 확인
            status = pod["status"]["phase"]
            ready_containers = "0/0"
            if "containerStatuses" in pod["status"]:
                ready_count = sum(1 for container in pod["status"]["containerStatuses"] if container.get("ready", False))
                total_count = len(pod["status"]["containerStatuses"])
                ready_containers = f"{ready_count}/{total_count}"
            
            # 파드 IP 확인
            pod_ip = pod["status"].get("podIP", "N/A")
            
            # 파드 생성 시간 계산
            creation_timestamp = pod["metadata"]["creationTimestamp"]
            age = "N/A"
            try:
                creation_time = time.strptime(creation_timestamp, "%Y-%m-%dT%H:%M:%SZ")
                current_time = time.gmtime()
                age_seconds = time.mktime(current_time) - time.mktime(creation_time)
                if age_seconds < 60:
                    age = f"{int(age_seconds)}s"
                elif age_seconds < 3600:
                    age = f"{int(age_seconds/60)}m"
                elif age_seconds < 86400:
                    age = f"{int(age_seconds/3600)}h"
                else:
                    age = f"{int(age_seconds/86400)}d"
            except Exception as e:
                logger.error(f"[Kubernetes] 파드 생성 시간 계산 오류: {str(e)}")
            
            # 파드 정보 구성
            pod_info = {
                "name": pod["metadata"]["name"],
                "namespace": pod["metadata"]["namespace"],
                "status": status,
                "ready_containers": ready_containers,
                "node": pod["spec"].get("nodeName", "N/A"),
                "pod_ip": pod_ip,
                "age": age,
                "restarts": sum(container.get("restartCount", 0) for container in pod["status"].get("containerStatuses", [])),
                "labels": pod["metadata"].get("labels", {}),
                "creation_timestamp": creation_timestamp
            }
            pods.append(pod_info)
            logger.info(f"[Kubernetes] 파드 정보 추가 완료: {json.dumps(pod_info, indent=2, ensure_ascii=False)}")
        
        # 파드 상태 통계 계산
        status_stats = {}
        for pod in pods:
            status = pod["status"]
            status_stats[status] = status_stats.get(status, 0) + 1
        
        logger.info(f"[Kubernetes] 총 {len(pods)}개 파드 처리 완료")
        logger.info(f"[Kubernetes] 파드 상태 통계:")
        for status, count in status_stats.items():
            logger.info(f"  - {status}: {count}개")
        
        return {
            "success": True,
            "data": {
                "pods": pods,
                "total_pods": len(pods),
                "status_stats": status_stats,
                "running_pods": sum(1 for p in pods if p["status"] == "Running"),
                "pending_pods": sum(1 for p in pods if p["status"] == "Pending"),
                "failed_pods": sum(1 for p in pods if p["status"] == "Failed")
            }
        }
    except Exception as e:
        logger.error(f"[Kubernetes] 예외 발생: {str(e)}")
        return {"success": False, "error": str(e)}

@app.post("/k8s/list_services")
async def list_services():
    logger.info("="*50)
    logger.info("[Kubernetes] 서비스 목록 조회 시작")
    logger.info("="*50)
    try:
        logger.info("[Kubernetes] kubectl 설정 확인 중...")
        result = subprocess.run(["kubectl", "config", "view"], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"[Kubernetes] kubectl 설정 오류: {result.stderr}")
            return {"success": False, "error": "kubectl 설정이 올바르지 않습니다."}
        logger.info("[Kubernetes] kubectl 설정 정상")

        logger.info("[Kubernetes] 서비스 정보 조회 중...")
        result = subprocess.run(["kubectl", "get", "services", "-A", "-o", "json"], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"[Kubernetes] 서비스 조회 오류: {result.stderr}")
            return {"success": False, "error": "서비스 정보를 가져오는데 실패했습니다."}
        
        logger.info("[Kubernetes] 서비스 정보 파싱 중...")
        services_data = json.loads(result.stdout)
        logger.info(f"[Kubernetes] 원본 서비스 데이터: {json.dumps(services_data, indent=2, ensure_ascii=False)}")
        
        services = []
        for service in services_data.get("items", []):
            logger.info(f"[Kubernetes] 서비스 처리 중: {service['metadata']['name']}")
            service_info = {
                "name": service["metadata"]["name"],
                "namespace": service["metadata"]["namespace"],
                "type": service["spec"]["type"],
                "cluster_ip": service["spec"]["clusterIP"],
                "external_ip": service["status"].get("loadBalancer", {}).get("ingress", [{}])[0].get("ip", "<pending>"),
                "ports": [f"{p.get('port', '')}:{p.get('targetPort', '')}/{p.get('protocol', 'TCP')}" 
                         for p in service["spec"].get("ports", [])],
                "age": service["metadata"]["creationTimestamp"]
            }
            services.append(service_info)
            logger.info(f"[Kubernetes] 서비스 정보 추가 완료: {json.dumps(service_info, indent=2, ensure_ascii=False)}")
        
        logger.info(f"[Kubernetes] 총 {len(services)}개 서비스 처리 완료")
        logger.info(f"[Kubernetes] 서비스 유형별 통계:")
        service_types = {}
        for service in services:
            service_type = service["type"]
            service_types[service_type] = service_types.get(service_type, 0) + 1
        for service_type, count in service_types.items():
            logger.info(f"  - {service_type}: {count}개")
        
        return {
            "success": True,
            "data": {
                "services": services,
                "total_services": len(services),
                "load_balancers": sum(1 for s in services if s["type"] == "LoadBalancer")
            }
        }
    except Exception as e:
        logger.error(f"[Kubernetes] 예외 발생: {str(e)}")
        return {"success": False, "error": str(e)}

@app.post("/k8s/list_namespaces")
async def list_namespaces():
    logger.info("Fetching Kubernetes namespace information...")
    try:
        result = subprocess.run(
            ["kubectl", "get", "namespaces", "-o", "json"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logger.error(f"Error fetching namespace information: {result.stderr}")
            raise HTTPException(status_code=500, detail=result.stderr)
        
        namespaces_data = json.loads(result.stdout)
        namespaces = []
        for namespace in namespaces_data["items"]:
            namespace_info = {
                "name": namespace["metadata"]["name"],
                "status": namespace["status"]["phase"],
                "age": "N/A"  # kubectl get namespaces에서 가져올 수 있음
            }
            namespaces.append(namespace_info)
            logger.info(f"Namespace found: {namespace_info['name']} status: {namespace_info['status']}")
        
        return {"success": True, "data": {"cluster_summary": {"total_pods": len(namespaces), "node_distribution": {namespace['name']: 1 for namespace in namespaces}, "status_distribution": {namespace['status']: 1 for namespace in namespaces}}, "namespaces": namespaces}}
    except Exception as e:
        logger.error(f"Error listing namespaces: {str(e)}")
        return {"success": False, "error": str(e)}

@app.post("/k8s/list_ingresses")
async def list_ingresses():
    logger.info("Fetching Kubernetes ingress information...")
    try:
        result = subprocess.run(
            ["kubectl", "get", "ingress", "-A", "-o", "json"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logger.error(f"Error fetching ingress information: {result.stderr}")
            raise HTTPException(status_code=500, detail=result.stderr)

        ingress_data = json.loads(result.stdout)
        ingresses = []
        for item in ingress_data.get("items", []):
            ingress_info = {
                "name": item["metadata"]["name"],
                "namespace": item["metadata"]["namespace"],
                "hosts": [rule.get("host") for rule in item.get("spec", {}).get("rules", []) if rule.get("host")],
                "address": ", ".join([addr.get("ip") or addr.get("hostname") for lb in item.get("status", {}).get("loadBalancer", {}).get("ingress", []) if addr.get("ip") or addr.get("hostname") for addr in [lb]]) if item.get("status", {}).get("loadBalancer", {}).get("ingress") else "<pending>",
                "age": "N/A"
            }
            ingresses.append(ingress_info)
            logger.info(f"Ingress found: {ingress_info['name']} namespace: {ingress_info['namespace']}")
        
        return {"success": True, "data": {"cluster_summary": {"total_pods": len(ingresses), "node_distribution": {ingress['name']: 1 for ingress in ingresses}, "status_distribution": {ingress['name']: 1 for ingress in ingresses}}, "ingresses": ingresses}}
    except Exception as e:
        logger.error(f"Error listing ingresses: {str(e)}")
        return {"success": False, "error": str(e)}

# Grafana API endpoints (grafana_server.py에서 이동 및 FastAPI endpoint addition)
@app.post("/search_grafana_dashboards")
def search_grafana_dashboards() -> Dict[str, Any]:
    logger.info("Searching Grafana dashboards...")
    return {
        "success": True,
        "data": {
            "dashboards": grafana_dashboards
        }
    }

@app.post("/get_dashboard_metrics")
def get_dashboard_metrics(dashboard_name: str) -> Dict[str, Any]:
    logger.info(f"Fetching dashboard metrics: {dashboard_name}")
    
    if dashboard_name not in grafana_dashboards and dashboard_name.lower() not in [d.lower() for d in grafana_dashboards]:
        logger.error(f"Dashboard not found: {dashboard_name}")
        return {"error": f"Dashboard '{dashboard_name}' not found"}
    
    metrics = {}
    
    if dashboard_name.lower() == "cpu-usage-dashboard" or dashboard_name.lower() == "cpu-usage":
        cpu_usage = random.randint(20, 100)
        metrics = {
            "title": "CPU Usage Dashboard",
            "metrics": {
                "current_usage": f"{cpu_usage}%",
                "average_usage_1h": f"{random.randint(20, cpu_usage)}%",
                "peak_usage_24h": f"{random.randint(cpu_usage, 100)}%",
                "threshold": "80%",
                "status": "Normal" if cpu_usage < 80 else "Warning"
            },
            "services": {
                "user-service": f"{random.randint(20, 60)}%",
                "restaurant-service": f"{random.randint(20, 60)}%",
                "order-service": f"{random.randint(20, 60)}%"
            }
        }
        logger.info(f"CPU usage metrics generated: {metrics}")
    elif dashboard_name.lower() == "memory-usage-dashboard" or dashboard_name.lower() == "memory-usage":
        memory_usage = random.randint(20, 100)
        metrics = {
            "title": "Memory Usage Dashboard",
            "metrics": {
                "current_usage": f"{memory_usage}%",
                "average_usage_1h": f"{random.randint(20, memory_usage)}%",
                "peak_usage_24h": f"{random.randint(memory_usage, 100)}%",
                "threshold": "85%",
                "status": "Normal" if memory_usage < 85 else "Warning"
            },
            "services": {
                "user-service": f"{random.randint(20, 70)}%",
                "restaurant-service": f"{random.randint(20, 70)}%",
                "order-service": f"{random.randint(20, 70)}%"
            }
        }
        logger.info(f"Memory usage metrics generated: {metrics}")
    elif dashboard_name.lower() == "pod-count-dashboard" or dashboard_name.lower() == "pod-count":
        pod_count = random.randint(15, 30)
        metrics = {
            "title": "Pod Count Dashboard",
            "metrics": {
                "total_pods": pod_count,
                "running_pods": random.randint(pod_count - 5, pod_count),
                "pending_pods": random.randint(0, 3),
                "failed_pods": random.randint(0, 2)
            },
            "services": {
                "user-service": random.randint(3, 8),
                "restaurant-service": random.randint(4, 10),
                "order-service": random.randint(5, 12)
            }
        }
        logger.info(f"Pod count metrics generated: {metrics}")
    
    return {
        "success": True,
        "data": {
            "dashboard_name": dashboard_name,
            "metrics": metrics
        }
    }

@app.post("/get_grafana_datasources")
def get_grafana_datasources() -> Dict[str, Any]:
    logger.info("Fetching Grafana data sources...")
    return {
        "success": True,
        "data": {
            "datasources": [
                {
                    "name": "Prometheus",
                    "type": "prometheus",
                    "url": "http://prometheus:9090",
                    "status": "Active"
                },
                {
                    "name": "Loki",
                    "type": "loki",
                    "url": "http://loki:3100",
                    "status": "Active"
                },
                {
                    "name": "Tempo",
                    "type": "tempo",
                    "url": "http://tempo:3200",
                    "status": "Active"
                }
            ]
        }
    }

# ArgoCD API endpoints (argocd_server.py에서 이동 및 FastAPI endpoint addition)
argocd_applications_data = [
    {"name": "user-service", "status": "Healthy"},
    {"name": "restaurant-service", "status": "Healthy"},
    {"name": "order-service", "status": "Healthy"},
    {"name": "payment-service", "status": "Healthy"},
    {"name": "delivery-service", "status": "Healthy"},
    {"name": "notification-service", "status": "Healthy"}
]

@app.post("/list_argocd_applications")
def list_argocd_applications() -> Dict[str, Any]:
    logger.info("="*50)
    logger.info("[ArgoCD] 애플리케이션 목록 조회 시작")
    logger.info("="*50)
    try:
        logger.info("[ArgoCD] 애플리케이션 목록 조회 중...")
        response_apps = []
        
        for app in argocd_applications_data:
            response_apps.append({
                "name": app["name"],
                "status": app["status"],
                "namespace": "default",
                "cluster": "in-cluster",
                "sync_status": "Synced" if app["status"] == "Healthy" else "OutOfSync"
            })
            logger.info(f"[ArgoCD] 애플리케이션 발견: {app['name']} 상태: {app['status']}")
        
        logger.info(f"[ArgoCD] 총 {len(response_apps)}개 애플리케이션 처리 완료")
        logger.info(f"[ArgoCD] 애플리케이션 상태 통계:")
        healthy_count = sum(1 for app in response_apps if app["status"] == "Healthy")
        logger.info(f"  - Healthy 상태: {healthy_count}개")
        logger.info(f"  - 기타 상태: {len(response_apps) - healthy_count}개")
        
        return {
            "success": True,
            "data": {
                "applications": response_apps
            }
        }
    except Exception as e:
        logger.error(f"[ArgoCD] 예외 발생: {str(e)}")
        return {"success": False, "error": str(e)}

@app.post("/deploy_application")
def deploy_application(app_name: str) -> Dict[str, Any]:
    logger.info(f"Deploying application: {app_name}")
    
    found_app = None
    
    for app in argocd_applications_data:
        if app["name"].lower() == app_name.lower():
            found_app = app
            break
    
    if not found_app:
        logger.error(f"Application not found: {app_name}")
        return {"error": f"Application '{app_name}' not found"}
    
    logger.info(f"{app_name} deployment started...")
    
    deploy_result = {
        "success": True,
        "message": f"Application {app_name} deployment started",
        "data": {
            "application": {
                "name": app_name,
                "previous_status": found_app["status"],
                "current_status": "Progressing",
                "deployment_started": True
            }
        }
    }
    
    logger.info(f"{app_name} deployment started")
    return deploy_result

@app.post("/check_deployment_status")
def check_deployment_status(app_name: str) -> Dict[str, Any]:
    logger.info(f"Checking deployment status: {app_name}")
    
    found_app = None
    
    for app in argocd_applications_data:
        if app["name"].lower() == app_name.lower():
            found_app = app
            break
    
    if not found_app:
        logger.error(f"Application not found: {app_name}")
        return {"error": f"Application '{app_name}' not found"}
    
    status_options = ["Progressing", "Healthy"]
    deployment_status = status_options[random.randint(0, len(status_options)-1)]
    
    if random.random() < 0.8:
        deployment_status = "Healthy"
    
    logger.info(f"{app_name} deployment status: {deployment_status}")
    
    return {
        "success": True,
        "data": {
            "application": {
                "name": app_name,
                "status": deployment_status,
                "health_status": deployment_status,
                "sync_status": "Synced" if deployment_status == "Healthy" else "Progressing",
                "message": f"Application {'deployed successfully' if deployment_status == 'Healthy' else 'still deploying'}"
            }
        }
    }

# GitHub API endpoints (github_server.py에서 이동 및 FastAPI endpoint addition)
@app.post("/list_github_prs")
def list_github_prs() -> Dict[str, Any]:
    logger.info("Fetching GitHub Pull Request list...")
    prs_info = []
    for pr in github_prs_data:
        if pr["approved"]:
            continue
        
        prs_info.append({
            "id": pr["id"],
            "title": pr["title"],
            "author": pr["author"],
            "branch": pr["branch"],
            "status": pr["status"],
            "created_at": pr["created_at"],
            "comments": pr["comments"]
        })
        logger.info(f"PR found: #{pr['id']} title: {pr['title']} author: {pr['author']}")
    
    return {
        "success": True,
        "data": {
            "pull_requests": prs_info
        }
    }

@app.post("/approve_github_pr")
def approve_github_pr(pr_id: int) -> Dict[str, Any]:
    logger.info(f"Approving GitHub PR: #{pr_id}")
    
    found_pr = None
    for pr in github_prs_data:
        if pr["id"] == pr_id:
            found_pr = pr
            break
    
    if not found_pr:
        logger.error(f"PR not found: #{pr_id}")
        return {"error": f"PR ID '{pr_id}' not found"}
    
    if found_pr["approved"]:
        logger.info(f"PR #{pr_id} is already approved")
        return {
            "success": False,
            "message": f"PR #{pr_id} is already approved"
        }
    
    found_pr["approved"] = True
    found_pr["status"] = "approved"
    found_pr["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    logger.info(f"PR #{pr_id} approval completed")
    
    return {
        "success": True,
        "message": f"PR #{pr_id} approved successfully",
        "data": {
            "pull_request": {
                "id": found_pr["id"],
                "title": found_pr["title"],
                "status": found_pr["status"],
                "approved_at": found_pr["updated_at"]
            }
        }
    }

# k6 API endpoints (k6_server.py에서 이동 및 FastAPI endpoint addition)
test_results_data = {}

@app.post("/run_k6_performance_test")
def run_k6_performance_test(request: K6TestRequest) -> Dict[str, Any]:
    logger.info(f"[성능 테스트] 서비스: {request.service_name}에 대한 성능 테스트를 시작합니다.")
    logger.info(f"[성능 테스트] 설정값 - 가상 사용자 수: {request.virtual_users}명, 테스트 시간: {request.duration}")
    
    if not request.service_name:
        logger.error("[성능 테스트] 오류: 서비스 이름이 입력되지 않았습니다.")
        return {"error": "서비스 이름은 필수 입력값입니다."}
    
    if request.virtual_users < 1:
        logger.error("[성능 테스트] 오류: 가상 사용자 수는 최소 1명 이상이어야 합니다.")
        return {"error": "가상 사용자 수는 1명 이상이어야 합니다."}
    
    if not request.duration.endswith(('s', 'm', 'h')):
        logger.error("[성능 테스트] 오류: 잘못된 시간 형식입니다.")
        return {"error": "시간은 's'(초), 'm'(분), 'h'(시간) 형식이어야 합니다. (예: '30s', '1m', '5m')"}
    
    test_id = str(uuid.uuid4())
    logger.info(f"[성능 테스트] 테스트 ID 생성: {test_id}")
    
    logger.info(f"[성능 테스트] {request.service_name} 서비스에 대한 성능 테스트를 시작합니다...")
    
    start_time = time.time()
    
    avg_response_time = random.uniform(50, 500)
    p95_response_time = avg_response_time * random.uniform(1.5, 2.5)
    requests_per_second = random.uniform(50, 2000)
    error_rate = random.uniform(0, 15)
    
    result = {
        "test_id": test_id,
        "service_name": request.service_name,
        "config": {
            "virtual_users": request.virtual_users,
            "duration": request.duration
        },
        "results": {
            "avg_response_time_ms": round(avg_response_time, 2),
            "p95_response_time_ms": round(p95_response_time, 2),
            "requests_per_second": round(requests_per_second, 2),
            "error_rate_percentage": round(error_rate, 2),
            "http_200": round(random.uniform(80, 100), 2),
            "http_4xx": round(random.uniform(0, 10), 2),
            "http_5xx": round(random.uniform(0, 10), 2)
        },
        "status": "Success" if error_rate < 5 else "Attention needed",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    }
    
    test_results_data[test_id] = result
    logger.info(f"[성능 테스트] {request.service_name} 서비스 테스트 완료")
    logger.info(f"[성능 테스트] 결과 요약:")
    logger.info(f"  - 평균 응답 시간: {result['results']['avg_response_time_ms']}ms")
    logger.info(f"  - 95% 응답 시간: {result['results']['p95_response_time_ms']}ms")
    logger.info(f"  - 초당 요청 수: {result['results']['requests_per_second']}")
    logger.info(f"  - 오류율: {result['results']['error_rate_percentage']}%")
    logger.info(f"  - HTTP 200 응답: {result['results']['http_200']}%")
    logger.info(f"  - HTTP 4xx 응답: {result['results']['http_4xx']}%")
    logger.info(f"  - HTTP 5xx 응답: {result['results']['http_5xx']}%")
    logger.info(f"  - 테스트 상태: {result['status']}")
    
    return {
        "success": True,
        "message": f"{request.service_name} 서비스의 성능 테스트가 완료되었습니다.",
        "data": {
            "test_id": test_id,
            "results": result
        }
    }

@app.post("/compare_k6_tests")
def compare_k6_tests(request: K6CompareRequest) -> Dict[str, Any]:
    logger.info(f"[테스트 비교] 테스트 비교를 시작합니다. - 테스트 1: {request.test_id1}, 테스트 2: {request.test_id2}")
    
    if request.test_id1 not in test_results_data:
        logger.error(f"[테스트 비교] 오류: 테스트 ID {request.test_id1}를 찾을 수 없습니다.")
        return {"error": f"테스트 ID '{request.test_id1}'를 찾을 수 없습니다."}
    
    if request.test_id2 not in test_results_data:
        logger.error(f"[테스트 비교] 오류: 테스트 ID {request.test_id2}를 찾을 수 없습니다.")
        return {"error": f"테스트 ID '{request.test_id2}'를 찾을 수 없습니다."}
    
    test1 = test_results_data[request.test_id1]
    test2 = test_results_data[request.test_id2]
    
    logger.info(f"[테스트 비교] 두 테스트 결과를 찾았습니다. 메트릭 비교를 시작합니다...")
    
    avg_response_time_diff = test2["results"]["avg_response_time_ms"] - test1["results"]["avg_response_time_ms"]
    avg_response_time_diff_percent = (avg_response_time_diff / test1["results"]["avg_response_time_ms"]) * 100
    
    p95_response_time_diff = test2["results"]["p95_response_time_ms"] - test1["results"]["p95_response_time_ms"]
    p95_response_time_diff_percent = (p95_response_time_diff / test1["results"]["p95_response_time_ms"]) * 100
    
    rps_diff = test2["results"]["requests_per_second"] - test1["results"]["requests_per_second"]
    rps_diff_percent = (rps_diff / test1["results"]["requests_per_second"]) * 100
    
    error_rate_diff = test2["results"]["error_rate_percentage"] - test1["results"]["error_rate_percentage"]
    
    performance_change = "향상" if avg_response_time_diff < 0 and rps_diff > 0 else "저하" if avg_response_time_diff > 0 and rps_diff < 0 else "혼합"
    
    comparison = {
        "test1": {
            "test_id": request.test_id1,
            "service_name": test1["service_name"],
            "config": test1["config"]
        },
        "test2": {
            "test_id": request.test_id2,
            "service_name": test2["service_name"],
            "config": test2["config"]
        },
        "comparison": {
            "avg_response_time_diff_ms": round(avg_response_time_diff, 2),
            "avg_response_time_diff_percent": round(avg_response_time_diff_percent, 2),
            "p95_response_time_diff_ms": round(p95_response_time_diff, 2),
            "p95_response_time_diff_percent": round(p95_response_time_diff_percent, 2),
            "requests_per_second_diff": round(rps_diff, 2),
            "requests_per_second_diff_percent": round(rps_diff_percent, 2),
            "error_rate_diff_percentage": round(error_rate_diff, 2)
        },
        "summary": {
            "performance_change": performance_change,
            "highlights": []
        }
    }
    
    if abs(avg_response_time_diff_percent) > 10:
        comparison["summary"]["highlights"].append(
            f"평균 응답 시간이 {abs(round(avg_response_time_diff_percent, 2))}% {'감소' if avg_response_time_diff < 0 else '증가'}했습니다."
        )
    
    if abs(rps_diff_percent) > 10:
        comparison["summary"]["highlights"].append(
            f"초당 요청 처리량이 {abs(round(rps_diff_percent, 2))}% {'증가' if rps_diff > 0 else '감소'}했습니다."
        )
    
    if abs(error_rate_diff) > 1:
        comparison["summary"]["highlights"].append(
            f"오류율이 {abs(round(error_rate_diff, 2))}% {'감소' if error_rate_diff < 0 else '증가'}했습니다."
        )
    
    logger.info(f"[테스트 비교] 비교 완료. 성능 변화: {performance_change}")
    logger.info(f"[테스트 비교] 주요 변경사항:")
    for highlight in comparison["summary"]["highlights"]:
        logger.info(f"  - {highlight}")
    
    return {
        "success": True,
        "message": f"{test1['service_name']} 서비스에 대한 두 테스트 결과를 비교했습니다.",
        "data": {
            "comparison": comparison
        }
    }

@app.get("/k8s/nodes")
async def get_nodes():
    """노드 정보를 조회하는 엔드포인트"""
    logger.info("="*50)
    logger.info("[Kubernetes] 노드 정보 조회 요청")
    logger.info("="*50)
    
    try:
        # kubectl 명령어 실행
        result = subprocess.run(
            ["kubectl", "get", "nodes", "-o", "json"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"[Kubernetes] 노드 조회 실패: {result.stderr}")
            return {
                "success": False,
                "error": "노드 정보를 가져오는데 실패했습니다.",
                "details": result.stderr
            }
        
        # JSON 파싱
        nodes_data = json.loads(result.stdout)
        nodes = []
        
        for node in nodes_data.get("items", []):
            # 노드 상태 확인
            status = "Ready" if any(
                condition["type"] == "Ready" and condition["status"] == "True"
                for condition in node["status"]["conditions"]
            ) else "NotReady"
            
            # 노드 정보 구성
            node_info = {
                "name": node["metadata"]["name"],
                "status": status,
                "cpu": node["status"]["capacity"]["cpu"],
                "memory": node["status"]["capacity"]["memory"],
                "age": node["metadata"]["creationTimestamp"],
                "labels": node["metadata"].get("labels", {}),
                "addresses": [
                    {
                        "type": addr["type"],
                        "address": addr["address"]
                    }
                    for addr in node["status"].get("addresses", [])
                ],
                "conditions": [
                    {
                        "type": condition["type"],
                        "status": condition["status"],
                        "reason": condition.get("reason", ""),
                        "message": condition.get("message", "")
                    }
                    for condition in node["status"]["conditions"]
                ]
            }
            nodes.append(node_info)
            
            # 로깅
            logger.info(f"\n[Kubernetes] 노드 정보: {node_info['name']}")
            logger.info(f"  - 상태: {node_info['status']}")
            logger.info(f"  - CPU: {node_info['cpu']}")
            logger.info(f"  - 메모리: {node_info['memory']}")
            logger.info(f"  - 생성 시간: {node_info['age']}")
            logger.info(f"  - 라벨: {json.dumps(node_info['labels'], ensure_ascii=False)}")
            logger.info("  - 주소:")
            for addr in node_info['addresses']:
                logger.info(f"    - {addr['type']}: {addr['address']}")
            logger.info("  - 상태 조건:")
            for condition in node_info['conditions']:
                logger.info(f"    - {condition['type']}: {condition['status']}")
                if condition['reason']:
                    logger.info(f"      이유: {condition['reason']}")
                if condition['message']:
                    logger.info(f"      메시지: {condition['message']}")
        
        # 상태 통계 계산
        total_nodes = len(nodes)
        ready_nodes = sum(1 for n in nodes if n["status"] == "Ready")
        
        logger.info(f"\n[Kubernetes] 노드 상태 요약:")
        logger.info(f"  - 총 노드 수: {total_nodes}")
        logger.info(f"  - Ready 상태: {ready_nodes}")
        logger.info(f"  - NotReady 상태: {total_nodes - ready_nodes}")
        
        return {
            "success": True,
            "data": {
                "nodes": nodes,
                "summary": {
                    "total": total_nodes,
                    "ready": ready_nodes,
                    "not_ready": total_nodes - ready_nodes
                }
            }
        }
        
    except Exception as e:
        logger.error(f"[Kubernetes] 예외 발생: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    logger.info("="*50)
    logger.info("MCP 서버 시작")
    logger.info("="*50)
    logger.info("FastAPI 서버 초기화 중...")
    logger.info(f"서버 주소: http://0.0.0.0:8001")
    logger.info("사용 가능한 API 엔드포인트:")
    logger.info("- /execute: 명령어 실행")
    logger.info("- /services: 서비스 목록 조회")
    logger.info("- /status: 서비스 상태 조회")
    logger.info("- /k8s/*: Kubernetes 관련 API")
    logger.info("- /search_grafana_dashboards: Grafana 대시보드 검색")
    logger.info("- /get_dashboard_metrics: 대시보드 메트릭 조회")
    logger.info("- /get_grafana_datasources: Grafana 데이터소스 조회")
    logger.info("- /list_argocd_applications: ArgoCD 애플리케이션 목록")
    logger.info("- /deploy_application: 애플리케이션 배포")
    logger.info("- /list_github_prs: GitHub PR 목록")
    logger.info("- /approve_github_pr: GitHub PR 승인")
    logger.info("- /run_k6_performance_test: k6 성능 테스트 실행")
    logger.info("- /compare_k6_tests: k6 테스트 결과 비교")
    logger.info("- /k8s/nodes: 노드 정보 조회")
    logger.info("="*50)
    
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="debug") 