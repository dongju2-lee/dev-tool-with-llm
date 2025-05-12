import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend } from 'k6/metrics';

// 사용자 정의 메트릭 생성
const firstCallDuration = new Trend('first_call_duration');
const cachedCallDuration = new Trend('cached_call_duration');
const cacheMissCallDuration = new Trend('cache_miss_call_duration');

// 환경변수에서 설정값 가져오기
const BASE_URL = __ENV.BASE_URL || 'http://localhost';
const USER_SERVICE_PORT = __ENV.USER_SERVICE_PORT || '8001';
const ORDER_SERVICE_PORT = __ENV.ORDER_SERVICE_PORT || '8003';
const RESTAURANT_SERVICE_PORT = __ENV.RESTAURANT_SERVICE_PORT || '8002';
const USERNAME = __ENV.USERNAME || 'user123';
const PASSWORD = __ENV.PASSWORD || 'password123';
const EMAIL = __ENV.EMAIL || 'user123@example.com';
const MENU_ID = parseInt(__ENV.MENU_ID || '1');
const QUANTITY = parseInt(__ENV.QUANTITY || '1');
const ADDRESS = __ENV.ADDRESS || '서울시 강남구 123-45';
const PHONE = __ENV.PHONE || '010-1234-5678';

// 테스트 구성
export const options = {
  stages: [
    { duration: __ENV.RAMP_UP || '10s', target: parseInt(__ENV.VUS || '5') },  // 5명의 가상 사용자로 증가
    { duration: __ENV.STEADY_STATE || '50s', target: parseInt(__ENV.VUS || '5') },  // 50초 동안 유지
    { duration: __ENV.RAMP_DOWN || '10s', target: 0 },  // 서서히 감소
  ],
  thresholds: {
    // 캐시된 호출은 첫 번째 호출보다 훨씬 빨라야 함
    'cached_call_duration': ['avg<' + (parseInt(__ENV.MAX_CACHED_AVG || '100'))],  // 평균 100ms 미만
    'first_call_duration': ['p(95)<' + (parseInt(__ENV.MAX_FIRST_CALL || '2000'))], // 95%가 2초 미만
    'http_req_duration': ['p(95)<' + (parseInt(__ENV.MAX_RESPONSE_TIME || '2000'))],
  },
};

// 테스트 설정
let token = '';
const createdOrderIds = [];

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

  const loginRes = http.post(`${BASE_URL}:${USER_SERVICE_PORT}/login`, formData, params);
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

// 초기화 함수 - 테스트 데이터 생성
export function setup() {
  console.log('캐싱 효과 테스트 준비 중');
  
  // 테스트 사용자 생성
  const signupPayload = JSON.stringify({
    username: USERNAME,
    email: EMAIL,
    password: PASSWORD
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const signupRes = http.post(`${BASE_URL}:${USER_SERVICE_PORT}/signup`, signupPayload, params);
  if (signupRes.status === 201 || signupRes.status === 400) {
    // 400은 이미 가입된 사용자일 수 있음
    console.log('사용자 생성/확인 완료');
    
    // 로그인하여 토큰 얻기
    if (login()) {
      console.log('로그인 성공');
      
      // 테스트용 주문 미리 생성
      const orderPayload = JSON.stringify({
        items: [
          { menu_id: MENU_ID, quantity: QUANTITY }
        ],
        address: ADDRESS,
        phone: PHONE
      });
      
      const orderParams = {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
      };
      
      // 테스트용 주문 하나 생성
      const orderRes = http.post(`${BASE_URL}:${ORDER_SERVICE_PORT}/orders`, orderPayload, orderParams);
      if (orderRes.status === 201) {
        const orderData = JSON.parse(orderRes.body);
        createdOrderIds.push(orderData.id);
        console.log(`테스트용 주문 생성 완료: ${orderData.id}`);
      }
    }
  }
  
  console.log('캐싱 효과 테스트 준비 완료');
  return { orderIds: createdOrderIds };
}

// 가상 사용자(VU) 스크립트 - 각 VU는 이 함수를 실행
export default function(data) {
  if (!token && !login()) {
    console.log('로그인 실패, 테스트를 건너뜁니다.');
    sleep(parseInt(__ENV.SLEEP_ON_ERROR || '1'));
    return;
  }
  
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
  };
  
  if (data.orderIds.length === 0) {
    console.log('테스트용 주문이 없습니다.');
    return;
  }
  
  const orderId = data.orderIds[0];

  // 1. 첫 번째 호출 (캐시 미스)
  console.log(`첫 번째 호출 - 주문 ID: ${orderId}`);
  const startFirstCall = new Date();
  const firstCallRes = http.get(`${BASE_URL}:${ORDER_SERVICE_PORT}/orders/${orderId}`, params);
  const firstCallDurationMs = new Date() - startFirstCall;
  
  check(firstCallRes, {
    'first call successful': (r) => r.status === 200,
  });
  
  firstCallDuration.add(firstCallDurationMs);
  console.log(`첫 번째 호출 시간: ${firstCallDurationMs}ms`);
  
  sleep(parseFloat(__ENV.WAIT_BETWEEN_CALLS || '1'));
  
  // 2. 두 번째 호출 (캐시 히트)
  console.log(`두 번째 호출 (캐시 히트) - 주문 ID: ${orderId}`);
  const startSecondCall = new Date();
  const secondCallRes = http.get(`${BASE_URL}:${ORDER_SERVICE_PORT}/orders/${orderId}`, params);
  const secondCallDurationMs = new Date() - startSecondCall;
  
  check(secondCallRes, {
    'cached call successful': (r) => r.status === 200,
  });
  
  cachedCallDuration.add(secondCallDurationMs);
  console.log(`두 번째 호출 시간 (캐시 히트): ${secondCallDurationMs}ms`);
  
  // 전체 메뉴 조회 호출 (Restaurant Service 캐싱 테스트)
  console.log(`전체 메뉴 조회 호출`);
  const startMenusCall = new Date();
  const menusRes = http.get(`${BASE_URL}:${RESTAURANT_SERVICE_PORT}/menus`, params);
  const menusCallDurationMs = new Date() - startMenusCall;
  
  check(menusRes, {
    'menus call successful': (r) => r.status === 200,
  });
  
  console.log(`전체 메뉴 조회 시간: ${menusCallDurationMs}ms`);
  
  sleep(parseFloat(__ENV.WAIT_BETWEEN_CALLS || '1'));
  
  // 두 번째 전체 메뉴 조회 (캐시 히트)
  const startMenusSecondCall = new Date();
  const menusSecondRes = http.get(`${BASE_URL}:${RESTAURANT_SERVICE_PORT}/menus`, params);
  const menusSecondCallDurationMs = new Date() - startMenusSecondCall;
  
  check(menusSecondRes, {
    'menus second call successful': (r) => r.status === 200,
  });
  
  console.log(`전체 메뉴 두 번째 조회 시간 (캐시 히트): ${menusSecondCallDurationMs}ms`);
  
  sleep(parseInt(__ENV.ITERATION_SLEEP || '3'));
}

// 테스트 종료 후 실행
export function teardown(data) {
  console.log('캐싱 효과 테스트 완료');
} 