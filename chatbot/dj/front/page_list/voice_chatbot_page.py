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

def send_text_to_tts_server(text):
    """
    TTS 서버로 텍스트를 전송하여 음성으로 변환
    
    Args:
        text: 변환할 텍스트
        
    Returns:
        dict: TTS 결과 (성공/실패, 오디오 데이터)
    """
    try:
        # TTS 서버 URL
        tts_server_url = "http://localhost:8504/text-to-speech"
        
        # 요청 데이터 준비
        payload = {
            "text": text
        }
        
        logger.info(f"TTS 서버로 텍스트를 전송합니다: '{text}'")
        
        # TTS 서버로 POST 요청
        response = requests.post(
            tts_server_url,
            json=payload,
            timeout=30  # 30초 타임아웃
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"TTS 변환 성공: {len(result.get('audio_data', ''))} 문자")
            return result
        else:
            error_msg = f"TTS 서버 오류: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
            
    except requests.exceptions.ConnectionError:
        error_msg = "TTS 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요."
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }
    except requests.exceptions.Timeout:
        error_msg = "TTS 서버 응답 시간이 초과되었습니다."
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }
    except Exception as e:
        error_msg = f"TTS 요청 중 오류 발생: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

def play_audio_from_base64(audio_base64):
    """
    Base64 오디오 데이터를 재생
    
    Args:
        audio_base64: Base64 인코딩된 오디오 데이터
    """
    try:
        # Base64 디코딩
        audio_bytes = base64.b64decode(audio_base64)
        
        # Streamlit 오디오 컴포넌트로 재생
        st.audio(audio_bytes, format='audio/wav', autoplay=True)
        logger.info("TTS 오디오 재생 시작")
        
    except Exception as e:
        logger.error(f"오디오 재생 중 오류: {str(e)}")
        st.error(f"❌ 오디오 재생 실패: {str(e)}")

def voice_chatbot_page():
    """음성 챗봇 페이지 구현 - 심플 버전"""
    # 로거 설정
    log = configure_logger()
    log.info("음성 챗봇 페이지가 로드되었습니다.")
    
    # 페이지 설정
    st.title("🎤 음성 챗봇")
    st.markdown("음성을 녹음하면 자동으로 텍스트로 변환됩니다.")
    st.markdown("---")
    
    # 세션 상태 초기화
    if 'transcripts' not in st.session_state:
        st.session_state.transcripts = []
    
    # temp_audio 디렉토리 설정
    temp_audio_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp_audio")
    os.makedirs(temp_audio_dir, exist_ok=True)
    
    # STT 서버 상태 확인
    try:
        response = requests.get("http://localhost:8504/health", timeout=2)
        if response.status_code == 200:
            health_data = response.json()
            stt_ready = health_data.get("speech_client_ready", False)
            tts_ready = health_data.get("tts_client_ready", False)
            server_ready = stt_ready and tts_ready
        else:
            server_ready = False
            stt_ready = False
            tts_ready = False
    except:
        server_ready = False
        stt_ready = False
        tts_ready = False
    
    # 상태 표시
    col1, col2, col3 = st.columns(3)
    with col1:
        if server_ready:
            st.success("🟢 음성 서버 연결됨")
        else:
            st.error("🔴 음성 서버 연결 안됨")
        st.info(f"🎤 처리된 음성: {len(st.session_state.transcripts)}개")
    
    with col2:
        if stt_ready:
            st.success("🎤 STT 준비됨")
        else:
            st.error("🎤 STT 준비 안됨")
    
    with col3:
        if tts_ready:
            st.success("🔊 TTS 준비됨")
        else:
            st.error("🔊 TTS 준비 안됨")
    
    st.markdown("---")
    
    # 메인 녹음 영역
    st.subheader("🎙️ 음성 녹음")
    
    if not server_ready:
        st.warning("⚠️ STT 서버를 먼저 실행해주세요:")
        st.code("cd /Users/idongju/dev/dev-tool-with-llm/chatbot/dj/voice-back && python voice_server.py")
    else:
        # 오디오 녹음 컴포넌트
        audio_bytes = st.audio_input("🎤 녹음 버튼을 클릭하여 음성을 녹음하세요")
        
        if audio_bytes is not None:
            st.success("🎵 음성이 녹음되었습니다!")
            
            # UploadedFile 객체에서 바이트 데이터 읽기
            audio_data = audio_bytes.read()
            
            # temp_audio에 파일 저장
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.wav"
            file_path = os.path.join(temp_audio_dir, filename)
            
            # 파일 저장
            with open(file_path, 'wb') as f:
                f.write(audio_data)
            
            st.info(f"📁 파일 저장됨: {filename}")
            log.info(f"오디오 파일 저장: {file_path}")
            
            # 1초 대기 후 STT 처리
            with st.spinner("🔄 1초 후 음성을 텍스트로 변환합니다..."):
                time.sleep(1)  # 1초 대기
                
                try:
                    # 저장된 파일을 다시 읽어서 Base64 인코딩
                    with open(file_path, 'rb') as f:
                        saved_audio_data = f.read()
                    
                    audio_base64 = base64.b64encode(saved_audio_data).decode('utf-8')
                    log.info(f"저장된 파일을 읽어서 Base64 인코딩 완료: {len(audio_base64)} 문자")
                    
                    # STT 서버로 전송
                    stt_result = send_audio_to_stt_server(audio_base64)
                    
                    if stt_result.get('success'):
                        transcript = stt_result.get('transcript', '')
                        confidence = stt_result.get('confidence', 0)
                        
                        # 결과 저장
                        st.session_state.transcripts.append({
                            'text': transcript,
                            'confidence': confidence,
                            'timestamp': time.time(),
                            'filename': filename
                        })
                        
                        # 결과 표시
                        st.success("🎤 음성 인식 완료!")
                        st.markdown(f"### 📝 인식된 텍스트:")
                        st.markdown(f"**{transcript}**")
                        st.markdown(f"*신뢰도: {confidence:.2f}*")
                        
                        log.info(f"음성 인식 성공: '{transcript}' (신뢰도: {confidence:.2f})")
                        
                        # TTS 변환 및 재생
                        with st.spinner("🔊 음성으로 변환 중..."):
                            tts_result = send_text_to_tts_server(transcript)
                            
                            if tts_result.get('success'):
                                audio_data = tts_result.get('audio_data')
                                st.success("🔊 음성 변환 완료! 자동 재생됩니다.")
                                
                                # 자동 재생
                                play_audio_from_base64(audio_data)
                                
                                log.info("TTS 변환 및 재생 완료")
                            else:
                                tts_error = tts_result.get('error', '알 수 없는 TTS 오류')
                                st.warning(f"⚠️ 음성 변환 실패: {tts_error}")
                                log.error(f"TTS 변환 실패: {tts_error}")
                        
                        # 저장된 파일 삭제 (처리 완료 후)
                        try:
                            os.remove(file_path)
                            log.info(f"처리 완료된 파일 삭제: {filename}")
                        except Exception as delete_error:
                            log.warning(f"파일 삭제 실패: {delete_error}")
                        
                    else:
                        error_msg = stt_result.get('error', '알 수 없는 오류')
                        st.error(f"❌ 음성 인식 실패: {error_msg}")
                        log.error(f"음성 인식 실패: {error_msg}")
                        
                        # 실패한 파일은 유지 (디버깅용)
                        st.info(f"⚠️ 실패한 파일은 디버깅을 위해 보관됩니다: {filename}")
                        
                except Exception as e:
                    st.error(f"❌ 처리 중 오류: {str(e)}")
                    log.error(f"음성 처리 오류: {str(e)}")
                    
                    # 오류 발생 시에도 파일 유지 (디버깅용)
                    st.info(f"⚠️ 오류 발생한 파일은 디버깅을 위해 보관됩니다: {filename}")
    
    # 이전 결과 표시
    if st.session_state.transcripts:
        st.markdown("---")
        st.subheader("📋 이전 음성 인식 결과")
        
        # 최근 5개만 표시
        recent_transcripts = list(reversed(st.session_state.transcripts))[:5]
        
        for idx, transcript_data in enumerate(recent_transcripts):
            with st.expander(f"🎤 음성 {len(st.session_state.transcripts) - idx}", expanded=(idx == 0)):
                st.markdown(f"**텍스트:** {transcript_data['text']}")
                st.markdown(f"**신뢰도:** {transcript_data['confidence']:.2f}")
                
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(transcript_data['timestamp']))
                st.markdown(f"**시간:** {timestamp}")
                
                if 'filename' in transcript_data:
                    st.markdown(f"**파일:** {transcript_data['filename']}")
        
        # 결과 초기화 버튼
        if st.button("🗑️ 모든 결과 삭제"):
            st.session_state.transcripts = []
            st.success("✅ 모든 결과가 삭제되었습니다.")
            st.rerun()
    
    # 디버깅 정보 (간단하게)
    with st.expander("🔧 디버깅 정보"):
        # temp_audio 디렉토리 상태
        wav_files = [f for f in os.listdir(temp_audio_dir) if f.endswith('.wav')]
        st.write(f"📁 temp_audio 디렉토리: {len(wav_files)}개 파일 대기 중")
        
        if wav_files:
            st.write("대기 중인 파일:")
            for file in wav_files[:3]:  # 최대 3개만 표시
                st.write(f"- {file}")
            if len(wav_files) > 3:
                st.write(f"... 외 {len(wav_files) - 3}개")
        
        # 수동 파일 처리 버튼
        if st.button("🔄 대기 중인 파일 처리"):
            if wav_files:
                processed_files = process_audio_files()
                if processed_files:
                    for result in processed_files:
                        if result['success']:
                            # 결과를 세션에 추가
                            st.session_state.transcripts.append({
                                'text': result['transcript'],
                                'confidence': result['confidence'],
                                'timestamp': time.time(),
                                'filename': result['file']
                            })
                            st.success(f"✅ {result['file']}: {result['transcript']}")
                        else:
                            st.error(f"❌ {result['file']}: {result['error']}")
                    st.rerun()
            else:
                st.info("처리할 파일이 없습니다.")
        
        # STT 서버 테스트
        if st.button("🔗 STT 서버 테스트"):
            try:
                response = requests.get("http://localhost:8504/health", timeout=5)
                if response.status_code == 200:
                    result = response.json()
                    if result.get("speech_client_ready"):
                        st.success("✅ STT 서버 정상 작동 중")
                    else:
                        st.warning("⚠️ Google Speech 클라이언트 준비 안됨")
                else:
                    st.error(f"❌ 서버 오류: {response.status_code}")
            except:
                st.error("❌ STT 서버에 연결할 수 없습니다.")