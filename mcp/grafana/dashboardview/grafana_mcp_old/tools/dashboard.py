"""
대시보드 관련 도구
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import base64
from ..context import grafana_context
from ..server import GrafanaMCPServer
from .base import create_tool

class GetDashboardByUIDParams(BaseModel):
    """UID로 대시보드 가져오기 매개변수"""
    uid: str = Field(..., description="조회할 대시보드의 UID")

def get_dashboard_by_uid(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    UID로 대시보드 가져오기
    
    Arguments:
        params: 대시보드 UID 매개변수
        
    Returns:
        대시보드 데이터
    """
    client = grafana_context.client
    if not client:
        raise ValueError("Grafana client is not initialized")
    
    uid = params.get("uid")
    if not uid:
        raise ValueError("Dashboard UID is required")
    
    dashboard_data = client.get_dashboard_by_uid(uid)
    
    # 결과 정리 및 변환
    if "dashboard" in dashboard_data:
        dashboard = dashboard_data["dashboard"]
        meta = dashboard_data.get("meta", {})
        
        return {
            "dashboard": dashboard,
            "meta": {
                "uid": meta.get("uid", ""),
                "slug": meta.get("slug", ""),
                "url": meta.get("url", ""),
                "folder_id": meta.get("folderId", 0),
                "folder_title": meta.get("folderTitle", ""),
                "folder_url": meta.get("folderUrl", ""),
                "is_starred": meta.get("isStarred", False),
                "created_by": meta.get("createdBy", ""),
                "updated_by": meta.get("updatedBy", ""),
                "version": meta.get("version", 0)
            }
        }
    
    return dashboard_data

class DashboardScreenshotParams(BaseModel):
    """대시보드 스크린샷 매개변수"""
    dashboard_uid: str = Field(..., description="대시보드 UID")
    panel_id: Optional[int] = Field(None, description="패널 ID (없으면 전체 대시보드)")
    width: int = Field(1000, description="이미지 너비")
    height: int = Field(500, description="이미지 높이")
    from_time: Optional[str] = Field(None, description="시작 시간 (예: 'now-6h')")
    to_time: Optional[str] = Field(None, description="종료 시간 (예: 'now')")
    theme: str = Field("light", description="테마 (light 또는 dark)")

def get_dashboard_screenshot(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    대시보드 스크린샷 가져오기
    
    Arguments:
        params: 스크린샷 매개변수
        
    Returns:
        Base64로 인코딩된 이미지 데이터
    """
    client = grafana_context.client
    if not client:
        raise ValueError("Grafana client is not initialized")
    
    dashboard_uid = params.get("dashboard_uid")
    if not dashboard_uid:
        raise ValueError("Dashboard UID is required")
    
    # 선택적 매개변수
    panel_id = params.get("panel_id")
    width = params.get("width", 1000)
    height = params.get("height", 500)
    from_time = params.get("from_time")
    to_time = params.get("to_time")
    theme = params.get("theme", "light")
    
    # 스크린샷 요청
    image_data = client.get_dashboard_screenshot(
        dashboard_uid=dashboard_uid,
        panel_id=panel_id,
        width=width,
        height=height,
        from_time=from_time,
        to_time=to_time,
        theme=theme
    )
    
    # 바이너리 이미지를 Base64로 인코딩
    encoded_image = base64.b64encode(image_data).decode("utf-8")
    
    # 이미지 타입 추정 (Grafana는 보통 PNG 반환)
    image_type = "image/png"
    
    return {
        "image_data": encoded_image,
        "image_type": image_type,
        "dashboard_uid": dashboard_uid,
        "panel_id": panel_id,
        "width": width,
        "height": height
    }

def add_tools(server: GrafanaMCPServer):
    """서버에 대시보드 관련 도구 추가"""
    # UID로 대시보드 가져오기 도구
    get_dashboard_tool = create_tool(
        name="get_dashboard_by_uid",
        description="UID로 Grafana 대시보드 조회",
        handler=get_dashboard_by_uid
    )
    
    # 대시보드 스크린샷 도구
    get_screenshot_tool = create_tool(
        name="get_dashboard_screenshot",
        description="Grafana 대시보드 또는 패널의 스크린샷 캡처",
        handler=get_dashboard_screenshot
    )
    
    # 도구 등록
    server.add_tool(get_dashboard_tool.to_mcp_tool(), get_dashboard_tool.handle)
    server.add_tool(get_screenshot_tool.to_mcp_tool(), get_screenshot_tool.handle) 