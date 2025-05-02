import logging
import streamlit as st
import time
import threading
import asyncio
from langchain_core.messages import HumanMessage
import os
from dotenv import load_dotenv
from mcp_client_agent import make_graph  # 비동기 컨텍스트 매니저 import

# 환경 변수 로드
load_dotenv()

logger = logging.getLogger(__name__)

# 세션 상태 초기화
if "agent" not in st.session_state:
    st.session_state.agent = None
if "server_info" not in st.session_state:
    st.session_state.server_info = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "error_message" not in st.session_state:
    st.session_state.error_message = None


def get_server_info(agent):
    """MCP 서버로부터 정보를 가져오는 함수"""
    if agent:
        try:
            result = agent.invoke({"messages": [HumanMessage(content="서버 상태 정보를 알려주세요.")]})
            return result
        except Exception as e:
            logger.error(f"서버 정보 가져오기 실패: {str(e)}")
            st.session_state.error_message = str(e)
            return None
    return None


def process_user_input(prompt, agent):
    """사용자 입력을 처리하고 에이전트에서 응답을 받아오는 함수"""
    if agent:
        try:
            result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
            response = result.get("messages", [])[-1].content
            return response
        except Exception as e:
            logger.error(f"에이전트 응답 처리 중 오류: {str(e)}")
            return f"오류가 발생했습니다: {str(e)}"
    else:
        return "MCP 서버에 연결되지 않았습니다. 잠시 후 다시 시도해주세요."


def setup_sidebar():
    """사이드바 설정"""
    with st.sidebar:
        st.title("MCP 서버 정보")
        st.divider()
        
        # MCP 서버 상태 표시
        st.subheader("연결 상태")
        
        # 새로고침 버튼
        if st.button("서버 정보 새로고침", key="refresh_server"):
            st.session_state.agent = None  # 에이전트 재초기화를 위해 None으로 설정
            st.rerun()
        
        # 서버 상태 표시
        if st.session_state.agent:
            if st.session_state.server_info:
                st.success("상태: 연결됨")
                
                # 서버 정보 표시
                st.subheader("서버 정보")
                
                # 서버 정보 파싱 및 표시
                server_content = st.session_state.server_info.get("messages", [])[-1].content
                st.info(f"서버 응답: {server_content}")
            else:
                st.warning("상태: 연결됨 (정보 없음)")
        elif st.session_state.error_message:
            st.error(f"상태: 연결 실패 - {st.session_state.error_message}")
            if st.button("재연결 시도", key="reconnect"):
                st.session_state.agent = None
                st.session_state.error_message = None
                st.rerun()
        else:
            st.warning("상태: 초기화 중...")
            st.info("서버 연결 대기 중...")


def init_chat_history():
    """채팅 히스토리 초기화"""
    if "messages" not in st.session_state:
        st.session_state.messages = []


def display_chat_history():
    """채팅 히스토리 표시"""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def handle_user_input(prompt, agent):
    """사용자 입력 처리 및 UI 업데이트"""
    # 사용자 메시지 추가
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 사용자 메시지 표시
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # 에이전트로부터 응답 받아오기
    with st.chat_message("assistant"):
        with st.spinner("응답 생성 중..."):
            response = process_user_input(prompt, agent)
            st.markdown(response)
    
    # 어시스턴트 응답 히스토리에 추가
    st.session_state.messages.append({"role": "assistant", "content": response})


def init_agent():
    """MCP 에이전트 초기화"""
    with st.status("MCP 서버에 연결 중...", expanded=True) as status:
        try:
            # 서버 연결 설정
            client_name = os.getenv("MCP_CLIENT_NAME", "mcp-server-test")
            server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000/sse")
            transport = os.getenv("MCP_TRANSPORT", "sse")
            
            st.write("서버 연결 설정 로드 완료")
            
            # 비동기 함수를 동기적으로 실행하는 헬퍼 함수
            def run_async(coro):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(coro)
                finally:
                    loop.close()
            
            # 비동기 함수 실행
            # make_graph는 비동기 컨텍스트 매니저이므로 코루틴으로 감싸서 실행
            async def init_agent_async():
                async with make_graph(client_name, server_url, transport) as agent:
                    return agent
            
            agent = run_async(init_agent_async())
            
            if agent:
                st.write("에이전트 초기화 완료")
                
                # 서버 상태 정보 가져오기 (동기식)
                st.write("서버 상태 정보 요청 중...")
                server_info = get_server_info(agent)
                
                if server_info:
                    st.write("서버 상태 정보 수신 완료")
                    status.update(label="MCP 서버 연결 성공", state="complete", expanded=False)
                else:
                    st.write("서버 상태 정보 수신 실패")
                    status.update(label="서버 정보 없음", state="complete", expanded=False)
                
                # 세션 상태에 저장
                st.session_state.agent = agent
                st.session_state.server_info = server_info
                
                return agent
            else:
                status.update(label="MCP 서버 연결 실패", state="error", expanded=True)
                return None
                
        except Exception as e:
            logger.error(f"MCP 서버 연결 실패: {str(e)}")
            st.session_state.error_message = str(e)
            status.update(label=f"MCP 서버 연결 실패: {str(e)}", state="error", expanded=True)
            return None


def run_chat_interface(agent):
    """채팅 인터페이스 실행"""
    # 사이드바 설정
    setup_sidebar()
    
    # 채팅 히스토리 초기화 및 표시
    init_chat_history()
    display_chat_history()
    
    # 사용자 입력 처리
    prompt = st.chat_input("질문을 입력해주세요")
    if prompt:
        handle_user_input(prompt, agent)


def main():
    """메인 함수"""
    st.title("MCP 연동 Streamlit 챗봇")
    
    # 에이전트 초기화 또는 기존 에이전트 사용
    agent = st.session_state.agent
    
    if agent is None:
        print("에이전트 초기화 중...")
        agent = init_agent()
    
    if agent:
        print("채팅 인터페이스 실행 중...")
        run_chat_interface(agent)
        
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Exit")