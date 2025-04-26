"""
대시보드 검색 도구
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from ..context import grafana_context
from ..server import GrafanaMCPServer
from .base import create_tool

class SearchDashboardsParams(BaseModel):
    """대시보드 검색 매개변수"""
    query: Optional[str] = Field(None, description="검색 쿼리 텍스트")
    tags: Optional[List[str]] = Field(None, description="필터링할 태그 목록")
    folder_ids: Optional[List[int]] = Field(None, description="필터링할 폴더 ID 목록")
    limit: int = Field(100, description="반환할 결과 수 제한 (기본값: 100)")

def search_dashboards(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    대시보드 검색 도구
    
    Arguments:
        params: 검색 매개변수
        
    Returns:
        검색된 대시보드 목록
    """
    client = grafana_context.client
    if not client:
        raise ValueError("Grafana client is not initialized")
    
    query = params.get("query")
    tags = params.get("tags")
    folder_ids = params.get("folder_ids")
    limit = params.get("limit", 100)
    
    results = client.search_dashboards(
        query=query,
        tags=tags,
        folder_ids=folder_ids,
        limit=limit
    )
    
    # 결과 정리 및 변환
    formatted_results = []
    for dash in results:
        formatted_results.append({
            "uid": dash.get("uid", ""),
            "title": dash.get("title", ""),
            "url": dash.get("url", ""),
            "type": dash.get("type", ""),
            "tags": dash.get("tags", []),
            "folder_title": dash.get("folderTitle", ""),
            "folder_uid": dash.get("folderUid", ""),
            "is_starred": dash.get("isStarred", False)
        })
    
    return formatted_results

def add_tools(server: GrafanaMCPServer):
    """서버에 검색 도구 추가"""
    search_tool = create_tool(
        name="search_dashboards",
        description="Grafana 대시보드 검색",
        handler=search_dashboards
    )
    
    server.add_tool(search_tool.to_mcp_tool(), search_tool.handle) 