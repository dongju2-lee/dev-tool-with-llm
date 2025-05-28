"""
음성 챗봇 페이지 구현
"""

import streamlit as st
import time
import os
import base64
import uuid
import tempfile
from pathlib import Path
from loguru import logger
import sys

# 로그 설정을 위한 함수
@st.cache_resource
def configure_logger():
    """로그 설정 함수 - 중복 로그 방지를 위해 캐시 리소스로 설정"""
    # 기존 로거 초기화
    logger.remove()
    
    # 로그 디렉토리 경로 설정
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "log")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "voice_chatbot.log")
    
    # 로그 포맷 설정
    log_format = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
    
    # 파일 및 콘솔 로거 추가
    logger.add(log_file, rotation="10 MB", format=log_format, level="INFO")
    logger.add(sys.stderr, format=log_format, level="DEBUG")
    
    logger.info("로그 시스템이 초기화되었습니다.")
    return logger

def voice_chatbot_page():
    """음성 챗봇 페이지 구현"""
    # 로거 설정
    log = configure_logger()
    log.info("음성 챗봇 페이지가 로드되었습니다.")
    
    # 페이지 타이틀 숨기기
    st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }
        header {
            visibility: hidden;
        }
        #MainMenu {
            visibility: hidden;
        }
        footer {
            visibility: hidden;
        }
        .stDeployButton {
            display: none;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # CSS 파일 로드 - 경로 문제 해결
    css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "css", "voice_chatbot.css")
    with open(css_path, "r") as f:
        css_content = f.read()
    
    # JS 파일 로드 - 인라인으로 포함
    js_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "css", "voice_chatbot.js")
    with open(js_path, "r") as f:
        js_content = f.read()
    
    log.debug(f"CSS 및 JS 파일을 성공적으로 로드했습니다. CSS: {css_path}, JS: {js_path}")
    
    # HTML 구성요소 (인라인 CSS 및 JS 포함)
    voice_interface_html = f"""
    <html>
    <head>
        <style>
            {css_content}
        </style>
    </head>
    <body>
        <div class="voice-container">
            <div id="circleContainer" class="circle-container idle">
                <div class="voice-circle">
                    <canvas id="audioCanvas" class="audio-canvas"></canvas>
                    <div class="stars" id="starsContainer"></div>
                    <div class="voice-visualizer">
                        <div class="audio-pulse audio-pulse-1"></div>
                        <div class="audio-pulse audio-pulse-2"></div>
                        <div class="audio-pulse audio-pulse-3"></div>
                    </div>
                </div>
            </div>
            
            <div class="voice-indicator">
                Standard voice
                <div class="info-icon">i</div>
            </div>
            
            <div class="controls">
                <button id="micButton" class="mic-button">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                        <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                        <line x1="12" y1="19" x2="12" y2="23"></line>
                        <line x1="8" y1="23" x2="16" y2="23"></line>
                    </svg>
                </button>
            </div>
        </div>
        
        <script>
            {js_content}
            
            // Streamlit과 통신하기 위한 코드를 수정
            window.addEventListener('message', function(event) {{
                if (event.data.type === 'recordingState') {{
                    const data = {{
                        isRecording: event.data.isRecording
                    }};
                    
                    // Streamlit에 데이터 전송
                    window.parent.postMessage({{
                        type: 'streamlit:setComponentValue',
                        value: data
                    }}, '*');
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    # HTML 컴포넌트 표시
    component_value = st.components.v1.html(voice_interface_html, height=700)
    log.debug("HTML 컴포넌트가 렌더링되었습니다.")
    
    # Streamlit에서 녹음 상태 확인을 위한 세션 상태 초기화
    if 'is_recording' not in st.session_state:
        st.session_state.is_recording = True
        log.info("녹음 상태가 초기화되었습니다.")
    
    # 컴포넌트로부터 받은 값을 처리
    if component_value and isinstance(component_value, dict) and 'isRecording' in component_value:
        previous_state = st.session_state.is_recording
        st.session_state.is_recording = component_value['isRecording']
        
        # 상태가 변경된 경우에만 로그 기록
        if previous_state != st.session_state.is_recording:
            log.info(f"녹음 상태가 변경되었습니다: {previous_state} -> {st.session_state.is_recording}")
    
    # 디버깅용 (실제 앱에서는 숨김 처리 가능)
    with st.expander("디버깅 정보", expanded=False):
        st.write("녹음 상태:", "활성화" if st.session_state.is_recording else "비활성화")
        
        if st.button("음성 처리 테스트"):
            log.info("음성 처리 테스트 버튼이 클릭되었습니다.")
            with st.spinner("음성을 처리 중입니다..."):
                # 실제로는 여기서 음성 인식 및 챗봇 처리 로직이 필요함
                log.debug("음성 처리를 시뮬레이션합니다...")
                time.sleep(2)
                
                # 음성 처리 결과 표시 (예시)
                st.session_state.last_voice_input = "안녕하세요, 무엇을 도와드릴까요?"
                st.session_state.last_response = "안녕하세요! 오늘 도움이 필요하신 내용이 있으신가요?"
                log.info(f"음성 처리 결과 - 입력: {st.session_state.last_voice_input}, 응답: {st.session_state.last_response}")
            
            # 처리 결과 표시
            if 'last_voice_input' in st.session_state and 'last_response' in st.session_state:
                st.text_area("음성 입력:", value=st.session_state.last_voice_input, height=100)
                st.text_area("챗봇 응답:", value=st.session_state.last_response, height=100)
                log.debug("음성 처리 결과가 UI에 표시되었습니다.")