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
    파일이 없으면 빈 객체({})를 반환합니다.

    Returns:
        dict: 로드된 설정
    """
    try:
        if os.path.exists(MCP_CONFIG_FILE_PATH):
            with open(MCP_CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            # 파일이 없으면 빈 객체 반환
            logger.info(f"MCP 설정 파일({MCP_CONFIG_FILE_PATH})이 없습니다. 빈 설정을 사용합니다.")
            return {}
    except Exception as e:
        logger.error(f"설정 파일 로드 오류: {str(e)}")
        return {}


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
        
    # MCP 도구 새로고침 예약 플래그 초기화
    if "scheduled_mcp_refresh" not in st.session_state:
        st.session_state.scheduled_mcp_refresh = False

    if "graph" not in st.session_state:
            logger.info("그래프 초기화")
            from simple.dev_tool_graph import get_dev_tool_graph
            st.session_state.graph = get_dev_tool_graph()


async def get_mcp_tools():
    """
    MCP 서버에 연결하여 사용 가능한 도구 목록을 가져옵니다.
    서버와의 연결도 테스트합니다.

    Returns:
        tuple: (성공 여부, 도구 목록 또는 오류 메시지)
    """
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
        
        # MCP 설정 가져오기
        mcp_config = st.session_state.mcp_config
        
        if not mcp_config:
            return False, "MCP 설정이 없습니다."
            
        # MCP 클라이언트 생성
        logger.info(f"MCP 클라이언트 생성 중... mcp_config : {mcp_config}")
        
        client = MultiServerMCPClient(mcp_config)
        logger.info("MCP 클라이언트 인스턴스 생성 완료")
        
        # MCP 서버에 연결 시도
        try:
            logger.info("MCP 서버에 연결 시도 중...")
            await client.__aenter__()
            logger.info("MCP 서버 연결 성공")
            
            # 도구 가져오기 시도
            logger.info("MCP 도구 가져오는 중...")
            tools = client.get_tools()
            
            # 도구 정보 로깅
            logger.info(f"총 {len(tools)}개의 MCP 도구를 가져왔습니다")
            
            # 도구 정보를 저장할 리스트
            tools_info = []
            
            for i, tool in enumerate(tools, 1):
                try:
                    tool_name = getattr(tool, "name", f"Tool-{i}")
                    tool_desc = getattr(tool, "description", "설명 없음")
                    logger.info(f"  도구 {i}: {tool_name} - {tool_desc}")
                    
                    # 도구 정보 저장
                    tools_info.append({
                        "name": tool_name,
                        "description": tool_desc
                    })
                except Exception as e:
                    logger.warning(f"  도구 {i}의 정보를 가져오는 중 오류: {str(e)}")
            
            # 연결 닫기
            await client.__aexit__(None, None, None)
            
            # 성공적으로 도구를 가져왔으면 캐시에 저장
            st.session_state.mcp_tools_cache = {
                "status": "ok",
                "tools": tools_info,
                "raw_tools": tools
            }
            
            return True, tools_info
            
        except Exception as e:
            error_msg = f"MCP 서버 연결 오류: {str(e)}"
            logger.error(error_msg)
            
            # 오류 정보 캐시에 저장
            st.session_state.mcp_tools_cache = {
                "status": "error",
                "error": error_msg
            }
            
            return False, error_msg
            
    except ImportError:
        error_msg = "langchain_mcp_adapters 패키지를 찾을 수 없습니다."
        logger.warning(error_msg)
        
        # 오류 정보 캐시에 저장
        st.session_state.mcp_tools_cache = {
            "status": "error",
            "error": error_msg
        }
        
        return False, error_msg
        
    except Exception as e:
        error_msg = f"MCP 도구 로드 중 오류 발생: {str(e)}"
        logger.error(error_msg)
        
        # 오류 정보 캐시에 저장
        st.session_state.mcp_tools_cache = {
            "status": "error",
            "error": error_msg
        }
        
        return False, error_msg


def clear_mcp_tools():
    """
    MCP 도구 캐시를 초기화합니다.
    """
    if "mcp_tools_cache" in st.session_state:
        st.session_state.mcp_tools_cache = {}
        logger.info("MCP 도구 캐시가 초기화되었습니다.")


async def get_chat_response(message, session_id=None):
    """그래프의 ainvoke를 사용하여 응답을 생성합니다."""
    try:
        # 요청 데이터 준비
        from langchain_core.messages import HumanMessage
        
        # 세션 ID가 있으면 메시지에 추가
        additional_kwargs = {}
        if session_id:
            additional_kwargs["session_id"] = session_id
            
        # 입력 메시지 생성
        input_message = HumanMessage(content=message, additional_kwargs=additional_kwargs)
        
        # 그래프 호출
        logger.info(f"그래프의 ainvoke 호출: {message[:1000]}...")
        response = await st.session_state.graph.ainvoke({"messages": [input_message]})
        
        # 응답 변환
        result = {
            Response.RESPONSE.value: response["messages"][-1].content
        }
        
        if session_id:
            result[Response.SESSION_ID.value] = session_id
            
        return result
    except Exception as e:
        logger.error(f"그래프 호출 중 오류 발생: {str(e)}")
        st.error(f"그래프 호출 중 오류 발생: {str(e)}")
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
            # 새로고침 버튼
            refresh_col, clear_col = st.columns(2)
            
            with refresh_col:
                if st.button("🔄 Refresh Tools", use_container_width=True, type="primary"):
                    # 설정 파일에서 MCP 설정 다시 로드
                    st.session_state.mcp_config = load_config_from_json()
                    # MCP 도구 캐시 초기화
                    clear_mcp_tools()
                    
                    # 비동기 함수 호출을 처리하기 위해 세션 상태에 작업 예약 플래그 설정
                    st.session_state.scheduled_mcp_refresh = True
                    st.toast("Refreshing tools... Please wait.", icon="🔄")
                    st.rerun()
            
            with clear_col:
                if st.button("🧹 Clear", use_container_width=True):
                    clear_mcp_tools()
                    st.toast("MCP tools cache cleared!", icon="🧹")
                    st.rerun()
            
            # MCP 도구 정보 표시
            if "mcp_tools_cache" in st.session_state and st.session_state.mcp_tools_cache:
                cache = st.session_state.mcp_tools_cache
                
                if cache.get("status") == "ok":
                    # 연결 성공 상태 표시
                    st.success("✅ MCP Server Connection Successful")
                    
                    # 도구 목록 표시
                    tools_info = cache.get("tools", [])
                    if tools_info:
                        st.subheader(f"Available Tools ({len(tools_info)})")
                        for i, tool in enumerate(tools_info, 1):
                            with st.expander(f"{i}. {tool['name']}", expanded=False):
                                st.markdown(f"**Description**: {tool['description']}")
                    else:
                        st.info("No available tools found.")
                
                elif cache.get("status") == "error":
                    # 연결 오류 표시
                    st.error(f"❌ MCP Server Connection Error: {cache.get('error', 'Unknown error')}")
            else:
                # MCP 설정 표시 (기존 코드)
                st.subheader("Registered MCP Configurations")
                tools = st.session_state.mcp_config
                
                if not tools:
                    st.info("No MCP configurations registered.")
                else:
                    # 등록된 도구 출력 (각 항목을 클릭하면 삭제 버튼 표시)
                    for client_name, client_config in tools.items():
                        with st.expander(f"Client: {client_name}", expanded=False):
                            st.json(client_config)
                            if st.button(f"🗑️ Delete", key=f"delete_{client_name}"):
                                # 도구 삭제 처리
                                current_config = st.session_state.mcp_config.copy()
                                if client_name in current_config:
                                    del current_config[client_name]
                                    if save_config_to_json(current_config):
                                        st.session_state.mcp_config = current_config
                                        # MCP 도구 캐시 초기화
                                        clear_mcp_tools()
                                        st.toast(f"{client_name} tool deleted successfully!", icon="✅")
                                        st.rerun()
                                    else:
                                        st.error(f"Error deleting tool {client_name}.")


def display_chat_history():
    """Show chat messages stored in session state"""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


async def process_chat(user_input):
    """Process user input asynchronously"""
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        status_placeholder = st.status(
            "Processing your request...", expanded=False
        )
        message_placeholder = st.empty()

    if not st.session_state.session_id:
        st.session_state.session_id = generate_session_id()
        st.sidebar.info(
            f"New session created with ID: {st.session_state.session_id}"
        )

    response_data = await get_chat_response(user_input, st.session_state.session_id)

    if response_data:
        if (
            Response.SESSION_ID.value in response_data
            and response_data[Response.SESSION_ID.value]
            != st.session_state.session_id
        ):
            st.session_state.session_id = response_data[
                Response.SESSION_ID.value
            ]
            st.sidebar.info(
                f"Session ID updated: {st.session_state.session_id}"
            )

        message_placeholder.markdown(response_data[Response.RESPONSE.value])
        status_placeholder.update(
            label="✅ Complete", state="complete", expanded=False
        )

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": response_data[Response.RESPONSE.value],
            }
        )
    else:
        message_placeholder.error(
            "Failed to get a valid response from the server"
        )
        status_placeholder.update(
            label="❌ Error", state="error", expanded=True
        )


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


async def render_chat_tab():
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
    if prompt := st.chat_input("Enter your message here..."):
        await process_chat(prompt)


def render_tool_add_tab():
    """도구 추가 탭 렌더링"""    
    # 도구 JSON 입력
    st.subheader("Tool JSON Input")
    
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
    "transport": "sse"
  }
}"""
    
    tool_json = st.text_area(
        "Enter JSON configuration for the tool",
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
        st.error(f"Invalid JSON: {json_error}")
    elif tool_json:
        st.success("Valid JSON format.")
    
    # 추가 버튼 및 처리
    if st.button("Add", disabled=not is_valid_json or not tool_json):
        if parsed_json:
            # 기존 설정 로드
            current_config = st.session_state.mcp_config.copy()
            
            # 새 설정 병합
            for key, value in parsed_json.items():
                current_config[key] = value
            
            # 설정 저장
            if save_config_to_json(current_config):
                # 세션 상태 업데이트
                st.session_state.mcp_config = current_config
                
                # 성공 메시지 표시
                st.success("도구 설정이 저장되었습니다. 서버에 연결하려면 사이드바에서 'Refresh Tools' 버튼을 클릭하세요.")
                st.toast("설정이 저장되었습니다!", icon="✅")
                
                # 화면 새로고침
                st.rerun()
            else:
                st.error("도구 설정 저장 중 오류가 발생했습니다.")

    # 현재 MCP 설정 표시 섹션 (항상 표시)
    st.divider()
    with st.expander("현재 MCP 설정 보기", expanded=True):
        # 파일 경로 표시
        file_path = os.path.abspath(MCP_CONFIG_FILE_PATH)
        st.caption(f"파일: {file_path}")
        
        # 파일 존재 여부 확인 및 내용 표시
        if os.path.exists(file_path):
            try:
                # 파일에서 직접 읽기
                with open(file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()
                
                # 파일 내용이 있으면 표시
                if file_content.strip():
                    st.code(file_content, language="json")
                else:
                    st.info("설정 파일이 비어 있습니다.")
            except Exception as e:
                st.error(f"설정 파일 읽기 오류: {str(e)}")
                # 오류 발생 시 세션 상태의 설정 표시
                if st.session_state.mcp_config:
                    st.code(json.dumps(st.session_state.mcp_config, indent=2, ensure_ascii=False), language="json")
                    st.caption("⚠️ 파일 읽기 오류로 세션 상태의 설정을 표시합니다")
        else:
            st.info("설정 파일이 아직 생성되지 않았습니다. 첫 도구를 추가하면 파일이 생성됩니다.")
            # 세션 상태에 설정이 있는 경우 표시
            if st.session_state.mcp_config:
                st.code(json.dumps(st.session_state.mcp_config, indent=2, ensure_ascii=False), language="json")
                st.caption("⚠️ 세션 상태의 설정을 표시합니다 (아직 파일에 저장되지 않음)")


async def main():
    logger.info("Starting MCP Chatbot")
    st.title("⚙️ MCP Chatbot - Interactive Agent")
    st.caption("A chatbot that uses the Model Context Protocol (MCP) to interact with tools.")

    initialize()
    logger.debug("Initialized application state")
    
    # 예약된 MCP 새로고침 작업 확인 및 처리
    if "scheduled_mcp_refresh" in st.session_state and st.session_state.scheduled_mcp_refresh:
        with st.spinner("Refreshing MCP tools..."):
            try:
                # MCP 도구 로드 실행
                success, result = await get_mcp_tools()
                
                if success:
                    st.toast("MCP tools refreshed successfully!", icon="✅")
                else:
                    st.toast(f"Failed to refresh MCP tools: {result}", icon="❌")
            except Exception as e:
                logger.error(f"Error refreshing MCP tools: {str(e)}")
                st.toast(f"Error refreshing MCP tools: {str(e)}", icon="❌")
            
            # 플래그 초기화
            st.session_state.scheduled_mcp_refresh = False
    
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
        await render_chat_tab()
    
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