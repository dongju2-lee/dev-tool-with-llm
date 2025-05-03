FROM python:3.9-slim

WORKDIR /app

# 필요한 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 포트 설정
EXPOSE 8000

# 필요한 환경변수 설정
ENV PYTHONPATH=/app:${PYTHONPATH}

# 실행 명령
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 