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

# 포트 8000 노출 (새로운 구조는 8000 포트 사용)
EXPOSE 8000

# 환경 변수 설정
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Grafana MCP 서버 URL 설정 (Docker Compose에서 덮어씌울 수 있음)
ENV GRAFANA_MCP_URL="http://host.docker.internal:8001"
ENV GRAFANA_RENDERER_MCP_URL="http://host.docker.internal:8002"

# 앱 실행 (새로운 구조의 앱 사용)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 