# Grafana Dashboard MCP Server

Grafana 대시보드 API를 LLM이 활용할 수 있도록 만든 MCP(Model Context Protocol) 서버입니다.

## 기능 목록
- 데이터소스 목록 조회
- 대시보드 목록 조회 (Dashboard folder 에 있는 목록)

## 실행 방법

- Grafana renderer 가 떠 있어야 작동합니다.

### 환경 변수 설정
`.env` 파일을 생성하고 다음 내용을 추가하세요:

```
GRAFANA_URL=http://grafana:3000
GRAFANA_API_KEY=your_api_key_here
```

### Grafana API 키 발급
1. Grafana 대시보드 로그인
2. 좌측 하단 Configuration > API Keys 메뉴
3. `Add API key` 버튼 클릭
4. 이름, 역할(Admin), 만료 기간 설정 후 키 생성
5. 생성된 키를 `.env` 파일의 `GRAFANA_API_KEY`에 설정

### 파이썬으로 실행
```bash
# 의존성 설치
pip install -r requirements.txt

# 서버 실행
python grafana_mcp_server.py
```

### Docker로 실행
```bash
# 이미지 빌드
docker build -t grafana-mcp-server .

# 컨테이너 실행
docker run -p 8000:8000 --env-file .env grafana-mcp-server
```

### Docker Compose로 실행
```bash
# Grafana와 함께 실행
docker-compose up -d
```

## 필요한 서비스

### Grafana
- 기본 URL: http://localhost:3000
- 기본 사용자/비밀번호: admin/admin

### Grafana Image Renderer 
- 렌더링 기능을 사용하기 위해 필요
- Docker Compose 설정 예시:

```yaml
services:
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_RENDERING_SERVER_URL=http://renderer:8081/render
      - GF_RENDERING_CALLBACK_URL=http://grafana:3000/
    
  renderer:
    image: grafana/grafana-image-renderer:latest
    ports:
      - "8081:8081"
```

## 기능

### 데이터소스 도구
- `list_datasources()`: 모든 데이터소스 목록 조회
- `get_datasource(id_or_name)`: 특정 데이터소스 상세 정보 조회
- `test_datasource(id_or_name)`: 데이터소스 연결 테스트

### 대시보드 도구
- `list_dashboards(folder_id, query)`: 대시보드 목록 조회
- `get_dashboard(uid)`: 특정 대시보드 상세 정보 조회

### 패널 도구
- `list_panels(dashboard_uid)`: 대시보드의 패널 목록 조회
- `get_panel_data(dashboard_uid, panel_id, time_range)`: 패널 데이터 쿼리
  - `time_range`: 딕셔너리 형태 (예: `{"from": "now-6h", "to": "now"}`)

### 시각화 도구
- `render_dashboard(dashboard_uid, time_range, width, height, theme)`: 대시보드 이미지 렌더링
  - `time_range`: 딕셔너리 형태 (예: `{"from": "now-6h", "to": "now"}`)
- `render_panel(dashboard_uid, panel_id, time_range, width, height, theme)`: 패널 이미지 렌더링
  - `time_range`: 딕셔너리 형태 (예: `{"from": "now-6h", "to": "now"}`)
