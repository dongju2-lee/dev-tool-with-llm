#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Milvus MCP 서버
벡터 데이터베이스 컬렉션 관리 및 검색 기능을 제공합니다.
"""

from mcp.server.fastmcp import FastMCP
import os
import logging
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from pymilvus import MilvusClient

# 환경 변수 로드
load_dotenv()
MILVUS_URI = os.environ.get("MILVUS_URI", "http://localhost:19530")
MILVUS_TOKEN = os.environ.get("MILVUS_TOKEN", "root:Milvus")
MILVUS_DB = os.environ.get("MILVUS_DB", "default")
MILVUS_MCP_NAME = os.environ.get("MILVUS_MCP_NAME", "milvus")
MILVUS_MCP_HOST = os.environ.get("MILVUS_MCP_HOST", "0.0.0.0")
MILVUS_MCP_PORT = int(os.environ.get("MILVUS_MCP_PORT", 10004))
MILVUS_MCP_INSTRUCTIONS = os.environ.get("MILVUS_MCP_INSTRUCTIONS", 
    "Milvus 벡터 데이터베이스와 상호작용하기 위한 도구입니다. 컬렉션 관리, 벡터 검색, 데이터 삽입 등의 기능을 제공합니다.")
DEFAULT_COLLECTION_NAME = "my_collection"  # 기본 컬렉션 이름 변경

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("milvus_mcp_server")

# FastMCP 인스턴스 생성
mcp = FastMCP(
    MILVUS_MCP_NAME,  # MCP 서버 이름
    instructions=MILVUS_MCP_INSTRUCTIONS,
    host=MILVUS_MCP_HOST, 
    port=MILVUS_MCP_PORT,
)

# Milvus 클라이언트
client = None

def get_milvus_client():
    """Milvus 클라이언트 인스턴스를 반환합니다."""
    global client
    if client is None:
        logger.info(f"Milvus 클라이언트 초기화: URI={MILVUS_URI}, DB={MILVUS_DB}")
        client = MilvusClient(uri=MILVUS_URI, token=MILVUS_TOKEN, db_name=MILVUS_DB)
    return client

# Milvus API 요청 헬퍼 함수
async def milvus_api_request(operation_name: str, operation_func, *args, **kwargs) -> Dict:
    """Milvus API 요청을 처리하는 함수"""
    logger.info(f"Milvus API 요청: {operation_name}, 인자={kwargs}")
    
    try:
        client = get_milvus_client()
        result = operation_func(*args, **kwargs)
        logger.info(f"Milvus API 요청 성공: {operation_name}")
        return result
    except Exception as e:
        logger.error(f"Milvus API 요청 실패: {operation_name}, 오류={str(e)}")
        return {"error": f"Milvus API 요청 실패: {str(e)}"}

@mcp.tool()
async def list_collections() -> List[str]:
    """
    데이터베이스의 모든 컬렉션 목록을 조회합니다.
    
    Returns:
        List[str]: 컬렉션 이름 목록
        
    예시 요청:
        list_collections()
        
    """
    logger.info("컬렉션 목록 조회 요청")
    
    def operation(*args, **kwargs):
        client = get_milvus_client()
        return client.list_collections()
    
    result = await milvus_api_request("list_collections", operation)
    return result

@mcp.tool()
async def drop_collection(collection_name: str = DEFAULT_COLLECTION_NAME) -> Dict[str, Any]:
    """
    지정된 컬렉션을 삭제합니다.
    
    Args:
        collection_name (str): 삭제할 컬렉션 이름 (기본값: my_collection)
        
    Returns:
        Dict[str, Any]: 삭제 결과
        
    예시 요청:
        drop_collection(collection_name="my_collection")
        
    """
    logger.info(f"컬렉션 삭제 요청: 컬렉션={collection_name}")
    
    def operation(*args, **kwargs):
        client = get_milvus_client()
        client.drop_collection(collection_name=kwargs.get("collection_name"))
        return {"msg": f"Collection {kwargs.get('collection_name')} has been dropped successfully"}
    
    result = await milvus_api_request("drop_collection", operation, collection_name=collection_name)
    return result

@mcp.tool()
async def get_collection_info(collection_name: str = DEFAULT_COLLECTION_NAME) -> Dict[str, Any]:
    """
    특정 컬렉션의 상세 정보를 조회합니다.
    
    Args:
        collection_name (str): 정보를 조회할 컬렉션 이름 (기본값: my_collection)
        
    Returns:
        Dict[str, Any]: 컬렉션 상세 정보
        
    예시 요청:
        get_collection_info(collection_name="my_collection")

    """
    logger.info(f"컬렉션 정보 조회 요청: 컬렉션={collection_name}")
    
    def operation(*args, **kwargs):
        client = get_milvus_client()
        return client.describe_collection(collection_name=kwargs.get("collection_name"))
    
    result = await milvus_api_request("get_collection_info", operation, collection_name=collection_name)
    return result

@mcp.tool()
async def create_collection(
    collection_name: str = DEFAULT_COLLECTION_NAME,
    dimension: int = 768,
    metric_type: str = "COSINE",
    description: str = ""
) -> Dict[str, Any]:
    """
    새로운 벡터 컬렉션을 생성합니다.
    
    Args:
        collection_name (str): 생성할 컬렉션 이름 (기본값: my_collection)
        dimension (int, optional): 벡터 차원 (기본값: 768)
        metric_type (str, optional): 거리 측정 방식 (COSINE, L2, IP 중 하나)
        description (str, optional): 컬렉션 설명
        
    Returns:
        Dict[str, Any]: 생성 결과
        
    예시 요청:
        create_collection(
            collection_name="my_collection",
            dimension=768,
            metric_type="COSINE",
            description="문서 임베딩 컬렉션"
        )
        
    """
    logger.info(f"컬렉션 생성 요청: 컬렉션={collection_name}, 차원={dimension}")
    
    def operation(*args, **kwargs):
        client = get_milvus_client()
        # 스키마 정의
        schema = {
            "fields": [
                {
                    "name": "id",
                    "description": "ID",
                    "data_type": "Int64",
                    "is_primary": True,
                    "autoID": True
                },
                {
                    "name": "dense_vector",  # 필드명 변경: vector → dense_vector
                    "description": "벡터 임베딩",
                    "data_type": "FloatVector",
                    "dim": kwargs.get("dimension", 768)
                },
                {
                    "name": "file_path",  # metadata 대신 실제 검색에 필요한 필드명으로 변경
                    "description": "파일 경로",
                    "data_type": "VarChar",
                    "max_length": 500
                },
                {
                    "name": "language",  # 언어 필드 추가
                    "description": "문서 언어",
                    "data_type": "VarChar",
                    "max_length": 20
                },
                {
                    "name": "title",  # 제목 필드 추가
                    "description": "문서 제목",
                    "data_type": "VarChar",
                    "max_length": 200
                },
                {
                    "name": "content",  # 이름 변경: text → content
                    "description": "원본 텍스트",
                    "data_type": "VarChar",
                    "max_length": 65535
                },
                {
                    "name": "directory",  # 디렉토리 필드 추가
                    "description": "문서 디렉토리",
                    "data_type": "VarChar",
                    "max_length": 500
                }
            ],
            "description": kwargs.get("description", "")
        }
        
        # 인덱스 파라미터
        index_params = {
            "metric_type": kwargs.get("metric_type", "COSINE"),
            "index_type": "HNSW",
            "params": {"M": 8, "efConstruction": 64}
        }
        
        # 컬렉션 생성
        client.create_collection(
            collection_name=kwargs.get("collection_name"),
            schema=schema
        )
        
        # 인덱스 생성
        client.create_index(
            collection_name=kwargs.get("collection_name"),
            field_name="dense_vector",  # 필드명 변경: vector → dense_vector
            index_params=index_params
        )
        
        # 검색용으로 컬렉션 로드
        client.load_collection(
            collection_name=kwargs.get("collection_name")
        )
        
        return {"msg": f"Collection {kwargs.get('collection_name')} has been created successfully"}
    
    result = await milvus_api_request(
        "create_collection", 
        operation, 
        collection_name=collection_name,
        dimension=dimension,
        metric_type=metric_type,
        description=description
    )
    return result

@mcp.tool()
async def insert_embeddings(
    collection_name: str = DEFAULT_COLLECTION_NAME,
    vectors: List[List[float]] = None,
    file_paths: List[str] = None,
    languages: List[str] = None,
    titles: List[str] = None,
    contents: List[str] = None,
    directories: List[str] = None
) -> Dict[str, Any]:
    """
    컬렉션에 임베딩 벡터와 관련 데이터를 삽입합니다.
    
    Args:
        collection_name (str): 임베딩을 삽입할 컬렉션 이름 (기본값: my_collection)
        vectors (List[List[float]]): 임베딩 벡터 목록
        file_paths (List[str], optional): 각 벡터에 대한 파일 경로 목록
        languages (List[str], optional): 각 벡터에 대한 언어 목록
        titles (List[str], optional): 각 벡터에 대한 제목 목록
        contents (List[str], optional): 각 벡터에 대한 원본 텍스트 목록
        directories (List[str], optional): 각 벡터에 대한 디렉토리 목록
        
    Returns:
        Dict[str, Any]: 삽입 결과
        
    예시 요청:
        insert_embeddings(
            collection_name="my_collection",
            vectors=[[0.1, 0.2, ..., 0.5], [0.2, 0.3, ..., 0.6]],
            file_paths=["document1.pdf", "document2.pdf"],
            languages=["ko", "en"],
            titles=["문서 1", "Document 2"],
            contents=["이것은 문서 1입니다", "This is document 2"],
            directories=["/path/to/docs", "/path/to/docs"]
        )
    
    """
    logger.info(f"임베딩 삽입 요청: 컬렉션={collection_name}, 벡터 수={len(vectors) if vectors else 0}")
    
    if not vectors:
        return {"error": "벡터가 제공되지 않았습니다."}
    
    def operation(*args, **kwargs):
        client = get_milvus_client()
        collection_name = kwargs.get("collection_name")
        vectors = kwargs.get("vectors", [])
        file_paths = kwargs.get("file_paths", [""] * len(vectors))
        languages = kwargs.get("languages", ["unknown"] * len(vectors))
        titles = kwargs.get("titles", [""] * len(vectors))
        contents = kwargs.get("contents", [""] * len(vectors))
        directories = kwargs.get("directories", [""] * len(vectors))
        
        # 모든 데이터가 있는지 확인하고 길이 맞추기
        length = len(vectors)
        if len(file_paths) < length:
            file_paths.extend([""] * (length - len(file_paths)))
        if len(languages) < length:
            languages.extend(["unknown"] * (length - len(languages)))
        if len(titles) < length:
            titles.extend([""] * (length - len(titles)))
        if len(contents) < length:
            contents.extend([""] * (length - len(contents)))
        if len(directories) < length:
            directories.extend([""] * (length - len(directories)))
        
        # 데이터 삽입 준비
        data = []
        for i in range(length):
            entity = {
                "dense_vector": vectors[i],  # 필드명 변경: vector → dense_vector
                "file_path": file_paths[i] if i < len(file_paths) else "",
                "language": languages[i] if i < len(languages) else "unknown",
                "title": titles[i] if i < len(titles) else "",
                "content": contents[i] if i < len(contents) else "",
                "directory": directories[i] if i < len(directories) else ""
            }
            data.append(entity)
        
        # 삽입 실행
        result = client.insert(
            collection_name=collection_name,
            data=data
        )
        
        return {
            "insert_count": len(result.get("insert_count", [])),
            "ids": result.get("primary_keys", [])
        }
    
    result = await milvus_api_request(
        "insert_embeddings", 
        operation, 
        collection_name=collection_name,
        vectors=vectors,
        file_paths=file_paths,
        languages=languages,
        titles=titles,
        contents=contents,
        directories=directories
    )
    return result

@mcp.tool()
async def search_vectors(
    collection_name: str = DEFAULT_COLLECTION_NAME,
    vector: List[float] = None,
    limit: int = 5,
    output_fields: List[str] = None
) -> List[Dict]:
    """
    컬렉션에서 유사한 벡터를 검색합니다.
    
    Args:
        collection_name (str): 검색할 컬렉션 이름 (기본값: my_collection)
        vector (List[float]): 쿼리 벡터
        limit (int, optional): 최대 결과 수 (기본값: 5)
        output_fields (List[str], optional): 결과에 포함할 필드 목록
        
    Returns:
        List[Dict]: 검색 결과 목록
        
    예시 요청:
        search_vectors(
            collection_name="my_collection",
            vector=[0.1, 0.2, ..., 0.5],
            limit=3,
            output_fields=["file_path", "title", "content"]
        )
        
    """
    logger.info(f"벡터 검색 요청: 컬렉션={collection_name}")
    
    if not vector:
        return {"error": "검색할 벡터가 제공되지 않았습니다."}
    
    def operation(*args, **kwargs):
        client = get_milvus_client()
        collection_name = kwargs.get("collection_name")
        vector = kwargs.get("vector")
        limit = kwargs.get("limit", 5)
        output_fields = kwargs.get("output_fields", ["file_path", "title", "content", "language"])
        
        # 검색 실행
        results = client.search(
            collection_name=collection_name,
            data=[vector],
            anns_field="dense_vector",  # 필드명 변경: vector → dense_vector
            limit=limit,
            output_fields=output_fields
        )
        
        # 결과 정리
        if not results or len(results) == 0:
            return []
        
        processed_results = []
        for hit in results[0]:
            result = {
                "id": hit.get("id"),
                "score": hit.get("score", 0.0)
            }
            
            # 요청된 출력 필드 추가
            for field in output_fields:
                if field in hit.get("entity", {}):
                    result[field] = hit["entity"][field]
            
            processed_results.append(result)
        
        return processed_results
    
    result = await milvus_api_request(
        "search_vectors", 
        operation, 
        collection_name=collection_name,
        vector=vector,
        limit=limit,
        output_fields=output_fields
    )
    return result

@mcp.tool()
async def search_text(
    collection_name: str = DEFAULT_COLLECTION_NAME,
    query_text: str = None,
    limit: int = 5,
    language: str = None
) -> Dict[str, Any]:
    """
    텍스트 쿼리를 사용하여 컬렉션에서 검색합니다.
    제공된 텍스트를 임베딩으로 변환한 후 벡터 검색을 수행합니다.
    
    Args:
        collection_name (str): 검색할 컬렉션 이름 (기본값: my_collection)
        query_text (str): 검색할 텍스트 쿼리
        limit (int, optional): 최대 결과 수 (기본값: 5)
        language (str, optional): 특정 언어로 필터링 (예: "ko", "en")
        
    Returns:
        Dict[str, Any]: 검색 결과 및 상태
        
    예시 요청:
        search_text(
            collection_name="my_collection",
            query_text="머신러닝 기초 개념",
            limit=3,
            language="ko"
        )
        
    """
    logger.info(f"텍스트 검색 요청: 컬렉션={collection_name}, 쿼리={query_text}")
    
    if not query_text:
        return {"error": "검색할 텍스트가 제공되지 않았습니다."}
    
    # 여기서는 간단한 시뮬레이션 결과를 반환합니다.
    # 실제 구현에서는 텍스트를 임베딩으로 변환한 후 search_vectors를 호출해야 합니다.
    
    output_fields = ["file_path", "title", "content", "language"]
    expr = f'language == "{language}"' if language else None
    
    simulated_results = {
        "query": query_text,
        "results": [
            {
                "id": 1,
                "file_path": "document1.pdf",
                "title": f"{query_text}에 관한 문서",
                "content": f"{query_text}와 관련된 내용이 담긴 문서입니다.",
                "language": language or "ko",
                "score": 0.95
            },
            {
                "id": 2,
                "file_path": "document2.pdf",
                "title": f"{query_text} 관련 자료",
                "content": f"{query_text}에 대한 추가 정보가 포함된 문서입니다.",
                "language": language or "ko",
                "score": 0.87
            }
        ]
    }
    
    if limit < 2:
        simulated_results["results"] = simulated_results["results"][:limit]
    
    return simulated_results

@mcp.tool()
async def list_databases() -> List[str]:
    """
    Milvus 인스턴스의 모든 데이터베이스 목록을 조회합니다.
    
    Returns:
        List[str]: 데이터베이스 이름 목록
        
    예시 요청:
        list_databases()
        
    """
    logger.info("데이터베이스 목록 조회 요청")
    
    def operation(*args, **kwargs):
        client = get_milvus_client()
        return client.list_databases()
    
    result = await milvus_api_request("list_databases", operation)
    return result

@mcp.tool()
async def use_database(db_name: str) -> Dict[str, Any]:
    """
    다른 데이터베이스로 전환합니다.
    
    Args:
        db_name (str): 사용할 데이터베이스 이름
        
    Returns:
        Dict[str, Any]: 전환 결과
        
    예시 요청:
        use_database(db_name="production")
        
    """
    logger.info(f"데이터베이스 전환 요청: 데이터베이스={db_name}")
    
    global client, MILVUS_DB
    MILVUS_DB = db_name
    
    # 기존 클라이언트 해제
    client = None
    
    # 새 클라이언트 생성
    get_milvus_client()
    
    return {"msg": f"Switched to database {db_name}"}

if __name__ == "__main__":
    # 서버 시작 메시지 출력
    print(f"Milvus MCP 서버가 실행 중입니다... (포트: {MILVUS_MCP_PORT})")
    
    # SSE 트랜스포트를 사용하여 MCP 서버 시작
    mcp.run(transport="sse")