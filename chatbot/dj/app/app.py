import streamlit as st
import requests
import json
import uuid
import asyncio
import os
from schema.state import SessionState, Response
from utils.logger_config import setup_logger
from config import *  # Import all constants and configuration values

logger = setup_logger(__name__, level=LOG_LEVEL)

# MCP 도구 설정 파일 경로
MCP_CONFIG_FILE_PATH = "mcp_tools_config.json"


def load_config_from_json():
    """
    JSON 파일에서 MCP 도구 설정을 로드합니다.
    파일이 없으면 기본 설정으로 파일을 생성합니다.

    Returns:
        dict: 로드된 설정
    """
    default_config = {
        "markdown_processor": {
            "command": "python",
            "args": ["./mcp_server_markdown.py"],
            "transport": "stdio"
        }
    }
    
    try:
        if os.path.exists(MCP_CONFIG_FILE_PATH):
            with open(MCP_CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            # 파일이 없으면 기본 설정으로 생성
            save_config_to_json(default_config)
            return default_config
    except Exception as e:
        logger.error(f"설정 파일 로드 오류: {str(e)}")
        return default_config


def save_config_to_json(config):
    """
    설정을 JSON 파일에 저장합니다.

    Args:
        config (dict): 저장할 설정

    Returns:
        bool: 저장 성공 여부
    """
    try:
        with open(MCP_CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"설정 파일 저장 오류: {str(e)}")
        return False


def generate_session_id():
    return str(uuid.uuid4())


def initialize():
    if 'session_id' not in st.session_state:
        st.session_state.session_id = generate_session_id()

    if SessionState.MESSAGES.value not in st.session_state:
        st.session_state.messages = []
        
    # 도구 캐시 초기화
    if "mcp_tools_cache" not in st.session_state:
        st.session_state.mcp_tools_cache = {}
        
    # 활성화된 메인 탭 상태 초기화
    if "active_main_tab" not in st.session_state:
        st.session_state.active_main_tab = 0
        
    # 채팅 입력 처리를 위한 상태 변수
    if "current_chat_input" not in st.session_state:
        st.session_state.current_chat_input = ""
    
    # MCP 도구 설정 초기화
    if "mcp_config" not in st.session_state:
        st.session_state.mcp_config = load_config_from_json()


def get_chat_response(message, session_id=None):
    url = f"{CHATBOT_API_URL}{CHAT_ENDPOINT}"
    headers = {"Content-Type": "application/json"}
    
    data = {'message': message}

    if session_id:
        data['session_id'] = session_id

    try:
        logger.debug(f"Sending request to {url} with data: {data}")
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_msg = ERROR_SERVER_CONNECTION.format(e)
        logger.error(error_msg)
        st.error(error_msg)
        return None
    except json.JSONDecodeError as e:
        error_msg = ERROR_JSON_DECODE.format(e)
        logger.error(error_msg)
        st.error(error_msg)
        return None


def render_sidebar():
    with st.sidebar:
        st.header("Session Management")
        
        
        # 현재 세션 ID 표시
        current_session = (
            st.session_state.session_id
            if st.session_state.session_id
            else SESSION_NONE
        )
        st.info(SESSION_CURRENT.format(current_session))
        
        # New Session 버튼
        if st.button("New Session", use_container_width=True):
            new_session_id = generate_session_id()
            st.session_state.session_id = new_session_id
            st.session_state.messages = []
            st.success(SESSION_NEW.format(new_session_id))
            st.rerun()
        
        # 구분선 추가
        st.divider()
            
        # 탭 구성: LLM과 MCP
        llm_tab, mcp_tab = st.tabs(["LLM", "MCP"])

        # LLM 탭 - 단순하게 환경 변수에서 모델 이름만 표시
        with llm_tab:
            # 환경 변수에서 모델 정보 표시
            model_name = os.environ.get("LLM_MODEL_NAME", "default-model")
            st.info(f"Current Model: {model_name}")
            
        # MCP 탭 - 도구 목록 및 새로고침 기능
        with mcp_tab:
            if st.button("🔄 Refresh Tools", use_container_width=True, type="primary"):
                st.session_state.mcp_config = load_config_from_json()
                st.session_state.mcp_tools_cache = st.session_state.mcp_config
                st.toast("Tools refreshed!", icon="🔄")
                st.rerun()
                
            # 도구 목록 표시
            tools = st.session_state.mcp_config
            
            # 등록된 도구 출력 (각 항목을 클릭하면 삭제 버튼 표시)
            for client_name, client_config in tools.items():
                with st.expander(f"Client: {client_name}", expanded=False):
                    st.json(client_config)
                    if st.button(f"🗑️ 삭제", key=f"delete_{client_name}"):
                        # 도구 삭제 처리
                        current_config = st.session_state.mcp_config.copy()
                        if client_name in current_config:
                            del current_config[client_name]
                            if save_config_to_json(current_config):
                                st.session_state.mcp_config = current_config
                                st.toast(f"{client_name} 도구가 삭제되었습니다.", icon="✅")
                                st.rerun()
                            else:
                                st.error(f"{client_name} 도구 삭제 중 오류가 발생했습니다.")


def display_chat_history():
    """Show chat messages stored in session state"""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


async def process_chat(user_input):
    """Process user input asynchronously"""
    logger.info(f"Processing user input: {user_input[:30]}...")
    
    # Add and display user message
    add_user_message(user_input)
    
    # Prepare UI elements for response
    status_placeholder, message_placeholder = prepare_assistant_ui()
    
    # Verify session ID exists
    ensure_session_id()
    
    # Get chat response
    response_data = get_chat_response(user_input, st.session_state.session_id)
    
    # Handle response
    handle_response(response_data, message_placeholder, status_placeholder)


def add_user_message(user_input):
    """Add user message to session state and display in UI"""
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.chat_message("user"):
        st.markdown(user_input)


def prepare_assistant_ui():
    """Create UI components for assistant response"""
    with st.chat_message("assistant"):
        status_placeholder = st.status(
            PROCESSING_MESSAGE, expanded=False
        )
        message_placeholder = st.empty()
    
    return status_placeholder, message_placeholder


def ensure_session_id():
    """Check if session ID exists, create new one if not"""
    if not st.session_state.session_id:
        st.session_state.session_id = generate_session_id()
        logger.info(f"Created new session ID: {st.session_state.session_id}")
        st.sidebar.info(
            SESSION_NEW.format(st.session_state.session_id)
        )


def handle_response(response_data, message_placeholder, status_placeholder):
    """Process response data and update UI"""
    if response_data:
        logger.debug(f"Received response: {response_data}")
        
        # Update session ID if needed
        update_session_id_if_needed(response_data)
        
        # Display response
        message_placeholder.markdown(response_data[Response.RESPONSE.value])
        status_placeholder.update(
            label=STATUS_COMPLETE, state="complete", expanded=False
        )
        
        # Save assistant message to session history
        add_assistant_message(response_data[Response.RESPONSE.value])
    else:
        logger.error(ERROR_NO_RESPONSE)
        message_placeholder.error(
            ERROR_NO_RESPONSE
        )
        status_placeholder.update(
            label=STATUS_ERROR, state="error", expanded=True
        )


def update_session_id_if_needed(response_data):
    """Update session ID if necessary"""
    if (
        'session_id' in response_data
        and response_data['session_id']
        != st.session_state.session_id
    ):
        logger.info(f"Updating session ID to: {response_data['session_id']}")
        st.session_state.session_id = response_data[
            'session_id'
        ]
        st.sidebar.info(
            SESSION_UPDATED.format(st.session_state.session_id)
        )


def add_assistant_message(content):
    """Add assistant message to session state"""
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": content,
        }
    )


def render_chat_tab():
    """대화창 탭 렌더링"""
    # 컨테이너를 생성하여 채팅 내역을 표시 (높이 제한)
    chat_container = st.container()
    # 스트림릿의 기본 여백을 줄이기 위한 CSS
    st.markdown(
        """
        <style>
        .chat-container {
            padding-bottom: 6px; /* 채팅 입력창이 표시될 공간 확보 */
        }
        .stChatInputContainer {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            padding: 1rem;
            background-color: rgba(255, 255, 255, 0.95);
            z-index: 999;
            backdrop-filter: blur(5px);
            border-top: 1px solid rgba(49, 51, 63, 0.2);
        }
        </style>
        """, 
        unsafe_allow_html=True
    )
    
    with chat_container:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        display_chat_history()
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 채팅 탭에서만 채팅 입력 표시
    prompt = st.chat_input("Ask something... (e.g., 'What files are in the root directory?')")
    if prompt:
        # 비동기 처리 실행
        asyncio.run(process_chat(prompt))
        st.rerun()  # UI 갱신


def render_tool_add_tab():
    """도구 추가 탭 렌더링"""    
    # 도구 JSON 입력
    st.subheader("도구 JSON 입력")
    
    # 초기 도구 JSON 예시
    default_json = """{
  "perplexity-search11": {
    "command": "npx",
    "args": [
      "-y",
      "@smithery/cli@latest",
      "run",
      "@arjunkmrm/perplexity-search",
      "--key",
      "SMITHERY_API_KEY"
    ],
    "transport": "stdio"
  }
}"""
    
    tool_json = st.text_area(
        "도구 구성을 위한 JSON을 입력하세요",
        value=default_json,
        height=300
    )
    
    # JSON 유효성 검사
    is_valid_json = True
    json_error = None
    parsed_json = None
    
    try:
        if tool_json:
            parsed_json = json.loads(tool_json)
    except json.JSONDecodeError as e:
        is_valid_json = False
        json_error = str(e)
    
    # 유효성 검사 결과 표시
    if not is_valid_json and tool_json:
        st.error(f"유효하지 않은 JSON: {json_error}")
    elif tool_json:
        st.success("유효한 JSON 형식입니다.")
    
    # 추가 버튼 및 처리
    if st.button("추가", disabled=not is_valid_json or not tool_json):
        if parsed_json:
            # 기존 설정 로드
            current_config = st.session_state.mcp_config.copy()
            
            # 새 설정 병합
            for key, value in parsed_json.items():
                current_config[key] = value
            
            # 설정 저장
            if save_config_to_json(current_config):
                st.session_state.mcp_config = current_config
                st.success("도구가 성공적으로 추가되었습니다. 사이드바의 'Refresh Tools' 버튼을 클릭하여 새로고침하세요.")
            else:
                st.error("도구 설정 저장 중 오류가 발생했습니다.")


async def main():
    logger.info("Starting MCP Chatbot")
    st.title("⚙️ MCP Chatbot - Interactive Agent")
    st.caption("A chatbot that uses the Model Context Protocol (MCP) to interact with tools.")

    initialize()
    logger.debug("Initialized application state")

    render_sidebar()

    # 탭 선택기 (숨겨진 셀렉트박스 없이 직접 탭 선택)
    tab_names = ["🔤 대화창", "🔨 도구 추가"]
    chat_tab, tool_tab = st.tabs(tab_names)
    
    # 대화창 탭
    with chat_tab:
        # 탭이 선택되면 활성 탭 상태 업데이트
        if "active_tab" not in st.session_state or st.session_state.active_tab != "대화창":
            st.session_state.active_tab = "대화창"
            st.session_state.active_main_tab = 0
        render_chat_tab()
    
    # 도구 추가 탭
    with tool_tab:
        # 탭이 선택되면 활성 탭 상태 업데이트
        if "active_tab" not in st.session_state or st.session_state.active_tab != "도구 추가":
            st.session_state.active_tab = "도구 추가"
            st.session_state.active_main_tab = 1
        render_tool_add_tab()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        pass