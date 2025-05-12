import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter } from 'k6/metrics';

// 사용자 정의 메트릭 생성
const failedOrders = new Counter('failed_orders');
const successfulOrders = new Counter('successful_orders');

// 환경변수에서 설정값 가져오기
const BASE_URL = __ENV.BASE_URL || 'http://localhost';
const USERNAME = __ENV.USERNAME || 'user123';
const PASSWORD = __ENV.PASSWORD || 'password123';
const EMAIL = __ENV.EMAIL || 'user123@example.com';
const PAYMENT_FAIL_PERCENT = parseInt(__ENV.PAYMENT_FAIL_PERCENT || '30');

// 테스트 구성 - 환경변수로 스테이지 구성을 조정할 수 있게 함
export const options = {
  stages: [
    { duration: __ENV.RAMP_UP || '30s', target: parseInt(__ENV.VUS || '10') },
    { duration: __ENV.STEADY_STATE || '1m', target: parseInt(__ENV.VUS || '10') },
    { duration: __ENV.RAMP_DOWN || '30s', target: 0 },
  ],
  thresholds: {
    // 성공적인 결제가 최소 60% 이상이어야 함 (결제 실패율 30% 설정으로 인해)
    'successful_orders': ['count>' + (parseInt(__ENV.MIN_SUCCESSFUL_ORDERS || '10'))],
    // 결제 실패가 40% 이하여야 함
    'failed_orders': ['count<' + (parseInt(__ENV.MAX_FAILED_ORDERS || '40'))],
    // 응답 시간은 p95에서 3초 미만이어야 함
    'http_req_duration': ['p(95)<' + (parseInt(__ENV.MAX_RESPONSE_TIME || '3000'))],
  },
};

// 테스트 설정
let token = '';

// 로그인하여 토큰 얻기
function login() {
  // OAuth2 형식으로 Form 데이터 전송
  const formData = {
    username: USERNAME,
    password: PASSWORD
  };

  const params = {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  };

  const loginRes = http.post(`${BASE_URL}:${__ENV.USER_SERVICE_PORT || '8001'}/login`, formData, params);
  check(loginRes, {
    'login successful': (r) => r.status === 200,
  });

  if (loginRes.status === 200) {
    const body = JSON.parse(loginRes.body);
    token = body.access_token;
    return true;
  }
  console.log(`로그인 실패: 상태 코드 ${loginRes.status}, 응답: ${loginRes.body}`);
  return false;
}

// 결제 실패율 설정
function setupPaymentFailRate() {
  const payload = JSON.stringify({
    fail_percent: PAYMENT_FAIL_PERCENT
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const res = http.post(`${BASE_URL}:${__ENV.ORDER_SERVICE_PORT || '8003'}/chaos/payment_fail`, payload, params);
  check(res, {
    'payment fail rate set': (r) => r.status === 200,
  });
}

// 초기화 함수 - 한 번만 실행됨
export function setup() {
  console.log('설정 중: 테스트 사용자 생성 및 결제 실패율 설정');
  
  // 테스트 사용자 생성
  const signupPayload = JSON.stringify({
    username: USERNAME,
    email: EMAIL,
    password: PASSWORD
  });

  const signupParams = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const signupRes = http.post(`${BASE_URL}:${__ENV.USER_SERVICE_PORT || '8001'}/signup`, signupPayload, signupParams);
  console.log(`사용자 생성 응답: ${signupRes.status}, ${signupRes.body}`);
  
  if (signupRes.status === 201 || signupRes.status === 400) {
    // 400은 이미 가입된 사용자일 수 있음
    console.log('사용자 생성/확인 완료');
    
    // 로그인 확인
    if (login()) {
      console.log('로그인 테스트 성공, 인증 서비스 정상 작동');
    } else {
      console.log('주의: 로그인 테스트 실패, 테스트에 영향이 있을 수 있습니다.');
    }
  }
  
  setupPaymentFailRate();
  console.log(`카오스 엔지니어링 테스트 준비 완료 (결제 실패율: ${PAYMENT_FAIL_PERCENT}%)`);
}

// 가상 사용자(VU) 스크립트 - 각 VU는 이 함수를 실행
export default function() {
  if (!token && !login()) {
    console.log('로그인 실패, 테스트를 건너뜁니다.');
    sleep(1);
    return;
  }

  // 주문 생성
  const orderPayload = JSON.stringify({
    items: [
      { menu_id: parseInt(__ENV.MENU_ID || '1'), quantity: parseInt(__ENV.QUANTITY || '2') }
    ],
    address: __ENV.ADDRESS || '서울시 강남구 123-45',
    phone: __ENV.PHONE || '010-1234-5678'
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
  };

  const orderRes = http.post(`${BASE_URL}:${__ENV.ORDER_SERVICE_PORT || '8003'}/orders`, orderPayload, params);
  
  check(orderRes, {
    'order response status 201': (r) => r.status === 201,
  });

  if (orderRes.status === 201) {
    const orderData = JSON.parse(orderRes.body);
    
    // 주문 결과 확인 (성공 또는 실패)
    if (orderData.status === 'FAILED') {
      failedOrders.add(1);
      console.log(`주문 실패: ${orderData.id}`);
    } else {
      successfulOrders.add(1);
      console.log(`주문 성공: ${orderData.id}`);
    }

    // 주문 상태 조회
    const orderDetailsRes = http.get(`${BASE_URL}:${__ENV.ORDER_SERVICE_PORT || '8003'}/orders/${orderData.id}`, params);
    check(orderDetailsRes, {
      'order details retrieved': (r) => r.status === 200,
    });
  }

  sleep(parseInt(__ENV.SLEEP_DURATION || '3'));
}

// 테스트 종료 후 실행
export function teardown() {
  console.log('카오스 엔지니어링 테스트 완료');
} 