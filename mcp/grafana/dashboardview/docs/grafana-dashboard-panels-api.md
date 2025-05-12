# Grafana 대시보드 패널 API

이 문서는 Grafana 대시보드의 패널을 조회하는 API 방법을 설명합니다.

## 대시보드 패널 조회 방법

그라파나는 별도의 패널만 조회하는 API를 제공하지 않으며, 대시보드 전체를 조회한 후 JSON 모델에서 패널 정보를 추출해야 합니다.

### 1. 대시보드 UID로 대시보드 조회

특정 대시보드의 패널을 조회하려면 먼저 대시보드 UID를 사용하여 대시보드 전체 정보를 가져와야 합니다.

```
GET /api/dashboards/uid/:uid
```

**예제 요청:**
```http
GET /api/dashboards/uid/cIBgcSjkk HTTP/1.1
Accept: application/json
Content-Type: application/json
Authorization: Bearer eyJrIjoiT0tTcG1pUlY2RnVKZTFVaDFsNFZXdE9ZWmNrMkZYbk
```

**예제 응답:**
```json
{
  "dashboard": {
    "id": 1,
    "uid": "cIBgcSjkk",
    "title": "Production Overview",
    "panels": [
      {
        "id": 1,
        "type": "graph",
        "title": "CPU Usage",
        "gridPos": { "x": 0, "y": 0, "w": 12, "h": 8 }
      },
      {
        "id": 2,
        "type": "stat",
        "title": "Memory Usage",
        "gridPos": { "x": 12, "y": 0, "w": 12, "h": 8 }
      }
    ]
  },
  "meta": {
    "isStarred": false,
    "url": "/d/cIBgcSjkk/production-overview",
    "folderId": 0
  }
}
```

### 2. 대시보드 JSON에서 패널 정보 추출

응답에서 `dashboard.panels` 배열을 추출하면 해당 대시보드의 모든 패널 정보를 얻을 수 있습니다. 각 패널 객체에는 다음과 같은 정보가 포함됩니다:

- `id`: 패널 식별자
- `type`: 패널 유형 (graph, stat, table 등)
- `title`: 패널 제목
- `gridPos`: 패널 위치 및 크기 정보
- 기타 패널별 구성 정보

### 3. 특정 패널 데이터 조회 (선택적)

특정 패널의 데이터를 조회하려면 별도의 쿼리 API를 사용해야 합니다:

```
POST /api/ds/query
```

요청 본문에 데이터 소스 정보와 패널에서 사용하는 쿼리를 포함해야 합니다.

## 대시보드 목록 조회

먼저 대시보드 목록을 조회하려면:

```
GET /api/search?query=&type=dash-db
```

**예제 요청:**
```http
GET /api/search?query=&type=dash-db HTTP/1.1
Accept: application/json
Content-Type: application/json
Authorization: Bearer eyJrIjoiT0tTcG1pUlY2RnVKZTFVaDFsNFZXdE9ZWmNrMkZYbk
```

이 요청은 모든 대시보드 목록을 반환하며, 각 항목에 대시보드 UID가 포함됩니다.

## 프로그래밍 예제

다음은 Python을 사용하여 특정 대시보드의 모든 패널을 조회하는 예제입니다:

```python
import requests

GRAFANA_URL = "http://your-grafana-instance:3000"
API_KEY = "your-api-key"
DASHBOARD_UID = "cIBgcSjkk"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# 대시보드 조회
response = requests.get(
    f"{GRAFANA_URL}/api/dashboards/uid/{DASHBOARD_UID}",
    headers=headers
)

if response.status_code == 200:
    dashboard_data = response.json()
    panels = dashboard_data["dashboard"]["panels"]
    
    print(f"대시보드 '{dashboard_data['dashboard']['title']}'의 패널 목록:")
    for panel in panels:
        print(f"ID: {panel['id']}, 유형: {panel['type']}, 제목: {panel['title']}")
else:
    print(f"오류: {response.status_code} - {response.text}")
```

## 주의사항

- 패널을 조회하려면 적절한 접근 권한이 필요합니다.
- 대시보드 JSON 모델은 Grafana 버전에 따라 다를 수 있습니다.
- `panels` 배열은 중첩될 수 있으며, 행(row)이나 반복(repeat) 패널의 경우 추가 처리가 필요할 수 있습니다.
- 대규모 대시보드의 경우 JSON 응답이 매우 클 수 있습니다.

## 참고 자료

- [Grafana HTTP API 문서](https://grafana.com/docs/grafana/latest/developers/http_api/)
- [Grafana Dashboard HTTP API](https://grafana.com/docs/grafana/latest/developers/http_api/dashboard/)
- [Grafana Folder/Dashboard Search HTTP API](https://grafana.com/docs/grafana/latest/developers/http_api/folder_dashboard_search/) 