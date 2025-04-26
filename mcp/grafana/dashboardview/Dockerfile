FROM python:3.11-slim

WORKDIR /app

# 의존성 파일 복사 및 설치
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# 소스 코드 복사
COPY . .

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1

# 기본 명령
ENTRYPOINT ["grafana-mcp"]
CMD ["serve", "--transport", "stdio"]

# SSE 전송을 위한 포트 노출
EXPOSE 8000 