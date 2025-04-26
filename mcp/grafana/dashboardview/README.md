# Grafana MCP dashboard view

Grafana를 위한 Model Context Protocol (MCP) 서버의 Python 구현체입니다. 이 서버는 AI 에이전트가 Grafana 대시보드와 상호작용할 수 있게 합니다.

## 기능

- [x] 대시보드 검색
- [x] 대시보드 관리
  - [x] UID로 대시보드 조회
- [] 대시보드 PNG 뷰

## 설치

### 소스에서 설치

```bash
# 저장소 클론
git clone https://github.com/your-username/grafana-mcp-python.git
cd grafana-mcp-python

# 개발 모드로 설치
pip install -e .
```

## 사용법

### 환경 변수 설정

MCP 서버를 실행하기 전에 Grafana API와 통신하기 위한 환경 변수를 설정하세요:

```bash
# .env 파일 생성
GRAFANA_URL=http://localhost:3000
GRAFANA_API_KEY=your-api-key-here
```

### CLI로 실행

```bash
# STDIO 전송으로 실행 (기본값)
grafana-mcp serve

# SSE 전송으로 실행
grafana-mcp serve --transport sse --host localhost --port 8000

# 디버그 모드 활성화
grafana-mcp serve --debug

# 특정 도구 비활성화
grafana-mcp serve --disabled-tools dashboard
```

### MCP 클라이언트와 함께 사용

Claude나 다른 MCP 클라이언트에서 사용하려면 다음과 같이 설정합니다 (Claude Desktop 예시):

```json
{
  "mcpServers": {
    "grafana": {
      "command": "grafana-mcp",
      "args": ["serve"],
      "env": {
        "GRAFANA_URL": "http://localhost:3000",
        "GRAFANA_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

## 도구 목록

| 도구 이름 | 카테고리 | 설명 |
|------------|----------|------|
| `search_dashboards` | 검색 | Grafana 대시보드 검색 |
| `get_dashboard_by_uid` | 대시보드 | UID로 대시보드 조회 |

## 테스트 인프라

테스트 및 개발을 위한 Docker 기반 인프라를 제공합니다. 이 인프라는 Grafana, Prometheus, 그리고 테스트용 API를 포함합니다.

### 테스트 인프라 시작

```bash
cd test_infra
docker compose up -d
```

이 명령을 실행하면 다음 서비스가 시작됩니다:
- Grafana: http://localhost:3000 (계정: admin / 비밀번호: admin)
- Prometheus: http://localhost:9090
- Target API: http://localhost:8080

자세한 내용은 [테스트 인프라 문서](test_infra/README.md)를 참조하세요.

## 개발

### 의존성 설치

```bash
# 개발 의존성 설치
pip install -e ".[dev]"
```

### 로컬에서 실행

```bash
# 소스에서 직접 실행
python -m grafana_mcp.cli serve
```

## 라이선스

MIT 