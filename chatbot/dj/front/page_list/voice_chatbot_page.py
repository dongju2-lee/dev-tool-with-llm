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
    log_file = os.path.join(log_dir, "voice_chatbot.log")
    
    # 로그 포맷 설정
    log_format = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
    
    # 파일 및 콘솔 로거 추가
    logger.add(log_file, rotation="10 MB", format=log_format, level="INFO")
    logger.add(sys.stderr, format=log_format, level="DEBUG")
    
    logger.info("로그 시스템이 초기화되었습니다.")
    return logger

def send_audio_to_stt_server(audio_data):
    """
    STT 서버로 오디오 데이터를 전송하여 텍스트로 변환
    
    Args:
        audio_data: Base64 인코딩된 오디오 데이터
        
    Returns:
        dict: STT 결과 (성공/실패, 텍스트, 신뢰도)
    """
    try:
        # STT 서버 URL (로컬 개발 환경)
        stt_server_url = "http://localhost:8504/transcribe"
        
        # 요청 데이터 준비
        payload = {
            "audio_data": audio_data
        }
        
        logger.info("STT 서버로 오디오 데이터를 전송합니다...")
        
        # STT 서버로 POST 요청
        response = requests.post(
            stt_server_url,
            json=payload,
            timeout=30  # 30초 타임아웃
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"STT 변환 성공: {result.get('transcript', '')} (신뢰도: {result.get('confidence', 0):.2f})")
            return result
        else:
            error_msg = f"STT 서버 오류: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
            
    except requests.exceptions.ConnectionError:
        error_msg = "STT 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요."
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }
    except requests.exceptions.Timeout:
        error_msg = "STT 서버 응답 시간이 초과되었습니다."
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }
    except Exception as e:
        error_msg = f"STT 요청 중 오류 발생: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

def save_audio_file(audio_data, file_type="wav"):
    """
    Base64 인코딩된 오디오 데이터를 임시 파일로 저장
    
    Args:
        audio_data: Base64 인코딩된 오디오 데이터
        file_type: 오디오 파일 타입 (기본값: wav)
        
    Returns:
        임시 파일 경로
    """
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

def process_audio_files():
    """
    temp_audio 디렉토리에서 WAV 파일을 찾아 처리하는 함수
    """
    log = configure_logger()
    temp_audio_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp_audio")
    
    # 디렉토리가 없으면 생성
    os.makedirs(temp_audio_dir, exist_ok=True)
    
    processed_files = []
    
    try:
        # WAV 파일 목록 가져오기
        wav_files = [f for f in os.listdir(temp_audio_dir) if f.endswith('.wav') and f.startswith('audio_')]
        
        if wav_files:
            log.info(f"🎵 {len(wav_files)}개의 오디오 파일을 발견했습니다: {wav_files}")
            
            for wav_file in wav_files:
                file_path = os.path.join(temp_audio_dir, wav_file)
                
                try:
                    # 파일을 Base64로 인코딩
                    with open(file_path, 'rb') as f:
                        audio_bytes = f.read()
                        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                    
                    log.info(f"📁 파일 처리 시작: {wav_file} (크기: {len(audio_bytes)} bytes)")
                    
                    # STT 서버로 전송
                    stt_result = send_audio_to_stt_server(audio_base64)
                    
                    if stt_result.get('success'):
                        transcript = stt_result.get('transcript', '')
                        confidence = stt_result.get('confidence', 0)
                        
                        # 변환된 텍스트를 세션에 저장
                        if 'transcripts' not in st.session_state:
                            st.session_state.transcripts = []
                        
                        st.session_state.transcripts.append({
                            'text': transcript,
                            'confidence': confidence,
                            'timestamp': time.time(),
                            'file_name': wav_file
                        })
                        
                        log.info(f"🎤 음성 인식 성공: '{transcript}' (신뢰도: {confidence:.2f})")
                        processed_files.append({
                            'file': wav_file,
                            'success': True,
                            'transcript': transcript,
                            'confidence': confidence
                        })
                    else:
                        error_msg = stt_result.get('error', '알 수 없는 오류')
                        log.error(f"STT 변환 실패: {error_msg}")
                        processed_files.append({
                            'file': wav_file,
                            'success': False,
                            'error': error_msg
                        })
                    
                    # 처리 완료된 파일 삭제
                    os.remove(file_path)
                    log.info(f"🗑️ 파일 삭제 완료: {wav_file}")
                    
                except Exception as e:
                    log.error(f"파일 처리 중 오류 ({wav_file}): {str(e)}")
                    processed_files.append({
                        'file': wav_file,
                        'success': False,
                        'error': str(e)
                    })
        
        return processed_files
        
    except Exception as e:
        log.error(f"오디오 파일 처리 중 전체 오류: {str(e)}")
        return []

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
    
    # 세션 상태 초기화
    if 'audio_files' not in st.session_state:
        st.session_state.audio_files = []
    
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
        <script src="https://cdn.jsdelivr.net/npm/streamlit-component-lib@1.3.0/dist/streamlit-component-lib.js"></script>
    </head>
    <body>
        <div class="voice-container">
            <!-- OpenAI 스타일 파도 애니메이션 - circle-container 밖으로 이동 -->
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
            // Streamlit 컴포넌트 초기화
            window.Streamlit = window.Streamlit || {{}};
            
            // 컴포넌트 준비 완료 알림
            if (window.Streamlit.setComponentReady) {{
                window.Streamlit.setComponentReady();
            }}
            
            // 글로벌 변수 폴링 (오디오 데이터 감지)
            let lastAudioData = null;
            
            function checkForAudioData() {{
                if (window.streamlitAudioData && window.streamlitAudioData !== lastAudioData) {{
                    console.log('글로벌 변수에서 새로운 오디오 데이터 감지:', window.streamlitAudioData);
                    
                    // Streamlit으로 데이터 전송
                    if (window.Streamlit && window.Streamlit.setComponentValue) {{
                        window.Streamlit.setComponentValue(window.streamlitAudioData);
                        console.log('글로벌 변수 데이터를 Streamlit으로 전송 완료');
                    }}
                    
                    lastAudioData = window.streamlitAudioData;
                    window.streamlitAudioData = null; // 처리 후 초기화
                }}
            }}
            
            // 500ms마다 글로벌 변수 확인
            setInterval(checkForAudioData, 500);
            
            {js_content}
        </script>
    </body>
    </html>
    """
    
    # HTML 컴포넌트 표시 - key 파라미터 제거 (지원되지 않음)
    component_value = st.components.v1.html(
        voice_interface_html, 
        height=700
    )
    log.debug("HTML 컴포넌트가 렌더링되었습니다.")
    
    # JavaScript에서 전송된 오디오 데이터 처리
    if component_value is not None:
        log.info(f"컴포넌트에서 수신한 데이터 타입: {type(component_value)}")
        log.info(f"컴포넌트 데이터 내용: {str(component_value)[:200]}...")  # 처음 200자만 로깅
        
        # 다양한 형태의 데이터 처리
        audio_data = None
        
        # 딕셔너리 형태인 경우
        if isinstance(component_value, dict):
            if component_value.get('type') == 'audio_data':
                audio_data = component_value
                log.info("딕셔너리 형태의 오디오 데이터 감지")
            elif 'audioBase64' in component_value:
                audio_data = component_value
                log.info("audioBase64 키가 있는 데이터 감지")
        
        # 문자열 형태인 경우 (JSON 파싱 시도)
        elif isinstance(component_value, str):
            try:
                import json
                parsed_data = json.loads(component_value)
                if isinstance(parsed_data, dict) and (parsed_data.get('type') == 'audio_data' or 'audioBase64' in parsed_data):
                    audio_data = parsed_data
                    log.info("JSON 문자열에서 오디오 데이터 파싱 성공")
            except:
                log.debug("문자열 데이터를 JSON으로 파싱할 수 없음")
        
        # 오디오 데이터 처리
        if audio_data:
            try:
                file_name = audio_data.get('fileName')
                audio_base64 = audio_data.get('audioBase64')
                
                log.info(f"처리할 파일명: {file_name}")
                log.info(f"Base64 데이터 길이: {len(audio_base64) if audio_base64 else 0}")
                
                if file_name and audio_base64:
                    # temp_audio 디렉토리 경로
                    temp_audio_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp_audio")
                    os.makedirs(temp_audio_dir, exist_ok=True)
                    
                    # 파일 경로 생성
                    file_path = os.path.join(temp_audio_dir, file_name)
                    
                    # Base64 디코딩하여 WAV 파일로 저장
                    audio_bytes = base64.b64decode(audio_base64)
                    
                    with open(file_path, 'wb') as f:
                        f.write(audio_bytes)
                    
                    log.info(f"🎵 오디오 파일 저장 완료: {file_name} (크기: {len(audio_bytes)} bytes)")
                    st.success(f"🎵 오디오 파일이 저장되었습니다: {file_name}")
                    
                    # 즉시 파일 처리
                    processed_files = process_audio_files()
                    if processed_files:
                        for result in processed_files:
                            if result['success']:
                                st.success(f"🎤 음성 인식 완료: {result['transcript']} (신뢰도: {result['confidence']:.2f})")
                            else:
                                st.error(f"❌ 음성 인식 실패: {result['error']}")
                    
                    # UI 새로고침
                    st.rerun()
                else:
                    log.warning(f"파일명 또는 Base64 데이터가 누락됨: fileName={file_name}, audioBase64 길이={len(audio_base64) if audio_base64 else 0}")
                    
            except Exception as e:
                log.error(f"오디오 데이터 처리 중 오류: {str(e)}")
                st.error(f"오디오 처리 오류: {str(e)}")
        else:
            log.debug(f"오디오 데이터가 아닌 일반 컴포넌트 데이터 수신")
    else:
        log.debug("component_value가 None입니다.")
    
    # Streamlit에서 녹음 상태 확인을 위한 세션 상태 초기화
    if 'is_recording' not in st.session_state:
        st.session_state.is_recording = False
        log.info("녹음 상태가 초기화되었습니다.")
    
    # 파일 폴링 시스템 - 2초마다 temp_audio 디렉토리 확인
    if 'last_poll_time' not in st.session_state:
        st.session_state.last_poll_time = 0
    
    current_time = time.time()
    if current_time - st.session_state.last_poll_time >= 2:  # 2초마다 폴링
        st.session_state.last_poll_time = current_time
        
        # 오디오 파일 처리 (JavaScript에서 직접 전송되지 않은 파일들)
        processed_files = process_audio_files()
        
        if processed_files:
            log.info(f"🔄 {len(processed_files)}개 파일 처리 완료")
            
            # 처리 결과를 UI에 표시
            for result in processed_files:
                if result['success']:
                    st.success(f"🎤 음성 인식 완료: {result['transcript']} (신뢰도: {result['confidence']:.2f})")
                else:
                    st.error(f"❌ 음성 인식 실패 ({result['file']}): {result['error']}")
            
            # 페이지 새로고침으로 UI 업데이트
            st.rerun()
    
    # 실시간 상태 표시
    col1, col2 = st.columns(2)
    with col1:
        if st.session_state.is_recording:
            st.success("🔴 녹음 중...")
        else:
            st.info("⚪ 대기 중")
    
    with col2:
        # STT 서버 상태 확인
        try:
            response = requests.get("http://localhost:8504/health", timeout=2)
            if response.status_code == 200:
                st.success("🟢 STT 서버 연결됨")
            else:
                st.error("🔴 STT 서버 오류")
        except:
            st.error("🔴 STT 서버 연결 안됨")
    
    # 디버깅용 (실제 앱에서는 숨김 처리 가능)
    with st.expander("디버깅 정보", expanded=False):
        st.write("녹음 상태:", "활성화" if st.session_state.is_recording else "비활성화")
        
        # STT 변환 결과 표시
        if 'transcripts' in st.session_state and st.session_state.transcripts:
            st.write("### 🎤 음성 인식 결과:")
            for idx, transcript_data in enumerate(reversed(st.session_state.transcripts[-5:])):  # 최근 5개만 표시
                timestamp = time.strftime("%H:%M:%S", time.localtime(transcript_data['timestamp']))
                st.write(f"**{len(st.session_state.transcripts)-idx}.** [{timestamp}] {transcript_data['text']} (신뢰도: {transcript_data['confidence']:.2f})")
        
        # 저장된 오디오 파일 목록
        if st.session_state.audio_files:
            st.write("### 📁 저장된 오디오 파일:")
            for idx, file_path in enumerate(st.session_state.audio_files):
                st.write(f"{idx+1}. {os.path.basename(file_path)}")
                if os.path.exists(file_path):
                    st.audio(file_path, format='audio/wav')
        
        # STT 서버 연결 테스트 버튼
        if st.button("🔗 STT 서버 연결 테스트"):
            try:
                response = requests.get("http://localhost:8504/health", timeout=5)
                if response.status_code == 200:
                    result = response.json()
                    if result.get("speech_client_ready"):
                        st.success("✅ STT 서버가 정상적으로 실행 중이며 Google Speech 클라이언트가 준비되었습니다.")
                    else:
                        st.warning("⚠️ STT 서버는 실행 중이지만 Google Speech 클라이언트가 준비되지 않았습니다.")
                else:
                    st.error(f"❌ STT 서버 응답 오류: {response.status_code}")
            except requests.exceptions.ConnectionError:
                st.error("❌ STT 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
            except Exception as e:
                st.error(f"❌ 연결 테스트 중 오류: {str(e)}")
        
        # 수동 오디오 테스트 버튼 (디버깅용)
        if st.button("🎤 수동 오디오 테스트"):
            # 더미 오디오 데이터로 테스트
            import base64
            
            # 간단한 더미 WAV 헤더 생성 (실제로는 빈 오디오)
            dummy_wav = b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
            dummy_base64 = base64.b64encode(dummy_wav).decode('utf-8')
            
            log.info("🧪 수동 오디오 테스트를 시작합니다...")
            
            # STT 서버로 더미 데이터 전송
            with st.spinner("더미 오디오 데이터를 STT 서버로 전송 중..."):
                stt_result = send_audio_to_stt_server(dummy_base64)
                
                if stt_result.get('success'):
                    st.success(f"✅ STT 테스트 성공: {stt_result.get('transcript', '(빈 결과)')}")
                else:
                    st.error(f"❌ STT 테스트 실패: {stt_result.get('error', '알 수 없는 오류')}")
                    
                log.info(f"수동 테스트 결과: {stt_result}")
        
        # JavaScript 통신 상태 확인
        st.write("### 🔧 파일 폴링 시스템 상태")
        
        temp_audio_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp_audio")
        
        # 디렉토리 상태 확인
        if os.path.exists(temp_audio_dir):
            wav_files = [f for f in os.listdir(temp_audio_dir) if f.endswith('.wav') and f.startswith('audio_')]
            st.write(f"📁 temp_audio 디렉토리: 존재함")
            st.write(f"🎵 대기 중인 WAV 파일: {len(wav_files)}개")
            if wav_files:
                st.write("파일 목록:", wav_files)
        else:
            st.write("📁 temp_audio 디렉토리: 존재하지 않음")
        
        # 마지막 폴링 시간
        if 'last_poll_time' in st.session_state:
            last_poll = time.strftime("%H:%M:%S", time.localtime(st.session_state.last_poll_time))
            next_poll = time.strftime("%H:%M:%S", time.localtime(st.session_state.last_poll_time + 2))
            st.write(f"⏰ 마지막 폴링: {last_poll}")
            st.write(f"⏰ 다음 폴링: {next_poll}")
        
        # 수동 파일 처리 버튼
        if st.button("🔄 수동 파일 처리"):
            processed_files = process_audio_files()
            if processed_files:
                st.write(f"처리된 파일: {len(processed_files)}개")
                for result in processed_files:
                    if result['success']:
                        st.success(f"✅ {result['file']}: {result['transcript']}")
                    else:
                        st.error(f"❌ {result['file']}: {result['error']}")
            else:
                st.info("처리할 파일이 없습니다.")