import http from 'k6/http';
import { sleep, check } from 'k6';

// 부하 테스트 옵션 설정
export const options = {
  stages: [
    { duration: '30s', target: 20 }, // 30초 동안 점진적으로 20명의 가상 사용자로 증가
    { duration: '1m', target: 20 },  // 1분 동안 20명의 가상 사용자 유지
    { duration: '30s', target: 0 },  // 30초 동안 점진적으로 0명으로 감소
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% 요청이 2초 미만으로 처리되어야 함
    http_req_failed: ['rate<0.1'],     // 10% 미만의 실패율 허용
  },
};

// 테스트할 API 서버 URL
const BASE_URL = __ENV.API_URL || 'http://localhost:8080';

// 임의의 아이템 데이터 생성
function generateRandomItem() {
  const itemNames = ['책', '컴퓨터', '스마트폰', '의자', '책상', '모니터'];
  const randomName = itemNames[Math.floor(Math.random() * itemNames.length)];
  
  return {
    name: `${randomName} ${Math.floor(Math.random() * 1000)}`,
    description: `설명 텍스트 ${Math.random().toString(36).substring(7)}`,
    price: Math.floor(Math.random() * 1000000) + 1000,
    tax: Math.floor(Math.random() * 100000),
  };
}

// 임의의 사용자 데이터 생성
function generateRandomUser() {
  const randomId = Math.floor(Math.random() * 10000);
  return {
    username: `user${randomId}`,
    email: `user${randomId}@example.com`,
    full_name: `테스트 사용자 ${randomId}`,
  };
}

// 메인 테스트 함수
export default function () {
  // 1. 루트 경로 테스트
  let res = http.get(`${BASE_URL}/`);
  check(res, {
    'Root API is working': (r) => r.status === 200,
    'Root message is correct': (r) => r.json().message === 'K6 Load Test Server is running',
  });
  
  // 짧은 휴식
  sleep(1);
  
  // 2. 아이템 목록 조회 API 테스트
  res = http.get(`${BASE_URL}/items`);
  check(res, {
    'Get items successful': (r) => r.status === 200,
    'Items list is array': (r) => Array.isArray(r.json()),
  });
  
  // 짧은 휴식
  sleep(1);
  
  // 3. 새 아이템 생성 API 테스트
  const newItem = generateRandomItem();
  res = http.post(`${BASE_URL}/items`, JSON.stringify(newItem), {
    headers: { 'Content-Type': 'application/json' },
  });
  check(res, {
    'Create item successful': (r) => r.status === 201,
    'Created item has ID': (r) => r.json().id !== undefined,
    'Created item has correct name': (r) => r.json().name === newItem.name,
  });
  
  const createdItemId = res.json().id;
  
  // 짧은 휴식
  sleep(1);
  
  // 4. 특정 아이템 조회 API 테스트
  res = http.get(`${BASE_URL}/items/${createdItemId}`);
  check(res, {
    'Get specific item successful': (r) => r.status === 200,
    'Item has correct ID': (r) => r.json().id === createdItemId,
  });
  
  // 짧은 휴식
  sleep(1);
  
  // 5. 사용자 생성 API 테스트
  const newUser = generateRandomUser();
  res = http.post(`${BASE_URL}/users`, JSON.stringify(newUser), {
    headers: { 'Content-Type': 'application/json' },
  });
  check(res, {
    'Create user successful': (r) => r.status === 201,
    'Created user has correct username': (r) => r.json().username === newUser.username,
  });
  
  // 짧은 휴식
  sleep(1);
  
  // 6. 사용자 조회 API 테스트 (지연 발생 API)
  res = http.get(`${BASE_URL}/users/${newUser.username}`);
  check(res, {
    'Get user successful': (r) => r.status === 200,
    'User has correct username': (r) => r.json().username === newUser.username,
  });
  
  // 짧은 휴식
  sleep(1);
  
  // 7. 통계 정보 조회 API 테스트
  res = http.get(`${BASE_URL}/stats`);
  check(res, {
    'Get stats successful': (r) => r.status === 200,
    'Stats has request_count': (r) => r.json().request_count !== undefined,
  });
  
  // API 호출 사이의 휴식 (사용자 행동 시뮬레이션)
  sleep(3);
} 