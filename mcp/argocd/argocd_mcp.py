#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ArgoCD MCP 서버
애플리케이션 목록 조회, 애플리케이션 배포 등의 기능을 제공합니다.
"""

import os
import random
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# 환경 변수 로드
load_dotenv()
ARGOCD_MCP_NAME = os.environ.get("ARGOCD_MCP_NAME", "argocd")
ARGOCD_MCP_HOST = os.environ.get("ARGOCD_MCP_HOST", "0.0.0.0")
ARGOCD_MCP_PORT = int(os.environ.get("ARGOCD_MCP_PORT", 10002))
ARGOCD_MCP_INSTRUCTIONS = os.environ.get("ARGOCD_MCP_INSTRUCTIONS", 
    "ArgoCD 배포 도구를 제어하는 서버입니다. 애플리케이션 목록 조회, 애플리케이션 배포 기능을 제공합니다.")

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("argocd_mcp_server")

# MCP 서버 인스턴스 생성
mcp = FastMCP(
    ARGOCD_MCP_NAME,  # MCP 서버 이름
    instructions=ARGOCD_MCP_INSTRUCTIONS,
    host=ARGOCD_MCP_HOST,
    port=ARGOCD_MCP_PORT,
)

# 시뮬레이션에 사용할 ArgoCD 애플리케이션 데이터
argocd_applications = [
    {"name": "user-service", "status": "Healthy"},
    {"name": "restaurant-service", "status": "Healthy"},
    {"name": "order-service", "status": "Healthy"},
    {"name": "payment-service", "status": "Healthy"},
    {"name": "delivery-service", "status": "Healthy"},
    {"name": "notification-service", "status": "Healthy"}
]

@mcp.tool()
async def list_argocd_applications() -> Dict[str, Any]:
    """
    ArgoCD 애플리케이션 목록을 조회합니다.
    현재 배포된 모든 마이크로서비스 목록과 상태를 반환합니다.
    
    Args:
        없음
        
    Returns:
        Dict[str, Any]: 애플리케이션 목록과 상태 정보
        
    예시 요청:
        list_argocd_applications()
        
    예시 응답:
        {
            "success": true,
            "applications": [
                {
                    "name": "user-service",
                    "status": "Healthy",
                    "namespace": "default",
                    "cluster": "in-cluster",
                    "sync_status": "Synced"
                },
                ...
            ]
        }
    """
    logger.info("애플리케이션 목록 조회 요청 수신")
    
    response_apps = []
    
    for app in argocd_applications:
        response_apps.append({
            "name": app["name"],
            "status": app["status"],
            "namespace": "default",
            "cluster": "in-cluster",
            "sync_status": "Synced" if app["status"] == "Healthy" else "OutOfSync"
        })
    
    return {
        "success": True,
        "applications": response_apps
    }

@mcp.tool()
async def deploy_application(app_name: str) -> Dict[str, Any]:
    """
    ArgoCD를 통해 특정 애플리케이션을 배포합니다.
    
    Args:
        app_name (str): 배포할 애플리케이션 이름
        
    Returns:
        Dict[str, Any]: 배포 결과 정보
        
    예시 요청:
        deploy_application(app_name="user-service")
        
    예시 응답:
        {
            "success": true,
            "message": "애플리케이션 user-service 배포를 시작했습니다.",
            "application": {
                "name": "user-service",
                "previous_status": "Healthy",
                "current_status": "Progressing",
                "deployment_started": true
            }
        }
        
    오류 응답:
        {
            "error": "애플리케이션 'unknown-app'을(를) 찾을 수 없습니다."
        }
    """
    logger.info(f"애플리케이션 배포 요청: 앱={app_name}")
    
    found_app = None
    
    for app in argocd_applications:
        if app["name"].lower() == app_name.lower():
            found_app = app
            break
    
    if not found_app:
        logger.error(f"애플리케이션 '{app_name}'을(를) 찾을 수 없습니다.")
        return {"error": f"애플리케이션 '{app_name}'을(를) 찾을 수 없습니다."}
    
    # 배포 진행 상황 시뮬레이션
    logger.info(f"애플리케이션 {app_name}를 배포 중입니다...")
    
    # 배포 시작 응답
    deploy_result = {
        "success": True,
        "message": f"애플리케이션 {app_name} 배포를 시작했습니다.",
        "application": {
            "name": app_name,
            "previous_status": found_app["status"],
            "current_status": "Progressing",
            "deployment_started": True
        }
    }
    
    # 실제로는 배포가 완료되지만, 시뮬레이션 상에서는 Progressing 상태를 반환
    # (실제 환경에서는 비동기로 처리하며, 상태 확인은 별도 API 호출을 통해 이루어짐)
    
    return deploy_result

# 배포 상태 확인 도구 추가
@mcp.tool()
async def check_deployment_status(app_name: str) -> Dict[str, Any]:
    """
    배포 중인 애플리케이션의 현재 상태를 확인합니다.
    
    Args:
        app_name (str): 상태를 확인할 애플리케이션 이름
        
    Returns:
        Dict[str, Any]: 애플리케이션 배포 상태 정보
        
    예시 요청:
        check_deployment_status(app_name="user-service")
        
    예시 응답:
        {
            "success": true,
            "application": {
                "name": "user-service",
                "status": "Healthy",
                "health_status": "Healthy",
                "sync_status": "Synced",
                "message": "애플리케이션이 성공적으로 배포되었습니다"
            }
        }
        
    오류 응답:
        {
            "error": "애플리케이션 'unknown-app'을(를) 찾을 수 없습니다."
        }
    """
    logger.info(f"배포 상태 확인 요청: 앱={app_name}")
    
    found_app = None
    
    for app in argocd_applications:
        if app["name"].lower() == app_name.lower():
            found_app = app
            break
    
    if not found_app:
        logger.error(f"애플리케이션 '{app_name}'을(를) 찾을 수 없습니다.")
        return {"error": f"애플리케이션 '{app_name}'을(를) 찾을 수 없습니다."}
    
    # 실제 환경에서는 배포 상태를 확인하지만, 여기서는 랜덤으로 성공/진행 중 상태를 반환
    status_options = ["Progressing", "Healthy"]
    deployment_status = status_options[random.randint(0, len(status_options)-1)]
    
    # 80%의 확률로 Healthy 상태 반환 (배포 성공)
    if random.random() < 0.8:
        deployment_status = "Healthy"
    
    return {
        "success": True,
        "application": {
            "name": app_name,
            "status": deployment_status,
            "health_status": deployment_status,
            "sync_status": "Synced" if deployment_status == "Healthy" else "Progressing",
            "message": f"애플리케이션이 {'성공적으로 배포되었습니다' if deployment_status == 'Healthy' else '아직 배포 중입니다'}"
        }
    }

if __name__ == "__main__":
    # 서버 시작 메시지 출력
    print(f"ArgoCD MCP 서버가 실행 중입니다... (포트: {ARGOCD_MCP_PORT})")
    
    # SSE 트랜스포트를 사용하여 MCP 서버 시작
    mcp.run(transport="sse") 