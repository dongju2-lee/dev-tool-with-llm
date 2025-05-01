# 슬라임 챗봇

## 개요
- Python + Streamlit 기반 대화형 챗봇
- 슬라임 이미지 생성 및 응답 기능
- MCP 서버 연동 가능

## 빠른 시작 (로컬 개발)

### 1. 가상환경 설정

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 가상환경 활성화 (macOS/Linux)
source venv/bin/activate

# 가상환경 비활성화 (작업 완료 후)
deactivate
```

### 2. 필요한 패키지 설치

```bash
# 패키지 설치
pip install -r requirements.txt
```

### 3. Streamlit 직접 실행

```bash
cd chatbot/kenokim
streamlit run app.py
```

Streamlit은 코드 변경을 자동으로 감지하여 새로고침하므로, 코드를 수정하면 바로 적용됩니다.
파일을 저장하면 자동으로 앱이 다시 로드됩니다.

## Docker 배포

### 이미지 빌드 및 실행

```bash
# 변경된 코드로 다시 빌드 및 실행
docker compose up --build

# 백그라운드에서 실행
docker compose up -d --build
```

### 컨테이너 관리

```bash
# 컨테이너 중지
docker compose down

# 로그 확인
docker compose logs -f
```

## 주요 파일 구조

```
chatbot/kenokim/
├── app.py                # 메인 Streamlit 애플리케이션
├── requirements.txt      # 필요한 패키지 목록
├── api/
│   └── client.py         # MCP 서버 API 클라이언트
└── docs/
    └── chatbot_design_1.md # 설계 문서
```

## 프로젝트 관리 팁

### .gitignore 설정

venv 디렉토리와 같은 로컬 개발 환경 파일은 Git에 포함되지 않도록 .gitignore 파일에 추가하세요:

```
# Python
__pycache__/
*.py[cod]
*$py.class
.env
venv/
ENV/

# Streamlit
.streamlit/

# 기타
.DS_Store
```