FROM python:3.9-slim

WORKDIR /app

# 기본 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 필요한 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY langgraph_server.py .

# 로그 디렉토리 생성
RUN mkdir -p /app/logs

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1

# 포트 노출
EXPOSE 8001

# 실행 명령
CMD ["uvicorn", "langgraph_server:app", "--host", "0.0.0.0", "--port", "8001"] 