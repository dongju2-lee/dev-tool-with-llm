# SonarQube MCP 서버

SonarQube MCP 서버는 [MCP(Model Context Protocol)](https://modelcontextprotocol.io) 표준에 따라 SonarQube의 코드 품질 분석 기능을 LLM 도구로 제공하는 서버입니다.

## 기능

이 MCP 서버는 SonarQube Community Edition API를 사용하여 다음과 같은 기능을 제공합니다:

1. **프로젝트 관리**
   - 프로젝트 목록 조회
   - 프로젝트 상세 정보 조회

2. **품질 분석**
   - 프로젝트 품질 게이트 상태 조회
   - 프로젝트 메트릭 조회 (코드 라인 수, 커버리지, 중복, 복잡성 등)

3. **이슈 관리**
   - 프로젝트의 이슈(버그, 취약점, 코드 스멜) 목록 조회
   - 이슈 상세 정보 조회

4. **코드 구성요소 탐색**
   - 프로젝트의 파일, 디렉토리 구조 탐색

5. **규칙 관리**
   - SonarQube 규칙 목록 조회
   - 규칙 상세 정보 조회

6. **서버 상태 관리**
   - SonarQube 서버 버전 정보 조회
   - 서버 상태 확인

## 설치 및 실행

### 필수 조건

- Python 3.8 이상
- SonarQube 서버 (Community Edition)

### 로컬 환경에서 실행

1. 가상 환경 생성 및 활성화 (선택사항)
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # venv\Scripts\activate    # Windows
   ```

2. 의존성 설치
   ```bash
   pip install -r requirements.txt
   ```

3. 환경 변수 설정
   ```bash
   # .env 파일 생성
   echo "SONARQUBE_URL=http://localhost:9000" > .env
   echo "SONARQUBE_TOKEN=your_token_here" >> .env
   ```

4. 서버 실행
   ```bash
   python sonarqube_mcp_server.py
   ```

### Docker를 이용한 실행

1. Docker 이미지 빌드
   ```bash
   docker build -t sonarqube-mcp-server .
   ```

2. Docker 컨테이너 실행
   ```bash
   docker run -p 8000:8000 -e SONARQUBE_URL=http://sonarqube:9000 -e SONARQUBE_TOKEN=your_token_here sonarqube-mcp-server
   ```

## API 사용 방법

MCP 서버는 기본적으로 `http://localhost:8000`에서 실행되며, 다음과 같은 엔드포인트를 제공합니다:

- `/mcp/sse`: Server-Sent Events를 통한 MCP 통신
- `/mcp/http`: HTTP를 통한 MCP 통신

### MCP 도구 목록

모든 도구에 대한 자세한 정보는 스키마 엔드포인트에서 확인할 수 있습니다:
- `/mcp/schema`

## 설정

### 환경 변수

| 변수명 | 설명 | 기본값 |
|--------|------|-------|
| `SONARQUBE_URL` | SonarQube 서버 URL | `http://sonarqube:9000` |
| `SONARQUBE_TOKEN` | SonarQube API 토큰 | `""` (빈 문자열) |

### SonarQube 토큰 생성 방법

1. SonarQube 웹 인터페이스에 로그인
2. 오른쪽 상단의 사용자 아이콘 클릭
3. "내 계정" 선택
4. "보안" 탭 선택
5. "토큰" 섹션에서 "토큰 생성" 버튼 클릭
6. 토큰 이름 입력 및 생성
7. 생성된 토큰을 `SONARQUBE_TOKEN` 환경 변수로 설정

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요. 