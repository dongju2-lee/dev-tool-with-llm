import streamlit as st
import os
import sys
import uuid
import asyncio
import logging
import traceback
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

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
        "gemini-2.0-flash": "Gemini 2.0 Flash",
        "gemini-1.5-flash": "Gemini 1.5 Flash"
    }
    selected_model = st.selectbox(
        "Gemini 모델",
        options=list(model_options.keys()),
        format_func=lambda x: model_options[x],
        index=0,
        help="사용할 Gemini 모델을 선택하세요"
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
            
            # 비동기 함수 실행
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            connection_result = loop.run_until_complete(test_connection())
            loop.close()
            
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

# MCP 에이전트를 통한 응답 생성 함수
async def get_mcp_response(query, history):
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
            
            # 에이전트 호출
            result = await agent.ainvoke({"messages": messages})
            return {
                "response": str(result),
                "status": "success"
            }
    except Exception as e:
        logger.error(f"MCP 응답 생성 오류: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "response": f"오류가 발생했습니다: {str(e)}",
            "status": "error"
        }

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
                
                # 비동기 함수 실행
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                response_data = loop.run_until_complete(get_mcp_response(prompt, history))
                loop.close()
                
                # 응답 추출
                response_content = response_data.get("response", "응답을 받지 못했습니다.")
                
                # 응답 표시
                st.markdown(response_content)
                
                # 세션에 저장
                st.session_state.messages.append({
                    "role": "assistant",
                    "type": "text",
                    "content": response_content
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