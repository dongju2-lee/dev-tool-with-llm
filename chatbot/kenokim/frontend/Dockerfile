FROM python:3.10-slim

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
COPY app.py .

# 환경 변수 설정
ENV API_BASE_URL=http://backend:8080/api

# 포트 설정
EXPOSE 8501

# 명령 설정
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"] 