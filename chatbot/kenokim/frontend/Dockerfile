FROM python:3.9-slim

WORKDIR /app

# 필요한 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 포트 설정
EXPOSE 8501

# 헬스체크를 위한 환경변수 설정
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_HEADLESS=true
ENV BACKEND_API_URL=http://backend:8000

# 실행 명령
ENTRYPOINT ["streamlit", "run"]
CMD ["app.py"] 