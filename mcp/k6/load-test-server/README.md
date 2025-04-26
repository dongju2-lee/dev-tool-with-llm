# K6 부하 테스트 서버

K6로 부하 테스트를 수행하기 위한 FastAPI 기반 샘플 API 서버입니다. 이 서버는 다양한 API 엔드포인트를 제공하며, 이 중 일부는 의도적으로 지연이 발생하도록 설계되어 있습니다.

## 특징

- FastAPI 기반 RESTful API 서버
- 아이템 및 사용자 관리 API 제공
- 랜덤 지연을 발생시키는 엔드포인트 포함
- K6 부하 테스트 스크립트 제공
- 메모리 기반 데이터 저장 (재시작 시 초기화)

## API 엔드포인트

서버는 다음과 같은 API 엔드포인트를 제공합니다:

| 메서드 | 경로 | 설명 | 특징 |
|--------|------|------|------|
| GET | / | 서버 상태 확인 | 정상 응답 |
| GET | /items | 모든 아이템 목록 조회 | 정상 응답 |
| POST | /items | 새 아이템 생성 | 정상 응답 |
| GET | /items/{item_id} | 특정 아이템 조회 | 정상 응답 |
| POST | /users | 새 사용자 생성 | 정상 응답 |
| GET | /users/{username} | 특정 사용자 조회 | **랜덤 지연 발생** |
| GET | /stats | 서버 통계 정보 조회 | 정상 응답 |

## 설치 및 실행

### 요구 사항

- Python 3.8 이상
- K6 (부하 테스트 실행용)

### 서버 설치 및 실행

1. 저장소 클론 후 디렉토리 이동
   ```bash
   git clone [repository-url]
   cd dev-tool-with-llm/mcp/k6/load-test-server
   ```

2. 가상 환경 생성 및 활성화
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. 의존성 설치
   ```bash
   pip install -r requirements.txt
   ```

4. 환경 변수 설정
   ```bash
   cp .env.example .env
   # 필요에 따라 .env 파일 수정
   ```

5. 서버 실행
   ```bash
   python server.py
   ```

서버는 기본적으로 http://localhost:8080 에서 실행되며, FastAPI의 자동 문서는 http://localhost:8080/docs 에서 확인할 수 있습니다.

## K6 부하 테스트 실행

### K6 설치

K6 설치 방법은 [공식 문서](https://k6.io/docs/getting-started/installation/)를 참조하세요.

### 기본 부하 테스트 실행

```bash
# 기본 테스트 실행
k6 run k6-scripts/basic-test.js

# 환경 변수로 API URL 지정
k6 run -e API_URL=http://localhost:8080 k6-scripts/basic-test.js

# VU(가상 사용자) 수와 기간 조정
k6 run --vus 50 --duration 2m k6-scripts/basic-test.js
```

## 랜덤 지연 발생 메커니즘

`/users/{username}` 엔드포인트는 랜덤한 지연을 발생시키는 특성이 있습니다:

- 20% 확률로 3~8초의 큰 지연 발생
- 80% 확률로 0.1~1초의 작은 지연 발생

이 지연은 실제 운영 환경에서 발생할 수 있는 네트워크 지연이나 서버 부하를 시뮬레이션합니다.

## 스크립트 사용자 정의

`k6-scripts/basic-test.js` 파일을 수정하여 테스트 시나리오를 조정할 수 있습니다:

- 부하 테스트 단계(`stages`) 수정
- 임계값(`thresholds`) 조정
- 테스트할 엔드포인트 추가 또는 변경
- 사용자 행동 패턴 변경

## 라이선스

MIT 