import streamlit as st
import os
import uuid
import asyncio
import logging
import traceback
import nest_asyncio
import platform
import requests
import json
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# Windows 환경 특별 처리
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# nest_asyncio 적용 - 중첩된 이벤트 루프 허용
nest_asyncio.apply()

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 백엔드 API URL 설정
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")

# 페이지 설정
st.set_page_config(
    page_title="슬라임 챗봇",
    page_icon="🤖",
    layout="centered"
)

# 글로벌 이벤트 루프 생성 및 재사용
if "event_loop" not in st.session_state:
    loop = asyncio.new_event_loop()
    st.session_state.event_loop = loop
    asyncio.set_event_loop(loop)

# CSS 추가
st.markdown("""
<style>
    .stChatMessage {
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# 페이지 제목 설정
st.title("슬라임 챗봇")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

# 타임아웃 설정
if "timeout_seconds" not in st.session_state:
    st.session_state.timeout_seconds = 60  # 기본 타임아웃 60초

# 사이드바 설정
with st.sidebar:
    st.header("설정")
    
    # MCP 서버 설정
    st.subheader("MCP 서버 설정")
    
    # 서버 URL 입력
    mcp_server_url = st.text_input(
        "MCP 서버 URL",
        value="http://localhost:8000/sse",
        help="MCP 서버 URL을 입력하세요"
    )
    
    # 클라이언트 이름 입력
    mcp_client_name = st.text_input(
        "MCP 클라이언트 이름",
        value="mcp-server-test",
        help="MCP 클라이언트 이름을 입력하세요"
    )
    
    # 전송 방식 선택
    mcp_transport = st.selectbox(
        "전송 방식",
        options=["sse", "websocket"],
        index=0,
        help="MCP 서버 전송 방식을 선택하세요"
    )
    
    # 백엔드 API URL 입력
    backend_api_url = st.text_input(
        "백엔드 API URL",
        value=BACKEND_API_URL,
        help="백엔드 API URL을 입력하세요"
    )
    
    # Gemini 모델 선택
    model_options = {
        "gemini-2.0-flash": "Gemini 2.0 Flash"
    }
    selected_model = st.selectbox(
        "Gemini 모델",
        options=list(model_options.keys()),
        format_func=lambda x: model_options[x],
        index=0,
        help="사용할 Gemini 모델을 선택하세요"
    )
    
    # 타임아웃 설정
    st.session_state.timeout_seconds = st.slider(
        "응답 시간 제한(초)",
        min_value=30,
        max_value=180,
        value=st.session_state.timeout_seconds,
        step=10,
        help="에이전트 응답 생성 시간 제한"
    )

# 서버 상태 확인 버튼
with st.sidebar:
    st.subheader("서버 연결 테스트")
    if st.button("MCP 서버 연결 테스트"):
        try:
            # 백엔드 API로 연결 테스트 요청
            response = requests.post(
                f"{backend_api_url}/api/connection_test",
                json={
                    "mcp_client_name": mcp_client_name,
                    "mcp_server_url": mcp_server_url,
                    "mcp_transport": mcp_transport
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                if result["status"] == "success":
                    st.success(result["message"])
                    st.session_state.mcp_connected = True
                else:
                    st.error(result["message"])
                    st.session_state.mcp_connected = False
            else:
                st.error(f"백엔드 API 오류: {response.status_code} - {response.text}")
                st.session_state.mcp_connected = False
                
        except Exception as e:
            st.error(f"MCP 서버 연결 테스트 오류: {str(e)}")
            st.session_state.mcp_connected = False
    
    # 대화 초기화 버튼
    if st.button("대화 초기화"):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.experimental_rerun()

# 대화 이력 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        # 텍스트 메시지 표시
        if "type" not in message or message["type"] == "text":
            st.markdown(message["content"])
        # 이미지 메시지 표시
        elif message["type"] == "image":
            if "text" in message:
                st.markdown(message["text"])
            st.image(message["content"], caption=message.get("caption", ""), use_column_width=True)

# 응답에서 텍스트와 이미지 추출 함수
def process_response(response):
    """MCP 응답에서 텍스트와 이미지 추출
    
    Args:
        response: MCP 에이전트 응답
    
    Returns:
        dict: 텍스트 내용과 이미지 데이터 포함
    """
    results = []
    
    # 문자열인 경우 그대로 반환
    if isinstance(response, str):
        return {"type": "text", "content": response}
    
    # 딕셔너리 형태로 응답이 온 경우
    if isinstance(response, dict):
        # AIMessage가 포함된 메시지 배열 처리
        if "messages" in response:
            for msg in response["messages"]:
                # AIMessage 객체 처리
                if hasattr(msg, "__class__") and msg.__class__.__name__ == "AIMessage":
                    # 텍스트 내용 추출
                    if hasattr(msg, "content") and msg.content:
                        results.append({"type": "text", "content": msg.content})
                    
                    # 이미지 추출 (tool_outputs에서 base64 이미지 찾기)
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            if "content_type" in tool_call.get("args", {}) and "image" in tool_call["args"]["content_type"]:
                                if "data" in tool_call["args"]:
                                    results.append({
                                        "type": "image",
                                        "content": tool_call["args"]["data"],
                                        "caption": tool_call["args"].get("message", "")
                                    })
                
                # ToolMessage 객체 처리
                elif hasattr(msg, "__class__") and msg.__class__.__name__ == "ToolMessage":
                    if hasattr(msg, "content") and msg.content:
                        try:
                            tool_content = json.loads(msg.content)
                            if "content_type" in tool_content and "image" in tool_content["content_type"]:
                                if "data" in tool_content:
                                    results.append({
                                        "type": "image",
                                        "content": tool_content["data"],
                                        "caption": tool_content.get("message", "")
                                    })
                            else:
                                results.append({"type": "text", "content": msg.content})
                        except:
                            results.append({"type": "text", "content": msg.content})
        
        # content 키가 있는 경우 (단일 메시지)
        elif "content" in response:
            results.append({"type": "text", "content": response["content"]})
    
    # 결과가 없으면 기본 텍스트 반환
    if not results:
        return {"type": "text", "content": str(response)}
    
    # 결과가 하나면 그대로 반환
    if len(results) == 1:
        return results[0]
    
    # 여러 결과가 있으면 첫 번째 반환
    return results[0]

# 사용자 인풋 처리
if query := st.chat_input("메시지를 입력하세요..."):
    # 사용자 메시지 표시
    with st.chat_message("user"):
        st.markdown(query)
    
    # 사용자 메시지 저장
    st.session_state.messages.append({"role": "user", "content": query})
    
    # 응답 생성 중 표시
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("답변을 생성하는 중입니다...")
    
    try:
        # 백엔드 API 호출
        response = requests.post(
            f"{backend_api_url}/api/chat",
            json={
                "query": query,
                "thread_id": st.session_state.thread_id,
                "history": st.session_state.messages,
                "mcp_client_name": mcp_client_name,
                "mcp_server_url": mcp_server_url,
                "mcp_transport": mcp_transport,
                "timeout_seconds": st.session_state.timeout_seconds
            },
            timeout=st.session_state.timeout_seconds + 10  # API 타임아웃은 챗봇 타임아웃보다 조금 더 크게
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if result["status"] == "success":
                # 응답 처리
                ai_response = process_response(result["response"])
                
                # 응답 표시
                with st.chat_message("assistant"):
                    message_placeholder.empty()
                    
                    # 텍스트 메시지
                    if ai_response["type"] == "text":
                        st.markdown(ai_response["content"])
                    # 이미지 메시지
                    elif ai_response["type"] == "image":
                        if "caption" in ai_response and ai_response["caption"]:
                            st.markdown(ai_response["caption"])
                        st.image(ai_response["content"], use_column_width=True)
                
                # 응답 저장
                st.session_state.messages.append({"role": "assistant", **ai_response})
            else:
                # 오류 또는 타임아웃 응답
                message_placeholder.error(result["response"])
                st.session_state.messages.append({"role": "assistant", "type": "text", "content": result["response"]})
        else:
            # API 오류
            error_msg = f"백엔드 API 오류: {response.status_code} - {response.text}"
            message_placeholder.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "type": "text", "content": error_msg})
            
    except Exception as e:
        # 예외 처리
        error_msg = f"오류가 발생했습니다: {str(e)}"
        message_placeholder.error(error_msg)
        st.session_state.messages.append({"role": "assistant", "type": "text", "content": error_msg})
        logger.error(traceback.format_exc()) 