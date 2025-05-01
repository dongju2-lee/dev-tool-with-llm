# MCP HTTP 서버

이 프로젝트는 MCP Python SDK를 사용한 HTTP/SSE 기반 Model Context Protocol 서버입니다.

## 실행 방법

### Docker로 실행
```bash
# 이미지 빌드
docker build -t mcp-http-server .

# 기본 실행 (포트 8000을 호스트의 8000으로 매핑)
docker run -p 8000:8000 mcp-http-server
```

### 직접 실행
```bash
# 의존성 설치
pip install -r requirements.txt

# 서버 실행
python app.py
```

## SSE 엔드포인트

MCP 서버는 SSE(Server-Sent Events) 방식으로 동작하며, 기본적으로 다음 엔드포인트에서 접근할 수 있습니다:
```
http://localhost:8000/sse
```

## 참고 자료
- MCP 공식 문서: https://modelcontextprotocol.io
- Model Context Protocol은 HTTP/WebSocket 또는 stdio를 통해 통신할 수 있습니다.
- 이 서버는 SSE(Server-Sent Events)를 통한 HTTP 통신을 구현했습니다.