"""
음성 처리 백엔드 서버
Google Cloud Speech-to-Text API를 이용한 음성 인식
Google Cloud Text-to-Speech API를 이용한 음성 합성
FastAPI 기반
"""

import os
import base64
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.cloud import speech
from google.cloud import texttospeech
import uvicorn

# 로그 디렉토리 생성
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "voice_server.log"

# 로그 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 서버 시작 로그
logger.info("=" * 50)
logger.info("음성 처리 서버 시작")
logger.info(f"로그 파일: {log_file}")
logger.info("=" * 50)

app = FastAPI(title="음성 처리 서버", description="Google Cloud Speech-to-Text API를 이용한 음성 인식")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경에서는 모든 origin 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Google Cloud Speech 클라이언트 초기화
try:
    speech_client = speech.SpeechClient()
    logger.info("Google Cloud Speech 클라이언트가 초기화되었습니다.")
    logger.info("Google Cloud 인증이 정상적으로 설정되어 있습니다.")
except Exception as e:
    logger.error(f"Google Cloud Speech 클라이언트 초기화 실패: {str(e)}")
    logger.error("Google Cloud 인증을 확인하세요: gcloud auth application-default login")
    speech_client = None

# Google Cloud Text-to-Speech 클라이언트 초기화
try:
    tts_client = texttospeech.TextToSpeechClient()
    logger.info("Google Cloud Text-to-Speech 클라이언트가 초기화되었습니다.")
except Exception as e:
    logger.error(f"Google Cloud Text-to-Speech 클라이언트 초기화 실패: {str(e)}")
    tts_client = None

# 요청 모델 정의
class AudioRequest(BaseModel):
    audio_data: str  # Base64 인코딩된 오디오 데이터

class TranscriptionResponse(BaseModel):
    success: bool
    transcript: str = None
    confidence: float = None
    error: str = None

# TTS 요청 모델 정의
class TTSRequest(BaseModel):
    text: str  # 변환할 텍스트

class TTSResponse(BaseModel):
    success: bool
    audio_data: str = None  # Base64 인코딩된 오디오 데이터
    error: str = None

def transcribe_audio(audio_content: str) -> dict:
    """
    오디오 데이터를 텍스트로 변환
    
    Args:
        audio_content: Base64 인코딩된 오디오 데이터
        
    Returns:
        dict: 변환 결과 (성공/실패, 텍스트, 오류 메시지)
    """
    if not speech_client:
        return {
            "success": False,
            "error": "Speech 클라이언트가 초기화되지 않았습니다."
        }
    
    try:
        # Base64 디코딩
        audio_bytes = base64.b64decode(audio_content)
        
        # 오디오 설정
        audio = speech.RecognitionAudio(content=audio_bytes)
        
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,  # WAV 파일 형식
            # sample_rate_hertz는 생략하여 WAV 헤더에서 자동 감지
            language_code="ko-KR",  # 한국어
            model="default",
            audio_channel_count=1,
            enable_word_confidence=True,
            enable_word_time_offsets=True,
        )
        
        # 음성 인식 수행
        logger.info("음성 인식을 시작합니다...")
        response = speech_client.recognize(config=config, audio=audio)
        
        # 결과 처리
        if response.results:
            transcript = response.results[0].alternatives[0].transcript
            confidence = response.results[0].alternatives[0].confidence
            
            logger.info(f"음성 인식 완료: {transcript} (신뢰도: {confidence:.2f})")
            
            return {
                "success": True,
                "transcript": transcript,
                "confidence": confidence
            }
        else:
            logger.warning("음성 인식 결과가 없습니다.")
            return {
                "success": False,
                "error": "음성을 인식할 수 없습니다."
            }
            
    except Exception as e:
        logger.error(f"음성 인식 중 오류 발생: {str(e)}")
        return {
            "success": False,
            "error": f"음성 인식 오류: {str(e)}"
        }

def text_to_speech(text: str) -> dict:
    """
    텍스트를 음성으로 변환 (Google Cloud TTS 공식 샘플 코드 기반)
    
    Args:
        text: 변환할 텍스트
        
    Returns:
        dict: 변환 결과 (성공/실패, 오디오 데이터, 오류 메시지)
    """
    if not tts_client:
        return {
            "success": False,
            "error": "TTS 클라이언트가 초기화되지 않았습니다."
        }
    
    try:
        # 텍스트 입력 설정
        input_text = texttospeech.SynthesisInput(text=text)
        
        # 음성 설정 - Chirp3-HD 고품질 한국어 음성 사용
        voice = texttospeech.VoiceSelectionParams(
            language_code="ko-KR",
            name="ko-KR-Chirp3-HD-Achernar",  # 고품질 한국어 음성
        )
        
        # 오디오 설정
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,  # WAV 형식
            speaking_rate=1.0,  # 자연스러운 말하기 속도
            sample_rate_hertz=24000
        )
        
        # TTS 수행 (공식 샘플 코드 방식)
        logger.info(f"TTS 변환 시작 (Chirp3-HD): '{text}'")
        response = tts_client.synthesize_speech(
            request={
                "input": input_text, 
                "voice": voice, 
                "audio_config": audio_config
            }
        )
        
        # Base64 인코딩
        audio_base64 = base64.b64encode(response.audio_content).decode('utf-8')
        
        logger.info(f"TTS 변환 완료 (Chirp3-HD): {len(response.audio_content)} bytes")
        
        return {
            "success": True,
            "audio_data": audio_base64
        }
        
    except Exception as e:
        logger.error(f"TTS 변환 중 오류 발생: {str(e)}")
        
        # Chirp3-HD가 실패하면 기본 음성으로 폴백
        try:
            logger.info("Chirp3-HD 실패, 기본 음성으로 재시도...")
            
            # 기본 한국어 음성으로 폴백
            voice_fallback = texttospeech.VoiceSelectionParams(
                language_code="ko-KR",
                name="ko-KR-Standard-A",  # 기본 한국어 여성 목소리
                ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
            )
            
            audio_config_fallback = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                speaking_rate=1.0,
                sample_rate_hertz=24000
            )
            
            response_fallback = tts_client.synthesize_speech(
                request={
                    "input": input_text,
                    "voice": voice_fallback,
                    "audio_config": audio_config_fallback
                }
            )
            
            audio_base64_fallback = base64.b64encode(response_fallback.audio_content).decode('utf-8')
            
            logger.info(f"TTS 변환 완료 (기본 음성): {len(response_fallback.audio_content)} bytes")
            
            return {
                "success": True,
                "audio_data": audio_base64_fallback
            }
            
        except Exception as fallback_error:
            logger.error(f"기본 음성으로도 TTS 변환 실패: {str(fallback_error)}")
            return {
                "success": False,
                "error": f"TTS 변환 오류: {str(e)} (폴백 실패: {str(fallback_error)})"
            }

@app.get("/health")
async def health_check():
    """서버 상태 확인"""
    return {
        "status": "healthy",
        "speech_client_ready": speech_client is not None,
        "tts_client_ready": tts_client is not None
    }

@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(request: AudioRequest):
    """음성 파일을 텍스트로 변환"""
    try:
        logger.info("음성 변환 요청을 받았습니다.")
        
        # 음성 인식 수행
        result = transcribe_audio(request.audio_data)
        
        if result["success"]:
            return TranscriptionResponse(
                success=True,
                transcript=result["transcript"],
                confidence=result["confidence"]
            )
        else:
            raise HTTPException(status_code=500, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"transcribe 엔드포인트 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

@app.post("/text-to-speech", response_model=TTSResponse)
async def text_to_speech_endpoint(request: TTSRequest):
    """텍스트를 음성으로 변환"""
    try:
        logger.info(f"TTS 변환 요청: '{request.text}'")
        
        # TTS 수행
        result = text_to_speech(request.text)
        
        if result["success"]:
            return TTSResponse(
                success=True,
                audio_data=result["audio_data"]
            )
        else:
            raise HTTPException(status_code=500, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"text-to-speech 엔드포인트 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

if __name__ == '__main__':
    # Google Cloud 인증 상태 확인
    if speech_client:
        logger.info("✅ Google Cloud Speech API 준비 완료")
    else:
        logger.error("❌ Google Cloud Speech API 초기화 실패")
        logger.info("해결 방법: gcloud auth application-default login 명령을 실행하세요.")
    
    if tts_client:
        logger.info("✅ Google Cloud Text-to-Speech API 준비 완료")
    else:
        logger.error("❌ Google Cloud Text-to-Speech API 초기화 실패")
    
    # 서버 시작
    logger.info("음성 처리 서버를 시작합니다...")
    logger.info("서버 주소: http://localhost:8504")
    logger.info("종료하려면 Ctrl+C를 누르세요.")
    
    uvicorn.run(
        "voice_server:app",  # 문자열로 앱 지정
        host="0.0.0.0", 
        port=8504, 
        reload=True,
        log_level="info",
        access_log=True
    )
