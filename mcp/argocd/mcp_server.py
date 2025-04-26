from mcp.server.fastmcp import FastMCP
import os
import requests
import json
import logging
from typing import Dict, List, Optional, Any, Union
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()
ARGOCD_SERVER = os.environ.get("ARGOCD_SERVER", "http://localhost:8080")
ARGOCD_TOKEN = os.environ.get("ARGOCD_TOKEN", "bearer-token")

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("argocd_mcp_server")

mcp = FastMCP(
    "ArgoCD Controller",
    instructions="ArgoCD를 관리하는 MCP 서버입니다. 배포 관리, 상태 확인, 문제 진단 기능을 제공합니다.",
    host="0.0.0.0",
    port=8000
)

def argocd_api_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
    """ArgoCD REST API 요청 헬퍼 함수"""
    headers = {
        "Authorization": f"Bearer {ARGOCD_TOKEN}",
        "Content-Type": "application/json"
    }
    url = f"{ARGOCD_SERVER}/api/v1{endpoint}"
    
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=data,
            verify=False  # TLS 검증 생략 (필요시 수정)
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        logger.error(f"API 요청 실패: {e.response.text}")
        return {"error": e.response.text}
    except Exception as e:
        logger.error(f"API 요청 중 오류: {str(e)}")
        return {"error": str(e)}

# 1. 배포 실패 로그 분석
@mcp.tool()
async def get_failure_logs(app_name: str, namespace: str = "default") -> Dict:
    """
    배포 실패시 관련 리소스 로그 수집
    - app_name: 애플리케이션 이름
    - namespace: 대상 네임스페이스
    """
    # 애플리케이션 상태 확인
    app_data = argocd_api_request("GET", f"/applications/{app_name}")
    if 'error' in app_data:
        return app_data
    
    if app_data['status']['health']['status'] == 'Healthy':
        return {"status": "healthy"}
    
    # 실패 리소스 수집
    failed_resources = [
        r for r in app_data['status']['resources']
        if r['health']['status'] != 'Healthy'
    ]
    
    # Kubernetes 로그 수집
    logs = {}
    for res in failed_resources:
        res_name = res['name']
        res_type = res['kind'].lower()
        
        # Pod 로그 수집
        if res_type == 'pod':
            log_resp = requests.get(
                f"{ARGOCD_SERVER}/api/v1/applications/{app_name}/resource?name={res_name}&namespace={namespace}&resourceName={res_name}&version=v1&kind=Pod&group=&log=true",
                headers={"Authorization": f"Bearer {ARGOCD_TOKEN}"}
            )
            logs[res_name] = log_resp.json().get('logs', '') if log_resp.ok else "로그 수집 실패"
    
    return {
        "application": app_name,
        "failed_resources": [r['name'] for r in failed_resources],
        "logs": logs
    }

# 2. 배포 자동화
@mcp.tool()
async def deploy_application(
    name: str,
    repo: str,
    path: str,
    project: str = "default",
    cluster: str = "https://kubernetes.default.svc",
    namespace: str = "default"
) -> Dict:
    """
    새로운 애플리케이션 배포
    - name: 애플리케이션 이름
    - repo: Git 저장소 URL
    - path: 매니페스트 경로
    - cluster: 대상 클러스터
    - namespace: 대상 네임스페이스
    """
    payload = {
        "metadata": {"name": name},
        "spec": {
            "project": project,
            "source": {
                "repoURL": repo,
                "path": path,
                "targetRevision": "HEAD"
            },
            "destination": {
                "server": cluster,
                "namespace": namespace
            },
            "syncPolicy": {"automated": {}}
        }
    }
    return argocd_api_request("POST", "/applications", payload)

# 3. Out-of-Sync 상태 애플리케이션 조회
@mcp.tool()
async def list_out_of_sync(project: str = None) -> List[Dict]:
    """
    동기화 필요한 애플리케이션 목록
    - project: 특정 프로젝트 필터링
    """
    endpoint = "/applications?syncStatus=OutOfSync"
    if project:
        endpoint += f"&project={project}"
    
    response = argocd_api_request("GET", endpoint)
    return response.get('items', []) if 'items' in response else response

# 4. 배포 히스토리 조회
@mcp.tool()
async def get_deployment_history(app_name: str, limit: int = 5) -> Dict:
    """
    배포 이력 조회
    - app_name: 애플리케이션 이름
    - limit: 최대 결과 수
    """
    response = argocd_api_request("GET", f"/applications/{app_name}/history")
    if 'error' in response:
        return response
    
    return {
        "history": response[:limit],
        "total": len(response)
    }

# 5. Pod 진단
@mcp.tool()
async def diagnose_pods(namespace: str = "default") -> Dict:
    """
    네임스페이스 내 비정상 Pod 진단
    - namespace: 대상 네임스페이스
    """
    endpoint = f"/applications?namespace={namespace}"
    apps = argocd_api_request("GET", endpoint).get('items', [])
    
    pod_status = {}
    for app in apps:
        app_name = app['metadata']['name']
        resources = argocd_api_request("GET", f"/applications/{app_name}/resource").get('items', [])
        
        for res in resources:
            if res['kind'] == 'Pod' and res['health']['status'] != 'Healthy':
                pod_status[res['name']] = {
                    "app": app_name,
                    "status": res['health']['status'],
                    "message": res['health']['message']
                }
    
    return pod_status

# 6. 애플리케이션 롤백
@mcp.tool()
async def rollback_application(app_name: str, revision_id: Optional[int] = None, revision_history_index: Optional[int] = None) -> Dict:
    """
    애플리케이션을 이전 버전으로 롤백
    - app_name: 애플리케이션 이름
    - revision_id: 롤백할 특정 리비전 ID (지정하지 않으면 revision_history_index 사용)
    - revision_history_index: 배포 히스토리 인덱스 (0이면 최신, 1이면 이전 버전, 지정하지 않으면 가장 최근 성공 버전)
    
    이 도구는 다음과 같은 방식으로 롤백합니다:
    1. 특정 revision_id가 제공되면 해당 ID로 롤백
    2. revision_history_index가 제공되면 배포 히스토리에서 해당 인덱스의 버전으로 롤백
    3. 둘 다 제공되지 않으면 최근 성공 배포 버전으로 롤백
    """
    # 먼저 배포 히스토리 조회
    history_response = argocd_api_request("GET", f"/applications/{app_name}/history")
    if 'error' in history_response:
        return {"error": f"배포 히스토리 조회 실패: {history_response['error']}"}
    
    if not history_response:
        return {"error": "배포 히스토리가 존재하지 않습니다."}
    
    # 롤백할 리비전 결정
    target_revision = None
    
    if revision_id is not None:
        # 특정 리비전 ID로 롤백
        target_revision = next((rev for rev in history_response if rev.get('id') == revision_id), None)
        if not target_revision:
            return {"error": f"리비전 ID {revision_id}를 찾을 수 없습니다."}
    elif revision_history_index is not None:
        # 인덱스로 롤백 (0은 최신)
        if revision_history_index < 0 or revision_history_index >= len(history_response):
            return {"error": f"유효하지 않은 인덱스입니다. 0부터 {len(history_response)-1} 사이여야 합니다."}
        target_revision = history_response[revision_history_index]
    else:
        # 가장 최근 성공 버전으로 롤백 (현재 버전이 아닌 것)
        if len(history_response) <= 1:
            return {"error": "롤백 가능한 이전 버전이 없습니다."}
        target_revision = history_response[1]  # 현재 버전이 아닌 직전 버전
    
    # 애플리케이션 정보 조회
    app_info = argocd_api_request("GET", f"/applications/{app_name}")
    if 'error' in app_info:
        return {"error": f"애플리케이션 정보 조회 실패: {app_info['error']}"}
    
    # 롤백 수행
    rollback_payload = {
        "appNamespace": app_info.get("spec", {}).get("destination", {}).get("namespace", "default"),
        "project": app_info.get("spec", {}).get("project", "default"),
        "name": app_name,
        "id": target_revision.get("id")
    }
    
    logger.info(f"애플리케이션 {app_name}을(를) 리비전 {target_revision.get('id')}(으)로 롤백합니다.")
    rollback_response = argocd_api_request("POST", f"/applications/{app_name}/rollback", rollback_payload)
    
    if 'error' in rollback_response:
        return {"error": f"롤백 실패: {rollback_response['error']}"}
    
    # 롤백 후 동기화
    sync_payload = {
        "name": app_name,
        "prune": True,
        "dryRun": False
    }
    sync_response = argocd_api_request("POST", f"/applications/{app_name}/sync", sync_payload)
    
    return {
        "status": "success",
        "message": f"애플리케이션 {app_name}이(가) 리비전 {target_revision.get('id')}(으)로 롤백되었습니다.",
        "revision": {
            "id": target_revision.get("id"),
            "revision": target_revision.get("revision"),
            "date": target_revision.get("deployedAt")
        },
        "sync_status": "initiated" if 'error' not in sync_response else f"sync_failed: {sync_response['error']}"
    }

# 7. 프로젝트 생성
@mcp.tool()
async def create_project(
    name: str,
    description: str = "",
    source_repos: List[str] = None,
    destinations: List[Dict[str, str]] = None,
    cluster_resource_whitelist: List[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    ArgoCD 프로젝트 생성
    - name: 프로젝트 이름
    - description: 프로젝트 설명
    - source_repos: 허용할 Git 저장소 목록 (예: ["https://github.com/my-org/*"])
    - destinations: 허용할 대상 클러스터 및 네임스페이스 목록 (예: [{"server": "https://kubernetes.default.svc", "namespace": "*"}])
    - cluster_resource_whitelist: 허용할 클러스터 리소스 종류 목록 (예: [{"group": "*", "kind": "*"}])
    """
    # 기본값 설정
    if source_repos is None:
        source_repos = ["*"]
    if destinations is None:
        destinations = [{"server": "https://kubernetes.default.svc", "namespace": "*"}]
    if cluster_resource_whitelist is None:
        cluster_resource_whitelist = [{"group": "*", "kind": "*"}]
    
    # 프로젝트 데이터 구성
    project_data = {
        "metadata": {
            "name": name
        },
        "spec": {
            "description": description,
            "sourceRepos": source_repos,
            "destinations": destinations,
            "clusterResourceWhitelist": cluster_resource_whitelist
        }
    }
    
    logger.info(f"프로젝트 생성 시작: {name}")
    response = argocd_api_request("POST", "/projects", project_data)
    
    if 'error' in response:
        logger.error(f"프로젝트 생성 실패: {response['error']}")
        return response
    
    logger.info(f"프로젝트 생성 완료: {name}")
    return {
        "status": "success",
        "message": f"프로젝트 '{name}'이(가) 생성되었습니다.",
        "project": response
    }

# 8. 프로젝트 목록 조회
@mcp.tool()
async def list_projects() -> Dict[str, Any]:
    """
    ArgoCD 프로젝트 목록 조회
    """
    logger.info("프로젝트 목록 조회 시작")
    response = argocd_api_request("GET", "/projects")
    
    if 'error' in response:
        logger.error(f"프로젝트 목록 조회 실패: {response['error']}")
        return response
    
    # 응답 데이터 가공
    projects = []
    if isinstance(response, list):
        for project in response:
            projects.append({
                "name": project.get("metadata", {}).get("name", ""),
                "description": project.get("spec", {}).get("description", ""),
                "source_repos": project.get("spec", {}).get("sourceRepos", []),
                "destinations": project.get("spec", {}).get("destinations", [])
            })
    
    logger.info(f"프로젝트 목록 조회 완료: {len(projects)}개 프로젝트 발견")
    return {
        "status": "success",
        "count": len(projects),
        "projects": projects
    }

# 9. 프로젝트 기반 애플리케이션 검색
@mcp.tool()
async def search_by_project(
    project: str,
    health_status: Optional[str] = None,
    sync_status: Optional[str] = None
) -> Dict[str, Any]:
    """
    특정 프로젝트에 속한 애플리케이션 검색
    - project: 대상 프로젝트 이름 (필수)
    - health_status: 건강 상태 필터링 (예: Healthy, Degraded, Progressing)
    - sync_status: 동기화 상태 필터링 (예: Synced, OutOfSync)
    """
    logger.info(f"프로젝트 '{project}' 기반 애플리케이션 검색 시작")
    
    # 쿼리 파라미터 구성
    endpoint = f"/applications?project={project}"
    if health_status:
        endpoint += f"&health={health_status}"
    if sync_status:
        endpoint += f"&sync={sync_status}"
    
    # API 요청 수행
    response = argocd_api_request("GET", endpoint)
    
    if 'error' in response:
        logger.error(f"프로젝트 기반 애플리케이션 검색 실패: {response['error']}")
        return response
    
    # 응답 데이터 가공
    applications = []
    if 'items' in response:
        for app in response['items']:
            applications.append({
                "name": app.get("metadata", {}).get("name", ""),
                "namespace": app.get("spec", {}).get("destination", {}).get("namespace", ""),
                "sync_status": app.get("status", {}).get("sync", {}).get("status", "Unknown"),
                "health_status": app.get("status", {}).get("health", {}).get("status", "Unknown")
            })
    
    logger.info(f"프로젝트 기반 애플리케이션 검색 완료: {len(applications)}개 애플리케이션 발견")
    return {
        "status": "success",
        "project": project,
        "count": len(applications),
        "applications": applications
    }

# 10. 고급 애플리케이션 생성
@mcp.tool()
async def create_application(
    name: str,
    repo_url: str,
    path: str,
    project: str = "default",
    target_revision: str = "HEAD",
    cluster: str = "https://kubernetes.default.svc",
    namespace: str = "default",
    sync_policy: Dict[str, Any] = None,
    auto_prune: bool = False,
    self_heal: bool = False
) -> Dict[str, Any]:
    """
    고급 옵션을 포함한 ArgoCD 애플리케이션 생성
    - name: 애플리케이션 이름
    - repo_url: Git 저장소 URL
    - path: 매니페스트 경로
    - project: 프로젝트 이름
    - target_revision: Git 리비전 (브랜치, 태그, 커밋 해시)
    - cluster: 대상 클러스터 URL
    - namespace: 대상 네임스페이스
    - sync_policy: 동기화 정책 (고급 사용자용)
    - auto_prune: 삭제된 리소스 자동 정리 여부
    - self_heal: 자동 복구 여부 (동기화 상태 유지)
    """
    logger.info(f"애플리케이션 생성 시작: {name}")
    
    # 동기화 정책 구성
    if sync_policy is None:
        sync_policy = {}
    
    if auto_prune or self_heal:
        if "automated" not in sync_policy:
            sync_policy["automated"] = {}
        if auto_prune:
            sync_policy["automated"]["prune"] = True
        if self_heal:
            sync_policy["automated"]["selfHeal"] = True
    
    # 애플리케이션 데이터 구성
    app_data = {
        "metadata": {
            "name": name
        },
        "spec": {
            "project": project,
            "source": {
                "repoURL": repo_url,
                "path": path,
                "targetRevision": target_revision
            },
            "destination": {
                "server": cluster,
                "namespace": namespace
            }
        }
    }
    
    # 동기화 정책이 있는 경우만 추가
    if sync_policy:
        app_data["spec"]["syncPolicy"] = sync_policy
    
    # 애플리케이션 생성 요청
    response = argocd_api_request("POST", "/applications", app_data)
    
    if 'error' in response:
        logger.error(f"애플리케이션 생성 실패: {response['error']}")
        return response
    
    logger.info(f"애플리케이션 생성 완료: {name}")
    return {
        "status": "success",
        "message": f"애플리케이션 '{name}'이(가) 생성되었습니다.",
        "application": {
            "name": response.get("metadata", {}).get("name", ""),
            "project": response.get("spec", {}).get("project", ""),
            "repo": response.get("spec", {}).get("source", {}).get("repoURL", ""),
            "path": response.get("spec", {}).get("source", {}).get("path", ""),
            "namespace": response.get("spec", {}).get("destination", {}).get("namespace", "")
        }
    }

# 11. 애플리케이션 검색
@mcp.tool()
async def search_applications(
    name_pattern: Optional[str] = None,
    project: Optional[str] = None,
    namespace: Optional[str] = None,
    health_status: Optional[str] = None,
    sync_status: Optional[str] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    다양한 필터 조건으로 애플리케이션 검색
    - name_pattern: 애플리케이션 이름 패턴 (예: "frontend*")
    - project: 프로젝트 필터링
    - namespace: 네임스페이스 필터링
    - health_status: 건강 상태 필터링 (예: Healthy, Degraded, Progressing)
    - sync_status: 동기화 상태 필터링 (예: Synced, OutOfSync)
    - limit: 최대 결과 수
    """
    logger.info("애플리케이션 검색 시작")
    
    # 쿼리 파라미터 구성
    endpoint = "/applications?"
    
    query_params = []
    if name_pattern:
        query_params.append(f"name={name_pattern}")
    if project:
        query_params.append(f"project={project}")
    if namespace:
        query_params.append(f"namespace={namespace}")
    if health_status:
        query_params.append(f"health={health_status}")
    if sync_status:
        query_params.append(f"sync={sync_status}")
    
    if query_params:
        endpoint += "&".join(query_params)
    
    # API 요청 수행
    response = argocd_api_request("GET", endpoint)
    
    if 'error' in response:
        logger.error(f"애플리케이션 검색 실패: {response['error']}")
        return response
    
    # 응답 데이터 가공
    applications = []
    if 'items' in response:
        items = response['items'][:limit]  # 결과 제한
        
        for app in items:
            app_info = {
                "name": app.get("metadata", {}).get("name", ""),
                "project": app.get("spec", {}).get("project", ""),
                "namespace": app.get("spec", {}).get("destination", {}).get("namespace", ""),
                "sync_status": app.get("status", {}).get("sync", {}).get("status", "Unknown"),
                "health_status": app.get("status", {}).get("health", {}).get("status", "Unknown"),
                "repo": app.get("spec", {}).get("source", {}).get("repoURL", ""),
                "path": app.get("spec", {}).get("source", {}).get("path", "")
            }
            applications.append(app_info)
    
    logger.info(f"애플리케이션 검색 완료: {len(applications)}개 애플리케이션 발견")
    
    return {
        "status": "success",
        "count": len(applications),
        "filters": {
            "name_pattern": name_pattern,
            "project": project,
            "namespace": namespace,
            "health_status": health_status,
            "sync_status": sync_status
        },
        "applications": applications
    }

if __name__ == "__main__":
    print("ArgoCD MCP 서버 실행 중...")
    mcp.run(transport="sse")
