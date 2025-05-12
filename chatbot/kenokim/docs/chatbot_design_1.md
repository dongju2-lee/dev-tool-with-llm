# 간단한 Streamlit 챗봇 만들기

## 개요
이 문서에서는 Python과 Streamlit을 사용하여 가장 간단한 형태의 챗봇을 만드는 방법을 설명합니다. Streamlit은 데이터 애플리케이션을 빠르게 구축할 수 있는 파이썬 라이브러리로, 챗봇 UI를 쉽게 구현할 수 있습니다.

## 필요한 패키지

```bash
pip install streamlit
```

## 기본 챗봇 코드

아래는 가장 간단한 형태의 Streamlit 챗봇 코드입니다:

```python
# app.py
import streamlit as st

# 페이지 제목 설정
st.title("간단한 챗봇")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 대화 이력 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 사용자 입력 처리
if prompt := st.chat_input("무엇이든 물어보세요"):
    # 사용자 메시지 추가
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 사용자 메시지 표시
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # 간단한 챗봇 응답 생성
    response = f"당신의 메시지: {prompt}"
    
    # 챗봇 응답 표시
    with st.chat_message("assistant"):
        st.markdown(response)
    
    # 챗봇 응답 저장
    st.session_state.messages.append({"role": "assistant", "content": response})
```

## 실행 방법

1. 위 코드를 `app.py` 파일로 저장합니다.
2. 터미널에서 다음 명령어를 실행합니다:

```bash
streamlit run app.py
```

3. 브라우저가 자동으로 열리고 챗봇 인터페이스가 표시됩니다(일반적으로 http://localhost:8501).

## 코드 설명

- **st.title()**: 페이지 제목을 설정합니다.
- **st.session_state**: 사용자 세션 간에 데이터를 유지하는 데 사용됩니다. 여기서는 대화 이력을 저장합니다.
- **st.chat_message()**: 채팅 메시지를 표시하는 컨테이너를 생성합니다.
- **st.chat_input()**: 사용자 입력을 받는 채팅 입력 필드를 생성합니다.
- **st.markdown()**: 마크다운 형식으로 텍스트를 표시합니다.

## 실제 챗봇으로 확장하기

위 코드는 단순히 사용자 입력을 반복하는 에코 봇입니다. 실제 챗봇을 구현하려면 다음과 같이 확장할 수 있습니다:

```python
# app_extended.py
import streamlit as st
import random

# 간단한 응답 목록
responses = [
    "흥미로운 질문이네요!",
    "더 자세히 설명해주실래요?",
    "그것에 대해 더 생각해볼게요.",
    "좋은 질문입니다!",
    "무엇을 도와드릴까요?",
]

# 페이지 제목 설정
st.title("간단한 챗봇")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 대화 이력 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 사용자 입력 처리
if prompt := st.chat_input("무엇이든 물어보세요"):
    # 사용자 메시지 추가 및 표시
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # 응답 생성 (실제로는 여기에 NLP 모델이나 API 호출이 들어갈 수 있음)
    response = random.choice(responses) + f"\n\n당신의 메시지: {prompt}"
    
    # 응답 표시 및 저장
    with st.chat_message("assistant"):
        with st.spinner("생각 중..."):
            # 실제 응용에서는 여기서 API 호출 등을 수행
            st.markdown(response)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
```

## 스타일링 추가하기

Streamlit에서는 간단히 스타일을 추가할 수 있습니다:

```python
# 페이지 설정
st.set_page_config(
    page_title="나의 챗봇",
    page_icon="🤖",
    layout="centered"
)

# CSS 추가
st.markdown("""
<style>
    .stChatMessage {
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)
```

## Docker 구성하기

### Dockerfile 생성

챗봇 애플리케이션을 Docker 컨테이너로 실행하기 위해 다음과 같은 `Dockerfile`을 생성합니다:

```dockerfile
# Dockerfile
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

# 실행 명령
ENTRYPOINT ["streamlit", "run"]
CMD ["app.py"]
```

### requirements.txt 생성

애플리케이션에 필요한 패키지를 명시합니다:

```
# requirements.txt
streamlit==1.35.0
```

### Docker Compose 구성

`docker-compose.yml` 파일을 생성하여 챗봇과 다른 서비스(예: MCP 서버)를 함께 구성합니다:

```yaml
# docker-compose.yml
version: '3.8'

services:
  # 챗봇 서비스
  chatbot:
    build:
      context: ./chatbot/kenokim
      dockerfile: Dockerfile
    ports:
      - "8501:8501"
    environment:
      - MCP_SERVER_URL=http://mcp-server:8000
    volumes:
      - ./chatbot/kenokim:/app
    restart: unless-stopped
    depends_on:
      - mcp-server

  # MCP 서버 서비스 (추후 구현 예정)
  mcp-server:
    build:
      context: ./mcp-server
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./mcp-server:/app
    restart: unless-stopped
```

### .dockerignore 생성

불필요한 파일이 이미지에 포함되지 않도록 `.dockerignore` 파일을 생성합니다:

```
# .dockerignore
__pycache__/
*.py[cod]
*$py.class
.env
.venv
env/
venv/
ENV/
.git
.gitignore
```

## Docker로 실행하기

### 단일 서비스 실행

챗봇만 실행하려면:

```bash
# 이미지 빌드
docker build -t simple-chatbot ./chatbot/kenokim

# 컨테이너 실행
docker run -p 8501:8501 simple-chatbot
```

### Docker Compose로 모든 서비스 실행

전체 서비스(챗봇 + MCP 서버)를 실행하려면:

```bash
# 모든 서비스 실행
docker-compose up

# 백그라운드에서 실행
docker-compose up -d

# 특정 서비스만 재시작
docker-compose restart chatbot

# 로그 확인
docker-compose logs -f
```

## 프로젝트 폴더 구조

Docker Compose를 사용하기 위한 프로젝트 구조는 다음과 같습니다:

```
project-root/
├── docker-compose.yml
├── chatbot/
│   └── kenokim/
│       ├── Dockerfile
│       ├── app.py
│       ├── requirements.txt
│       └── docs/
│           ├── chatbot_design_1.md
│           └── design.md
├── mcp-server/
│   ├── Dockerfile
│   └── [MCP 서버 관련 파일들]
└── .dockerignore
```

## 개발 및 배포 워크플로우

1. 로컬에서 개발 및 테스트:
   ```bash
   cd chatbot/kenokim
   streamlit run app.py
   ```

2. Docker 이미지 빌드 및 테스트:
   ```bash
   docker build -t chatbot ./chatbot/kenokim
   docker run -p 8501:8501 chatbot
   ```

3. Docker Compose로 전체 시스템 실행:
   ```bash
   docker-compose up -d
   ```

4. 변경사항 적용 후 재배포:
   ```bash
   docker-compose build chatbot  # 변경된 서비스만 재빌드
   docker-compose up -d          # 업데이트된 서비스 실행
   ```

## 다음 단계

이 기본적인 챗봇에서 다음과 같은 기능을 추가할 수 있습니다:

1. 외부 API를 통한한 실제 답변 생성 (OpenAI API, Hugging Face 등)
2. 대화 컨텍스트 관리
3. 사이드바를 통한 설정 옵션 제공
4. 히스토리 저장 및 로드 기능
5. 다양한 시각적 요소 추가 (이미지, 차트 등)

## 요약

이 가이드에서는 Streamlit을 사용하여 가장 간단한 형태의 챗봇을 만드는 방법과 Docker 및 Docker Compose를 사용하여 배포하는 방법을 보여드렸습니다. Streamlit의 강력한 기능과 파이썬의 다양한 라이브러리를 활용하면 이 기본 템플릿을 확장하여 더 복잡하고 유용한 챗봇을 만들 수 있으며, Docker를 통해 쉽게 배포하고 확장할 수 있습니다.
