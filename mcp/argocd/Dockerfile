FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 시스템 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 필요한 Python 패키지 설치 파일 복사
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY mcp_server.py .
COPY docker-entrypoint.sh .

# 엔트리포인트 스크립트 실행 권한 설정
RUN chmod +x docker-entrypoint.sh

# 환경 변수 기본값 설정
ENV ARGOCD_INSECURE=false

# MCP 서버 포트 노출
EXPOSE 8000

# 컨테이너 시작 시 실행될 명령
ENTRYPOINT ["/app/docker-entrypoint.sh"] 