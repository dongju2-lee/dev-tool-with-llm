from mcp.server.fastmcp import FastMCP
import os
import requests
import json
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_API_URL = os.environ.get("GITHUB_API_URL", "https://api.github.com")
GITHUB_OWNER = os.environ.get("GITHUB_OWNER", "dongju2-lee")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "dev-tool-with-llm")
GITHUB_MCP_NAME = os.environ.get("GITHUB_MCP_NAME", "github")
GITHUB_MCP_HOST = os.environ.get("GITHUB_MCP_HOST", "0.0.0.0")
GITHUB_MCP_PORT = int(os.environ.get("GITHUB_MCP_PORT", 10005))
GITHUB_MCP_INSTRUCTIONS = os.environ.get("GITHUB_MCP_INSTRUCTIONS", 
    "GitHub API를 활용하여 이슈와 풀 리퀘스트를 관리하는 도구입니다. 이슈 검색, 코멘트 추가, 이슈 생성, PR 검색 기능을 제공합니다.")

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("github_mcp_server")

# FastMCP 인스턴스 생성
mcp = FastMCP(
    GITHUB_MCP_NAME,  # MCP 서버 이름
    instructions=GITHUB_MCP_INSTRUCTIONS,
    host=GITHUB_MCP_HOST, 
    port=GITHUB_MCP_PORT,
)

# GitHub API 요청 헤더
def get_github_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

# GitHub API 요청 함수
async def github_api_request(endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict:
    """GitHub API에 요청을 보내는 함수"""
    url = f"{GITHUB_API_URL}{endpoint}"
    logger.info(f"GitHub API 요청: {method} {url}")
    
    try:
        headers = get_github_headers()
        
        if method.upper() == "GET":
            response = requests.get(url, headers=headers)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data)
        else:
            return {"error": f"지원하지 않는 HTTP 메서드: {method}"}
        
        if response.status_code >= 400:
            logger.error(f"GitHub API 오류: {response.status_code} - {response.text}")
            return {"error": f"GitHub API 오류: {response.status_code}", "details": response.text}
            
        result = response.json()
        logger.info(f"GitHub API 응답 상태 코드: {response.status_code}")
        return result
    except Exception as e:
        logger.error(f"GitHub API 요청 실패: {str(e)}")
        return {"error": f"GitHub API 요청 실패: {str(e)}"}

@mcp.tool()
async def search_issues(query: str, owner: str = GITHUB_OWNER, repo: str = None, state: str = "open", per_page: int = 5) -> Dict[str, Any]:
    """
    GitHub 이슈를 검색합니다.
    
    Args:
        query (str): 검색할 키워드
        owner (str, optional): 리포지토리 소유자 (기본값: .env에 설정된 GITHUB_OWNER)
        repo (str, optional): 리포지토리 이름 (owner와 함께 지정하면 특정 리포지토리 내에서만 검색)
        state (str, optional): 이슈 상태 ("open", "closed", "all" 중 하나, 기본값은 "open")
        per_page (int, optional): 한 페이지당 결과 수 (기본값은 5)
        
    Returns:
        Dict[str, Any]: 검색된 이슈 목록과 메타데이터
        
    예시 요청:
        search_issues(query="bug")
        
    예시 응답:
        {{
            "total_count": 10,
            "incomplete_results": false,
            "items": [
                {{
                    "id": 1296269,
                    "number": 1347,
                    "title": "버그: 로그인 페이지 오류",
                    "state": "open",
                    "html_url": "https://github.com/octocat/hello-world/issues/1347",
                    "body": "로그인 페이지에서 오류가 발생합니다.",
                    "user": {{"login": "octocat"}},
                    "created_at": "2011-04-22T13:33:48Z",
                    "updated_at": "2011-04-22T13:33:48Z"
                }},
                ...
            ]
        }}
    """
    logger.info(f"이슈 검색 요청: 쿼리={query}, 소유자={owner}, 레포={repo}, 상태={state}")
    
    search_query = query
    
    # 특정 리포지토리로 검색 범위 제한
    if owner and repo:
        search_query += f" repo:{owner}/{repo}"
    elif owner:
        search_query += f" user:{owner}"
    
    # 이슈 상태 추가
    search_query += f" is:issue state:{state}"
    
    endpoint = f"/search/issues?q={search_query}&per_page={per_page}"
    result = await github_api_request(endpoint)
    
    # 결과 간소화 (필요한 필드만 포함)
    if "items" in result and not "error" in result:
        simplified_items = []
        for item in result["items"]:
            simplified_items.append({
                "id": item.get("id"),
                "number": item.get("number"),
                "title": item.get("title"),
                "state": item.get("state"),
                "html_url": item.get("html_url"),
                "body": item.get("body"),
                "user": {"login": item.get("user", {}).get("login")},
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at")
            })
        
        result["items"] = simplified_items
    
    return result

@mcp.tool()
async def get_issue(owner: str = GITHUB_OWNER, repo: str = GITHUB_REPO, issue_number: int = 1) -> Dict[str, Any]:
    """
    특정 GitHub 이슈의 상세 정보를 조회합니다.
    
    Args:
        owner (str, optional): 리포지토리 소유자 (기본값: .env에 설정된 GITHUB_OWNER)
        repo (str, optional): 리포지토리 이름 (기본값: .env에 설정된 GITHUB_REPO)
        issue_number (int): 이슈 번호
        
    Returns:
        Dict[str, Any]: 이슈 상세 정보
        
    예시 요청:
        get_issue(issue_number=1)
        
    예시 응답:
        {{
            "id": 1296269,
            "node_id": "MDU6SXNzdWUxMjk2MjY5",
            "number": 1347,
            "title": "버그: 로그인 페이지 오류",
            "user": {{
                "login": "octocat",
                "id": 1
            }},
            "state": "open",
            "locked": false,
            "assignee": {{
                "login": "octocat",
                "id": 1
            }},
            "assignees": [
                {{
                    "login": "octocat",
                    "id": 1
                }}
            ],
            "milestone": {{
                "title": "v1.0",
                "number": 1
            }},
            "comments": 0,
            "created_at": "2011-04-22T13:33:48Z",
            "updated_at": "2011-04-22T13:33:48Z",
            "body": "로그인 페이지에서 오류가 발생합니다."
        }}
    """
    logger.info(f"이슈 조회 요청: 소유자={owner}, 레포={repo}, 이슈 번호={issue_number}")
    
    endpoint = f"/repos/{owner}/{repo}/issues/{issue_number}"
    result = await github_api_request(endpoint)
    
    return result

@mcp.tool()
async def create_issue(title: str, body: str, owner: str = GITHUB_OWNER, repo: str = GITHUB_REPO, labels: List[str] = None, assignees: List[str] = None) -> Dict[str, Any]:
    """
    새로운 GitHub 이슈를 생성합니다.
    
    Args:
        title (str): 이슈 제목
        body (str): 이슈 본문 내용
        owner (str, optional): 리포지토리 소유자 (기본값: .env에 설정된 GITHUB_OWNER)
        repo (str, optional): 리포지토리 이름 (기본값: .env에 설정된 GITHUB_REPO)
        labels (List[str], optional): 이슈에 적용할 라벨 목록
        assignees (List[str], optional): 이슈를 할당할 사용자 목록
        
    Returns:
        Dict[str, Any]: 생성된 이슈 정보
        
    예시 요청:
        create_issue(
            title="새로운 기능 요청: 대시보드 필터링", 
            body="대시보드에 필터링 기능을 추가해주세요.", 
            labels=["enhancement", "feature"], 
            assignees=["octocat"]
        )
        
    예시 응답:
        {{
            "id": 1296269,
            "number": 1347,
            "title": "새로운 기능 요청: 대시보드 필터링",
            "state": "open",
            "html_url": "https://github.com/octocat/hello-world/issues/1347",
            "body": "대시보드에 필터링 기능을 추가해주세요.",
            "user": {{"login": "octocat"}},
            "created_at": "2011-04-22T13:33:48Z",
            "updated_at": "2011-04-22T13:33:48Z"
        }}
    """
    logger.info(f"이슈 생성 요청: 소유자={owner}, 레포={repo}, 제목={title}")
    
    endpoint = f"/repos/{owner}/{repo}/issues"
    data = {
        "title": title,
        "body": body
    }
    
    if labels:
        data["labels"] = labels
    
    if assignees:
        data["assignees"] = assignees
    
    result = await github_api_request(endpoint, "POST", data)
    
    return result

@mcp.tool()
async def add_issue_comment(issue_number: int, body: str, owner: str = GITHUB_OWNER, repo: str = GITHUB_REPO) -> Dict[str, Any]:
    """
    GitHub 이슈에 코멘트를 추가합니다.
    
    Args:
        issue_number (int): 이슈 번호
        body (str): 코멘트 내용
        owner (str, optional): 리포지토리 소유자 (기본값: .env에 설정된 GITHUB_OWNER)
        repo (str, optional): 리포지토리 이름 (기본값: .env에 설정된 GITHUB_REPO)
        
    Returns:
        Dict[str, Any]: 생성된 코멘트 정보
        
    예시 요청:
        add_issue_comment(
            issue_number=1347,
            body="이 이슈는 다음 스프린트에서 처리할 예정입니다."
        )
        
    예시 응답:
        {{
            "id": 1,
            "node_id": "MDEyOklzc3VlQ29tbWVudDE=",
            "url": "https://api.github.com/repos/octocat/hello-world/issues/comments/1",
            "html_url": "https://github.com/octocat/hello-world/issues/1347#issuecomment-1",
            "body": "이 이슈는 다음 스프린트에서 처리할 예정입니다.",
            "user": {{
                "login": "octocat",
                "id": 1
            }},
            "created_at": "2011-04-22T13:33:48Z",
            "updated_at": "2011-04-22T13:33:48Z"
        }}
    """
    logger.info(f"이슈 코멘트 추가 요청: 소유자={owner}, 레포={repo}, 이슈 번호={issue_number}")
    
    endpoint = f"/repos/{owner}/{repo}/issues/{issue_number}/comments"
    data = {"body": body}
    
    result = await github_api_request(endpoint, "POST", data)
    
    return result

@mcp.tool()
async def search_pull_requests(owner: str = GITHUB_OWNER, repo: str = GITHUB_REPO, state: str = "open", sort: str = "created", direction: str = "desc", per_page: int = 5) -> Dict[str, Any]:
    """
    GitHub 풀 리퀘스트를 검색합니다.
    
    Args:
        owner (str, optional): 리포지토리 소유자 (기본값: .env에 설정된 GITHUB_OWNER)
        repo (str, optional): 리포지토리 이름 (기본값: .env에 설정된 GITHUB_REPO)
        state (str, optional): PR 상태 ("open", "closed", "all" 중 하나, 기본값은 "open")
        sort (str, optional): 정렬 기준 ("created", "updated", "popularity", "long-running" 중 하나, 기본값은 "created")
        direction (str, optional): 정렬 방향 ("asc", "desc" 중 하나, 기본값은 "desc")
        per_page (int, optional): 한 페이지당 결과 수 (기본값은 5)
        
    Returns:
        Dict[str, Any]: 검색된 풀 리퀘스트 목록
        
    예시 요청:
        search_pull_requests()
        
    예시 응답:
        [
            {{
                "id": 1,
                "number": 1347,
                "title": "새로운 기능: 사용자 프로필",
                "state": "open",
                "html_url": "https://github.com/octocat/hello-world/pull/1347",
                "body": "사용자 프로필 기능을 추가했습니다.",
                "user": {{"login": "octocat"}},
                "created_at": "2011-04-22T13:33:48Z",
                "updated_at": "2011-04-22T13:33:48Z",
                "merged_at": null
            }},
            ...
        ]
    """
    logger.info(f"PR 검색 요청: 소유자={owner}, 레포={repo}, 상태={state}")
    
    endpoint = f"/repos/{owner}/{repo}/pulls?state={state}&sort={sort}&direction={direction}&per_page={per_page}"
    result = await github_api_request(endpoint)
    
    # 결과 간소화 (필요한 필드만 포함)
    if isinstance(result, list) and not "error" in result:
        simplified_items = []
        for item in result:
            simplified_items.append({
                "id": item.get("id"),
                "number": item.get("number"),
                "title": item.get("title"),
                "state": item.get("state"),
                "html_url": item.get("html_url"),
                "body": item.get("body"),
                "user": {"login": item.get("user", {}).get("login")},
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "merged_at": item.get("merged_at")
            })
        
        return simplified_items
    
    return result

if __name__ == "__main__":
    # 서버 시작 메시지 출력
    print("GitHub MCP 서버가 실행 중입니다...")
    
    # SSE 트랜스포트를 사용하여 MCP 서버 시작
    mcp.run(transport="sse") 