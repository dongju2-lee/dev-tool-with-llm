from mcp.server.fastmcp import FastMCP
import logging
from typing import Dict, Any, Optional, List
import time
import requests
import os
from dotenv import load_dotenv

# .env 파일의 절대 경로 계산
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, '.env')

# .env 파일 로드 (있는 경우) - override=True로 설정하여 기존 환경 변수 덮어쓰기
load_dotenv(dotenv_path=env_path, override=True)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 시작 시간 기록
start_time = time.time()

# SonarQube URL을 환경 변수에서 가져오거나 기본값 사용
SONARQUBE_URL = os.environ.get("SONARQUBE_URL", "http://sonarqube:9000")
# API 토큰을 환경 변수에서 가져오기
SONARQUBE_TOKEN = os.environ.get("SONARQUBE_TOKEN", "")
logger.info(f"SonarQube URL: {SONARQUBE_URL}")
logger.info(f"API Token configured: {'Yes' if SONARQUBE_TOKEN else 'No'}")
logger.info(f"Using .env from: {env_path}")
logger.info(f"API Token: {SONARQUBE_TOKEN[:5]}...{SONARQUBE_TOKEN[-5:] if SONARQUBE_TOKEN else ''}")

# FastMCP 서버 생성
mcp = FastMCP("SonarQubeServer")

def get_sonarqube_auth():
    """SonarQube API 요청에 사용할 인증 정보를 반환합니다."""
    if SONARQUBE_TOKEN:
        return (SONARQUBE_TOKEN, '')
    return None

def get_headers():
    """SonarQube API 요청에 사용할 헤더를 반환합니다."""
    return {
        "Content-Type": "application/json"
    }

# 프로젝트 관련 도구

@mcp.tool()
def list_projects() -> List[Dict[str, Any]]:
    """SonarQube의 모든 프로젝트 목록을 반환합니다.
    
    Returns:
        List[Dict[str, Any]]: 프로젝트 목록
    """
    logger.info("list_projects 도구 호출")

    url = f"{SONARQUBE_URL}/api/projects/search"
    
    try:
        response = requests.get(url, headers=get_headers(), auth=get_sonarqube_auth())
        
        if response.status_code == 200:
            return response.json().get('components', [])
        else:
            logger.error(f"프로젝트 목록 가져오기 실패: HTTP {response.status_code}, {response.text}")
            return []
    
    except Exception as e:
        logger.error(f"프로젝트 목록 가져오기 오류: {str(e)}")
        return []

@mcp.tool()
def get_project(project_key: str) -> Dict[str, Any]:
    """특정 프로젝트의 상세 정보를 반환합니다.
    
    Args:
        project_key: 프로젝트 키
        
    Returns:
        Dict[str, Any]: 프로젝트 상세 정보
    """
    logger.info(f"get_project 도구 호출: project_key={project_key}")
    
    url = f"{SONARQUBE_URL}/api/projects/search"
    params = {"projects": project_key}
    
    try:
        response = requests.get(url, params=params, headers=get_headers(), auth=get_sonarqube_auth())
        
        if response.status_code == 200:
            components = response.json().get('components', [])
            if components:
                return components[0]
            else:
                return {"error": "프로젝트를 찾을 수 없습니다."}
        else:
            logger.error(f"프로젝트 정보 가져오기 실패: HTTP {response.status_code}, {response.text}")
            return {"error": f"프로젝트 정보 가져오기 실패: HTTP {response.status_code}"}
    
    except Exception as e:
        logger.error(f"프로젝트 정보 가져오기 오류: {str(e)}")
        return {"error": f"프로젝트 정보 가져오기 오류: {str(e)}"}

# 품질 게이트 관련 도구

@mcp.tool()
def get_quality_gate_status(project_key: str) -> Dict[str, Any]:
    """특정 프로젝트의 품질 게이트 상태를 반환합니다.
    
    Args:
        project_key: 프로젝트 키
        
    Returns:
        Dict[str, Any]: 품질 게이트 상태 정보
    """
    logger.info(f"get_quality_gate_status 도구 호출: project_key={project_key}")
    
    url = f"{SONARQUBE_URL}/api/qualitygates/project_status"
    params = {"projectKey": project_key}
    
    try:
        response = requests.get(url, params=params, headers=get_headers(), auth=get_sonarqube_auth())
        
        if response.status_code == 200:
            return response.json().get('projectStatus', {})
        else:
            logger.error(f"품질 게이트 상태 가져오기 실패: HTTP {response.status_code}, {response.text}")
            return {"error": f"품질 게이트 상태 가져오기 실패: HTTP {response.status_code}"}
    
    except Exception as e:
        logger.error(f"품질 게이트 상태 가져오기 오류: {str(e)}")
        return {"error": f"품질 게이트 상태 가져오기 오류: {str(e)}"}

# 이슈 관련 도구

@mcp.tool()
def get_project_issues(project_key: str, issue_types: Optional[List[str]] = None, 
                      severities: Optional[List[str]] = None, statuses: Optional[List[str]] = None, 
                      max_results: int = 100, page: int = 1) -> Dict[str, Any]:
    """특정 프로젝트의 이슈 목록을 반환합니다.
    
    Args:
        project_key: 프로젝트 키
        issue_types: 이슈 유형 필터 (BUG, VULNERABILITY, CODE_SMELL)
        severities: 심각도 필터 (BLOCKER, CRITICAL, MAJOR, MINOR, INFO)
        statuses: 상태 필터 (OPEN, CONFIRMED, RESOLVED, CLOSED)
        max_results: 페이지당 결과 수
        page: 페이지 번호
        
    Returns:
        Dict[str, Any]: 이슈 목록과 페이지네이션 정보
    """
    logger.info(f"get_project_issues 도구 호출: project_key={project_key}, issue_types={issue_types}, severities={severities}, statuses={statuses}, max_results={max_results}, page={page}")
    
    url = f"{SONARQUBE_URL}/api/issues/search"
    params = {
        "componentKeys": project_key,
        "ps": max_results,
        "p": page
    }
    
    if issue_types:
        params["types"] = ",".join(issue_types)
    
    if severities:
        params["severities"] = ",".join(severities)
    
    if statuses:
        params["statuses"] = ",".join(statuses)
    
    try:
        response = requests.get(url, params=params, headers=get_headers(), auth=get_sonarqube_auth())
        
        if response.status_code == 200:
            data = response.json()
            return {
                "issues": data.get("issues", []),
                "total": data.get("total", 0),
                "p": data.get("p", 1),
                "ps": data.get("ps", max_results)
            }
        else:
            logger.error(f"이슈 목록 가져오기 실패: HTTP {response.status_code}, {response.text}")
            return {"error": f"이슈 목록 가져오기 실패: HTTP {response.status_code}"}
    
    except Exception as e:
        logger.error(f"이슈 목록 가져오기 오류: {str(e)}")
        return {"error": f"이슈 목록 가져오기 오류: {str(e)}"}

@mcp.tool()
def get_issue_details(issue_key: str) -> Dict[str, Any]:
    """특정 이슈의 상세 정보를 반환합니다.
    
    Args:
        issue_key: 이슈 키
        
    Returns:
        Dict[str, Any]: 이슈 상세 정보
    """
    logger.info(f"get_issue_details 도구 호출: issue_key={issue_key}")
    
    url = f"{SONARQUBE_URL}/api/issues/search"
    params = {"issues": issue_key}
    
    try:
        response = requests.get(url, params=params, headers=get_headers(), auth=get_sonarqube_auth())
        
        if response.status_code == 200:
            issues = response.json().get("issues", [])
            if issues:
                return issues[0]
            else:
                return {"error": "이슈를 찾을 수 없습니다."}
        else:
            logger.error(f"이슈 상세 정보 가져오기 실패: HTTP {response.status_code}, {response.text}")
            return {"error": f"이슈 상세 정보 가져오기 실패: HTTP {response.status_code}"}
    
    except Exception as e:
        logger.error(f"이슈 상세 정보 가져오기 오류: {str(e)}")
        return {"error": f"이슈 상세 정보 가져오기 오류: {str(e)}"}

# 메트릭 관련 도구

@mcp.tool()
def get_project_metrics(project_key: str, metrics: List[str]) -> Dict[str, Any]:
    """특정 프로젝트의 메트릭 값들을 반환합니다.
    
    Args:
        project_key: 프로젝트 키
        metrics: 조회할 메트릭 키 목록 (예: ncloc, coverage, duplicated_lines_density)
        
    Returns:
        Dict[str, Any]: 메트릭 값 목록
    """
    logger.info(f"get_project_metrics 도구 호출: project_key={project_key}, metrics={metrics}")
    
    url = f"{SONARQUBE_URL}/api/measures/component"
    params = {
        "component": project_key,
        "metricKeys": ",".join(metrics)
    }
    
    try:
        response = requests.get(url, params=params, headers=get_headers(), auth=get_sonarqube_auth())
        
        if response.status_code == 200:
            component = response.json().get("component", {})
            return {
                "component": component.get("key"),
                "name": component.get("name"),
                "measures": component.get("measures", [])
            }
        else:
            logger.error(f"메트릭 가져오기 실패: HTTP {response.status_code}, {response.text}")
            return {"error": f"메트릭 가져오기 실패: HTTP {response.status_code}"}
    
    except Exception as e:
        logger.error(f"메트릭 가져오기 오류: {str(e)}")
        return {"error": f"메트릭 가져오기 오류: {str(e)}"}

@mcp.tool()
def list_metrics() -> List[Dict[str, Any]]:
    """사용 가능한 모든 메트릭 목록을 반환합니다.
    
    Returns:
        List[Dict[str, Any]]: 메트릭 목록
    """
    logger.info("list_metrics 도구 호출")
    
    url = f"{SONARQUBE_URL}/api/metrics/search"
    params = {"ps": 500}  # 최대 개수 설정
    
    try:
        response = requests.get(url, params=params, headers=get_headers(), auth=get_sonarqube_auth())
        
        if response.status_code == 200:
            return response.json().get("metrics", [])
        else:
            logger.error(f"메트릭 목록 가져오기 실패: HTTP {response.status_code}, {response.text}")
            return []
    
    except Exception as e:
        logger.error(f"메트릭 목록 가져오기 오류: {str(e)}")
        return []

# 구성요소 관련 도구

@mcp.tool()
def get_project_components(project_key: str, qualifiers: Optional[List[str]] = None, 
                          max_results: int = 100, page: int = 1) -> Dict[str, Any]:
    """특정 프로젝트의 구성요소(파일, 디렉토리 등) 목록을 반환합니다.
    
    Args:
        project_key: 프로젝트 키
        qualifiers: 구성요소 유형 (DIR, FIL, UTS 등)
        max_results: 페이지당 결과 수
        page: 페이지 번호
        
    Returns:
        Dict[str, Any]: 구성요소 목록과 페이지네이션 정보
    """
    logger.info(f"get_project_components 도구 호출: project_key={project_key}, qualifiers={qualifiers}, max_results={max_results}, page={page}")
    
    url = f"{SONARQUBE_URL}/api/components/tree"
    params = {
        "component": project_key,
        "ps": max_results,
        "p": page
    }
    
    if qualifiers:
        params["qualifiers"] = ",".join(qualifiers)
    
    try:
        response = requests.get(url, params=params, headers=get_headers(), auth=get_sonarqube_auth())
        
        if response.status_code == 200:
            data = response.json()
            return {
                "components": data.get("components", []),
                "paging": data.get("paging", {})
            }
        else:
            logger.error(f"구성요소 목록 가져오기 실패: HTTP {response.status_code}, {response.text}")
            return {"error": f"구성요소 목록 가져오기 실패: HTTP {response.status_code}"}
    
    except Exception as e:
        logger.error(f"구성요소 목록 가져오기 오류: {str(e)}")
        return {"error": f"구성요소 목록 가져오기 오류: {str(e)}"}

# 규칙 관련 도구

@mcp.tool()
def get_rules(languages: Optional[List[str]] = None, severities: Optional[List[str]] = None, 
             max_results: int = 50, page: int = 1) -> Dict[str, Any]:
    """SonarQube의 규칙 목록을 반환합니다.
    
    Args:
        languages: 특정 언어로 필터링 (java, js, py 등)
        severities: 심각도로 필터링 (BLOCKER, CRITICAL, MAJOR, MINOR, INFO)
        max_results: 페이지당 결과 수
        page: 페이지 번호
        
    Returns:
        Dict[str, Any]: 규칙 목록과 페이지네이션 정보
    """
    logger.info(f"get_rules 도구 호출: languages={languages}, severities={severities}, max_results={max_results}, page={page}")
    
    url = f"{SONARQUBE_URL}/api/rules/search"
    params = {
        "ps": max_results,
        "p": page
    }
    
    if languages:
        params["languages"] = ",".join(languages)
    
    if severities:
        params["severities"] = ",".join(severities)
    
    try:
        response = requests.get(url, params=params, headers=get_headers(), auth=get_sonarqube_auth())
        
        if response.status_code == 200:
            data = response.json()
            return {
                "rules": data.get("rules", []),
                "total": data.get("total", 0),
                "p": data.get("p", 1),
                "ps": data.get("ps", max_results)
            }
        else:
            logger.error(f"규칙 목록 가져오기 실패: HTTP {response.status_code}, {response.text}")
            return {"error": f"규칙 목록 가져오기 실패: HTTP {response.status_code}"}
    
    except Exception as e:
        logger.error(f"규칙 목록 가져오기 오류: {str(e)}")
        return {"error": f"규칙 목록 가져오기 오류: {str(e)}"}

@mcp.tool()
def get_rule_details(rule_key: str) -> Dict[str, Any]:
    """특정 규칙의 상세 정보를 반환합니다.
    
    Args:
        rule_key: 규칙 키
        
    Returns:
        Dict[str, Any]: 규칙 상세 정보
    """
    logger.info(f"get_rule_details 도구 호출: rule_key={rule_key}")
    
    url = f"{SONARQUBE_URL}/api/rules/show"
    params = {"key": rule_key}
    
    try:
        response = requests.get(url, params=params, headers=get_headers(), auth=get_sonarqube_auth())
        
        if response.status_code == 200:
            return response.json().get("rule", {})
        else:
            logger.error(f"규칙 상세 정보 가져오기 실패: HTTP {response.status_code}, {response.text}")
            return {"error": f"규칙 상세 정보 가져오기 실패: HTTP {response.status_code}"}
    
    except Exception as e:
        logger.error(f"규칙 상세 정보 가져오기 오류: {str(e)}")
        return {"error": f"규칙 상세 정보 가져오기 오류: {str(e)}"}

# 유틸리티 도구

@mcp.tool()
def get_server_version() -> Dict[str, Any]:
    """SonarQube 서버 버전 정보를 반환합니다.
    
    Returns:
        Dict[str, Any]: 서버 버전 정보
    """
    logger.info("get_server_version 도구 호출")
    
    url = f"{SONARQUBE_URL}/api/server/version"
    
    try:
        response = requests.get(url, headers=get_headers(), auth=get_sonarqube_auth())
        
        if response.status_code == 200:
            version = response.text.strip()
            return {
                "version": version,
                "uptime": time.time() - start_time
            }
        else:
            logger.error(f"서버 버전 가져오기 실패: HTTP {response.status_code}, {response.text}")
            return {"error": f"서버 버전 가져오기 실패: HTTP {response.status_code}"}
    
    except Exception as e:
        logger.error(f"서버 버전 가져오기 오류: {str(e)}")
        return {"error": f"서버 버전 가져오기 오류: {str(e)}"}

@mcp.tool()
def get_server_health() -> Dict[str, str]:
    """SonarQube 서버 상태를 확인합니다.
    
    Returns:
        Dict[str, str]: 서버 상태 정보
    """
    logger.info("get_server_health 도구 호출")
    
    url = f"{SONARQUBE_URL}/api/system/health"
    
    try:
        response = requests.get(url, headers=get_headers(), auth=get_sonarqube_auth())
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"서버 상태 확인 실패: HTTP {response.status_code}, {response.text}")
            return {"health": "RED", "error": f"HTTP {response.status_code}"}
    
    except Exception as e:
        logger.error(f"서버 상태 확인 오류: {str(e)}")
        return {"health": "RED", "error": str(e)}

if __name__ == "__main__":
    # HTTP 모드로 서버 실행
    logger.info("Grafana Dashboard MCP 서버 시작...")
    try:
        # SSE 트랜스포트 모드로 실행 (FastAPI/Uvicorn 기반)
        mcp.run(transport="sse")
        
    except KeyboardInterrupt:
        logger.info("서버가 중지되었습니다.")
    except Exception as e:
        logger.error(f"서버 오류: {str(e)}") 