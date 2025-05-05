import streamlit as st
import os
import uuid
import requests
import json
import base64
import logging
from io import BytesIO
from datetime import datetime

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 환경 변수에서 API URL 가져오기 (기본값 설정)
API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8080/api")

# 페이지 설정
st.set_page_config(
    page_title="슬라임 챗봇",
    page_icon="🤖",
    layout="centered"
)

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

if "session_id" not in st.session_state:
    # 새 세션 생성 API 호출
    try:
        response = requests.post(f"{API_BASE_URL}/chat/sessions")
        if response.status_code == 200:
            session_data = response.json()
            st.session_state.session_id = session_data["session_id"]
        else:
            # API 호출 실패 시 임시 UUID 생성
            st.session_state.session_id = str(uuid.uuid4())
            st.warning("백엔드 연결에 실패했습니다. 오프라인 모드로 시작합니다.")
    except Exception as e:
        # 네트워크 오류 등의 예외 처리
        st.session_state.session_id = str(uuid.uuid4())
        st.warning(f"백엔드 연결 중 오류 발생: {str(e)}. 오프라인 모드로 시작합니다.")

# 타임아웃 설정
if "timeout_seconds" not in st.session_state:
    st.session_state.timeout_seconds = 60  # 기본 타임아웃 60초

# 사이드바 설정
with st.sidebar:
    st.header("설정")
    
    # 백엔드 API 설정
    st.subheader("백엔드 API 설정")
    
    # 서버 URL 입력
    api_base_url = st.text_input(
        "백엔드 API URL",
        value=API_BASE_URL,
        help="백엔드 API URL을 입력하세요"
    )
    
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
    
    # 모델 선택 (API에서 가져오기)
    st.subheader("모델 설정")
    
    try:
        # 사용 가능한 모델 목록 API 호출
        response = requests.get(f"{api_base_url}/models")
        if response.status_code == 200:
            models_data = response.json()
            model_options = {m["id"]: m["name"] for m in models_data["models"]}
        else:
            # API 호출 실패 시 기본 모델 설정
            model_options = {"gemini-2.0-flash": "Gemini 2.0 Flash"}
    except Exception:
        # 네트워크 오류 등의 예외 처리
        model_options = {"gemini-2.0-flash": "Gemini 2.0 Flash"}
    
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

# MCP 서버 연결 저장 및 테스트
with st.sidebar:
    st.subheader("서버 연결 설정")
    
    if st.button("MCP 서버 설정 저장"):
        try:
            # MCP 서버 설정 저장 API 호출
            settings_data = {
                "client_name": mcp_client_name,
                "url": mcp_server_url,
                "transport": mcp_transport
            }
            response = requests.post(f"{api_base_url}/mcp/settings", json=settings_data)
            
            if response.status_code == 200:
                st.success("MCP 서버 설정이 저장되었습니다.")
            else:
                st.error(f"MCP 서버 설정 저장 실패: {response.status_code}")
        except Exception as e:
            st.error(f"MCP 서버 설정 저장 중 오류 발생: {str(e)}")
    
    if st.button("MCP 서버 연결 테스트"):
        try:
            # MCP 서버 연결 테스트 API 호출
            connection_data = {
                "client_name": mcp_client_name,
                "url": mcp_server_url,
                "transport": mcp_transport
            }
            response = requests.post(f"{api_base_url}/mcp/connection/test", json=connection_data)
            
            if response.status_code == 200:
                result = response.json()
                if result["status"] == "success":
                    st.success(f"MCP 서버 연결 성공: {result['message']}")
                else:
                    st.error(f"MCP 서버 연결 실패: {result['message']}")
            else:
                st.error(f"MCP 서버 연결 테스트 실패: {response.status_code}")
        except Exception as e:
            st.error(f"MCP 서버 연결 테스트 중 오류 발생: {str(e)}")
    
    # 대화 초기화 버튼
    if st.button("대화 초기화"):
        # 세션 삭제 API 호출
        try:
            requests.delete(f"{api_base_url}/chat/sessions/{st.session_state.session_id}")
        except Exception:
            pass  # 오류 무시
        
        # 새 세션 생성
        try:
            response = requests.post(f"{api_base_url}/chat/sessions")
            if response.status_code == 200:
                session_data = response.json()
                st.session_state.session_id = session_data["session_id"]
            else:
                st.session_state.session_id = str(uuid.uuid4())
        except Exception:
            st.session_state.session_id = str(uuid.uuid4())
        
        st.session_state.messages = []
        st.experimental_rerun()

# 서버에서 대화 기록 불러오기 (초기화 시)
if not st.session_state.messages:
    try:
        response = requests.get(f"{api_base_url}/chat/sessions/{st.session_state.session_id}/messages")
        if response.status_code == 200:
            data = response.json()
            st.session_state.messages = data["messages"]
    except Exception:
        pass  # 에러 발생 시 무시 (로컬 상태 유지)

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
            try:
                image_data = base64.b64decode(message["content"])
                st.image(BytesIO(image_data), caption=message.get("caption", ""), use_column_width=True)
            except Exception as e:
                st.error(f"이미지 표시 오류: {str(e)}")

# 메시지 전송 함수
def send_message(session_id, prompt):
    """메시지를 전송하는 함수"""
    try:
        # 메시지 전송 API 호출
        data = {
            "content": prompt,
            "model_config": {
                "model": selected_model,
                "timeout_seconds": st.session_state.timeout_seconds
            }
        }
        
        with st.spinner("응답을 생성하는 중..."):
            response = requests.post(f"{api_base_url}/chat/sessions/{session_id}/messages", json=data)
        
        if response.status_code == 200:
            response_data = response.json()
            
            # 응답 데이터 로깅
            logger.info(f"백엔드 응답: {json.dumps(response_data, ensure_ascii=False)}...")
            logger.info(f"응답 타입: {type(response_data)}, 배열인 경우 길이: {len(response_data) if isinstance(response_data, dict) else 'N/A'}")
            
            # 응답이 배열인지 단일 메시지인지 확인
            if isinstance(response_data, list):
                logger.info(f"응답 데이터: {response_data}")
                # 배열 응답 처리 (여러 메시지)
                logger.info(f"여러 메시지 처리: {len(response_data)}개 메시지")
                for i, message_data in enumerate(response_data):
                    logger.info(f"메시지 {i+1}/{len(response_data)} 처리: {message_data.get('type', 'text')}")
                    process_message(message_data)
            else:
                # 단일 메시지 처리
                logger.info(f"단일 메시지 처리: {response_data.get('type', 'text')}")
                process_message(response_data)
            
            return True
        else:
            # API 오류 응답 처리
            error_message = f"응답 처리 중 오류가 발생했습니다: {response.status_code}"
            logger.error(f"백엔드 오류 응답: {response.status_code}, {response.text if hasattr(response, 'text') else ''}")
            with st.chat_message("assistant"):
                st.error(error_message)
            
            st.session_state.messages.append({
                "role": "assistant",
                "type": "text",
                "content": error_message
            })
            return False
    
    except Exception as e:
        # 예외 처리
        error_message = f"메시지 전송 중 오류가 발생했습니다: {str(e)}"
        logger.exception(f"메시지 전송 예외: {str(e)}")
        with st.chat_message("assistant"):
            st.error(error_message)
        
        st.session_state.messages.append({
            "role": "assistant",
            "type": "text",
            "content": error_message
        })
        return False

def process_message(message_data):
    """개별 메시지를 처리하고 화면에 표시하는 함수"""
    # 메시지 내용 로깅
    message_type = message_data.get("type", "text")
    if message_type == "text":
        logger.info(f"텍스트 메시지 표시: {message_data.get('content', '')[:200]}...")
    elif message_type == "image":
        logger.info(f"이미지 메시지 표시: {message_data.get('caption', '이미지')}")
    
    # 응답 메시지 추가
    if "type" in message_data and message_data["type"] == "image":
        # 이미지 응답 처리
        with st.chat_message("assistant"):
            try:
                image_data = base64.b64decode(message_data["content"])
                st.image(BytesIO(image_data), caption=message_data.get("caption", ""), use_column_width=True)
            except Exception as e:
                logger.error(f"이미지 디코딩 오류: {str(e)}")
                st.error(f"이미지 표시 오류: {str(e)}")
    else:
        # 텍스트 응답 처리
        with st.chat_message("assistant"):
            st.markdown(message_data["content"])
    
    # 세션 상태 업데이트
    message_data["role"] = "assistant" if "role" not in message_data else message_data["role"]
    st.session_state.messages.append(message_data)

# 사용자 입력 처리
if prompt := st.chat_input("무엇이든 물어보세요"):
    # 사용자 메시지 추가 및 표시
    user_message = {"role": "user", "type": "text", "content": prompt}
    st.session_state.messages.append(user_message)
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # 메시지 전송
    send_message(st.session_state.session_id, prompt) 