FROM python:3.9-slim

WORKDIR /app

# 기본 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 로그 디렉토리 생성
RUN mkdir -p /app/logs

# 환경 변수 설정
ENV PORT=8002
ENV LOKI_URL="http://localhost:3100"
ENV LOKI_USERNAME=""
ENV LOKI_PASSWORD=""
ENV LOG_LEVEL="INFO"

# 포트 노출
EXPOSE 8002

# 앱 실행
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8002"] 