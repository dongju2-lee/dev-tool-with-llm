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
                st.session_state.mcp_tools_cache = {}
                st.toast("Tools refreshed!", icon="🔄")
                st.rerun()
                
            # 샘플 도구 목록 표시
            tools = st.session_state.mcp_tools_cache.get("tools", [])
            
            # 기본 클라이언트로 "markdown_processor" 표시
            with st.expander("Client: markdown_processor (2 tools)", expanded=False):
                st.markdown("**Tool 1: `read_markdown_file`**")
                st.caption("Reads content from markdown files in specified directory")
                with st.popover("Schema"):
                    st.json({
                        "directory_path": "string",
                        "file_pattern": "string (optional)"
                    })
                st.divider()
                
                st.markdown("**Tool 2: `write_markdown_file`**")
                st.caption("Writes content to markdown files in specified directory")
                with st.popover("Schema"):
                    st.json({
                        "directory_path": "string",
                        "file_name": "string",
                        "content": "string"
                    })


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


async def main():
    logger.info("Starting Github Issue Assistant Bot")
    st.title("⚙️ MCP Chatbot - Interactive Agent")
    st.caption("A chatbot that uses the Model Context Protocol (MCP) to interact with tools.")

    initialize()
    logger.debug("Initialized application state")

    render_sidebar()

    display_chat_history()

    if prompt := st.chat_input("Ask something... (e.g., 'What files are in the root directory?')"):
        logger.info("Received new user input")
        await process_chat(prompt)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        pass
