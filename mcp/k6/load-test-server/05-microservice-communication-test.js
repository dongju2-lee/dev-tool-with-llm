import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// 사용자 정의 메트릭 생성
const authenticationsCount = new Counter('authentications');
const userValidationsCount = new Counter('user_validations');
const inventoryUpdatesCount = new Counter('inventory_updates');
const serviceCallsRate = new Rate('service_calls_success_rate');
const serviceCommsLatency = new Trend('service_communication_latency');

// 환경변수에서 설정값 가져오기
const BASE_URL = __ENV.BASE_URL || 'http://localhost';
const USER_SERVICE_PORT = __ENV.USER_SERVICE_PORT || '8001';
const ORDER_SERVICE_PORT = __ENV.ORDER_SERVICE_PORT || '8003';
const RESTAURANT_SERVICE_PORT = __ENV.RESTAURANT_SERVICE_PORT || '8002';
const DEFAULT_USERNAME = __ENV.DEFAULT_USERNAME || 'testuser';
const DEFAULT_PASSWORD = __ENV.DEFAULT_PASSWORD || 'testpass123';
const DEFAULT_EMAIL = __ENV.DEFAULT_EMAIL || 'testuser@example.com';
const ADDRESS = __ENV.ADDRESS || '서울시 강남구 123-45';
const PHONE = __ENV.PHONE || '010-1234-5678';

// 테스트 구성
export const options = {
  stages: [
    { duration: __ENV.RAMP_UP || '20s', target: parseInt(__ENV.VUS || '5') },   // 5명의 가상 사용자로 증가
    { duration: __ENV.STEADY_STATE || '1m', target: parseInt(__ENV.VUS || '5') },    // 1분 동안 유지
    { duration: __ENV.RAMP_DOWN || '10s', target: 0 },   // 서서히 감소
  ],
  thresholds: {
    // 서비스 간 통신 성공률 95% 이상
    'service_calls_success_rate': ['rate>' + (parseFloat(__ENV.MIN_SUCCESS_RATE || '0.95'))],
    // 서비스 간 통신 시간 1초 미만
    'service_communication_latency': ['p(95)<' + (parseInt(__ENV.MAX_COMM_LATENCY || '1000'))],
    'http_req_duration': ['p(95)<' + (parseInt(__ENV.MAX_RESPONSE_TIME || '3000'))],
  },
};

// 테스트 설정
let users = [];
// 고정 사용자 자격 증명 - 테스트 전에 한 명은 생성해야 함
const defaultUser = {
  username: DEFAULT_USERNAME,
  email: DEFAULT_EMAIL,
  password: DEFAULT_PASSWORD
};

// 로그인하여 토큰 얻기 - OAuth2 형식으로 수정
function login(username, password) {
  const startTime = new Date();
  
  console.log(`로그인 시도 중: ${username}`);
  
  // OAuth2 형식의 form 데이터로 전송해야 함
  const formData = {
    username: username,
    password: password,
  };

  const params = {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  };

  const loginRes = http.post(
    `${BASE_URL}:${USER_SERVICE_PORT}/login`, 
    formData,
    params
  );
  
  const success = loginRes.status === 200;
  serviceCallsRate.add(success);
  
  const duration = new Date() - startTime;
  serviceCommsLatency.add(duration);
  
  check(loginRes, {
    'login successful': (r) => r.status === 200,
  });

  if (success) {
    authenticationsCount.add(1);
    console.log(`로그인 성공: ${username}`);
    const body = JSON.parse(loginRes.body);
    return body.access_token;
  }
  
  console.log(`로그인 실패: ${username}, 상태: ${loginRes.status}, 응답: ${loginRes.body}`);
  return null;
}

// 초기화 함수 - 기본 테스트 사용자 생성
export function setup() {
  console.log('마이크로서비스 간 통신 테스트 준비 중');
  
  // 기본 사용자 만들기
  console.log(`기본 테스트 사용자 생성: ${defaultUser.username}`);
  const signupPayload = JSON.stringify({
    username: defaultUser.username,
    email: defaultUser.email,
    password: defaultUser.password
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const signupRes = http.post(`${BASE_URL}:${USER_SERVICE_PORT}/signup`, signupPayload, params);
  console.log(`사용자 생성 응답: ${signupRes.status}, ${signupRes.body}`);
  
  if (signupRes.status === 201 || signupRes.status === 400) {
    // 400은 이미 가입된 사용자일 수 있으므로 추가
    console.log(`사용자 생성/확인 완료: ${defaultUser.username}`);
    users.push(defaultUser);
    
    // 로그인 확인
    const token = login(defaultUser.username, defaultUser.password);
    if (token) {
      console.log("로그인 테스트 성공, 인증 서비스 정상 작동");
    } else {
      console.log("주의: 로그인 테스트 실패, 테스트에 영향이 있을 수 있습니다.");
    }
  }
  
  console.log('마이크로서비스 간 통신 테스트 준비 완료');
  return { users };
}

// 가상 사용자(VU) 스크립트 - 각 VU는 이 함수를 실행
export default function(data) {
  // 기본 사용자 사용
  const user = defaultUser;
  
  // 1. 로그인 (User Service)
  console.log(`${user.username} 로그인 시도`);
  const token = login(user.username, user.password);
  
  if (!token) {
    console.log(`${user.username} 로그인 실패, 테스트를 건너뜁니다.`);
    sleep(parseInt(__ENV.SLEEP_ON_ERROR || '1'));
    return;
  }
  
  console.log(`${user.username} 로그인 성공`);
  
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
  };
  
  // 2. 메뉴 조회 (Restaurant Service)
  console.log('메뉴 조회 중');
  const startMenusTime = new Date();
  const menusRes = http.get(`${BASE_URL}:${RESTAURANT_SERVICE_PORT}/menus`, params);
  
  const menusSuccess = menusRes.status === 200;
  serviceCallsRate.add(menusSuccess);
  serviceCommsLatency.add(new Date() - startMenusTime);
  
  check(menusRes, {
    'menus retrieved successfully': (r) => r.status === 200,
  });
  
  if (!menusSuccess) {
    console.log(`메뉴 조회 실패: ${menusRes.status}, ${menusRes.body}`);
    sleep(parseInt(__ENV.SLEEP_ON_ERROR || '1'));
    return;
  }
  
  // 메뉴 목록에서 첫 번째 메뉴 선택
  const menuItems = JSON.parse(menusRes.body);
  if (!menuItems || menuItems.length === 0) {
    console.log('메뉴 없음, 테스트를 건너뜁니다.');
    sleep(parseInt(__ENV.SLEEP_ON_ERROR || '1'));
    return;
  }
  
  const selectedMenu = menuItems[0];
  console.log(`메뉴 선택: ${selectedMenu.name}, ID: ${selectedMenu.id}`);
  
  // 3. 주문 생성 (Order Service -> User Service -> Restaurant Service)
  console.log('주문 생성 중');
  const orderPayload = JSON.stringify({
    items: [
      { menu_id: selectedMenu.id, quantity: parseInt(__ENV.QUANTITY || '1') }
    ],
    address: ADDRESS,
    phone: PHONE
  });
  
  const startOrderTime = new Date();
  const orderRes = http.post(`${BASE_URL}:${ORDER_SERVICE_PORT}/orders`, orderPayload, params);
  
  const orderSuccess = orderRes.status === 201;
  serviceCallsRate.add(orderSuccess);
  serviceCommsLatency.add(new Date() - startOrderTime);
  
  check(orderRes, {
    'order created successfully': (r) => r.status === 201,
  });
  
  if (orderSuccess) {
    // 사용자 검증 카운트 (Order Service -> User Service)
    userValidationsCount.add(1);
    // 재고 업데이트 카운트 (Order Service -> Restaurant Service)
    inventoryUpdatesCount.add(1);
    
    const orderData = JSON.parse(orderRes.body);
    console.log(`주문 생성 성공: ${orderData.id}, 상태: ${orderData.status}`);
    
    // 4. 주문 상태 조회 (Order Service)
    console.log(`주문 상태 조회 중: ${orderData.id}`);
    const startStatusTime = new Date();
    const statusRes = http.get(`${BASE_URL}:${ORDER_SERVICE_PORT}/orders/${orderData.id}`, params);
    
    const statusSuccess = statusRes.status === 200;
    serviceCallsRate.add(statusSuccess);
    serviceCommsLatency.add(new Date() - startStatusTime);
    
    check(statusRes, {
      'order status retrieved': (r) => r.status === 200,
    });
    
    if (statusSuccess) {
      const statusData = JSON.parse(statusRes.body);
      console.log(`주문 상태: ${statusData.status}`);
    } else {
      console.log(`주문 상태 조회 실패: ${statusRes.status}, ${statusRes.body}`);
    }
  } else {
    console.log(`주문 생성 실패: ${orderRes.status}, ${orderRes.body}`);
  }
  
  sleep(parseInt(__ENV.ITERATION_SLEEP || '3'));
}

// 테스트 종료 후 실행
export function teardown(data) {
  console.log('마이크로서비스 간 통신 테스트 완료');
  console.log(`인증 횟수: ${authenticationsCount.name}`);
  console.log(`사용자 검증 횟수: ${userValidationsCount.name}`);
  console.log(`재고 업데이트 횟수: ${inventoryUpdatesCount.name}`);
} 