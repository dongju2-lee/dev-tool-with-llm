# 챗봇 백엔드 API 서버

이 프로젝트는 FastAPI를 사용하여 구현된, Streamlit 프론트엔드와 MCP 서버 사이의 중개 역할을 하는 백엔드 API 서버입니다.

## 기능

- 채팅 세션 관리 API
- 메시지 처리 및 응답 생성 API (일반/스트리밍)
- MCP 서버 연결 관리 API
- 사용 가능한 모델 정보 제공 API

## 로컬 실행 방법

### 준비 사항
- Python 3.9 이상
- virtualenv 또는 conda 환경 (선택사항)

### 가상 환경 설정 (선택사항)
```bash
# virtualenv 사용
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows

# 또는 conda 사용
conda create -n chatbot-backend python=3.9
conda activate chatbot-backend
```

### 의존성 설치
```bash
pip install -r requirements.txt
```

### 환경 변수 설정 (선택사항)
```bash
# Linux/Mac
export MCP_SERVER_URL=http://localhost:8000/sse
export MCP_CLIENT_NAME=backend-client
export MCP_TRANSPORT=sse

# Windows
set MCP_SERVER_URL=http://localhost:8000/sse
set MCP_CLIENT_NAME=backend-client
set MCP_TRANSPORT=sse
```

### 서버 실행
```bash
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

이제 백엔드 서버는 `http://localhost:8080`에서 실행됩니다.

## Docker로 실행하기

### Docker 이미지 빌드
```bash
docker build -t chatbot-backend .
```

### Docker 컨테이너 실행
```bash
docker run -p 8080:8080 -e MCP_SERVER_URL=http://host.docker.internal:8000/sse chatbot-backend
```

## API 엔드포인트

### 기본 엔드포인트
- `GET /` - API 홈 엔드포인트

### 채팅 세션 관리
- `POST /api/chat/sessions` - 새 채팅 세션 생성
- `GET /api/chat/sessions/{session_id}/messages` - 채팅 이력 조회
- `DELETE /api/chat/sessions/{session_id}` - 채팅 세션 삭제
- `POST /api/chat/sessions/{session_id}/messages` - 메시지 전송 및 응답 받기
- `POST /api/chat/sessions/{session_id}/messages/stream` - 메시지 전송 및 응답 스트리밍

### MCP 서버 설정
- `GET /api/mcp/settings` - MCP 설정 조회
- `POST /api/mcp/settings` - MCP 설정 저장
- `POST /api/mcp/connection/test` - MCP 연결 테스트

### 모델 정보
- `GET /api/models` - 사용 가능한 모델 목록 조회

## 개발 참고사항

현재 MCP 서버와의 실제 연결은 구현되어 있지 않으며, 가상의 응답을 제공합니다. 실제 환경에서는 `call_mcp_server` 함수를 수정하여 실제 MCP 서버와 통신하도록 구현해야 합니다. 