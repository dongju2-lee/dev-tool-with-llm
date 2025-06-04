# 음성 처리 백엔드 서버

Google Cloud Speech-to-Text API를 이용한 음성 인식 서버입니다.

## 설치 및 설정

### 1. 의존성 설치

```bash
cd /Users/idongju/dev/dev-tool-with-llm/chatbot/dj/voice-back
pip install -r requirements.txt
```

### 2. Google Cloud 인증 설정

Google Cloud Speech-to-Text API를 사용하기 위해 인증이 필요합니다.

```bash
# gcloud CLI를 통한 인증 (이미 설정되어 있다고 하셨으니 생략 가능)
gcloud auth application-default login
```

### 3. 서버 실행

```bash
python voice_server.py
```

서버는 `http://localhost:8504`에서 실행됩니다.

## API 엔드포인트

### GET /health
서버 상태 및 Google Speech 클라이언트 준비 상태를 확인합니다.

**응답 예시:**
```json
{
  "status": "healthy",
  "speech_client_ready": true
}
```

### POST /transcribe
Base64 인코딩된 오디오 데이터를 텍스트로 변환합니다.

**요청 예시:**
```json
{
  "audio_data": "UklGRiQAAABXQVZFZm10IBAAAAABAAEA..."
}
```

**응답 예시:**
```json
{
  "success": true,
  "transcript": "안녕하세요",
  "confidence": 0.95
}
```

## 사용법

1. 음성 챗봇 페이지에서 마이크 버튼을 클릭하여 녹음을 시작합니다.
2. 음성을 말한 후 다시 마이크 버튼을 클릭하여 녹음을 중지합니다.
3. 자동으로 STT 서버로 오디오 데이터가 전송되어 텍스트로 변환됩니다.
4. 변환된 텍스트는 로그와 디버깅 섹션에서 확인할 수 있습니다.

## 문제 해결

### STT 서버 연결 오류
- 서버가 실행 중인지 확인: `http://localhost:8504/health`
- 방화벽 설정 확인
- 포트 8504가 사용 중인지 확인

### Google Speech 클라이언트 오류
- Google Cloud 인증 확인: `gcloud auth list`
- Speech-to-Text API 활성화 확인
- 프로젝트 설정 확인 