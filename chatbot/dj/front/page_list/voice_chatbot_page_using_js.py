"""
음성 챗봇 페이지 구현 - 다이나믹 UI
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
import json
import requests

# 로그 설정을 위한 함수
@st.cache_resource
def configure_logger():
    """로그 설정 함수 - 중복 로그 방지를 위해 캐시 리소스로 설정"""
    # 기존 로거 초기화
    logger.remove()
    
    # 로그 디렉토리 경로 설정
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "log")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "voice_chatbot_dynamic.log")
    
    # 로그 포맷 설정
    log_format = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
    
    # 파일 및 콘솔 로거 추가
    logger.add(log_file, rotation="10 MB", format=log_format, level="INFO")
    logger.add(sys.stderr, format=log_format, level="DEBUG")
    
    logger.info("다이나믹 UI 로그 시스템이 초기화되었습니다.")
    return logger

def send_audio_to_stt_server(audio_data):
    """STT 서버로 오디오 데이터를 전송하여 텍스트로 변환"""
    try:
        stt_server_url = "http://localhost:8504/transcribe"
        payload = {"audio_data": audio_data}
        
        logger.info("STT 서버로 오디오 데이터를 전송합니다...")
        response = requests.post(stt_server_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"STT 변환 성공: {result.get('transcript', '')} (신뢰도: {result.get('confidence', 0):.2f})")
            return result
        else:
            error_msg = f"STT 서버 오류: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
            
    except Exception as e:
        error_msg = f"STT 요청 중 오류 발생: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

def send_message_to_chatbot(message, session_id=None):
    """챗봇 API로 메시지를 전송하여 답변을 받음"""
    try:
        chatbot_server_url = "http://localhost:8800/ask"
        payload = {
            "message": message,
            "agent_mode": "general"
        }
        
        if session_id:
            payload["session_id"] = session_id
        
        logger.info(f"챗봇 API로 메시지 전송: '{message}'")
        response = requests.post(chatbot_server_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            chatbot_response = result.get('response', '')
            logger.info(f"챗봇 응답 수신: '{chatbot_response[:100]}...'")
            return {
                "success": True,
                "response": chatbot_response,
                "session_id": result.get('session_id', session_id)
            }
        else:
            error_msg = f"챗봇 서버 오류: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
            
    except Exception as e:
        error_msg = f"챗봇 요청 중 오류 발생: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

def send_text_to_tts_server(text):
    """TTS 서버로 텍스트를 전송하여 음성으로 변환"""
    try:
        tts_server_url = "http://localhost:8504/text-to-speech"
        payload = {"text": text}
        
        logger.info(f"TTS 서버로 텍스트를 전송합니다: '{text}'")
        response = requests.post(tts_server_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"TTS 변환 성공: {len(result.get('audio_data', ''))} 문자")
            return result
        else:
            error_msg = f"TTS 서버 오류: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
            
    except Exception as e:
        error_msg = f"TTS 요청 중 오류 발생: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

def save_audio_file(audio_data, file_type="wav"):
    """Base64 인코딩된 오디오 데이터를 임시 파일로 저장"""
    try:
        # 디코딩
        audio_bytes = base64.b64decode(audio_data)
        
        # 임시 디렉토리 생성
        temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        # 고유한 파일명 생성
        file_name = f"audio_{uuid.uuid4()}.{file_type}"
        file_path = os.path.join(temp_dir, file_name)
        
        # 파일 저장
        with open(file_path, "wb") as f:
            f.write(audio_bytes)
            
        return file_path
    except Exception as e:
        logger.error(f"오디오 파일 저장 중 오류 발생: {str(e)}")
        return None

def check_server_status():
    """서버 상태 확인"""
    # 음성 서버 상태 확인
    try:
        voice_response = requests.get("http://localhost:8504/health", timeout=2)
        if voice_response.status_code == 200:
            health_data = voice_response.json()
            stt_ready = health_data.get("speech_client_ready", False)
            tts_ready = health_data.get("tts_client_ready", False)
            voice_server_ready = stt_ready and tts_ready
        else:
            voice_server_ready = False
            stt_ready = False
            tts_ready = False
    except:
        voice_server_ready = False
        stt_ready = False
        tts_ready = False
    
    # 챗봇 서버 상태 확인
    try:
        chatbot_response = requests.get("http://localhost:8800/health", timeout=2)
        chatbot_ready = chatbot_response.status_code == 200
    except:
        chatbot_ready = False
    
    return {
        "voice_server_ready": voice_server_ready,
        "stt_ready": stt_ready,
        "tts_ready": tts_ready,
        "chatbot_ready": chatbot_ready
    }

def dynamic_voice_chatbot_page():
    """다이나믹 음성 챗봇 페이지 구현"""
    # 로거 설정
    log = configure_logger()
    log.info("다이나믹 음성 챗봇 페이지가 로드되었습니다.")
    
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
    
    # 세션 상태 초기화
    if 'audio_files' not in st.session_state:
        st.session_state.audio_files = []
    if 'conversations' not in st.session_state:
        st.session_state.conversations = []
    if 'chatbot_session_id' not in st.session_state:
        st.session_state.chatbot_session_id = None
    
    # CSS 파일 로드
    css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "css", "voice_chatbot.css")
    with open(css_path, "r") as f:
        css_content = f.read()
    
    # JS 파일 로드
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
            <!-- OpenAI 스타일 파도 애니메이션 -->
            <div id="waveContainer" class="wave-container">
                <div class="wave-bar idle"></div>
                <div class="wave-bar idle"></div>
                <div class="wave-bar idle"></div>
                <div class="wave-bar idle"></div>
                <div class="wave-bar idle"></div>
                <div class="wave-bar idle"></div>
                <div class="wave-bar idle"></div>
                <div class="wave-bar idle"></div>
            </div>
            
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
                AI 음성 챗봇
                <div class="info-icon">🎤</div>
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
        </script>
    </body>
    </html>
    """
    
    # HTML 컴포넌트 표시
    component_value = st.components.v1.html(voice_interface_html, height=700)
    log.debug("HTML 컴포넌트가 렌더링되었습니다.")
    
    # Streamlit에서 녹음 상태 확인을 위한 세션 상태 초기화
    if 'is_recording' not in st.session_state:
        st.session_state.is_recording = False
        log.info("녹음 상태가 초기화되었습니다.")
    
    # 컴포넌트로부터 받은 값 처리
    if component_value and isinstance(component_value, dict):
        # 녹음 상태 업데이트
        if 'isRecording' in component_value:
            previous_state = st.session_state.is_recording
            st.session_state.is_recording = component_value['isRecording']
            
            # 상태가 변경된 경우에만 로그 기록
            if previous_state != st.session_state.is_recording:
                log.info(f"녹음 상태가 변경되었습니다: {previous_state} -> {st.session_state.is_recording}")
        
        # 오디오 데이터 처리
        if 'audioData' in component_value and component_value['audioData']:
            log.info("오디오 데이터를 수신했습니다.")
            
            try:
                # STT 처리
                with st.spinner("🎤 음성을 텍스트로 변환 중..."):
                    stt_result = send_audio_to_stt_server(component_value['audioData'])
                    
                    if stt_result.get('success'):
                        transcript = stt_result.get('transcript', '')
                        confidence = stt_result.get('confidence', 0)
                        
                        st.success("🎤 음성 인식 완료!")
                        st.markdown(f"**📝 인식된 질문:** {transcript}")
                        st.markdown(f"*신뢰도: {confidence:.2f}*")
                        
                        # 챗봇에 질문 전송
                        with st.spinner("🤖 AI가 답변을 생성 중..."):
                            chatbot_result = send_message_to_chatbot(transcript, st.session_state.chatbot_session_id)
                            
                            if chatbot_result.get('success'):
                                chatbot_response = chatbot_result.get('response', '')
                                session_id = chatbot_result.get('session_id')
                                
                                # 세션 ID 업데이트
                                if session_id:
                                    st.session_state.chatbot_session_id = session_id
                                
                                st.success("🤖 AI 답변 완료!")
                                st.markdown(f"**💬 AI 답변:** {chatbot_response}")
                                
                                # TTS 변환 및 재생
                                with st.spinner("🔊 답변을 음성으로 변환 중..."):
                                    tts_result = send_text_to_tts_server(chatbot_response)
                                    
                                    if tts_result.get('success'):
                                        audio_data = tts_result.get('audio_data')
                                        st.success("🔊 음성 변환 완료! 자동 재생됩니다.")
                                        
                                        # Base64 디코딩하여 재생
                                        audio_bytes = base64.b64decode(audio_data)
                                        st.audio(audio_bytes, format='audio/wav', autoplay=True)
                                    else:
                                        st.warning(f"⚠️ 음성 변환 실패: {tts_result.get('error', '알 수 없는 오류')}")
                                
                                # 대화 기록 저장
                                st.session_state.conversations.append({
                                    'question': transcript,
                                    'answer': chatbot_response,
                                    'confidence': confidence,
                                    'timestamp': time.time()
                                })
                            else:
                                st.error(f"❌ 챗봇 응답 실패: {chatbot_result.get('error', '알 수 없는 오류')}")
                    else:
                        st.error(f"❌ 음성 인식 실패: {stt_result.get('error', '알 수 없는 오류')}")
                        
            except Exception as e:
                log.error(f"오디오 데이터 처리 중 오류 발생: {str(e)}")
                st.error(f"❌ 처리 중 오류: {str(e)}")
    
    # 대화 기록 표시
    if st.session_state.conversations:
        st.markdown("---")
        st.subheader("💬 최근 대화")
        
        # 최근 3개만 표시
        recent_conversations = list(reversed(st.session_state.conversations))[:3]
        
        for idx, conversation in enumerate(recent_conversations):
            with st.expander(f"🗣️ 대화 {len(st.session_state.conversations) - idx}", expanded=(idx == 0)):
                st.markdown(f"**👤 질문:** {conversation['question']}")
                st.markdown(f"**🤖 답변:** {conversation['answer']}")
                st.markdown(f"**🎯 신뢰도:** {conversation['confidence']:.2f}")
                
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(conversation['timestamp']))
                st.markdown(f"**⏰ 시간:** {timestamp}")
    
    # 서버 상태를 아래쪽에 접을 수 있도록 배치
    st.markdown("---")
    with st.expander("🔧 서버 상태 확인", expanded=False):
        server_status = check_server_status()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if server_status["voice_server_ready"]:
                st.success("🟢 음성 서버 연결됨")
            else:
                st.error("🔴 음성 서버 연결 안됨")
        
        with col2:
            if server_status["stt_ready"]:
                st.success("🎤 STT 준비됨")
            else:
                st.error("🎤 STT 준비 안됨")
        
        with col3:
            if server_status["tts_ready"]:
                st.success("🔊 TTS 준비됨")
            else:
                st.error("🔊 TTS 준비 안됨")
        
        with col4:
            if server_status["chatbot_ready"]:
                st.success("🤖 챗봇 준비됨")
            else:
                st.error("🤖 챗봇 준비 안됨")
        
        # 서버 실행 가이드
        if not all(server_status.values()):
            st.warning("⚠️ 일부 서버가 실행되지 않았습니다:")
            if not server_status["voice_server_ready"]:
                st.code("cd /Users/idongju/dev/dev-tool-with-llm/chatbot/dj/voice-back && python voice_server.py")
            if not server_status["chatbot_ready"]:
                st.code("cd /Users/idongju/dev/dev-tool-with-llm/chatbot/dj/back && python server.py")
    
    # 디버깅 정보 (개발용)
    with st.expander("🔍 디버깅 정보", expanded=False):
        st.write("녹음 상태:", "활성화" if st.session_state.is_recording else "비활성화")
        st.write("대화 수:", len(st.session_state.conversations))
        
        # 대화 기록 초기화 버튼
        if st.button("🗑️ 모든 대화 기록 삭제"):
            st.session_state.conversations = []
            st.session_state.chatbot_session_id = None
            st.success("✅ 모든 대화 기록이 삭제되었습니다.")
            st.rerun()
        
        # 임시 파일 정리 버튼
        if st.button("🧹 임시 파일 정리"):
            log.info("임시 파일 정리를 시작합니다.")
            temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp")
            
            if os.path.exists(temp_dir):
                # 임시 파일 삭제
                for file_name in os.listdir(temp_dir):
                    if file_name.startswith("audio_"):
                        try:
                            os.remove(os.path.join(temp_dir, file_name))
                            log.debug(f"파일 삭제: {file_name}")
                        except Exception as e:
                            log.error(f"파일 삭제 중 오류: {str(e)}")
            
            # 세션 상태 초기화
            st.session_state.audio_files = []
            log.info("임시 파일 정리가 완료되었습니다.")
            st.success("�� 임시 파일이 정리되었습니다.")