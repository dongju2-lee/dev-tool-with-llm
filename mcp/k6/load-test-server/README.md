# 마이크로서비스 부하 테스트 스크립트

이 디렉토리에는 마이크로서비스 아키텍처 테스트를 위한 k6 부하 테스트 스크립트가 포함되어 있습니다.

## 스크립트 설명

1. **01-chaos-engineering-test.js**: 카오스 엔지니어링 테스트로 결제 실패율을 설정하고 시스템의 복원력을 테스트합니다.
2. **02-concurrent-orders-test.js**: 동시 주문 처리 테스트로 동시에 많은 사용자가 같은 메뉴를 주문할 때의 동시성 제어를 테스트합니다.
3. **03-cancel-reorder-test.js**: 주문 취소 후 재주문 테스트로 재고 관리의 일관성을 테스트합니다.
4. **04-caching-effect-test.js**: 캐싱 효과 테스트로 Redis 캐싱이 성능에 미치는 영향을 측정합니다.
5. **05-microservice-communication-test.js**: 마이크로서비스 간 통신 테스트로 서비스 간 호출 흐름을 테스트합니다.

## 환경 설정

스크립트를 실행하기 전에 마이크로서비스 애플리케이션이 실행 중이어야 합니다.

```bash
# 애플리케이션 실행 (필요한 경우)
cd ../..
docker-compose up -d
```

## 공통 환경변수

모든 스크립트에서 사용되는 공통 환경변수는 다음과 같습니다:

| 환경변수 | 설명 | 기본값 |
|----------|------|--------|
| BASE_URL | 마이크로서비스가 실행 중인 기본 URL | http://localhost |
| USER_SERVICE_PORT | 사용자 서비스 포트 | 8001 |
| ORDER_SERVICE_PORT | 주문 서비스 포트 | 8003 |
| RESTAURANT_SERVICE_PORT | 레스토랑 서비스 포트 | 8002 |
| VUS | 가상 사용자 수 | 각 스크립트마다 다름 |
| RAMP_UP | 가상 사용자가 증가하는 기간 | 각 스크립트마다 다름 |
| STEADY_STATE | 부하를 유지하는 기간 | 각 스크립트마다 다름 |
| RAMP_DOWN | 가상 사용자가 감소하는 기간 | 각 스크립트마다 다름 |
| MENU_ID | 주문할 메뉴 ID | 1 |
| QUANTITY | 주문 수량 | 1 또는 2 |
| ADDRESS | 배송 주소 | 서울시 강남구 123-45 |
| PHONE | 연락처 | 010-1234-5678 |

## 스크립트별 환경변수

### 01-chaos-engineering-test.js

| 환경변수 | 설명 | 기본값 |
|----------|------|--------|
| USERNAME | 테스트 사용자 이름 | user123 |
| PASSWORD | 테스트 사용자 비밀번호 | password123 |
| EMAIL | 테스트 사용자 이메일 | user123@example.com |
| PAYMENT_FAIL_PERCENT | 결제 실패율 | 30 |
| MIN_SUCCESSFUL_ORDERS | 최소 성공 주문 수 | 10 |
| MAX_FAILED_ORDERS | 최대 실패 주문 수 | 40 |
| MAX_RESPONSE_TIME | 최대 응답 시간 (ms) | 3000 |

### 02-concurrent-orders-test.js

| 환경변수 | 설명 | 기본값 |
|----------|------|--------|
| USER_COUNT | 테스트 사용자 수 | 10 |
| START_RATE | 초기 도착률 | 1 |
| TIME_UNIT | 도착률 시간 단위 | 1s |
| PRE_ALLOCATED_VUS | 사전 할당된 가상 사용자 수 | 50 |
| MAX_VUS | 최대 가상 사용자 수 | 100 |
| RAMP_UP_TARGET | 초기 증가 목표 | 10 |
| PEAK_TARGET | 최대 부하 도착률 | 30 |
| STEADY_TARGET | 유지 부하 도착률 | 30 |
| MAX_FAILURE_RATE | 최대 실패율 | 0.1 |
| MIN_SUCCESSFUL_ORDERS | 최소 성공 주문 수 | 50 |
| REQUEST_DELAY | 요청 간 지연 시간 (초) | 0.5 |

### 03-cancel-reorder-test.js

| 환경변수 | 설명 | 기본값 |
|----------|------|--------|
| USERNAME | 테스트 사용자 이름 | user123 |
| PASSWORD | 테스트 사용자 비밀번호 | password123 |
| EMAIL | 테스트 사용자 이메일 | user123@example.com |
| MIN_REORDERS | 최소 재주문 수 | 5 |
| MIN_CANCELLED_ORDERS | 최소 취소 주문 수 | 5 |
| WAIT_AFTER_ORDER | 주문 후 대기 시간 (초) | 1 |
| WAIT_AFTER_CANCEL | 취소 후 대기 시간 (초) | 1 |
| ITERATION_SLEEP | 반복 간 대기 시간 (초) | 3 |

### 04-caching-effect-test.js

| 환경변수 | 설명 | 기본값 |
|----------|------|--------|
| USERNAME | 테스트 사용자 이름 | user123 |
| PASSWORD | 테스트 사용자 비밀번호 | password123 |
| EMAIL | 테스트 사용자 이메일 | user123@example.com |
| MAX_CACHED_AVG | 캐시된 호출의 최대 평균 시간 (ms) | 100 |
| MAX_FIRST_CALL | 첫 번째 호출의 최대 p95 시간 (ms) | 2000 |
| WAIT_BETWEEN_CALLS | 호출 간 대기 시간 (초) | 1 |

### 05-microservice-communication-test.js

| 환경변수 | 설명 | 기본값 |
|----------|------|--------|
| DEFAULT_USERNAME | 테스트 사용자 이름 | testuser |
| DEFAULT_PASSWORD | 테스트 사용자 비밀번호 | testpass123 |
| DEFAULT_EMAIL | 테스트 사용자 이메일 | testuser@example.com |
| MIN_SUCCESS_RATE | 최소 서비스 호출 성공률 | 0.95 |
| MAX_COMM_LATENCY | 최대 서비스 간 통신 지연 시간 (ms) | 1000 |
| SLEEP_ON_ERROR | 오류 발생 시 대기 시간 (초) | 1 |

## 실행 방법

k6 스크립트를 실행하는 방법은 다음과 같습니다:

```bash
# 기본 실행
k6 run 01-chaos-engineering-test.js

# 환경변수 설정하여 실행
k6 run -e VUS=20 -e RAMP_UP=1m -e STEADY_STATE=5m -e PAYMENT_FAIL_PERCENT=50 01-chaos-engineering-test.js

# 여러 환경변수 설정하여 실행
k6 run -e BASE_URL=http://test-server -e USER_SERVICE_PORT=9001 -e ORDER_SERVICE_PORT=9003 -e RESTAURANT_SERVICE_PORT=9002 -e VUS=30 02-concurrent-orders-test.js
```

## 실행 예제

### 1. 카오스 엔지니어링 테스트

```bash
# 결제 실패율 50%로 테스트
k6 run -e PAYMENT_FAIL_PERCENT=50 -e VUS=15 -e STEADY_STATE=2m 01-chaos-engineering-test.js
```

### 2. 동시 주문 부하 테스트

```bash
# 초당 50개의 주문 요청으로 테스트
k6 run -e PEAK_TARGET=50 -e STEADY_TARGET=50 -e MAX_VUS=200 -e STEADY_STATE=3m 02-concurrent-orders-test.js
```

### 3. 취소-재주문 테스트

```bash
# 20명의 가상 사용자로 2분간 테스트
k6 run -e VUS=20 -e STEADY_STATE=2m 03-cancel-reorder-test.js
```

### 4. 캐싱 효과 테스트

```bash
# 10명의 가상 사용자로 1분간 테스트
k6 run -e VUS=10 -e STEADY_STATE=1m 04-caching-effect-test.js
```

### 5. 마이크로서비스 간 통신 테스트

```bash
# 사용자 지정 환경에서 15명의 가상 사용자로 테스트
k6 run -e BASE_URL=http://192.168.1.100 -e VUS=15 -e STEADY_STATE=2m 05-microservice-communication-test.js
```

## 결과 분석

테스트 결과는 k6가 제공하는 표준 출력으로 확인할 수 있습니다. 추가적인 분석을 위해 다음과 같은 명령을 사용할 수 있습니다:

```bash
# JSON 형식으로 결과 저장
k6 run -e VUS=10 01-chaos-engineering-test.js --out json=results.json

# InfluxDB로 결과 전송 (InfluxDB 실행 필요)
k6 run -e VUS=10 01-chaos-engineering-test.js --out influxdb=http://localhost:8086/k6
```

Grafana와 InfluxDB를 사용하여 결과를 시각화하는 방법은 [k6 공식 문서](https://k6.io/docs/results-visualization/influxdb-+-grafana)를 참조하세요.

## 문제 해결

- **마이크로서비스 접근 오류**: BASE_URL과 포트 번호가 올바르게 설정되었는지 확인하세요.
- **인증 오류**: 사용자 계정이 올바르게 생성되었는지 확인하세요.
- **메모리 부족 오류**: 가상 사용자 수(VUS)를 줄이거나 시스템의 메모리를 늘리세요.
- **테스트 데이터 부재 오류**: 테스트 전에 필요한 데이터(메뉴 등)가 데이터베이스에 있는지 확인하세요. 