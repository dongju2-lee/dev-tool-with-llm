import streamlit as st
import time
import asyncio
import uuid
from typing import Optional, List, Dict, Any
import datetime
import os
import sys
import requests
import json

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.messages.ai import AIMessageChunk
from langchain_core.runnables import RunnableConfig
from simple.dev_tool_graph import get_dev_tool_graph,get_mermaid_graph

from utils.logger_config import setup_logger
from config import *  # Import all constants and configuration values

# 로거 설정'
logger = setup_logger("chatbot_page", level=LOG_LEVEL)
MCP_CONFIG_FILE_PATH = "mcp_tools_config.json"

# 로거 설정

# LANGFUSE_SECRET_KEY= os.environ.get("LANGFUSE_SECRET_KEY")
# LANGFUSE_PUBLIC_KEY= os.environ.get("LANGFUSE_PUBLIC_KEY")
# LANGFUSE_HOST= os.environ.get("LANGFUSE_HOST")

# from langfuse.callback import CallbackHandler
# langfuse_handler = CallbackHandler(
#     public_key=LANGFUSE_PUBLIC_KEY,
#     secret_key=LANGFUSE_SECRET_KEY,
#     host=LANGFUSE_HOST
# )
# logger.info(f"langfuse셋팅 :: LANGFUSE_SECRET_KEY : {LANGFUSE_SECRET_KEY} :: LANGFUSE_PUBLIC_KEY : {LANGFUSE_PUBLIC_KEY} :: LANGFUSE_HOST : {LANGFUSE_HOST} ")
# from langfuse.callback import CallbackHandler
# langfuse_handler = CallbackHandler()



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


def print_message():
    """
    채팅 기록을 화면에 출력합니다.
    """
    for message in st.session_state.history:
        if message["role"] == "user":
            st.chat_message("user").markdown(message["content"])
        elif message["role"] == "assistant":
            st.chat_message("assistant").markdown(message["content"])
        elif message["role"] == "agent":
            with st.chat_message("assistant"):
                st.info(f"**{message['name']}**: {message['content']}")


def get_streaming_callback(response_placeholder):
    """
    스트리밍 콜백 함수를 생성합니다.
    
    Args:
        response_placeholder: 응답을 표시할 Streamlit 컴포넌트
    
    Returns:
        callback_func: 스트리밍 콜백 함수
    """
    accumulated_text = []
    
    def callback_func(chunk):
        nonlocal accumulated_text
        
        # 청크가 메시지인 경우
        if isinstance(chunk, dict) and "messages" in chunk:
            messages = chunk["messages"]
            if messages and len(messages) > 0:
                last_message = messages[-1]
                if hasattr(last_message, 'content'):
                    content = last_message.content
                    accumulated_text.append(content)
                    response_placeholder.markdown("".join(accumulated_text))
        
        # 청크가 AIMessageChunk인 경우
        elif isinstance(chunk, AIMessageChunk):
            if chunk.content:
                accumulated_text.append(chunk.content)
                response_placeholder.markdown("".join(accumulated_text))
                
        # 청크가 다른 형태의 메시지인 경우
        elif isinstance(chunk, dict) and "content" in chunk:
            accumulated_text.append(chunk["content"])
            response_placeholder.markdown("".join(accumulated_text))
        
        return None
    
    return callback_func, accumulated_text


async def process_query_streaming(query: str, response_placeholder, timeout_seconds=60) -> Optional[str]:
    """
    사용자 질문을 처리하고 응답을 스트리밍 방식으로 생성합니다.
    
    Args:
        query: 사용자가 입력한 질문 텍스트
        response_placeholder: 응답을 표시할 Streamlit 컴포넌트
        timeout_seconds: 응답 생성 제한 시간(초)
    
    Returns:
        final_text: 최종 응답 텍스트
    """
    start_time = time.time()  # 시작 시간 기록
    
    try:
        if st.session_state.graph:
            # 그래프 호출
            logger.info(f"사용자 쿼리 처리 시작: '{query[:50]}'..." if len(query) > 50 else query)
            
            # 스트리밍 방식으로 호출
            try:
                inputs = {"messages": [HumanMessage(content=query)]}
                config = RunnableConfig(
                    recursion_limit=100
                )
                
                # 간단한 접근 방식: 비동기로 먼저 전체 응답을 받음
                response = await asyncio.wait_for(
                    # st.session_state.graph.ainvoke(inputs,config={"callbacks": [langfuse_handler]}),
                    st.session_state.graph.ainvoke(inputs),
                    timeout=timeout_seconds
                )
                
                # 마지막 메시지 추출
                if "messages" in response and response["messages"]:
                    final_text = response["messages"][-1].content
                    
                    # 사용자 설정 워드 딜레이 가져오기
                    word_delay = st.session_state.get("word_delay", 0.01)
                    
                    # 응답 텍스트를 단어 단위로 스트리밍처럼 표시 (실제 스트리밍 대신 시뮬레이션)
                    words = final_text.split()
                    current_text = []
                    
                    for word in words:
                        current_text.append(word)
                        display_text = " ".join(current_text)
                        response_placeholder.markdown(display_text)
                        # 단어 사이 사용자 설정 딜레이 적용
                        await asyncio.sleep(word_delay)
                    
                    # 처리 시간 계산 및 표시
                    end_time = time.time()
                    processing_time = end_time - start_time
                    processing_time_msg = f"\n\n*응답 처리 시간: {processing_time:.2f}초*"
                    
                    # 최종 텍스트에 처리 시간 추가
                    final_text_with_time = final_text + processing_time_msg
                    response_placeholder.markdown(final_text_with_time)
                    
                    logger.info(f"쿼리 처리 완료: '{query[:30]}...', 처리 시간: {processing_time:.2f}초")
                    return final_text_with_time
                else:
                    logger.warning("응답 메시지가 없습니다.")
                    error_msg = "죄송합니다. 응답을 생성하지 못했습니다."
                    
                    # 처리 시간 계산 및 표시
                    end_time = time.time()
                    processing_time = end_time - start_time
                    error_msg_with_time = f"{error_msg}\n\n*응답 처리 시간: {processing_time:.2f}초*"
                    
                    response_placeholder.markdown(error_msg_with_time)
                    return error_msg_with_time
                
            except asyncio.TimeoutError:
                error_msg = f"⏱️ 요청 시간이 {timeout_seconds}초를 초과했습니다. 나중에 다시 시도해 주세요."
                logger.error(error_msg)
                
                # 처리 시간 계산 및 표시
                end_time = time.time()
                processing_time = end_time - start_time
                error_msg_with_time = f"{error_msg}\n\n*응답 처리 시간: {processing_time:.2f}초*"
                
                response_placeholder.markdown(error_msg_with_time)
                return error_msg_with_time
            
            except Exception as e:
                import traceback
                error_msg = f"스트리밍 처리 중 오류: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                
                # 처리 시간 계산 및 표시
                end_time = time.time()
                processing_time = end_time - start_time
                error_msg_with_time = f"죄송합니다. 오류가 발생했습니다: {str(e)}\n\n*응답 처리 시간: {processing_time:.2f}초*"
                
                response_placeholder.markdown(error_msg_with_time)
                return error_msg_with_time
        else:
            logger.error("그래프가 초기화되지 않았습니다.")
            error_msg = "시스템이 아직 초기화 중입니다. 잠시 후 다시 시도해주세요."
            
            # 처리 시간 계산 및 표시
            end_time = time.time()
            processing_time = end_time - start_time
            error_msg_with_time = f"{error_msg}\n\n*응답 처리 시간: {processing_time:.2f}초*"
            
            response_placeholder.markdown(error_msg_with_time)
            return error_msg_with_time
    except Exception as e:
        import traceback
        error_msg = f"쿼리 처리 중 오류 발생: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        # 처리 시간 계산 및 표시
        end_time = time.time()
        processing_time = end_time - start_time
        error_msg_with_time = f"죄송합니다. 오류가 발생했습니다: {str(e)}\n\n*응답 처리 시간: {processing_time:.2f}초*"
        
        response_placeholder.markdown(error_msg_with_time)
        return error_msg_with_time


async def process_query(query: str) -> Optional[str]:
    """
    사용자 질문을 처리하고 응답을 생성합니다. (비스트리밍 방식)
    
    Args:
        query: 사용자가 입력한 질문 텍스트
    
    Returns:
        response_content: 최종 응답 텍스트
    """
    start_time = time.time()  # 시작 시간 기록
    
    try:
        if st.session_state.graph:
            # 그래프 호출
            logger.info(f"사용자 쿼리 처리 시작: '{query[:50]}'..." if len(query) > 50 else query)
            
            inputs = {"messages": [HumanMessage(content=query)]}
            # response = await st.session_state.graph.ainvoke(inputs,config={"callbacks": [langfuse_handler]})
            response = await st.session_state.graph.ainvoke(inputs)


            # 응답 처리
            if "messages" in response:
                if response["messages"]:
                    last_message = response["messages"][-1]
                    response_content = last_message.content
                    
                    # 처리 시간 계산 및 표시
                    end_time = time.time()
                    processing_time = end_time - start_time
                    response_content_with_time = f"{response_content}\n\n*응답 처리 시간: {processing_time:.2f}초*"
                    
                    logger.info(f"쿼리 처리 완료: '{query[:30]}...', 처리 시간: {processing_time:.2f}초")
                    return response_content_with_time
                else:
                    logger.warning("응답 메시지가 없습니다.")
                    # 처리 시간 계산 및 표시
                    end_time = time.time()
                    processing_time = end_time - start_time
                    error_msg = f"죄송합니다. 응답을 생성하지 못했습니다.\n\n*응답 처리 시간: {processing_time:.2f}초*"
                    return error_msg
            else:
                logger.warning("응답에 'messages' 키가 없습니다.")
                # 처리 시간 계산 및 표시
                end_time = time.time()
                processing_time = end_time - start_time
                error_msg = f"죄송합니다. 응답 형식이 올바르지 않습니다.\n\n*응답 처리 시간: {processing_time:.2f}초*"
                return error_msg
        else:
            logger.error("그래프가 초기화되지 않았습니다.")
            # 처리 시간 계산 및 표시
            end_time = time.time()
            processing_time = end_time - start_time
            error_msg = f"시스템이 아직 초기화 중입니다. 잠시 후 다시 시도해주세요.\n\n*응답 처리 시간: {processing_time:.2f}초*"
            return error_msg
    except Exception as e:
        import traceback
        error_msg = f"쿼리 처리 중 오류 발생: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        # 처리 시간 계산 및 표시
        end_time = time.time()
        processing_time = end_time - start_time
        error_msg_with_time = f"죄송합니다. 오류가 발생했습니다: {str(e)}\n\n*응답 처리 시간: {processing_time:.2f}초*"
        
        return error_msg_with_time


def initialize_chatbot():
    """
    챗봇 기능을 초기화합니다.
    이벤트 루프와 그래프를 설정합니다.
    """
    try:
        logger.info("챗봇 초기화 시작")
        
        # 이벤트 루프
        if "event_loop" not in st.session_state:
            import asyncio
            logger.info("이벤트 루프 초기화")
            st.session_state.event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(st.session_state.event_loop)
        
        # 그래프 초기화 (이미 없는 경우에만)
        if "graph" not in st.session_state:
            logger.info("그래프 초기화")
            st.session_state.graph = get_dev_tool_graph()
        
        # 세션 ID 초기화 (이미 없는 경우에만)
        if "session_id" not in st.session_state:
            logger.info("세션 ID 초기화")
            st.session_state.session_id = generate_session_id()
        
        # 스레드 ID 초기화 (이미 없는 경우에만) - session_id와 동일하게 설정
        if "thread_id" not in st.session_state:
            logger.info("스레드 ID 초기화")
            st.session_state.thread_id = st.session_state.session_id
        
        # 대화 기록 초기화 (이미 없는 경우에만)
        if "history" not in st.session_state:
            logger.info("대화 기록 초기화")
            st.session_state.history = []
        
        # MCP 설정 초기화 (이미 없는 경우에만)
        if "mcp_config" not in st.session_state:
            logger.info("MCP 설정 초기화")
            st.session_state.mcp_config = load_config_from_json()
        
        # 초기화 상태 설정
        logger.info("챗봇 초기화 완료")
        return True
    except Exception as e:
        import traceback
        logger.error(f"챗봇 초기화 실패: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def render_chat_tab(is_initialized: Any):
    # 대화 기록 출력
    print_message()
    
    # 사용자 입력 처리
    user_query = st.chat_input("💬 Dev Tool 관리 명령이나 질문을 입력하세요")
    if user_query:
        if is_initialized:
            # 사용자 메시지 표시
            st.chat_message("user").markdown(user_query)
            
            # 응답 생성 중 표시
            with st.chat_message("assistant"):
                response_placeholder = st.empty()
                
                # 사용자 선택에 따라 스트리밍 또는 일반 방식으로 처리
                if st.session_state.get("streaming_mode", True):
                    # 스트리밍 방식
                    with st.spinner("🤖 Dev Tool 시스템이 응답을 생성하고 있습니다..."):
                        response = st.session_state.event_loop.run_until_complete(
                            process_query_streaming(user_query, response_placeholder)
                        )
                else:
                    # 일반 방식
                    with st.spinner("🤖 Dev Tool 시스템이 응답을 생성하고 있습니다..."):
                        response = st.session_state.event_loop.run_until_complete(
                            process_query(user_query)
                        )
                        response_placeholder.markdown(response)
            
            # 대화 기록 저장
            st.session_state.history.append({"role": "user", "content": user_query})
            st.session_state.history.append({"role": "assistant", "content": response})
            
            # 페이지 리로드
            st.rerun()
        else:
            st.warning("⏳ 시스템을 초기화하는 중 문제가 발생했습니다. 페이지를 새로고침하거나 잠시 후 다시 시도해주세요.")



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



def chatbot_page():
    """
    멀티에이전트 Dev Tool 시스템 채팅봇 페이지입니다.
    """
    st.title("💬 Dev Tool 채팅봇")
    st.markdown("---")
    
    # 챗봇 초기화
    is_initialized = initialize_chatbot()
    
    # 채팅봇 소개
    st.markdown("""
    자연어로 Dev Tool 시스템과 대화할 수 있는 인터페이스입니다.  
    명령을 내리거나 질문을 하면 멀티에이전트 시스템이 적절한 응답을 제공합니다.
    """)
    
    # LLM 모델 정보
    with st.sidebar:
        
        # 현재 세션 ID 표시
        if "session_id" in st.session_state:
            st.info(f"현재 세션 ID: {st.session_state.session_id[:8]}...")
        else:
            st.info("세션 ID가 설정되지 않았습니다.")
        
        st.divider()
        with st.expander("LLM 모델 세부 정보"):
            # 환경 변수에서 모델 이름 가져오기
            supervisor_model = os.environ.get("SUPERVISOR_MODEL", "gemini-2.5-pro-exp-03-25")
            
            
            st.markdown(f"""
            - **슈퍼바이저 에이전트**: {supervisor_model}
            """)
        
        # 시스템 정보 표시 옵션
        st.divider()
        refresh_col, clear_col = st.columns(2)
        
        with refresh_col:
            if st.button("🔄 Refresh Tools", use_container_width=True, type="primary"):
                # 설정 파일에서 MCP 설정 다시 로드
                st.session_state.mcp_config = load_config_from_json()
                logger.info(f"mpc 리프레시 버튼 : {st.session_state.mcp_config}")
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
        
        # MCP 설정 헤더 및 내용 표시 (별도 섹션으로 분리)
        st.subheader("Registered MCP Configurations")
            
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
            # MCP 설정 표시
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

        st.divider()

        # 에이전트 그래프 표시
        if st.checkbox("에이전트 그래프 표시"):
            display_agent_graph()
        
       
    # 탭 선택기 (숨겨진 셀렉트박스 없이 직접 탭 선택)
    tab_names = ["🔤 대화창", "🔨 도구 추가"]
    chat_tab, tool_tab = st.tabs(tab_names)
    
    # 대화창 탭
    with chat_tab:
        # 탭이 선택되면 활성 탭 상태 업데이트
        if "active_tab" not in st.session_state or st.session_state.active_tab != "대화창":
            st.session_state.active_tab = "대화창"
            st.session_state.active_main_tab = 0
        # await render_chat_tab(is_initialized) 대신에 run_until_complete 사용
        if "event_loop" in st.session_state:
            # 비동기 함수를 동기적으로 실행
            render_chat_tab(is_initialized)
        else:
            st.error("이벤트 루프가 초기화되지 않았습니다.")
    
    # 도구 추가 탭
    with tool_tab:
        # 탭이 선택되면 활성 탭 상태 업데이트
        if "active_tab" not in st.session_state or st.session_state.active_tab != "도구 추가":
            st.session_state.active_tab = "도구 추가"
            st.session_state.active_main_tab = 1
        render_tool_add_tab()
    
    logger.info("챗봇 페이지가 로드되었습니다.")



def display_agent_graph():
    """에이전트 그래프를 시각화하여 표시합니다."""
    try:
        # 그래프 이미지 생성 (더 긴 타임아웃 설정)
        with st.spinner("그래프 이미지를 생성하는 중입니다. 이 작업은 최대 60초까지 소요될 수 있습니다..."):
            import threading
            import time
            
            # 그래프 이미지 생성 결과를 저장할 변수
            result = {"image": None, "error": None}
            
            # 그래프 이미지 생성 함수
            def generate_graph():
                try:
                    result["image"] = get_mermaid_graph()
                except Exception as e:
                    result["error"] = str(e)
            
            # 스레드 생성 및 시작
            graph_thread = threading.Thread(target=generate_graph)
            graph_thread.daemon = True
            graph_thread.start()
            
            # 최대 60초 대기 (타임아웃 대폭 증가)
            wait_time = 60  # 60초
            start_time = time.time()
            
            # 진행 상황 표시를 위한 진행 바
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            while graph_thread.is_alive() and time.time() - start_time < wait_time:
                # 경과 시간 표시
                elapsed = time.time() - start_time
                progress = min(int((elapsed / wait_time) * 100), 99)
                progress_bar.progress(progress)
                status_text.text(f"그래프 생성 중... ({int(elapsed)}초 경과)")
                time.sleep(0.5)
            
            if graph_thread.is_alive():
                # 시간 초과
                status_text.text("시간 초과, 이미지 생성 중단.")
                st.warning("그래프 이미지 생성 시간이 초과되었습니다(60초). 인터넷 연결 상태를 확인하거나 나중에 다시 시도해주세요.")
                
                # 대체 방안: 네트워크 문제일 수 있으니 다시 시도 버튼 제공
                if st.button("그래프 생성 다시 시도"):
                    st.rerun()
            elif result["error"]:
                # 에러 발생
                status_text.text("오류 발생.")
                st.warning(f"그래프 이미지 생성 실패: {result['error']}")
                
                # 다시 시도 버튼 제공
                if st.button("그래프 생성 다시 시도"):
                    st.rerun()
            else:
                # 이미지 생성 성공
                progress_bar.progress(100)
                status_text.text("그래프 생성 완료!")
                # 이미지 표시
                st.image(result["image"], use_container_width=True)
    except Exception as e:
        st.warning(f"그래프 시각화 실패: {str(e)}")
        
        # 다시 시도 버튼 제공
        if st.button("그래프 생성 다시 시도"):
            st.rerun()
