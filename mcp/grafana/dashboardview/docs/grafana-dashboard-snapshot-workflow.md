# Grafana 대시보드 조회 및 스냅샷 생성 프로세스 API 구상

대시보드 목록 조회부터 스냅샷 생성 및 조회까지의 전체 워크플로우에 필요한 API 목록과 순서를 구상했습니다.

## 1. 대시보드 목록 조회

```
GET /api/search
```

**매개변수**:
- `query`: 검색어 (선택적)
- `tag`: 특정 태그로 필터링 (선택적)
- `type`: "dash-db"로 지정하여 대시보드만 조회
- `limit`: 반환할 최대 항목 수 (선택적)

**응답 예시**:
```json
[
  {
    "id": 1,
    "uid": "cIBgcSjkk",
    "title": "Production Overview",
    "url": "/d/cIBgcSjkk/production-overview",
    "type": "dash-db",
    "tags": ["production", "metrics"],
    "isStarred": true
  },
  {
    "id": 2,
    "uid": "ABCd123kk",
    "title": "Application Performance",
    "url": "/d/ABCd123kk/application-performance",
    "type": "dash-db",
    "tags": ["application", "performance"],
    "isStarred": false
  }
]
```

## 2. 대시보드 상세 정보 조회

```
GET /api/dashboards/uid/:uid
```

**매개변수**:
- `uid`: 대시보드 고유 식별자 (URL 경로에 포함)

**응답 예시**:
```json
{
  "dashboard": {
    "id": 1,
    "uid": "cIBgcSjkk",
    "title": "Production Overview",
    "version": 1,
    "panels": [
      {
        "id": 1,
        "type": "graph",
        "title": "CPU Usage",
        "targets": [
          {
            "refId": "A",
            "expr": "sum(rate(container_cpu_usage_seconds_total[5m]))"
          }
        ]
      }
    ],
    "time": {
      "from": "now-6h",
      "to": "now"
    }
  },
  "meta": {
    "isStarred": true,
    "url": "/d/cIBgcSjkk/production-overview",
    "folderId": 0,
    "folderTitle": "General",
    "canSave": true,
    "canEdit": true,
    "canAdmin": true,
    "canStar": true,
    "canDelete": true
  }
}
```

## 3. 대시보드 데이터 조회 (패널 데이터 가져오기)

```
POST /api/ds/query
```

**요청 본문**:
```json
{
  "queries": [
    {
      "refId": "A",
      "datasource": {
        "uid": "P8E80F9AEF21F6940",
        "type": "prometheus"
      },
      "expr": "sum(rate(container_cpu_usage_seconds_total[5m]))",
      "instant": false,
      "range": true,
      "format": "time_series"
    }
  ],
  "range": {
    "from": "2023-01-01T00:00:00.000Z",
    "to": "2023-01-01T01:00:00.000Z",
    "raw": {
      "from": "now-1h",
      "to": "now"
    }
  },
  "from": "1672531200000",
  "to": "1672534800000"
}
```

**응답 예시**:
```json
{
  "results": {
    "A": {
      "frames": [
        {
          "schema": {
            "fields": [
              {"name": "time", "type": "time"},
              {"name": "value", "type": "number"}
            ]
          },
          "data": {
            "values": [
              [1672531200000, 1672531500000, 1672531800000],
              [0.25, 0.30, 0.28]
            ]
          }
        }
      ]
    }
  }
}
```

## 4. 스냅샷 생성 준비 (대시보드 모델 준비)

이 단계는 클라이언트 측 작업으로, API 호출은 없습니다. 대시보드 JSON 모델과 패널 데이터를 결합하여 스냅샷 생성에 필요한 형태로 준비합니다.

## 5. 스냅샷 생성

```
POST /api/snapshots
```

**요청 본문**:
```json
{
  "dashboard": {
    "id": 1,
    "uid": "cIBgcSjkk",
    "title": "Production Overview Snapshot",
    "panels": [
      {
        "id": 1,
        "type": "graph",
        "title": "CPU Usage",
        "targets": [
          {
            "refId": "A",
            "expr": "sum(rate(container_cpu_usage_seconds_total[5m]))"
          }
        ],
        "snapshotData": {
          "data": {
            "values": [
              [1672531200000, 1672531500000, 1672531800000],
              [0.25, 0.30, 0.28]
            ]
          }
        }
      }
    ],
    "time": {
      "from": "2023-01-01T00:00:00.000Z",
      "to": "2023-01-01T01:00:00.000Z"
    }
  },
  "name": "Production Overview - Jan 1st 2023",
  "expires": 3600
}
```

**응답 예시**:
```json
{
  "key": "SNAPSHOT_KEY",
  "deleteKey": "DELETE_KEY",
  "url": "/dashboard/snapshot/SNAPSHOT_KEY",
  "deleteUrl": "/api/snapshots-delete/DELETE_KEY",
  "id": 1
}
```

## 6. 스냅샷 목록 조회 (선택적)

```
GET /api/snapshots
```

**응답 예시**:
```json
[
  {
    "id": 1,
    "name": "Production Overview - Jan 1st 2023",
    "key": "SNAPSHOT_KEY",
    "orgId": 1,
    "userId": 1,
    "external": false,
    "externalUrl": "",
    "expires": "2023-01-02T00:00:00Z",
    "created": "2023-01-01T00:00:00Z",
    "updated": "2023-01-01T00:00:00Z"
  }
]
```

## 7. 특정 스냅샷 조회

```
GET /api/snapshots/SNAPSHOT_KEY
```

**응답 예시**:
```json
{
  "meta": {
    "isSnapshot": true,
    "type": "snapshot",
    "canSave": false,
    "canEdit": false,
    "canAdmin": false,
    "canStar": false,
    "slug": "",
    "expires": "2023-01-02T00:00:00Z",
    "created": "2023-01-01T00:00:00Z"
  },
  "dashboard": {
    "id": null,
    "title": "Production Overview Snapshot",
    "panels": [
      {
        "id": 1,
        "type": "graph",
        "title": "CPU Usage",
        "snapshotData": {
          "data": {
            "values": [
              [1672531200000, 1672531500000, 1672531800000],
              [0.25, 0.30, 0.28]
            ]
          }
        }
      }
    ],
    "time": {
      "from": "2023-01-01T00:00:00.000Z",
      "to": "2023-01-01T01:00:00.000Z"
    }
  }
}
```

## 전체 워크플로우 구현 예시 (TypeScript)

```typescript
class GrafanaService {
  private readonly baseUrl: string;
  private readonly headers: Record<string, string>;

  constructor(baseUrl: string, apiKey: string) {
    this.baseUrl = baseUrl;
    this.headers = {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json'
    };
  }

  // 1. 대시보드 목록 조회
  async getDashboards(query?: string, tag?: string): Promise<Dashboard[]> {
    const params = new URLSearchParams({
      type: 'dash-db'
    });
    
    if (query) params.append('query', query);
    if (tag) params.append('tag', tag);
    
    const response = await fetch(`${this.baseUrl}/api/search?${params}`, {
      headers: this.headers
    });
    
    if (!response.ok) {
      throw new Error(`대시보드 목록 조회 실패: ${response.status}`);
    }
    
    return await response.json();
  }

  // 2. 대시보드 상세 정보 조회
  async getDashboardByUid(uid: string): Promise<DashboardDetail> {
    const response = await fetch(`${this.baseUrl}/api/dashboards/uid/${uid}`, {
      headers: this.headers
    });
    
    if (!response.ok) {
      throw new Error(`대시보드 상세 정보 조회 실패: ${response.status}`);
    }
    
    return await response.json();
  }

  // 3. 대시보드 패널 데이터 조회
  async getPanelData(datasourceUid: string, queries: any[], timeRange: TimeRange): Promise<any> {
    const request = {
      queries: queries.map(q => ({
        ...q,
        datasource: {
          uid: datasourceUid,
          type: 'prometheus' // 또는 다른 타입
        }
      })),
      range: timeRange
    };
    
    const response = await fetch(`${this.baseUrl}/api/ds/query`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify(request)
    });
    
    if (!response.ok) {
      throw new Error(`패널 데이터 조회 실패: ${response.status}`);
    }
    
    return await response.json();
  }

  // 5. 스냅샷 생성
  async createSnapshot(dashboardModel: any, name: string, expires: number = 0): Promise<SnapshotResponse> {
    const request = {
      dashboard: dashboardModel,
      name,
      expires
    };
    
    const response = await fetch(`${this.baseUrl}/api/snapshots`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify(request)
    });
    
    if (!response.ok) {
      throw new Error(`스냅샷 생성 실패: ${response.status}`);
    }
    
    return await response.json();
  }

  // 6. 스냅샷 목록 조회
  async getSnapshots(): Promise<Snapshot[]> {
    const response = await fetch(`${this.baseUrl}/api/snapshots`, {
      headers: this.headers
    });
    
    if (!response.ok) {
      throw new Error(`스냅샷 목록 조회 실패: ${response.status}`);
    }
    
    return await response.json();
  }

  // 7. 특정 스냅샷 조회
  async getSnapshotByKey(key: string): Promise<SnapshotDetail> {
    const response = await fetch(`${this.baseUrl}/api/snapshots/${key}`, {
      headers: this.headers
    });
    
    if (!response.ok) {
      throw new Error(`스냅샷 조회 실패: ${response.status}`);
    }
    
    return await response.json();
  }

  // 전체 워크플로우: 대시보드 조회부터 스냅샷 생성까지
  async createDashboardSnapshot(dashboardUid: string, snapshotName: string): Promise<SnapshotResponse> {
    // 대시보드 상세 정보 조회
    const dashboardDetail = await this.getDashboardByUid(dashboardUid);
    const dashboard = dashboardDetail.dashboard;
    
    // 패널 데이터 수집 (모든 패널에 대해 데이터 조회)
    const panelsWithData = await Promise.all(
      dashboard.panels.map(async (panel) => {
        if (!panel.targets || panel.targets.length === 0) {
          return panel; // 데이터 소스가 없는 패널은 그대로 반환
        }
        
        // 패널의 쿼리 데이터 조회
        const queries = panel.targets.map(target => ({
          refId: target.refId,
          expr: target.expr,
          instant: false,
          range: true
        }));
        
        const datasourceUid = panel.datasource?.uid || 'default';
        const data = await this.getPanelData(
          datasourceUid,
          queries,
          dashboard.time
        );
        
        // 패널에 스냅샷 데이터 추가
        return {
          ...panel,
          snapshotData: data
        };
      })
    );
    
    // 패널 데이터가 포함된 대시보드 모델 생성
    const snapshotDashboard = {
      ...dashboard,
      panels: panelsWithData,
      title: `${dashboard.title} (Snapshot)`
    };
    
    // 스냅샷 생성
    return await this.createSnapshot(snapshotDashboard, snapshotName);
  }
}

// 인터페이스 정의
interface Dashboard {
  id: number;
  uid: string;
  title: string;
  url: string;
  type: string;
  tags: string[];
  isStarred: boolean;
}

interface DashboardDetail {
  dashboard: any;
  meta: {
    isStarred: boolean;
    url: string;
    folderId: number;
    folderTitle: string;
    canSave: boolean;
    canEdit: boolean;
    canAdmin: boolean;
    canStar: boolean;
    canDelete: boolean;
  };
}

interface TimeRange {
  from: string;
  to: string;
  raw?: {
    from: string;
    to: string;
  };
}

interface SnapshotResponse {
  key: string;
  deleteKey: string;
  url: string;
  deleteUrl: string;
  id: number;
}

interface Snapshot {
  id: number;
  name: string;
  key: string;
  orgId: number;
  userId: number;
  external: boolean;
  externalUrl: string;
  expires: string;
  created: string;
  updated: string;
}

interface SnapshotDetail {
  meta: {
    isSnapshot: boolean;
    type: string;
    canSave: boolean;
    canEdit: boolean;
    canAdmin: boolean;
    canStar: boolean;
    slug: string;
    expires: string;
    created: string;
  };
  dashboard: any;
}
```

이 구현은 대시보드 목록 조회부터 스냅샷 생성 및 조회까지의 전체 워크플로우를 포함하며, 각 단계에 필요한 모든 API 호출과 데이터 흐름을 보여줍니다. 