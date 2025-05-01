import streamlit as st
import os
import sys
import uuid
from dotenv import load_dotenv
from api.client import MCPClient

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 이제 상대 경로로 임포트
from langchain_gemini_mcp_client import GeminiMCPClient

# 환경 변수 로드
load_dotenv()

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

# 세션에 LangGraph MCP 클라이언트 초기화
if "mcp_react_client" not in st.session_state:
    st.session_state.mcp_react_client = None

# 사이드바 설정
with st.sidebar:
    st.header("설정")
    # Gemini 모델 선택
    model_options = {
        "gemini-2.0-flash": "Gemini Flash"
    }
    selected_model = st.selectbox(
        "Gemini 모델",
        options=list(model_options.keys()),
        format_func=lambda x: model_options[x],
        index=0,
        help="사용할 Gemini 모델을 선택하세요"
    )
    
    # 응답 생성 방식 선택
    response_type = st.radio(
        "응답 생성 방식",
        ["MCP 서버", "MCP_REACT (LangGraph)"]
    )

# MCP 클라이언트 초기화 - 사이드바에서 선택한 모델 사용
try:
    mcp_client = MCPClient(model_name=selected_model)
    st.sidebar.success(f"Vertex AI 연결 성공 (모델: {model_options[selected_model]})")
except Exception as e:
    st.sidebar.error(f"Vertex AI 연결 오류: {str(e)}")
    st.sidebar.warning("환경 변수 설정을 확인하세요 (VERTEX_API_KEY, GCP_PROJECT_ID)")
    mcp_client = None

# LangGraph MCP 클라이언트 초기화
if response_type == "MCP_REACT (LangGraph)" and st.session_state.mcp_react_client is None:
    try:
        with st.sidebar:
            with st.spinner("LangGraph MCP 클라이언트 초기화 중..."):
                # 새로운 초기화 방식으로 변경
                st.session_state.mcp_react_client = GeminiMCPClient(
                    model_name=selected_model,
                    # 필요시 API 키 직접 전달 가능
                    # api_key="YOUR_API_KEY"
                )
                st.session_state.mcp_react_client.initialize()
                st.success("LangGraph MCP 클라이언트 초기화 성공")
    except Exception as e:
        st.sidebar.error(f"LangGraph MCP 클라이언트 초기화 오류: {str(e)}")
        st.session_state.mcp_react_client = None

# 서버 상태 확인 버튼
with st.sidebar:
    if st.button("서버 상태 확인"):
        if response_type == "MCP_REACT (LangGraph)" and st.session_state.mcp_react_client:
            try:
                status = st.session_state.mcp_react_client.check_connection()
                st.success(f"LangGraph MCP 서버 상태: {status['status']}, 모델: {status.get('model', 'N/A')}")
                if status['status'] == 'online':
                    st.info(f"사용 가능한 도구: {', '.join(status.get('available_tools', []))}")
            except Exception as e:
                st.error(f"LangGraph MCP 서버 연결 오류: {str(e)}")
        elif mcp_client:
            try:
                status = mcp_client.check_connection()
                st.success(f"MCP 서버 상태: {status['status']}, 모델: {status.get('model', 'N/A')}")
            except Exception as e:
                st.error(f"MCP 서버 연결 오류: {str(e)}")
                # 연결 오류 시 로컬 모드로 전환
                response_type = "기본 (랜덤)"
        else:
            st.error("클라이언트 초기화에 실패했습니다")
    
    # 도구 목록 표시 영역
    st.subheader("사용 가능한 도구")
    if st.button("도구 목록 가져오기"):
        if response_type == "MCP_REACT (LangGraph)" and st.session_state.mcp_react_client:
            try:
                with st.spinner("도구 목록 가져오는 중..."):
                    tools = st.session_state.mcp_react_client.get_tools()
                    if tools:
                        st.success(f"{len(tools)}개의 도구를 찾았습니다")
                        for tool in tools:
                            with st.expander(f"🔧 {tool['name']}"):
                                st.write(tool.get('description', '설명 없음'))
                    else:
                        st.warning("사용 가능한 도구가 없습니다")
            except Exception as e:
                st.error(f"도구 목록 가져오기 오류: {str(e)}")
    
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

# 사용자 입력 처리
if prompt := st.chat_input("무엇이든 물어보세요"):
    # 사용자 메시지 추가 및 표시
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # 응답 생성
    with st.chat_message("assistant"):
        with st.spinner("생각 중..."):
            if response_type == "MCP 서버" and mcp_client:
                try:
                    # MCP 서버로 메시지 전송
                    response_data = mcp_client.process_query(
                        query=prompt,
                        history=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1] if "type" not in m or m["type"] == "text"]
                    )
                    
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
                    response_content = f"MCP 서버 연결 오류: {str(e)}"
                    st.markdown(response_content)
                    
                    # 세션에 저장
                    st.session_state.messages.append({
                        "role": "assistant",
                        "type": "text",
                        "content": response_content
                    })
            elif response_type == "MCP_REACT (LangGraph)" and st.session_state.mcp_react_client:
                try:
                    # 대화 이력 추출
                    history = [{"role": m["role"], "content": m["content"]} 
                              for m in st.session_state.messages[:-1] 
                              if "type" not in m or m["type"] == "text"]
                    
                    # LangGraph MCP ReAct 에이전트로 메시지 전송
                    response_data = st.session_state.mcp_react_client.process_query(
                        query=prompt,
                        history=history,
                        thread_id=st.session_state.thread_id
                    )
                    
                    # 응답 추출
                    response_content = response_data.get("response", "응답을 받지 못했습니다.")
                    
                    # 도구 출력 정보 추가
                    tool_outputs = response_data.get("tool_outputs", [])
                    if tool_outputs:
                        tool_info = "\n\n**도구 사용 정보:**\n"
                        for tool_output in tool_outputs:
                            tool_info += f"- **{tool_output.get('tool', '알 수 없음')}**: {tool_output.get('result', '')}\n"
                        response_content += tool_info
                    
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
                    response_content = f"LangGraph MCP 처리 오류: {str(e)}"
                    st.markdown(response_content)
                    
                    # 세션에 저장
                    st.session_state.messages.append({
                        "role": "assistant",
                        "type": "text",
                        "content": response_content
                    })
            else:
                # 응답 생성 방식이 없거나 클라이언트가 초기화되지 않은 경우
                response_content = "죄송합니다. 선택한 응답 생성 방식에 대한 서비스가 초기화되지 않았습니다."
                st.markdown(response_content)
                
                # 세션에 저장
                st.session_state.messages.append({
                    "role": "assistant",
                    "type": "text",
                    "content": response_content
                }) 