# Loki API 서버

로그 쿼리 처리를 위한 API 서버입니다. Loki에 접근하여 로그 데이터를 조회하고 분석합니다.

## 구성 요소

- `api_server.py`: Loki API 서버의 주요 코드
- `Dockerfile`: 컨테이너화를 위한 도커 이미지 설정
- `requirements.txt`: 필요한 Python 패키지 목록

## 주요 기능

- Loki 로그 데이터 쿼리 및 검색
- 라벨 및 로그 레벨 필터링
- JSON-RPC 기반 API 제공

## API 엔드포인트

### JSON-RPC 엔드포인트

- `/rpc/v1`: JSON-RPC 2.0 프로토콜을 사용한 API 요청 처리

### 주요 메서드

- `query_loki_logs`: 로그 쿼리 실행
- `list_loki_label_names`: 사용 가능한 라벨 목록 조회
- `list_loki_label_values`: 특정 라벨의 가능한 값 목록 조회

## 환경 변수

- `LOKI_URL`: Loki 서버 URL (기본값: "http://loki:3100")
- `PORT`: API 서버 포트 (기본값: 8002)

## 실행 방법

### 도커 실행

```bash
docker build -t loki-api .
docker run -p 8002:8002 -e LOKI_URL=http://your-loki-url:3100 loki-api
```

### 직접 실행

```bash
pip install -r requirements.txt
python api_server.py
```

## 사용 예제

```python
import requests

# 로그 쿼리 예제
response = requests.post(
    "http://localhost:8002/rpc/v1",
    json={
        "jsonrpc": "2.0",
        "method": "query_loki_logs",
        "params": {
            "query": '{service="order-service"}',
            "start": "2023-01-01T00:00:00Z",
            "end": "2023-01-02T00:00:00Z",
            "limit": 100
        },
        "id": 1
    }
)

print(response.json())
```

## 관련 서비스

- `loki-mcp`: Loki MCP 서버와 연동
- `langgraph`: LangGraph 서버를 통한 로그 분석 기능 제공 