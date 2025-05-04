# Tempo API 서버

트레이스 쿼리 처리를 위한 API 서버입니다. Tempo에 접근하여 분산 트레이싱 데이터를 조회하고 분석합니다.

## 구성 요소

- `api_server.py`: Tempo API 서버의 주요 코드
- `Dockerfile`: 컨테이너화를 위한 도커 이미지 설정
- `requirements.txt`: 필요한 Python 패키지 목록

## 주요 기능

- Tempo 트레이스 데이터 쿼리 및 검색
- 서비스, 작업 및 태그 기반 필터링
- 트레이스 ID 검색
- JSON-RPC 기반 API 제공

## API 엔드포인트

### JSON-RPC 엔드포인트

- `/rpc/v1`: JSON-RPC 2.0 프로토콜을 사용한 API 요청 처리

### 주요 메서드

- `query_tempo`: 트레이스 검색 및 필터링
- `get_trace`: 특정 트레이스 ID로 트레이스 조회
- `list_services`: 사용 가능한 서비스 목록 조회
- `list_operations`: 특정 서비스의 작업 목록 조회

## 환경 변수

- `TEMPO_URL`: Tempo 서버 URL (기본값: "http://tempo:3200")
- `TEMPO_API_URL`: Tempo API URL (기본값: "http://tempo:3200/api")
- `PORT`: API 서버 포트 (기본값: 8005)

## 실행 방법

### 도커 실행

```bash
docker build -t tempo-api .
docker run -p 8005:8005 -e TEMPO_URL=http://your-tempo:3200 tempo-api
```

### 직접 실행

```bash
pip install -r requirements.txt
python api_server.py
```

## 사용 예제

```python
import requests

# 트레이스 ID로 트레이스 조회 예제
response = requests.post(
    "http://localhost:8005/rpc/v1",
    json={
        "jsonrpc": "2.0",
        "method": "get_trace",
        "params": {
            "trace_id": "a4232e946496f5f98d9bfc70eb9458e1"
        },
        "id": 1
    }
)

print(response.json())

# 서비스 기반 트레이스 검색 예제
response = requests.post(
    "http://localhost:8005/rpc/v1",
    json={
        "jsonrpc": "2.0",
        "method": "query_tempo",
        "params": {
            "service": "order-service",
            "start": "2023-01-01T00:00:00Z", 
            "end": "2023-01-02T00:00:00Z",
            "limit": 20
        },
        "id": 1
    }
)

print(response.json())
```

## 관련 서비스

- `tempo-mcp`: Tempo MCP 서버와 연동
- `langgraph`: LangGraph 서버를 통한 트레이스 분석 기능 제공 