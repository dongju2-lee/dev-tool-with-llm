# LangGraph Agent API

DevOps 작업을 도와주는 LangGraph 기반 에이전트 API 서버입니다.

## 개요

이 애플리케이션은 FastAPI와 LangGraph를 사용하여 구축된 멀티 에이전트 시스템입니다. 다음과 같은 전문 에이전트들이 포함되어 있습니다:

- **Grafana Agent**: Grafana 데이터 분석, 메트릭 조회, 모니터링 정보 제공
- **Grafana Renderer Agent**: Grafana 대시보드 시각화 및 렌더링
- **Server Info Agent**: 서버 정보 및 시스템 상태 확인

## 사전 요구사항

- Python 3.8+
- pip 또는 poetry
- 환경 변수 설정

## 환경 설정

### 1. 환경 변수 설정

`.env` 파일을 생성하고 다음 변수들을 설정하세요:

```bash
# Google Gemini API Key (필수)
GEMINI_API_KEY=your_gemini_api_key

# Grafana 설정 (선택사항)
GRAFANA_URL=http://localhost:3000
GRAFANA_API_KEY=your_grafana_api_key

# 기타 설정 (선택사항)
LOG_LEVEL=INFO
```

### 2. 가상환경 설정 (권장)

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 가상환경 비활성화 (필요 시)
deactivate
```

### 3. 의존성 설치

```bash
# 패키지 설치 (requirements.txt가 있는 경우)
pip install -r requirements.txt

# 또는 주요 패키지 직접 설치
pip install fastapi uvicorn langgraph langchain-google-genai python-dotenv pydantic

# 필요한 경우 pip 업그레이드
pip install --upgrade pip
```

## 실행 방법

### 방법 1: uvicorn으로 main.py 실행 (권장)

```bash
# 프로젝트 루트 디렉토리에서 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 방법 2: uvicorn으로 fastapi_server 실행

```bash
# fastapi_server.py 사용
uvicorn app.fastapi_server:app --host 0.0.0.0 --port 8000 --reload
```

### 방법 3: Python으로 직접 실행

```bash
# main.py 실행 (개발용)
python -m app.main
```

## API 엔드포인트

### 기본 정보
- **Base URL**: `http://localhost:8000`
- **API Documentation**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/health`

### 주요 엔드포인트

#### 1. 기본 API (main.py 기반)
- `GET /` - 기본 정보
- `GET /api/v1/health` - 헬스 체크
- `POST /api/v1/invocations` - 에이전트 호출
- `POST /api/v1/stream` - 스트리밍 응답
- `WebSocket /api/v1/ws/stream` - WebSocket 스트리밍

#### 2. 확장 API (fastapi_server.py 기반)
- `POST /agent/invoke` - 에이전트 단일 호출
- `POST /agent/stream` - 에이전트 스트리밍 호출

## 사용 예시

### cURL을 사용한 API 호출

```bash
# 기본 정보 확인
curl http://localhost:8000/

# 헬스 체크
curl http://localhost:8000/health

# 채팅 요청
curl -X POST "http://localhost:8000/agent/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "messages": [
        {
          "role": "user",
          "content": "서버 상태를 확인해줘"
        }
      ]
    }
  }'
```

### Python 클라이언트 예시

```python
import requests
import json

# API 호출
url = "http://localhost:8000/agent/invoke"
payload = {
    "input": {
        "messages": [
            {
                "role": "user",
                "content": "Grafana 대시보드 상태를 보여줘"
            }
        ]
    }
}

response = requests.post(url, json=payload)
print(json.dumps(response.json(), indent=2, ensure_ascii=False))
```

## 프로젝트 구조

```
app/
├── main.py                    # 메인 FastAPI 애플리케이션
├── fastapi_server.py         # 확장 FastAPI 서버
├── api/
│   └── v1/
│       ├── __init__.py
│       ├── endpoints.py      # API 엔드포인트
│       └── schemas.py        # Pydantic 스키마
├── graph/
│   ├── __init__.py
│   ├── instance.py           # 그래프 인스턴스 생성
│   ├── grafana_mcp_agent.py  # Grafana 에이전트
│   ├── grafana_renderer_mcp_agent.py  # 렌더러 에이전트
│   └── server_info_agent.py  # 서버 정보 에이전트
└── core/                     # 핵심 유틸리티
```

## 개발 모드

개발 시에는 `--reload` 옵션을 사용하여 코드 변경 시 자동으로 서버가 재시작되도록 할 수 있습니다:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 문제 해결

### 1. 환경 변수 오류
- `.env` 파일이 올바른 경로에 있는지 확인
- `GEMINI_API_KEY`가 정확히 설정되었는지 확인

### 2. 포트 충돌
- 다른 포트 사용: `--port 8001`
- 실행 중인 프로세스 확인: `lsof -i :8000`

### 3. 의존성 오류
- 패키지 재설치: `pip install --upgrade -r requirements.txt`
- 가상환경 확인 및 활성화

## 로그 확인

애플리케이션 로그는 콘솔에 출력됩니다. 로그 레벨은 환경 변수 `LOG_LEVEL`로 조정할 수 있습니다.

```bash
# 로그 레벨 설정
export LOG_LEVEL=DEBUG
``` 