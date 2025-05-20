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
        
    예시 응답:
        ["documents", "images", "embeddings"]
    """
    logger.info("컬렉션 목록 조회 요청")
    
    def operation(*args, **kwargs):
        client = get_milvus_client()
        return client.list_collections()
    
    result = await milvus_api_request("list_collections", operation)
    return result

@mcp.tool()
async def drop_collection(collection_name: str) -> Dict[str, Any]:
    """
    지정된 컬렉션을 삭제합니다.
    
    Args:
        collection_name (str): 삭제할 컬렉션 이름
        
    Returns:
        Dict[str, Any]: 삭제 결과
        
    예시 요청:
        drop_collection(collection_name="test_collection")
        
    예시 응답:
        {{ "msg": "Collection test_collection has been dropped successfully" }}
    """
    logger.info(f"컬렉션 삭제 요청: 컬렉션={collection_name}")
    
    def operation(*args, **kwargs):
        client = get_milvus_client()
        client.drop_collection(collection_name=kwargs.get("collection_name"))
        return {"msg": f"Collection {kwargs.get('collection_name')} has been dropped successfully"}
    
    result = await milvus_api_request("drop_collection", operation, collection_name=collection_name)
    return result

@mcp.tool()
async def get_collection_info(collection_name: str) -> Dict[str, Any]:
    """
    특정 컬렉션의 상세 정보를 조회합니다.
    
    Args:
        collection_name (str): 정보를 조회할 컬렉션 이름
        
    Returns:
        Dict[str, Any]: 컬렉션 상세 정보
        
    예시 요청:
        get_collection_info(collection_name="documents")
        
    예시 응답:
        {{
            "collection_name": "documents",
            "description": "",
            "fields": [
                {{
                    "name": "id",
                    "description": "",
                    "type": "Int64",
                    "params": {{}},
                    "is_primary": true
                }},
                {{
                    "name": "vector",
                    "description": "",
                    "type": "FloatVector",
                    "params": {{"dim": 128}},
                    "is_primary": false
                }}
            ],
            "indexes": [...],
            "load_status": {...}
        }}
    """
    logger.info(f"컬렉션 정보 조회 요청: 컬렉션={collection_name}")
    
    def operation(*args, **kwargs):
        client = get_milvus_client()
        return client.describe_collection(collection_name=kwargs.get("collection_name"))
    
    result = await milvus_api_request("get_collection_info", operation, collection_name=collection_name)
    return result

@mcp.tool()
async def create_collection(
    collection_name: str,
    dimension: int = 768,
    metric_type: str = "COSINE",
    description: str = ""
) -> Dict[str, Any]:
    """
    새로운 벡터 컬렉션을 생성합니다.
    
    Args:
        collection_name (str): 생성할 컬렉션 이름
        dimension (int, optional): 벡터 차원 (기본값: 768)
        metric_type (str, optional): 거리 측정 방식 (COSINE, L2, IP 중 하나)
        description (str, optional): 컬렉션 설명
        
    Returns:
        Dict[str, Any]: 생성 결과
        
    예시 요청:
        create_collection(
            collection_name="my_documents",
            dimension=768,
            metric_type="COSINE",
            description="문서 임베딩 컬렉션"
        )
        
    예시 응답:
        {{ "msg": "Collection my_documents has been created successfully" }}
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
                    "name": "vector",
                    "description": "벡터 임베딩",
                    "data_type": "FloatVector",
                    "dim": kwargs.get("dimension", 768)
                },
                {
                    "name": "metadata",
                    "description": "메타데이터 (JSON 문자열)",
                    "data_type": "VarChar",
                    "max_length": 65535
                },
                {
                    "name": "text",
                    "description": "원본 텍스트",
                    "data_type": "VarChar",
                    "max_length": 65535
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
            field_name="vector",
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
    collection_name: str,
    vectors: List[List[float]],
    metadata_list: List[Dict] = None,
    texts: List[str] = None
) -> Dict[str, Any]:
    """
    컬렉션에 임베딩 벡터와 관련 데이터를 삽입합니다.
    
    Args:
        collection_name (str): 임베딩을 삽입할 컬렉션 이름
        vectors (List[List[float]]): 임베딩 벡터 목록
        metadata_list (List[Dict], optional): 각 벡터에 대한 메타데이터 목록
        texts (List[str], optional): 각 벡터에 대한 원본 텍스트 목록
        
    Returns:
        Dict[str, Any]: 삽입 결과
        
    예시 요청:
        insert_embeddings(
            collection_name="documents",
            vectors=[[0.1, 0.2, ..., 0.5], [0.2, 0.3, ..., 0.6]],
            metadata_list=[{{"source": "document1.pdf"}}, {{"source": "document2.pdf"}}],
            texts=["This is document 1", "This is document 2"]
        )
        
    예시 응답:
        {{
            "insert_count": 2,
            "ids": [1, 2]
        }}
    """
    logger.info(f"임베딩 삽입 요청: 컬렉션={collection_name}, 벡터 수={len(vectors)}")
    
    def operation(*args, **kwargs):
        client = get_milvus_client()
        collection_name = kwargs.get("collection_name")
        vectors = kwargs.get("vectors", [])
        metadata_list = kwargs.get("metadata_list", [{}] * len(vectors))
        texts = kwargs.get("texts", [""] * len(vectors))
        
        # 모든 데이터가 같은 길이인지 확인
        if len(metadata_list) != len(vectors) or len(texts) != len(vectors):
            return {"error": "vectors, metadata_list, texts의 길이가 일치해야 합니다."}
        
        # 데이터 삽입 준비
        data = []
        for i in range(len(vectors)):
            entity = {
                "vector": vectors[i],
                "metadata": str(metadata_list[i]) if i < len(metadata_list) else "{}",
                "text": texts[i] if i < len(texts) else ""
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
        metadata_list=metadata_list,
        texts=texts
    )
    return result

@mcp.tool()
async def search_vectors(
    collection_name: str,
    vector: List[float],
    limit: int = 5,
    output_fields: List[str] = None
) -> List[Dict]:
    """
    컬렉션에서 유사한 벡터를 검색합니다.
    
    Args:
        collection_name (str): 검색할 컬렉션 이름
        vector (List[float]): 쿼리 벡터
        limit (int, optional): 최대 결과 수 (기본값: 5)
        output_fields (List[str], optional): 결과에 포함할 필드 목록
        
    Returns:
        List[Dict]: 검색 결과 목록
        
    예시 요청:
        search_vectors(
            collection_name="documents",
            vector=[0.1, 0.2, ..., 0.5],
            limit=3,
            output_fields=["metadata", "text"]
        )
        
    예시 응답:
        [
            {{
                "id": 1,
                "metadata": "{\"source\": \"document1.pdf\"}",
                "text": "This is document 1",
                "score": 0.95
            }},
            {{
                "id": 3,
                "metadata": "{\"source\": \"document3.pdf\"}",
                "text": "This is document 3",
                "score": 0.82
            }},
            {{
                "id": 2,
                "metadata": "{\"source\": \"document2.pdf\"}",
                "text": "This is document 2",
                "score": 0.78
            }}
        ]
    """
    logger.info(f"벡터 검색 요청: 컬렉션={collection_name}")
    
    def operation(*args, **kwargs):
        client = get_milvus_client()
        collection_name = kwargs.get("collection_name")
        vector = kwargs.get("vector")
        limit = kwargs.get("limit", 5)
        output_fields = kwargs.get("output_fields", ["metadata", "text"])
        
        # 검색 실행
        results = client.search(
            collection_name=collection_name,
            data=[vector],
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
    collection_name: str,
    query_text: str,
    limit: int = 5,
    output_fields: List[str] = None
) -> Dict[str, Any]:
    """
    텍스트 쿼리를 사용하여 컬렉션에서 검색합니다.
    (이 함수는 실제로 벡터 검색을 수행하지만, 외부 임베딩 모델을 활용해야 하므로 현재 시뮬레이션만 제공합니다)
    
    Args:
        collection_name (str): 검색할 컬렉션 이름
        query_text (str): 검색할 텍스트 쿼리
        limit (int, optional): 최대 결과 수 (기본값: 5)
        output_fields (List[str], optional): 결과에 포함할 필드 목록
        
    Returns:
        Dict[str, Any]: 검색 결과 및 상태
        
    예시 요청:
        search_text(
            collection_name="documents",
            query_text="머신러닝 기초 개념",
            limit=3,
            output_fields=["metadata", "text"]
        )
        
    예시 응답:
        {{
            "status": "simulated",
            "message": "텍스트 검색은 현재 시뮬레이션됩니다. 실제 검색을 위해서는 외부 임베딩 모델이 필요합니다.",
            "query": "머신러닝 기초 개념",
            "results": [
                {{
                    "id": 1,
                    "metadata": "{\"source\": \"ml_basic.pdf\"}",
                    "text": "머신러닝의 기초 개념과 알고리즘을 설명합니다.",
                    "score": 0.95
                }},
                {{
                    "id": 5,
                    "metadata": "{\"source\": \"deep_learning.pdf\"}",
                    "text": "딥러닝과 머신러닝 비교 및 기본 개념",
                    "score": 0.82
                }}
            ]
        }}
    """
    logger.info(f"텍스트 검색 요청: 컬렉션={collection_name}, 쿼리={query_text}")
    
    # 실제 구현에서는 여기서 외부 임베딩 모델을 호출하여 텍스트를 벡터로 변환한 후
    # search_vectors 함수를 호출해야 합니다.
    # 현재는 시뮬레이션된 결과를 반환합니다.
    
    # 시뮬레이션된 결과
    simulated_results = {
        "status": "simulated",
        "message": "텍스트 검색은 현재 시뮬레이션됩니다. 실제 검색을 위해서는 외부 임베딩 모델이 필요합니다.",
        "query": query_text,
        "results": [
            {
                "id": 1,
                "metadata": f"{{'source': 'simulated_doc1.pdf'}}",
                "text": f"{query_text}와 관련된 시뮬레이션 문서 1",
                "score": 0.95
            },
            {
                "id": 2,
                "metadata": f"{{'source': 'simulated_doc2.pdf'}}",
                "text": f"{query_text}에 대한 시뮬레이션 문서 2",
                "score": 0.82
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
        
    예시 응답:
        ["default", "production", "testing"]
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
        
    예시 응답:
        {{ "msg": "Switched to database production" }}
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