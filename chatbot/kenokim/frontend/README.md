# 슬라임 챗봇 프론트엔드

이 프로젝트는 Streamlit을 사용하여 구현된 챗봇 프론트엔드입니다. 백엔드 API와 통신하여 채팅 기능을 제공합니다.

## 기능

- 텍스트 및 이미지 메시지 지원
- 스트리밍 응답 처리
- 대화 세션 관리
- MCP 서버 연결 설정 관리
- 다양한 모델 선택 지원

## 실행 방법

### 가상 환경 설정

#### Python venv 사용

```bash
# 가상 환경 생성
python -m venv venv

# 가상 환경 활성화 (Windows)
venv\Scripts\activate

# 가상 환경 활성화 (macOS/Linux)
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```
### 로컬 개발 환경에서 실행

1. 가상 환경 활성화 (위의 단계에서 이미 완료)

2. 환경 변수 설정 (선택 사항)
```bash
# Windows
set API_BASE_URL=http://localhost:8000/api

# macOS/Linux
export API_BASE_URL=http://localhost:8000/api
```

3. 애플리케이션 실행
```bash
streamlit run app.py
```

### Docker로 실행

1. Docker 이미지 빌드
```bash
docker build -t chatbot-frontend .
```

2. Docker 컨테이너 실행
```bash
docker run -p 8501:8501 -e API_BASE_URL=http://localhost:8000/api chatbot-frontend
```

## 환경 변수

- `API_BASE_URL`: 백엔드 API 서버 URL (기본값: http://localhost:8000/api)

## 백엔드 요구사항

이 프론트엔드가 제대로 작동하려면 다음 API 엔드포인트를 제공하는 백엔드 서버가 필요합니다:

- `POST /api/chat/sessions`: 새 채팅 세션 생성
- `POST /api/chat/sessions/{session_id}/messages`: 메시지 전송
- `GET /api/chat/sessions/{session_id}/messages`: 대화 이력 조회
- `DELETE /api/chat/sessions/{session_id}`: 세션 삭제
- `POST /api/mcp/connection/test`: MCP 서버 연결 테스트
- `POST /api/mcp/settings`: MCP 서버 설정 저장
- `GET /api/mcp/settings`: MCP 서버 설정 조회
- `GET /api/models`: 사용 가능한 모델 목록 조회

## 개발 참고사항

백엔드 API가 아직 개발 중일 경우, 프론트엔드는 오프라인 모드로 작동할 수 있지만 실제 채팅 응답은 제공하지 않습니다. 이 경우 백엔드 API 개발에 참조할 수 있는 API 인터페이스는 `../api_design.md`에서 확인할 수 있습니다. 