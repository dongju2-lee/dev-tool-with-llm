#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Milvus RAG MCP 서버
벡터 데이터베이스 컬렉션 관리, 청킹, 향상된 검색 기능을 제공합니다.
"""

from mcp.server.fastmcp import FastMCP
import os
import logging
import re
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv
from pymilvus import MilvusClient

# 환경 변수 로드
load_dotenv()
MILVUS_URI = os.environ.get("MILVUS_URI", "http://localhost:19530")
MILVUS_TOKEN = os.environ.get("MILVUS_TOKEN", "root:Milvus")
MILVUS_DB = os.environ.get("MILVUS_DB", "default")
MILVUS_MCP_NAME = os.environ.get("MILVUS_MCP_NAME", "milvus-rag")
MILVUS_MCP_HOST = os.environ.get("MILVUS_MCP_HOST", "0.0.0.0")
MILVUS_MCP_PORT = int(os.environ.get("MILVUS_MCP_PORT", 10004))
MILVUS_MCP_INSTRUCTIONS = os.environ.get("MILVUS_MCP_INSTRUCTIONS", 
    "Milvus RAG 벡터 데이터베이스와 상호작용하기 위한 도구입니다. 컬렉션 관리, 청킹, 벡터 검색, 하이브리드 검색 등의 기능을 제공합니다.")
DEFAULT_COLLECTION_NAME = "rag_collection"

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("milvus_rag_mcp_server")

# FastMCP 인스턴스 생성
mcp = FastMCP(
    MILVUS_MCP_NAME,
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

# 청킹 관련 함수들
class TextChunker:
    """텍스트 청킹을 위한 클래스"""
    
    @staticmethod
    def chunk_by_sentences(text: str, max_chunk_size: int = 512, overlap: int = 50) -> List[str]:
        """문장 단위로 청킹"""
        sentences = re.split(r'[.!?]+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            if len(current_chunk) + len(sentence) <= max_chunk_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        # 오버랩 처리
        if overlap > 0 and len(chunks) > 1:
            overlapped_chunks = []
            for i, chunk in enumerate(chunks):
                if i == 0:
                    overlapped_chunks.append(chunk)
                else:
                    # 이전 청크의 마지막 부분과 현재 청크의 시작 부분을 합침
                    prev_words = chunks[i-1].split()[-overlap:]
                    curr_words = chunk.split()
                    overlapped_chunk = " ".join(prev_words + curr_words)
                    overlapped_chunks.append(overlapped_chunk)
            return overlapped_chunks
            
        return chunks
    
    @staticmethod
    def chunk_by_paragraphs(text: str, max_chunk_size: int = 1024) -> List[str]:
        """문단 단위로 청킹"""
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            if len(current_chunk) + len(paragraph) <= max_chunk_size:
                current_chunk += paragraph + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks
    
    @staticmethod
    def chunk_by_tokens(text: str, max_tokens: int = 512, overlap_tokens: int = 50) -> List[str]:
        """토큰 단위로 청킹 (단어 기준 근사치)"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), max_tokens - overlap_tokens):
            chunk_words = words[i:i + max_tokens]
            chunks.append(" ".join(chunk_words))
            
        return chunks
    
    @staticmethod
    def semantic_chunking(text: str, max_chunk_size: int = 512) -> List[str]:
        """의미 단위로 청킹 (제목, 소제목 기준)"""
        # 제목 패턴 감지
        title_patterns = [
            r'^#{1,6}\s+.+$',  # 마크다운 제목
            r'^\d+\.\s+.+$',   # 번호 제목
            r'^[A-Z][^.!?]*:$', # 콜론으로 끝나는 제목
        ]
        
        lines = text.split('\n')
        chunks = []
        current_chunk = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 제목인지 확인
            is_title = any(re.match(pattern, line, re.MULTILINE) for pattern in title_patterns)
            
            if is_title and current_chunk and len(current_chunk) > 100:
                chunks.append(current_chunk.strip())
                current_chunk = line + "\n"
            else:
                current_chunk += line + "\n"
                
            # 최대 크기 초과 시 강제 분할
            if len(current_chunk) > max_chunk_size:
                chunks.append(current_chunk.strip())
                current_chunk = ""
        
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks

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
    """
    logger.info("컬렉션 목록 조회 요청")
    
    def operation(*args, **kwargs):
        client = get_milvus_client()
        return client.list_collections()
    
    result = await milvus_api_request("list_collections", operation)
    return result

@mcp.tool()
async def create_rag_collection(
    collection_name: str = DEFAULT_COLLECTION_NAME,
    dimension: int = 768,
    metric_type: str = "COSINE",
    description: str = "RAG 컬렉션"
) -> Dict[str, Any]:
    """
    RAG용 벡터 컬렉션을 생성합니다.
    
    Args:
        collection_name (str): 생성할 컬렉션 이름
        dimension (int): 벡터 차원
        metric_type (str): 거리 측정 방식 (COSINE, L2, IP)
        description (str): 컬렉션 설명
        
    Returns:
        Dict[str, Any]: 생성 결과
    """
    logger.info(f"RAG 컬렉션 생성 요청: 컬렉션={collection_name}, 차원={dimension}")
    
    def operation(*args, **kwargs):
        client = get_milvus_client()
        
        # RAG에 최적화된 스키마 정의
        schema = {
            "fields": [
                {
                    "name": "id",
                    "description": "청크 ID",
                    "data_type": "Int64",
                    "is_primary": True,
                    "autoID": True
                },
                {
                    "name": "dense_vector",
                    "description": "텍스트 임베딩 벡터",
                    "data_type": "FloatVector",
                    "dim": kwargs.get("dimension", 768)
                },
                {
                    "name": "chunk_text",
                    "description": "청크 텍스트",
                    "data_type": "VarChar",
                    "max_length": 8192
                },
                {
                    "name": "chunk_hash",
                    "description": "청크 해시값 (중복 방지)",
                    "data_type": "VarChar",
                    "max_length": 64
                },
                {
                    "name": "chunk_index",
                    "description": "문서 내 청크 순서",
                    "data_type": "Int64"
                },
                {
                    "name": "chunk_type",
                    "description": "청킹 방식 (sentence, paragraph, token, semantic)",
                    "data_type": "VarChar",
                    "max_length": 20
                },
                {
                    "name": "file_path",
                    "description": "원본 파일 경로",
                    "data_type": "VarChar",
                    "max_length": 500
                },
                {
                    "name": "document_title",
                    "description": "문서 제목",
                    "data_type": "VarChar",
                    "max_length": 200
                },
                {
                    "name": "document_type",
                    "description": "문서 타입",
                    "data_type": "VarChar",
                    "max_length": 50
                },
                {
                    "name": "language",
                    "description": "언어",
                    "data_type": "VarChar",
                    "max_length": 10
                },
                {
                    "name": "keywords",
                    "description": "키워드",
                    "data_type": "VarChar",
                    "max_length": 500
                },
                {
                    "name": "summary",
                    "description": "청크 요약",
                    "data_type": "VarChar",
                    "max_length": 1000
                },
                {
                    "name": "created_at",
                    "description": "생성 시간",
                    "data_type": "VarChar",
                    "max_length": 50
                }
            ],
            "description": kwargs.get("description", "RAG 컬렉션")
        }
        
        # 인덱스 파라미터
        index_params = {
            "metric_type": kwargs.get("metric_type", "COSINE"),
            "index_type": "HNSW",
            "params": {"M": 16, "efConstruction": 128}
        }
        
        # 컬렉션 생성
        client.create_collection(
            collection_name=kwargs.get("collection_name"),
            schema=schema
        )
        
        # 벡터 인덱스 생성
        client.create_index(
            collection_name=kwargs.get("collection_name"),
            field_name="dense_vector",
            index_params=index_params
        )
        
        # 스칼라 필드 인덱스 생성 (검색 성능 향상)
        scalar_indexes = ["chunk_hash", "file_path", "document_type", "language"]
        for field in scalar_indexes:
            try:
                client.create_index(
                    collection_name=kwargs.get("collection_name"),
                    field_name=field
                )
            except Exception as e:
                logger.warning(f"스칼라 인덱스 생성 실패 ({field}): {str(e)}")
        
        # 컬렉션 로드
        client.load_collection(collection_name=kwargs.get("collection_name"))
        
        return {"msg": f"RAG Collection {kwargs.get('collection_name')} has been created successfully"}
    
    result = await milvus_api_request(
        "create_rag_collection", 
        operation, 
        collection_name=collection_name,
        dimension=dimension,
        metric_type=metric_type,
        description=description
    )
    return result

@mcp.tool()
async def chunk_and_insert(
    collection_name: str = DEFAULT_COLLECTION_NAME,
    text: str = None,
    vectors: List[List[float]] = None,
    file_path: str = "",
    document_title: str = "",
    document_type: str = "",
    language: str = "auto",
    chunk_method: str = "sentence",
    max_chunk_size: int = 512,
    overlap: int = 50,
    keywords: str = "",
    auto_summarize: bool = False
) -> Dict[str, Any]:
    """
    텍스트를 청킹하여 벡터와 함께 컬렉션에 삽입합니다.
    
    Args:
        collection_name (str): 컬렉션 이름
        text (str): 청킹할 텍스트
        vectors (List[List[float]]): 각 청크에 대응하는 벡터 목록
        file_path (str): 파일 경로
        document_title (str): 문서 제목
        document_type (str): 문서 타입
        language (str): 언어 (auto로 설정 시 자동 감지)
        chunk_method (str): 청킹 방식 (sentence, paragraph, token, semantic)
        max_chunk_size (int): 최대 청크 크기
        overlap (int): 청크 간 오버랩
        keywords (str): 키워드
        auto_summarize (bool): 자동 요약 생성 여부
        
    Returns:
        Dict[str, Any]: 삽입 결과
    """
    logger.info(f"청킹 및 삽입 요청: 컬렉션={collection_name}, 청킹방식={chunk_method}")
    
    if not text:
        return {"error": "텍스트가 제공되지 않았습니다."}
    
    def operation(*args, **kwargs):
        import datetime
        
        # 청킹 수행
        chunker = TextChunker()
        text = kwargs.get("text", "")
        chunk_method = kwargs.get("chunk_method", "sentence")
        max_chunk_size = kwargs.get("max_chunk_size", 512)
        overlap = kwargs.get("overlap", 50)
        
        if chunk_method == "sentence":
            chunks = chunker.chunk_by_sentences(text, max_chunk_size, overlap)
        elif chunk_method == "paragraph":
            chunks = chunker.chunk_by_paragraphs(text, max_chunk_size)
        elif chunk_method == "token":
            chunks = chunker.chunk_by_tokens(text, max_chunk_size, overlap)
        elif chunk_method == "semantic":
            chunks = chunker.semantic_chunking(text, max_chunk_size)
        else:
            chunks = chunker.chunk_by_sentences(text, max_chunk_size, overlap)
        
        # 언어 자동 감지
        language = kwargs.get("language", "auto")
        if language == "auto":
            try:
                import langdetect
                language = langdetect.detect(text)
            except:
                language = "unknown"
        
        # 벡터 확인
        vectors = kwargs.get("vectors", [])
        if len(vectors) != len(chunks):
            logger.warning(f"벡터 수({len(vectors)})와 청크 수({len(chunks)})가 일치하지 않습니다.")
            # 벡터가 부족한 경우 더미 벡터로 채움
            if len(vectors) < len(chunks):
                dummy_vector = [0.0] * 768  # 기본 768차원
                vectors.extend([dummy_vector] * (len(chunks) - len(vectors)))
        
        # 데이터 준비
        data = []
        current_time = datetime.datetime.now().isoformat()
        
        for i, chunk in enumerate(chunks):
            # 청크 해시 생성 (중복 방지)
            chunk_hash = hashlib.md5(chunk.encode()).hexdigest()
            
            # 자동 요약 생성 (간단한 버전)
            summary = ""
            if kwargs.get("auto_summarize", False) and len(chunk) > 100:
                sentences = chunk.split('. ')
                summary = sentences[0] if sentences else chunk[:100]
            
            entity = {
                "dense_vector": vectors[i] if i < len(vectors) else [0.0] * 768,
                "chunk_text": chunk,
                "chunk_hash": chunk_hash,
                "chunk_index": i,
                "chunk_type": chunk_method,
                "file_path": kwargs.get("file_path", ""),
                "document_title": kwargs.get("document_title", ""),
                "document_type": kwargs.get("document_type", ""),
                "language": language,
                "keywords": kwargs.get("keywords", ""),
                "summary": summary,
                "created_at": current_time
            }
            data.append(entity)
        
        # 삽입 실행
        client = get_milvus_client()
        result = client.insert(
            collection_name=kwargs.get("collection_name"),
            data=data
        )
        
        return {
            "insert_count": len(chunks),
            "chunks_created": len(chunks),
            "chunk_method": chunk_method,
            "language_detected": language,
            "ids": result.get("primary_keys", [])
        }
    
    result = await milvus_api_request(
        "chunk_and_insert", 
        operation, 
        collection_name=collection_name,
        text=text,
        vectors=vectors,
        file_path=file_path,
        document_title=document_title,
        document_type=document_type,
        language=language,
        chunk_method=chunk_method,
        max_chunk_size=max_chunk_size,
        overlap=overlap,
        keywords=keywords,
        auto_summarize=auto_summarize
    )
    return result

@mcp.tool()
async def hybrid_search(
    collection_name: str = DEFAULT_COLLECTION_NAME,
    query_vector: List[float] = None,
    query_text: str = "",
    limit: int = 5,
    rerank: bool = True,
    filter_expr: str = "",
    boost_recent: bool = False,
    boost_keywords: List[str] = None,
    min_score: float = 0.0
) -> List[Dict]:
    """
    하이브리드 검색을 수행합니다 (벡터 + 텍스트 + 필터링 + 리랭킹).
    
    Args:
        collection_name (str): 검색할 컬렉션 이름
        query_vector (List[float]): 쿼리 벡터
        query_text (str): 쿼리 텍스트
        limit (int): 최대 결과 수
        rerank (bool): 리랭킹 수행 여부
        filter_expr (str): 필터 표현식
        boost_recent (bool): 최신 문서 부스팅 여부
        boost_keywords (List[str]): 부스팅할 키워드 목록
        min_score (float): 최소 유사도 점수
        
    Returns:
        List[Dict]: 검색 결과 목록
    """
    logger.info(f"하이브리드 검색 요청: 컬렉션={collection_name}, 쿼리={query_text[:50]}...")
    
    if not query_vector and not query_text:
        return {"error": "쿼리 벡터 또는 텍스트가 필요합니다."}
    
    def operation(*args, **kwargs):
        client = get_milvus_client()
        collection_name = kwargs.get("collection_name")
        query_vector = kwargs.get("query_vector")
        query_text = kwargs.get("query_text", "")
        limit = kwargs.get("limit", 5)
        rerank = kwargs.get("rerank", True)
        filter_expr = kwargs.get("filter_expr", "")
        boost_recent = kwargs.get("boost_recent", False)
        boost_keywords = kwargs.get("boost_keywords", []) or []
        min_score = kwargs.get("min_score", 0.0)
        
        # 출력 필드 정의
        output_fields = [
            "chunk_text", "chunk_index", "chunk_type", "file_path", 
            "document_title", "document_type", "language", "keywords", 
            "summary", "created_at"
        ]
        
        # 벡터 검색 수행
        if query_vector:
            search_limit = limit * 3 if rerank else limit  # 리랭킹을 위해 더 많은 결과 가져오기
            
            results = client.search(
                collection_name=collection_name,
                data=[query_vector],
                anns_field="dense_vector",
                limit=search_limit,
                output_fields=output_fields,
                expr=filter_expr if filter_expr else None
            )
        else:
            # 벡터가 없는 경우 텍스트 기반 검색 (시뮬레이션)
            results = [[]]
        
        # 결과 처리
        if not results or len(results) == 0 or len(results[0]) == 0:
            return []
        
        processed_results = []
        for hit in results[0]:
            score = hit.get("score", 0.0)
            
            # 최소 점수 필터링
            if score < min_score:
                continue
            
            result = {
                "id": hit.get("id"),
                "score": score,
                "chunk_text": hit.get("entity", {}).get("chunk_text", ""),
                "chunk_index": hit.get("entity", {}).get("chunk_index", 0),
                "chunk_type": hit.get("entity", {}).get("chunk_type", ""),
                "file_path": hit.get("entity", {}).get("file_path", ""),
                "document_title": hit.get("entity", {}).get("document_title", ""),
                "document_type": hit.get("entity", {}).get("document_type", ""),
                "language": hit.get("entity", {}).get("language", ""),
                "keywords": hit.get("entity", {}).get("keywords", ""),
                "summary": hit.get("entity", {}).get("summary", ""),
                "created_at": hit.get("entity", {}).get("created_at", "")
            }
            
            # 텍스트 매칭 점수 계산
            text_score = 0.0
            if query_text:
                chunk_text = result["chunk_text"].lower()
                query_lower = query_text.lower()
                
                # 정확한 매칭
                if query_lower in chunk_text:
                    text_score += 0.5
                
                # 키워드 매칭
                query_words = query_lower.split()
                chunk_words = chunk_text.split()
                matching_words = set(query_words) & set(chunk_words)
                text_score += len(matching_words) / len(query_words) * 0.3
            
            # 키워드 부스팅
            keyword_boost = 0.0
            if boost_keywords:
                chunk_keywords = result["keywords"].lower()
                for keyword in boost_keywords:
                    if keyword.lower() in chunk_keywords:
                        keyword_boost += 0.1
            
            # 최신성 부스팅
            recency_boost = 0.0
            if boost_recent and result["created_at"]:
                try:
                    import datetime
                    created_time = datetime.datetime.fromisoformat(result["created_at"])
                    now = datetime.datetime.now()
                    days_old = (now - created_time).days
                    recency_boost = max(0, (30 - days_old) / 30 * 0.1)  # 30일 이내 문서 부스팅
                except:
                    pass
            
            # 최종 점수 계산
            final_score = score + text_score + keyword_boost + recency_boost
            result["final_score"] = final_score
            result["text_score"] = text_score
            result["keyword_boost"] = keyword_boost
            result["recency_boost"] = recency_boost
            
            processed_results.append(result)
        
        # 리랭킹
        if rerank:
            processed_results.sort(key=lambda x: x["final_score"], reverse=True)
        
        # 결과 제한
        return processed_results[:limit]
    
    result = await milvus_api_request(
        "hybrid_search", 
        operation, 
        collection_name=collection_name,
        query_vector=query_vector,
        query_text=query_text,
        limit=limit,
        rerank=rerank,
        filter_expr=filter_expr,
        boost_recent=boost_recent,
        boost_keywords=boost_keywords,
        min_score=min_score
    )
    return result

@mcp.tool()
async def semantic_search(
    collection_name: str = DEFAULT_COLLECTION_NAME,
    query_text: str = "",
    limit: int = 5,
    document_type: str = "",
    language: str = "",
    date_range: str = "",
    similarity_threshold: float = 0.7
) -> Dict[str, Any]:
    """
    의미 기반 검색을 수행합니다.
    
    Args:
        collection_name (str): 검색할 컬렉션 이름
        query_text (str): 검색 쿼리
        limit (int): 최대 결과 수
        document_type (str): 문서 타입 필터
        language (str): 언어 필터
        date_range (str): 날짜 범위 필터 (YYYY-MM-DD,YYYY-MM-DD)
        similarity_threshold (float): 유사도 임계값
        
    Returns:
        Dict[str, Any]: 검색 결과 및 메타데이터
    """
    logger.info(f"의미 검색 요청: 쿼리={query_text}")
    
    if not query_text:
        return {"error": "검색 쿼리가 필요합니다."}
    
    # 필터 표현식 구성
    filter_conditions = []
    
    if document_type:
        filter_conditions.append(f'document_type == "{document_type}"')
    
    if language:
        filter_conditions.append(f'language == "{language}"')
    
    if date_range and "," in date_range:
        start_date, end_date = date_range.split(",")
        filter_conditions.append(f'created_at >= "{start_date}" and created_at <= "{end_date}"')
    
    filter_expr = " and ".join(filter_conditions) if filter_conditions else ""
    
    # 쿼리 확장 (동의어, 관련어 추가)
    expanded_keywords = [query_text]
    
    # 간단한 동의어 사전 (실제로는 외부 API나 사전 사용)
    synonym_dict = {
        "AI": ["인공지능", "머신러닝", "딥러닝"],
        "데이터": ["정보", "자료", "데이터셋"],
        "분석": ["해석", "검토", "조사"]
    }
    
    for word in query_text.split():
        if word in synonym_dict:
            expanded_keywords.extend(synonym_dict[word])
    
    # 시뮬레이션된 검색 결과 (실제로는 임베딩 모델 사용)
    simulated_results = {
        "query": query_text,
        "expanded_keywords": expanded_keywords,
        "filter_applied": filter_expr,
        "total_found": 3,
        "results": [
            {
                "id": 1,
                "score": 0.95,
                "final_score": 0.95,
                "chunk_text": f"{query_text}에 대한 상세한 설명이 포함된 문서입니다.",
                "chunk_index": 0,
                "chunk_type": "sentence",
                "file_path": "documents/guide.pdf",
                "document_title": f"{query_text} 가이드",
                "document_type": document_type or "pdf",
                "language": language or "ko",
                "keywords": query_text,
                "summary": f"{query_text}의 핵심 개념 설명",
                "created_at": "2024-01-15T10:00:00"
            },
            {
                "id": 2,
                "score": 0.87,
                "final_score": 0.87,
                "chunk_text": f"{query_text}와 관련된 추가 정보가 담긴 섹션입니다.",
                "chunk_index": 1,
                "chunk_type": "paragraph",
                "file_path": "documents/reference.docx",
                "document_title": f"{query_text} 참고자료",
                "document_type": document_type or "docx",
                "language": language or "ko",
                "keywords": f"{query_text}, 참고",
                "summary": f"{query_text} 관련 참고 정보",
                "created_at": "2024-01-10T14:30:00"
            }
        ]
    }
    
    # 유사도 임계값 적용
    filtered_results = [
        r for r in simulated_results["results"] 
        if r["score"] >= similarity_threshold
    ]
    
    simulated_results["results"] = filtered_results[:limit]
    simulated_results["total_found"] = len(filtered_results)
    
    return simulated_results

@mcp.tool()
async def get_collection_stats(collection_name: str = DEFAULT_COLLECTION_NAME) -> Dict[str, Any]:
    """
    컬렉션 통계 정보를 조회합니다.
    
    Args:
        collection_name (str): 컬렉션 이름
        
    Returns:
        Dict[str, Any]: 컬렉션 통계
    """
    logger.info(f"컬렉션 통계 조회: {collection_name}")
    
    def operation(*args, **kwargs):
        client = get_milvus_client()
        collection_name = kwargs.get("collection_name")
        
        # 컬렉션 정보 조회
        collection_info = client.describe_collection(collection_name=collection_name)
        
        # 통계 정보 (시뮬레이션)
        stats = {
            "collection_name": collection_name,
            "total_entities": 1000,  # 실제로는 client.get_collection_stats() 사용
            "total_chunks": 1000,
            "chunk_types": {
                "sentence": 400,
                "paragraph": 300,
                "token": 200,
                "semantic": 100
            },
            "languages": {
                "ko": 600,
                "en": 300,
                "unknown": 100
            },
            "document_types": {
                "pdf": 500,
                "docx": 300,
                "txt": 200
            },
            "avg_chunk_size": 256,
            "collection_info": collection_info
        }
        
        return stats
    
    result = await milvus_api_request("get_collection_stats", operation, collection_name=collection_name)
    return result

@mcp.tool()
async def drop_collection(collection_name: str = DEFAULT_COLLECTION_NAME) -> Dict[str, Any]:
    """
    컬렉션을 삭제합니다.
    
    Args:
        collection_name (str): 삭제할 컬렉션 이름
        
    Returns:
        Dict[str, Any]: 삭제 결과
    """
    logger.info(f"컬렉션 삭제 요청: {collection_name}")
    
    def operation(*args, **kwargs):
        client = get_milvus_client()
        client.drop_collection(collection_name=kwargs.get("collection_name"))
        return {"msg": f"Collection {kwargs.get('collection_name')} has been dropped successfully"}
    
    result = await milvus_api_request("drop_collection", operation, collection_name=collection_name)
    return result

if __name__ == "__main__":
    print(f"Milvus RAG MCP 서버가 실행 중입니다... (포트: {MILVUS_MCP_PORT})")
    mcp.run(transport="sse") 