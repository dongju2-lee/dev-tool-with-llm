"""
스마트홈 관리 시스템 메인 애플리케이션
"""

import streamlit as st
import nest_asyncio

from page_list.chatbot_page import chatbot_page
from page_list.rag_page import rag_page
from page_list.voice_chatbot_page import voice_chatbot_page
from page_list.helpers import (
    CHATBOT_PAGE,
    RAG_PAGE,
    VOICE_CHATBOT_PAGE,
)
from utils.logging_config import setup_logger

# 비동기 중첩 실행 허용
nest_asyncio.apply()

# 로거 설정
logger = setup_logger("app")


class MultiApp:
    """여러 페이지를 관리하는 멀티앱 클래스"""

    def __init__(self):
        self.apps = []

    def add_app(self, title, func):
        """앱 페이지 추가"""
        self.apps.append({"title": title, "function": func})

    def run(self):
        """멀티앱 실행"""
        # 페이지 설정
        st.set_page_config(
            page_title="Dev Tool 매니저",
            page_icon="🏠",
            layout="wide",
            initial_sidebar_state="expanded",
        )

        # 사이드바 설정
        with st.sidebar:
            st.title("Dev Tool 매니저 🏠")
            st.markdown("## 메인 메뉴")

            # 페이지 선택 셀렉트박스
            selected_app = st.selectbox(
                "페이지 선택", self.apps, format_func=lambda app: app["title"]
            )

            st.markdown("---")

            # 설정 섹션
            st.subheader("설정")

            # 챗봇 페이지일 때만 스트리밍 모드와 지연 시간 설정 표시
            if selected_app["title"] == CHATBOT_PAGE:
                # 스트리밍 모드 설정
                streaming_mode = st.checkbox(
                    "응답 스트리밍 모드",
                    value=st.session_state.get("streaming_mode", True),
                )
                if (
                    "streaming_mode" not in st.session_state
                    or st.session_state.streaming_mode != streaming_mode
                ):
                    st.session_state.streaming_mode = streaming_mode

                # 스트리밍 지연 시간 설정
                if streaming_mode:
                    word_delay = st.slider(
                        "단어 지연 시간 (초)",
                        min_value=0.0,
                        max_value=0.1,
                        value=st.session_state.get("word_delay", 0.01),
                        step=0.01,
                        format="%.2f",
                    )
                    if (
                        "word_delay" not in st.session_state
                        or st.session_state.word_delay != word_delay
                    ):
                        st.session_state.word_delay = word_delay
            elif selected_app["title"] == RAG_PAGE:
                # RAG 페이지일 경우 설정 정보 표시
                st.info(
                    "RAG 문서 관리 페이지입니다. 로컬 파일을 업로드하여 분석할 수 있습니다."
                )
            elif selected_app["title"] == VOICE_CHATBOT_PAGE:
                # Voice Chatbot 페이지일 경우 설정 정보 표시
                st.info(
                    "Voice Chatbot 페이지입니다. 음성 챗봇을 사용할 수 있습니다."
                )
            elif selected_app["title"] == DYNAMIC_UI_PAGE:
                # Dynamic UI 페이지일 경우 설정 정보 표시
                st.info(
                    "다이나믹 UI 페이지입니다. JavaScript와 CSS로 구현된 인터랙티브 음성 인터페이스를 사용할 수 있습니다."
                )

        # 선택한 앱 실행
        selected_app["function"]()


# 메인 실행 코드
if __name__ == "__main__":
    # 멀티앱 인스턴스 생성
    app = MultiApp()

    # 앱 등록
    app.add_app(CHATBOT_PAGE, chatbot_page)
    app.add_app(RAG_PAGE, rag_page)
    app.add_app(VOICE_CHATBOT_PAGE, voice_chatbot_page)

    # 앱 실행
    app.run()