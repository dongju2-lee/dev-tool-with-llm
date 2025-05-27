from mcp.server.fastmcp import FastMCP
import logging
from typing import Dict, Any, Optional, List
import time
import requests
import base64
import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

# .env 파일의 절대 경로 계산
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, '.env')

# .env 파일 로드 (있는 경우) - override=True로 설정하여 기존 환경 변수 덮어쓰기
load_dotenv(dotenv_path=env_path, override=True)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 간단한 메모리 저장소 (실제로는 데이터베이스를 사용할 것)
threads = {}
messages = {}

# 시작 시간 기록
start_time = time.time()

# Grafana URL을 환경 변수에서 가져오거나 기본값 사용
GRAFANA_URL = os.environ.get("GRAFANA_URL", "http://grafana:3000")
# API 키를 환경 변수에서 가져오기
GRAFANA_API_KEY = os.environ.get("GRAFANA_API_KEY", "")
logger.info(f"Grafana URL: {GRAFANA_URL}")
logger.info(f"API Key configured: {'Yes' if GRAFANA_API_KEY else 'No'}")
logger.info(f"Using .env from: {env_path}")
logger.info(f"API Key: {GRAFANA_API_KEY[:5]}...{GRAFANA_API_KEY[-5:] if GRAFANA_API_KEY else ''}")

# FastMCP 서버 생성
mcp = FastMCP("GrafanaDashboardServer")

def get_grafana_headers():
    """Grafana API 요청에 사용할 헤더를 반환합니다."""
    if GRAFANA_API_KEY:
        return {
            "Authorization": f"Bearer {GRAFANA_API_KEY}",
            "Content-Type": "application/json"
            }
    return {}

# 데이터소스 조회 도구

@mcp.tool()
def list_datasources() -> List[Dict[str, Any]]:
    """Grafana의 모든 데이터소스 목록을 반환합니다.
    
    Returns:
        List[Dict[str, Any]]: 데이터소스 목록
    """
    logger.info("list_datasources 도구 호출")

    url = f"{GRAFANA_URL}/api/datasources"
    
    try:
        response = requests.get(url, headers=get_grafana_headers())
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"데이터소스 목록 가져오기 실패: HTTP {response.status_code}, {response.text}")
            return []
    
    except Exception as e:
        logger.error(f"데이터소스 목록 가져오기 오류: {str(e)}")
        return []

@mcp.tool()
def get_datasource(id_or_name: str) -> Dict[str, Any]:
    """특정 데이터소스의 상세 정보를 반환합니다.
    
    Args:
        id_or_name: 데이터소스의 ID 또는 이름
        
    Returns:
        Dict[str, Any]: 데이터소스 상세 정보
    """
    logger.info(f"get_datasource 도구 호출: id_or_name={id_or_name}")
    
    # ID인지 이름인지 확인 (숫자면 ID로 가정)
    if id_or_name.isdigit():
        url = f"{GRAFANA_URL}/api/datasources/{id_or_name}"
    else:
        url = f"{GRAFANA_URL}/api/datasources/name/{quote_plus(id_or_name)}"
    
    try:
        response = requests.get(url, headers=get_grafana_headers())
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"데이터소스 정보 가져오기 실패: HTTP {response.status_code}, {response.text}")
            return {"error": f"데이터소스 정보 가져오기 실패: HTTP {response.status_code}"}
    
    except Exception as e:
        logger.error(f"데이터소스 정보 가져오기 오류: {str(e)}")
        return {"error": f"데이터소스 정보 가져오기 오류: {str(e)}"}

@mcp.tool()
def test_datasource(id_or_name: str) -> Dict[str, Any]:
    """데이터소스 연결을 테스트합니다.
    
    Args:
        id_or_name: 테스트할 데이터소스의 ID 또는 이름
        
    Returns:
        Dict[str, Any]: 테스트 결과
    """
    logger.info(f"test_datasource 도구 호출: id_or_name={id_or_name}")
    
    # 먼저 데이터소스 정보 가져오기
    datasource = get_datasource(id_or_name)
    
    if "error" in datasource:
        return datasource
    
    # 데이터소스 ID로 테스트 요청
    url = f"{GRAFANA_URL}/api/datasources/{datasource.get('id')}/health"
    
    try:
        response = requests.get(url, headers=get_grafana_headers())
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"데이터소스 테스트 실패: HTTP {response.status_code}, {response.text}")
            return {"status": "error", "message": f"데이터소스 테스트 실패: HTTP {response.status_code}"}
    
    except Exception as e:
        logger.error(f"데이터소스 테스트 오류: {str(e)}")
        return {"status": "error", "message": f"데이터소스 테스트 오류: {str(e)}"}

# 대시보드 조회 도구

@mcp.tool()
def list_dashboards(folder_id: Optional[int] = None, query: Optional[str] = None) -> List[Dict[str, Any]]:
    """대시보드 목록을 반환합니다.
    
    Args:
        folder_id: 특정 폴더의 대시보드만 필터링 (선택 사항)
        query: 검색 쿼리 (선택 사항)
        
    Returns:
        List[Dict[str, Any]]: 대시보드 목록
    """
    logger.info(f"list_dashboards 도구 호출: folder_id={folder_id}, query={query}")
    
    url = f"{GRAFANA_URL}/api/search"
    params = {}
    
    if folder_id is not None:
        params["folderIds"] = folder_id
    
    if query:
        params["query"] = query
    
    # 대시보드만 검색
    params["type"] = "dash-db"
    
    try:
        response = requests.get(url, params=params, headers=get_grafana_headers())
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"대시보드 목록 가져오기 실패: HTTP {response.status_code}, {response.text}")
            return []
    
    except Exception as e:
        logger.error(f"대시보드 목록 가져오기 오류: {str(e)}")
        return []

@mcp.tool()
def get_dashboard(uid: str) -> Dict[str, Any]:
    """특정 대시보드의 상세 정보를 반환합니다.
    
    Args:
        uid: 대시보드 UID
        
    Returns:
        Dict[str, Any]: 대시보드 상세 정보
    """
    logger.info(f"get_dashboard 도구 호출: uid={uid}")
    
    url = f"{GRAFANA_URL}/api/dashboards/uid/{uid}"
    
    try:
        response = requests.get(url, headers=get_grafana_headers())
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"대시보드 정보 가져오기 실패: HTTP {response.status_code}, {response.text}")
            return {"error": f"대시보드 정보 가져오기 실패: HTTP {response.status_code}"}
    
    except Exception as e:
        logger.error(f"대시보드 정보 가져오기 오류: {str(e)}")
        return {"error": f"대시보드 정보 가져오기 오류: {str(e)}"}

# 패널 조회 도구

@mcp.tool()
def list_panels(dashboard_uid: str) -> List[Dict[str, Any]]:
    """특정 대시보드에 포함된 패널 목록을 반환합니다.
    
    Args:
        dashboard_uid: 대시보드 UID
        
    Returns:
        List[Dict[str, Any]]: 패널 목록
    """
    logger.info(f"list_panels 도구 호출: dashboard_uid={dashboard_uid}")
    
    # 대시보드 정보 가져오기
    dashboard = get_dashboard(dashboard_uid)
    
    if "error" in dashboard:
        return []
    
    try:
        panels = []
        # 대시보드 모델에서 패널 추출
        dashboard_data = dashboard.get("dashboard", {})
        
        for panel in dashboard_data.get("panels", []):
            panels.append({
                "id": panel.get("id"),
                "title": panel.get("title"),
                "type": panel.get("type"),
                "description": panel.get("description", ""),
                "datasource": panel.get("datasource")
            })
        
        return panels
    
    except Exception as e:
        logger.error(f"패널 목록 추출 오류: {str(e)}")
        return []

@mcp.tool()
def get_panel_data(dashboard_uid: str, panel_id: int, time_range: Dict[str, str]) -> Dict[str, Any]:
    """특정 패널의 데이터를 쿼리합니다.
    
    Args:
        dashboard_uid: 대시보드 UID
        panel_id: 패널 ID
        time_range: 시간 범위 (딕셔너리 형태: {"from": "now-6h", "to": "now"} 등)
        
    Returns:
        Dict[str, Any]: 패널 데이터
    """
    logger.info(f"get_panel_data 도구 호출: dashboard_uid={dashboard_uid}, panel_id={panel_id}, time_range={time_range}")
    
    # 대시보드 정보 가져오기
    dashboard = get_dashboard(dashboard_uid)
    
    if "error" in dashboard:
        return {"error": dashboard.get("error")}
    
    # 패널 찾기
    panel = None
    dashboard_data = dashboard.get("dashboard", {})
    
    for p in dashboard_data.get("panels", []):
        if p.get("id") == panel_id:
            panel = p
            break
    
    if not panel:
        return {"error": f"패널 ID {panel_id}를 찾을 수 없습니다"}
    
    # 패널의 데이터소스와 쿼리 추출
    datasource = panel.get("datasource")
    targets = panel.get("targets", [])
    
    if not targets:
        return {"error": "패널에 데이터 쿼리가 없습니다"}
    
    # 쿼리 요청 준비
    url = f"{GRAFANA_URL}/api/ds/query"
    
    # 요청 데이터 구성
    request_data = {
        "queries": targets,
        "from": time_range.get("from", "now-1h"),
        "to": time_range.get("to", "now")
    }
    
    try:
        response = requests.post(url, json=request_data, headers=get_grafana_headers())
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"패널 데이터 쿼리 실패: HTTP {response.status_code}, {response.text}")
            return {"error": f"패널 데이터 쿼리 실패: HTTP {response.status_code}"}
    
    except Exception as e:
        logger.error(f"패널 데이터 쿼리 오류: {str(e)}")
        return {"error": f"패널 데이터 쿼리 오류: {str(e)}"}

# 스크린샷 도구

@mcp.tool()
def render_dashboard(dashboard_uid: str, time_range: Dict[str, str], width: int = 1000, height: int = 500, theme: str = "light") -> str:
    """대시보드 이미지를 렌더링합니다.
    
    Args:
        dashboard_uid: 대시보드 UID
        time_range: 시간 범위 (딕셔너리 형태: {"from": "now-6h", "to": "now"} 등)
        width: 이미지 너비 (픽셀)
        height: 이미지 높이 (픽셀)
        theme: 테마 ("light" 또는 "dark")
        
    Returns:
        str: base64로 인코딩된 이미지 데이터
    """
    logger.info(f"render_dashboard 도구 호출: dashboard_uid={dashboard_uid}, time_range={time_range}")
    
    # 렌더링 URL 구성
    url = f"{GRAFANA_URL}/render/d/{dashboard_uid}"
    
    params = {
        "from": time_range.get("from", "now-1h"),
        "to": time_range.get("to", "now"),
        "width": width,
        "height": height,
        "theme": theme
    }
    
    try:
        # Grafana에 HTTP 요청
        logger.info(f"Grafana 렌더링 요청 전송: {url}")
        response = requests.get(url, params=params, headers=get_grafana_headers())
        
        # 응답 확인
        if response.status_code == 200:
            # PNG 데이터를 Base64로 인코딩
            png_base64 = base64.b64encode(response.content).decode('utf-8')
            return png_base64
        else:
            logger.error(f"대시보드 렌더링 실패: HTTP {response.status_code}, {response.text}")
            return ""
    
    except Exception as e:
        logger.error(f"대시보드 렌더링 오류: {str(e)}")
        return ""

@mcp.tool()
def render_panel(dashboard_uid: str, panel_id: int, time_range: Dict[str, str], width: int = 500, height: int = 300, theme: str = "light") -> str:
    """패널 이미지를 렌더링합니다.
    
    Args:
        dashboard_uid: 대시보드 UID
        panel_id: 패널 ID
        time_range: 시간 범위 (딕셔너리 형태: {"from": "now-6h", "to": "now"} 등)
        width: 이미지 너비 (픽셀)
        height: 이미지 높이 (픽셀)
        theme: 테마 ("light" 또는 "dark")
        
    Returns:
        str: base64로 인코딩된 이미지 데이터
    """
    logger.info(f"render_panel 도구 호출: dashboard_uid={dashboard_uid}, panel_id={panel_id}, time_range={time_range}")
    
    # 렌더링 URL 구성 (solo 모드로 패널만 렌더링)
    url = f"{GRAFANA_URL}/render/d-solo/{dashboard_uid}"
    
    params = {
        "panelId": panel_id,
        "from": time_range.get("from", "now-1h"),
        "to": time_range.get("to", "now"),
        "width": width,
        "height": height,
        "theme": theme
    }
    
    try:
        # Grafana에 HTTP 요청
        logger.info(f"Grafana 패널 렌더링 요청 전송: {url}")
        response = requests.get(url, params=params, headers=get_grafana_headers())
        
        # 응답 확인
        if response.status_code == 200:
            # PNG 데이터를 Base64로 인코딩
            png_base64 = base64.b64encode(response.content).decode('utf-8')
            return png_base64
        else:
            logger.error(f"패널 렌더링 실패: HTTP {response.status_code}, {response.text}")
            return ""
    
    except Exception as e:
        logger.error(f"패널 렌더링 오류: {str(e)}")
        return ""

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