import http from 'k6/http';
import { check, sleep } from 'k6';
import { SharedArray } from 'k6/data';
import { Counter } from 'k6/metrics';

// 사용자 정의 메트릭 생성
const successfulOrders = new Counter('successful_orders');
const failedOrders = new Counter('failed_orders');

// 환경변수에서 설정값 가져오기
const BASE_URL = __ENV.BASE_URL || 'http://localhost';
const USER_SERVICE_PORT = __ENV.USER_SERVICE_PORT || '8001';
const ORDER_SERVICE_PORT = __ENV.ORDER_SERVICE_PORT || '8003';
const MENU_ID = parseInt(__ENV.MENU_ID || '1');
const USER_COUNT = parseInt(__ENV.USER_COUNT || '10');
const ADDRESS = __ENV.ADDRESS || '서울시 강남구 123-45';
const PHONE = __ENV.PHONE || '010-1234-5678';

// 테스트 구성
export const options = {
  scenarios: {
    // 동시 접속 시나리오: 짧은 시간에 많은 동시 주문 생성
    concurrent_orders: {
      executor: 'ramping-arrival-rate', // 도착 속도 기반 부하 모델
      startRate: parseInt(__ENV.START_RATE || '1'),
      timeUnit: __ENV.TIME_UNIT || '1s',
      preAllocatedVUs: parseInt(__ENV.PRE_ALLOCATED_VUS || '50'),
      maxVUs: parseInt(__ENV.MAX_VUS || '100'),
      stages: [
        { duration: __ENV.RAMP_UP || '10s', target: parseInt(__ENV.RAMP_UP_TARGET || '10') },  // 초당 1개에서 10개로 증가
        { duration: __ENV.RAMP_TO_PEAK || '30s', target: parseInt(__ENV.PEAK_TARGET || '30') },  // 초당 30개 주문으로 증가
        { duration: __ENV.STEADY_STATE || '1m', target: parseInt(__ENV.STEADY_TARGET || '30') },   // 1분 동안 초당 30개 유지
        { duration: __ENV.RAMP_DOWN || '20s', target: 0 },   // 서서히 감소
      ],
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<' + (parseInt(__ENV.MAX_RESPONSE_TIME || '3000'))], // 95%의 요청이 3초 이내에 완료되어야 함
    http_req_failed: ['rate<' + (parseFloat(__ENV.MAX_FAILURE_RATE || '0.1'))],     // 실패율 10% 미만
    'successful_orders': ['count>' + (parseInt(__ENV.MIN_SUCCESSFUL_ORDERS || '50'))],  // 최소 50개 주문 성공
  },
};

// 생성할 사용자 정보
const users = new SharedArray('users', function() {
  return Array(USER_COUNT).fill(0).map((_, i) => ({
    username: `testuser${i}`,
    password: `password${i}`,
    token: null
  }));
});

// 테스트 설정
let token = '';

// 로그인하여 토큰 얻기
function login(user) {
  // OAuth2 형식으로 Form 데이터 전송
  const formData = {
    username: user.username,
    password: user.password
  };

  const params = {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  };

  const loginRes = http.post(`${BASE_URL}:${USER_SERVICE_PORT}/login`, formData, params);
  check(loginRes, {
    'login successful': (r) => r.status === 200,
  });

  if (loginRes.status === 200) {
    const body = JSON.parse(loginRes.body);
    token = body.access_token;
    return true;
  }
  console.log(`로그인 실패: ${user.username}, 상태: ${loginRes.status}, 응답: ${loginRes.body}`);
  return false;
}

// 초기화 - 사용자 회원가입 진행
export function setup() {
  console.log('동시 주문 부하 테스트 준비 중');
  
  // 테스트 사용자 생성
  for (const user of users) {
    const signupPayload = JSON.stringify({
      username: user.username,
      email: `${user.username}@example.com`,
      password: user.password
    });

    const params = {
      headers: {
        'Content-Type': 'application/json',
      },
    };

    const signupRes = http.post(`${BASE_URL}:${USER_SERVICE_PORT}/signup`, signupPayload, params);
    if (signupRes.status === 201 || signupRes.status === 400) {
      // 400은 이미 가입된 사용자일 수 있음
      console.log(`사용자 생성/확인 완료: ${user.username}`);
    }
  }
  
  console.log(`동시 주문 부하 테스트 준비 완료 (생성된 사용자 수: ${users.length})`);
  return users;
}

// 가상 사용자(VU) 스크립트 - 각 VU는 이 함수를 실행
export default function(usersData) {
  // 랜덤 사용자 선택
  const userIndex = Math.floor(Math.random() * users.length);
  const user = users[userIndex];
  
  // 토큰이 없으면 로그인
  if (!token && !login(user)) {
    console.log(`${user.username} 로그인 실패, 요청 건너뜁니다`);
    sleep(parseInt(__ENV.SLEEP_ON_ERROR || '1'));
    return;
  }
  
  // 같은 메뉴(ID=1)에 대한 주문 생성
  const orderPayload = JSON.stringify({
    items: [
      { menu_id: MENU_ID, quantity: parseInt(__ENV.QUANTITY || '1') }  // 모든 사용자가 같은 메뉴 아이템을 주문
    ],
    address: ADDRESS,
    phone: PHONE
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
  };

  // 주문 요청 전송
  const orderRes = http.post(`${BASE_URL}:${ORDER_SERVICE_PORT}/orders`, orderPayload, params);
  
  // 응답 검증
  check(orderRes, {
    'order created successfully': (r) => r.status === 201,
  });

  // 주문 실패 로깅
  if (orderRes.status !== 201) {
    console.log(`주문 생성 실패: ${orderRes.status}, ${orderRes.body}`);
    failedOrders.add(1);
  } else {
    const orderData = JSON.parse(orderRes.body);
    console.log(`주문 생성 성공: ${orderData.id}, 상태: ${orderData.status}`);
    successfulOrders.add(1);
  }

  // 요청 간 짧은 지연
  sleep(parseFloat(__ENV.REQUEST_DELAY || '0.5'));
}

// 테스트 종료 후 실행
export function teardown() {
  console.log('동시 주문 부하 테스트 완료');
} 