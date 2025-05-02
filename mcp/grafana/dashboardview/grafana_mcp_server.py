from mcp.server.fastmcp import FastMCP
import logging
from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime
import time
import random
import requests
import base64
import os

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
logger.info(f"Grafana URL: {GRAFANA_URL}")

# FastMCP 서버 생성
mcp = FastMCP("ChatServer")

@mcp.tool()
def get_status() -> Dict[str, Any]:
    """서버 상태 정보를 반환합니다.
    
    Returns:
        서버 상태 정보 (상태, 버전, 가동 시간)
    """
    logger.info("get_status 도구 호출")
    return {
        "status": "online",
        "version": "0.1.0",
        "uptime": int(time.time() - start_time),
        "grafana_url": GRAFANA_URL
    }


@mcp.tool()
def get_sample_png(message: str) -> Dict[str, Any]:
    """대시보드 스크린샷을 반환합니다."""
    
    logger.info(f"get_sample_png 도구 호출: 메시지={message}")
    
    # Grafana 렌더링 URL 구성 (환경 변수에서 가져온 URL 사용)
    url = f"{GRAFANA_URL}/render/d-solo/spring_boot_21/spring-boot-3-x-statistics"
    params = {
        "orgId": "1",
        "from": "now-1h",
        "to": "now",
        "panelId": "42",
        "var-application": "target-api",
        "var-instance": "target-api:8080",
        "width": "800",
        "height": "400"
    }
    
    headers = {
        "Authorization": f"Bearer <GRAFANA_API_KEY"
    }
    
    try:
        # Grafana에 HTTP 요청
        logger.info(f"Grafana 요청 전송: {url}")
        response = requests.get(url, params=params, headers=headers)
        
        # 응답 확인
        if response.status_code == 200:
            # PNG 데이터를 Base64로 인코딩
            png_base64 = base64.b64encode(response.content).decode('utf-8')
            
            return {
                "status": "success",
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "content_type": "image/png",
                "data": png_base64,
                "encoding": "base64"
            }
        else:
            logger.error(f"Grafana 요청 실패: HTTP {response.status_code}, {response.text}")
            return {
                "status": "error",
                "message": f"Grafana 요청 실패: HTTP {response.status_code}",
                "error_details": response.text
            }
    
    except Exception as e:
        logger.error(f"대시보드 PNG 가져오기 오류: {str(e)}")
        return {
            "status": "error",
            "message": f"대시보드 PNG 가져오기 오류: {str(e)}"
        }

@mcp.tool()
def send_message(message: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
    """채팅 메시지를 전송하고 응답을 받습니다.
    
    Args:
        message: 사용자 메시지
        thread_id: 대화 스레드 ID (없으면 새로 생성)
        
    Returns:
        응답 메시지와 스레드 ID
    """
    logger.info(f"send_message 도구 호출: 메시지='{message}', 스레드={thread_id}")
    
    # 스레드 ID가 없으면 새로 생성
    thread_id = thread_id or str(uuid.uuid4())
    
    # 스레드 정보 저장/업데이트
    if thread_id not in threads:
        threads[thread_id] = {
            "created_at": datetime.now().isoformat(),
            "metadata": {}
        }
    
    # 메시지 ID 생성 및 저장
    message_id = str(uuid.uuid4())
    message_obj = {
        "id": message_id,
        "role": "user",
        "content": message,
        "created_at": datetime.now().isoformat()
    }
    
    if thread_id not in messages:
        messages[thread_id] = []
    
    messages[thread_id].append(message_obj)
    
    # 응답 생성 (실제로는 LLM을 호출할 것)
    response_options = [
        "안녕하세요! 무엇을 도와드릴까요?",
        "좋은 질문이네요. 더 자세히 알려주시겠어요?",
        "흥미로운 주제입니다. 어떤 측면에 관심이 있으신가요?",
        "도움이 필요하시면 언제든지 물어보세요!",
        f"'{message}'에 대한 답변을 준비 중입니다..."
    ]
    
    response_content = random.choice(response_options)
    
    # 응답 저장
    response_obj = {
        "id": str(uuid.uuid4()),
        "role": "assistant",
        "content": response_content,
        "created_at": datetime.now().isoformat()
    }
    
    messages[thread_id].append(response_obj)
    
    return {
        "content": response_content,
        "thread_id": thread_id
    }

@mcp.tool()
def list_threads() -> Dict[str, List[Dict[str, Any]]]:
    """모든 스레드 목록을 조회합니다.
    
    Returns:
        모든 스레드 목록
    """
    logger.info("list_threads 도구 호출")
    return {"threads": [{"thread_id": tid, **info} for tid, info in threads.items()]}

@mcp.tool()
def create_thread(metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """새 스레드를 생성합니다.
    
    Args:
        metadata: 스레드 메타데이터(선택 사항)
        
    Returns:
        생성된 스레드 정보
    """
    logger.info(f"create_thread 도구 호출: 메타데이터={metadata}")
    
    thread_id = str(uuid.uuid4())
    threads[thread_id] = {
        "created_at": datetime.now().isoformat(),
        "metadata": metadata or {}
    }
    messages[thread_id] = []
    
    return {
        "thread_id": thread_id,
        "created_at": threads[thread_id]["created_at"],
        "metadata": threads[thread_id]["metadata"]
    }

@mcp.tool()
def get_thread_messages(thread_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """특정 스레드의 메시지를 조회합니다.
    
    Args:
        thread_id: 스레드 ID
        
    Returns:
        해당 스레드의 메시지 목록
    """
    logger.info(f"get_thread_messages 도구 호출: 스레드={thread_id}")
    
    if thread_id not in threads:
        return {"error": "스레드를 찾을 수 없습니다", "messages": []}
    
    return {"messages": messages.get(thread_id, [])}

@mcp.tool()
def execute_tool(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """도구를 실행합니다.
    
    Args:
        tool_name: 실행할 도구 이름
        parameters: 도구 파라미터
        
    Returns:
        도구 실행 결과
    """
    logger.info(f"execute_tool 도구 호출: 도구={tool_name}, 파라미터={parameters}")
    
    # 실제 도구 실행 로직은 구현 예정
    return {
        "result": f"도구 '{tool_name}'가 파라미터 {parameters}로 실행되었습니다 (더미 응답)",
        "status": "success"
    }

if __name__ == "__main__":
    # HTTP 모드로 서버 실행 (포트 8000)
    logger.info("MCP HTTP 서버 시작...")
    try:
        # mcp.run 메서드는 'transport'만 인식하고 'port'를 직접 인자로 받지 않음
        # 대신 'stdio' 또는 'sse' 전송 방식을 선택하고, 
        # 'sse'의 경우에는 FastAPI/Uvicorn이 내부적으로 실행됨
        # 참조: https://github.com/jlowin/fastmcp
        mcp.run(transport="sse")
        
    except KeyboardInterrupt:
        logger.info("서버가 중지되었습니다.")
    except Exception as e:
        logger.error(f"서버 오류: {str(e)}") 