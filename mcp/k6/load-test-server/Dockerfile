FROM python:3.11-slim

WORKDIR /app

# 필요한 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 파일 복사
COPY server.py .
COPY .env.example .env

# 포트 노출
EXPOSE 8080

# 서버 실행
CMD ["python", "server.py"] 