import streamlit as st
import os
import sys
import uuid
import asyncio
import logging
import traceback
import nest_asyncio
import platform
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Windows 환경 특별 처리
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# nest_asyncio 적용 - 중첩된 이벤트 루프 허용
nest_asyncio.apply()

# mcp_client_agent에서 make_graph 함수 임포트
from mcp_client_agent import make_graph

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
            # 비동기 함수를 실행하기 위한 임시 함수
            async def test_connection():
                try:
                    async with make_graph(mcp_client_name, mcp_server_url, mcp_transport) as agent:
                        st.success(f"MCP 서버 연결 성공: {mcp_server_url}")
                        return True
                except Exception as e:
                    st.error(f"MCP 서버 연결 오류: {str(e)}")
                    return False
            
            # 글로벌 이벤트 루프에서 비동기 함수 직접 실행
            connection_result = st.session_state.event_loop.run_until_complete(test_connection())
            
            if connection_result:
                st.session_state.mcp_connected = True
            else:
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


# 대화 응답 처리
# 1. content_type 이 image/png 인 경우 data 를 읽어서 ui 에 뿌려준다. (base64)
# 2. AIMessage 가 있는 경우 content 를 읽어서 ui 에 뿌려준다.

# MCP 에이전트를 통한 응답 생성 함수
async def get_mcp_response(query, history, timeout_seconds=60):
    """MCP 에이전트를 통해 응답을 생성하는 함수"""
    try:
        # make_graph 함수를 사용하여 에이전트 생성
        async with make_graph(mcp_client_name, mcp_server_url, mcp_transport) as agent:
            # 메시지 형식 변환
            messages = []
            for msg in history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
            
            # 현재 쿼리 추가
            messages.append(HumanMessage(content=query))
            
            # 에이전트 호출 (타임아웃 처리 추가)
            try:
                result = await asyncio.wait_for(
                    agent.ainvoke({"messages": messages}),
                    timeout=timeout_seconds
                )
                return {
                    "response": result,
                    "status": "success"
                }
            except asyncio.TimeoutError:
                return {
                    "response": f"요청 시간이 {timeout_seconds}초를 초과했습니다. 좀 더 간단한 질문을 해보세요.",
                    "status": "timeout"
                }
    except Exception as e:
        logger.error(f"MCP 응답 생성 오류: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "response": f"오류가 발생했습니다: {str(e)}",
            "status": "error"
        }

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
                    if hasattr(msg, "content"):
                        try:
                            tool_data = eval(msg.content)
                            if isinstance(tool_data, dict) and "content_type" in tool_data and "image" in tool_data["content_type"]:
                                if "data" in tool_data:
                                    results.append({
                                        "type": "image",
                                        "content": tool_data["data"],
                                        "caption": tool_data.get("message", "")
                                    })
                        except:
                            pass
    
    # 결과가 없으면 원본 응답을 문자열로 변환
    if not results:
        return {"type": "text", "content": str(response)}
    
    # 결과가 하나면 그대로 반환
    if len(results) == 1:
        return results[0]
    
    # 여러 결과가 있으면 배열로 반환
    return results

# 사용자 입력 처리
if prompt := st.chat_input("무엇이든 물어보세요"):
    # 사용자 메시지 추가 및 표시
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # 응답 생성
    with st.chat_message("assistant"):
        with st.spinner("생각 중..."):
            try:
                # 대화 이력 추출
                history = [{"role": m["role"], "content": m["content"]} 
                          for m in st.session_state.messages[:-1] 
                          if "type" not in m or m["type"] == "text"]
                
                # 글로벌 이벤트 루프에서 비동기 함수 직접 실행
                response_data = st.session_state.event_loop.run_until_complete(
                    get_mcp_response(prompt, history, st.session_state.timeout_seconds)
                )
                
                # 응답 추출 및 처리
                response_content = response_data.get("response", "응답을 받지 못했습니다.")
                processed_response = process_response(response_content)
                
                # 응답 표시
                if isinstance(processed_response, list):
                    # 여러 응답 처리
                    for item in processed_response:
                        if item["type"] == "text":
                            st.markdown(item["content"])
                        elif item["type"] == "image":
                            try:
                                import base64
                                from io import BytesIO
                                image_data = base64.b64decode(item["content"])
                                print(image_data)
                                st.image(BytesIO(image_data), caption=item.get("caption", ""))
                            except Exception as e:
                                st.error(f"이미지 처리 오류: {str(e)}")
                else:
                    # 단일 응답 처리
                    if processed_response["type"] == "text":
                        st.markdown(processed_response["content"])
                    elif processed_response["type"] == "image":
                        try:
                            import base64
                            from io import BytesIO
                            image_data = base64.b64decode(processed_response["content"])
                            st.image(BytesIO(image_data), caption=processed_response.get("caption", ""))
                        except Exception as e:
                            st.error(f"이미지 처리 오류: {str(e)}")
                
                # 세션에 저장
                if isinstance(processed_response, list):
                    for item in processed_response:
                        st.session_state.messages.append({
                            "role": "assistant",
                            **item
                        })
                else:
                    st.session_state.messages.append({
                        "role": "assistant",
                        **processed_response
                    })
                
            except Exception as e:
                # 오류 발생 시 대체 응답 사용
                response_content = f"처리 오류: {str(e)}"
                st.markdown(response_content)
                
                # 세션에 저장
                st.session_state.messages.append({
                    "role": "assistant",
                    "type": "text",
                    "content": response_content
                })