FROM python:3.9-slim

WORKDIR /app

# 타임존 설정
ENV TZ=Asia/Seoul
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 필요한 시스템 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 포트 8080 노출
EXPOSE 8080

# 환경 변수 설정
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 기본 MCP 서버 URL 설정 (Docker Compose에서 덮어씌울 수 있음)
ENV MCP_SERVER_URL="http://host.docker.internal:8090/sse"
ENV MCP_CLIENT_NAME="backend-client"
ENV MCP_TRANSPORT="sse"

# 앱 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"] 