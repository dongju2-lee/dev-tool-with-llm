"""
Grafana API 클라이언트
"""
import httpx
import os
import json
import logging
from typing import Dict, Any, Optional, List, Union
from urllib.parse import urljoin

# 로깅 설정
logger = logging.getLogger("grafana-client")

class GrafanaClient:
    """Grafana API와 통신하는 클라이언트"""
    
    def __init__(self, base_url: str, api_key: str, debug: bool = False):
        """
        Grafana 클라이언트 초기화
        
        Args:
            base_url: Grafana 서버 URL (예: http://localhost:3000)
            api_key: Grafana API 키
            debug: 디버그 모드 활성화 여부
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.debug = debug
        self.http_client = httpx.Client(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0  # 30초 타임아웃
        )
    
    def __del__(self):
        """클라이언트 정리"""
        if hasattr(self, 'http_client'):
            self.http_client.close()
    
    def request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None, 
                json_data: Optional[Dict[str, Any]] = None) -> Any:
        """
        Grafana API에 요청을 보냅니다.
        
        Args:
            method: HTTP 메서드 (GET, POST, PUT, DELETE)
            path: API 경로
            params: URL 매개변수
            json_data: 요청 본문 데이터
            
        Returns:
            응답 데이터 (JSON)
        """
        url = urljoin(self.base_url, path)
        
        if self.debug:
            debug_info = {
                "method": method,
                "url": url,
                "params": params,
                "json_data": json_data
            }
            logger.debug(f"Grafana API 요청: {json.dumps(debug_info)}")
        
        try:
            response = self.http_client.request(
                method=method,
                url=url,
                params=params,
                json=json_data
            )
            
            if self.debug:
                logger.debug(f"Grafana API 응답 상태: {response.status_code}")
                logger.debug(f"Grafana API 응답 내용: {response.text[:1000]}")
            
            response.raise_for_status()
            
            # 응답이 JSON인 경우 파싱
            if response.headers.get("content-type", "").startswith("application/json"):
                return response.json()
            
            return response.text
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP 오류: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP 요청 오류: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"요청 중 오류 발생: {str(e)}")
            raise

    # Dashboard 관련 메서드
    def search_dashboards(self, query: Optional[str] = None, 
                         tags: Optional[List[str]] = None, 
                         folder_ids: Optional[List[int]] = None,
                         limit: int = 100) -> List[Dict[str, Any]]:
        """
        대시보드 검색
        
        Args:
            query: 검색 쿼리
            tags: 태그 필터
            folder_ids: 폴더 ID 필터
            limit: 결과 제한
            
        Returns:
            대시보드 목록
        """
        params = {
            "type": "dash-db",
            "limit": limit
        }
        
        if query:
            params["query"] = query
        if tags:
            params["tag"] = tags
        if folder_ids:
            params["folderIds"] = folder_ids
        
        return self.request("GET", "/api/search", params=params)
    
    def get_dashboard_by_uid(self, uid: str) -> Dict[str, Any]:
        """
        UID로 대시보드 가져오기
        
        Args:
            uid: 대시보드 UID
            
        Returns:
            대시보드 데이터
        """
        return self.request("GET", f"/api/dashboards/uid/{uid}")
    
    def get_dashboard_screenshot(self, dashboard_uid: str, panel_id: Optional[int] = None, 
                               width: int = 1000, height: int = 500, 
                               from_time: Optional[str] = None, to_time: Optional[str] = None, 
                               theme: str = "light") -> bytes:
        """
        대시보드 또는 패널 스크린샷 가져오기
        
        Args:
            dashboard_uid: 대시보드 UID
            panel_id: 패널 ID (None인 경우 전체 대시보드)
            width: 이미지 너비
            height: 이미지 높이
            from_time: 시작 시간 (예: "now-6h")
            to_time: 종료 시간 (예: "now")
            theme: 테마 (light 또는 dark)
            
        Returns:
            스크린샷 이미지 바이너리 데이터
        """
        url = f"/api/dashboards/uid/{dashboard_uid}/panels"
        
        if panel_id is not None:
            url = f"{url}/{panel_id}/render"
        else:
            url = f"/render/d-solo/{dashboard_uid}"
            
        params = {
            "width": width,
            "height": height,
            "theme": theme
        }
        
        if from_time:
            params["from"] = from_time
        if to_time:
            params["to"] = to_time
            
        # 바이너리 응답을 직접 처리
        full_url = urljoin(self.base_url, url)
        
        try:
            response = self.http_client.request(
                method="GET",
                url=full_url,
                params=params
            )
            
            response.raise_for_status()
            return response.content
            
        except httpx.HTTPStatusError as e:
            logger.error(f"스크린샷 요청 오류: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"스크린샷 요청 중 오류 발생: {str(e)}")
            raise
    
    def update_dashboard(self, dashboard_model: Dict[str, Any], message: str = "Updated via MCP", 
                        folder_id: Optional[int] = None, overwrite: bool = False) -> Dict[str, Any]:
        """
        대시보드 업데이트 또는 생성
        
        Args:
            dashboard_model: 대시보드 모델
            message: 변경 메시지
            folder_id: 폴더 ID
            overwrite: 덮어쓰기 여부
            
        Returns:
            업데이트 결과
        """
        payload = {
            "dashboard": dashboard_model,
            "message": message,
            "overwrite": overwrite
        }
        
        if folder_id is not None:
            payload["folderId"] = folder_id
        
        return self.request("POST", "/api/dashboards/db", json_data=payload)

    # 데이터소스 관련 메서드
    def list_datasources(self) -> List[Dict[str, Any]]:
        """
        데이터소스 목록 조회
        
        Returns:
            데이터소스 목록
        """
        return self.request("GET", "/api/datasources")
    
    def get_datasource_by_uid(self, uid: str) -> Dict[str, Any]:
        """
        UID로 데이터소스 가져오기
        
        Args:
            uid: 데이터소스 UID
            
        Returns:
            데이터소스 데이터
        """
        return self.request("GET", f"/api/datasources/uid/{uid}")
    
    def get_datasource_by_name(self, name: str) -> Dict[str, Any]:
        """
        이름으로 데이터소스 가져오기
        
        Args:
            name: 데이터소스 이름
            
        Returns:
            데이터소스 데이터
        """
        return self.request("GET", f"/api/datasources/name/{name}") 