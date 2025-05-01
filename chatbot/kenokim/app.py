import streamlit as st
import random
import io
from PIL import Image
import os
import uuid
from api.client import MCPClient

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

# strangekino.png 이미지 로드 함수
def load_strangekino_image():
    # 현재 스크립트의 디렉토리 위치 확인
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 이미지 경로 지정
    image_path = os.path.join(current_dir, "strangekino.png")
    
    try:
        # 이미지 파일 열기
        return Image.open(image_path)
    except Exception as e:
        st.error(f"이미지 로드 오류: {str(e)}")
        # 오류 발생 시 빈 이미지 반환
        return Image.new('RGB', (100, 100), color=(255, 0, 0))

# 간단한 응답 목록 (MCP 연동 실패 시 폴백용)
responses = [
    "흥미로운 질문이네요!",
    "더 자세히 설명해주실래요?",
    "그것에 대해 더 생각해볼게요.",
    "좋은 질문입니다!",
    "무엇을 도와드릴까요?",
]

# 페이지 제목 설정
st.title("슬라임 챗봇")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

# MCP 클라이언트 초기화
mcp_client = MCPClient()

# 사이드바 설정
with st.sidebar:
    st.header("설정")
    
    # MCP 서버 URL 표시
    mcp_url = os.environ.get("MCP_SERVER_URL", "http://localhost:8000")
    st.text_input("MCP 서버 URL", value=mcp_url, disabled=True)
    
    # 응답 생성 방식 선택
    response_type = st.radio(
        "응답 생성 방식",
        ["스트레인지 키노", "MCP 서버", "기본 (랜덤)"]
    )
    
    # 서버 상태 확인
    if st.button("서버 상태 확인"):
        try:
            status = mcp_client.check_connection()
            st.success(f"서버 상태: {status['status']}, 모델: {status.get('model', 'N/A')}")
        except Exception as e:
            st.error(f"서버 연결 오류: {str(e)}")
            # 연결 오류 시 로컬 모드로 전환
            response_type = "기본 (랜덤)"
    
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
            # 스트레인지 키노 이미지 응답 모드
            if response_type == "스트레인지 키노":
                # 이미지 로드
                image = load_strangekino_image()
                
                # 응답 텍스트
                response_text = "안녕하세요! 저는 스트레인지 키노예요~"
                st.markdown(response_text)
                
                # 이미지 표시
                st.image(image, caption="스트레인지 키노", use_column_width=True)
                
                # 세션에 저장
                st.session_state.messages.append({
                    "role": "assistant",
                    "type": "image",
                    "content": image,
                    "caption": "스트레인지 키노",
                    "text": response_text
                })
            elif response_type == "MCP 서버":
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
                    response_content = f"MCP 서버 연결 오류: {str(e)}\n\n기본 응답: {random.choice(responses)}"
                    st.markdown(response_content)
                    
                    # 세션에 저장
                    st.session_state.messages.append({
                        "role": "assistant",
                        "type": "text",
                        "content": response_content
                    })
            else:
                # 기본 응답 생성 (랜덤)
                response = random.choice(responses) + f"\n\n당신의 메시지: {prompt}"
                st.markdown(response)
                
                # 세션에 저장
                st.session_state.messages.append({
                    "role": "assistant",
                    "type": "text",
                    "content": response
                }) 