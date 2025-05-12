# MCP ArgoCD 서버

MCP(Management Control Panel) ArgoCD 서버는 ArgoCD API를 활용하여 Kubernetes 애플리케이션을 관리할 수 있는 도구입니다.

## 기능

- 애플리케이션 목록 조회
- 애플리케이션 상태 확인
- 애플리케이션 동기화 
- 애플리케이션 재시작
- 애플리케이션 이전 버전으로 롤백
- 다양한 배포 리소스 관리

## 도커 이미지 사용하기

### 도커 이미지 빌드

```bash
docker build -t mcp-argocd-server .
```

### 도커 컨테이너 실행

다음과 같이 필요한 환경 변수를 설정하여 컨테이너를 실행합니다:

```bash
docker run -d --name mcp-argocd-server \
  -p 8000:8000 \
  -e ARGOCD_SERVER=https://your-argocd-server \
  -e ARGOCD_AUTH_TOKEN=your-argocd-token \
  mcp-argocd-server
```

또는 사용자 이름/비밀번호 인증 방식을 사용할 수 있습니다:

```bash
docker run -d --name mcp-argocd-server \
  -p 8000:8000 \
  -e ARGOCD_SERVER=https://your-argocd-server \
  -e ARGOCD_USERNAME=your-username \
  -e ARGOCD_PASSWORD=your-password \
  mcp-argocd-server
```

### 환경 변수

| 변수명 | 필수 여부 | 설명 |
|--------|----------|------|
| ARGOCD_SERVER | 필수 | ArgoCD 서버 URL |
| ARGOCD_AUTH_TOKEN | 선택적* | ArgoCD 인증 토큰 |
| ARGOCD_USERNAME | 선택적* | ArgoCD 사용자 이름 |
| ARGOCD_PASSWORD | 선택적* | ArgoCD 비밀번호 |
| MCP_HOST | 선택적 | MCP 서버 호스트 (기본값: 0.0.0.0) |
| MCP_PORT | 선택적 | MCP 서버 포트 (기본값: 8000) |

\* ARGOCD_AUTH_TOKEN 또는 ARGOCD_USERNAME + ARGOCD_PASSWORD 중 하나는 반드시 제공해야 합니다.

## API 사용법

서버가 실행되면 다음 URL에서 API 문서를 확인할 수 있습니다:

```
http://localhost:8000/docs
```

여기서는 API 엔드포인트의 전체 목록과 각 엔드포인트의 사용 방법을 확인할 수 있습니다. 