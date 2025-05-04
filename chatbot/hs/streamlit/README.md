# Streamlit 프론트엔드

Streamlit 프론트엔드는 MCP DevOps 어시스턴트의 웹 사용자 인터페이스를 제공하는 컴포넌트입니다. 사용자가 자연어로 쿼리를 입력하고 결과를 시각적으로 확인할 수 있는 채팅 인터페이스를 제공합니다.

## 주요 기능

- 대화형 채팅 인터페이스
- 쿼리 입력 및 결과 표시
- 사용자 컨텍스트 유지 관리
- 서비스 상태 모니터링
- 지원하는 서비스 목록 표시
- 채팅 이력 관리

## 사용자 인터페이스

```
+---------------------------+------------------+
|                           |                  |
| 🛠️ MCP DevOps 어시스턴트    | 📋 사용 가이드     |
|                           |                  |
| 채팅 이력 및 결과 표시 영역   | 지원하는 기능      |
|                           | 서비스 목록        |
|                           | 예시 쿼리         |
|                           | 서버 상태         |
|                           |                  |
|                           | 채팅 초기화 버튼   |
|                           |                  |
| 쿼리 입력 필드              |                  |
+---------------------------+------------------+
```

## 사용 기술

- Streamlit: 대화형 웹 인터페이스
- Requests: HTTP 요청 처리
- Python-dotenv: 환경 변수 관리

## 환경 변수

| 환경 변수 | 설명 | 기본값 |
|---------|------|--------|
| `API_URL` | MCP 서버 URL | http://localhost:8000 |

## 세션 상태

- `messages`: 채팅 이력 저장
- `context`: 사용자 컨텍스트 데이터 저장
- `services`: 지원하는 서비스 목록

## 실행 방법

### 로컬 환경

```bash
# 의존성 설치
pip install -r requirements.txt

# 앱 실행
streamlit run streamlit_app.py
```

### Docker 환경

```bash
# 직접 빌드 및 실행
docker build -t mcp-streamlit -f Dockerfile .
docker run -p 8501:8501 -e API_URL=http://mcp:8000 mcp-streamlit

# docker-compose 사용
docker-compose up streamlit
```

## 예시 쿼리

- "지난 1시간 동안의 api-gateway 서비스 오류 로그를 보여줘"
- "오늘 auth 서비스에서 발생한 ERROR 로그 분석해줘"
- "현재 MCP 서비스의 상태는 어때?"
- "지원하는 서비스 목록을 알려줘"

## 브라우저 액세스

Streamlit 앱은 기본적으로 다음 URL에서 접근할 수 있습니다:
- http://localhost:8501

## 로그

로그는 기본적으로 `logs/streamlit.log` 파일에 기록됩니다. Docker 환경에서는 `/app/logs` 디렉토리에 마운트됩니다.

## 의존 관계

Streamlit 프론트엔드는 다음 서비스에 의존합니다:
- MCP 서버: 쿼리 처리 및 결과 수신 