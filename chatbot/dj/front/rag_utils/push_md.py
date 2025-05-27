import os
import pathlib
import numpy as np
import time
from typing import List, Dict
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer

import vertexai
from vertexai.language_models import TextEmbeddingModel
from pymilvus import (
    connections,
    FieldSchema, CollectionSchema, DataType,
    Collection, utility
)

# -------- 설정 값 --------
MILVUS_HOST      = "localhost"
MILVUS_PORT      = "19530"
COLLECTION_NAME  = "COLLECTION_NAME"

VERTEX_PROJECT_ID = "USER-PROJECT-ID"
VERTEX_LOCATION   = "us-central1"
VERTEX_MODEL_ID   = "text-multilingual-embedding-002"  # 다국어 모델 사용
EMBEDDING_DIM     = 768  # 모델 출력 차원

LANGUAGE_DIRS     = ["en", "ko"]
DOCS_ROOT      = pathlib.Path(
    "FILE_PATH"
)

# 청킹 파라미터 (문자 단위)
CHUNK_SIZE        = 700   # 한 청크당 최대 문자 수
CHUNK_OVERLAP     = 150   # 이웃 청크와 겹칠 문자 수

# Vertex AI API 제한사항
MAX_BATCH_SIZE    = 250   # API 요청당 최대 텍스트 수

def setup_tfidf_vectorizer():
    """TF-IDF 벡터라이저 초기화 (희소 벡터 생성용)"""
    vectorizer = TfidfVectorizer(
        max_features=5000,
        stop_words="english",  # 영어 불용어 제거
        min_df=2,              # 최소 2개 문서에 등장하는 단어만 사용
        max_df=0.85            # 문서의 85%이상 등장하는 단어 제외
    )
    return vectorizer

def setup_vertex_ai():
    """Vertex AI 임베딩 모델 초기화"""
    vertexai.init(project=VERTEX_PROJECT_ID, location=VERTEX_LOCATION)
    model = TextEmbeddingModel.from_pretrained(VERTEX_MODEL_ID)
    print(f"[VertexAI] 모델 로드 완료: {VERTEX_MODEL_ID}")
    return model

def setup_milvus_collection():
    """Milvus 연결 및 하이브리드 검색용 컬렉션 생성/설정"""
    print("setup_milvus_collection")
    connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)
    if utility.has_collection(COLLECTION_NAME):
        utility.drop_collection(COLLECTION_NAME)
        print(f"[Milvus] 기존 컬렉션 삭제: {COLLECTION_NAME}")
    

    print(f"컬렉션 생성 : {COLLECTION_NAME}")

    fields = [
        FieldSchema(name="id",           dtype=DataType.INT64,            is_primary=True, auto_id=True),
        FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR,     dim=EMBEDDING_DIM),
        FieldSchema(name="sparse_vector",dtype=DataType.SPARSE_FLOAT_VECTOR),
        FieldSchema(name="file_path",    dtype=DataType.VARCHAR,          max_length=500),
        FieldSchema(name="language",     dtype=DataType.VARCHAR,          max_length=20),
        FieldSchema(name="title",        dtype=DataType.VARCHAR,          max_length=200),
        FieldSchema(name="content",      dtype=DataType.VARCHAR,          max_length=10000),
        FieldSchema(name="directory",    dtype=DataType.VARCHAR,          max_length=500),
    ]
    schema = CollectionSchema(fields, description="MkDocs 문서 하이브리드 검색 저장소")
    coll = Collection(name=COLLECTION_NAME, schema=schema,consistency_level="Strong")
    print(f"[Milvus] 컬렉션 생성: {COLLECTION_NAME}")

    # 밀집 벡터 인덱스 생성
    dense_index_params = {
        "index_type":  "HNSW",
        "metric_type": "COSINE",
        "params":      {"M": 8, "efConstruction": 64}
    }
    # dense_index_params = {
    #     "index_type":  "AUTOINDEX",
    #     "metric_type": "IP"
    # }
    coll.create_index("dense_vector", dense_index_params)
    print(f"dense_vector 인덱스 생성 ")

    # 희소 벡터 인덱스 생성
    sparse_index_params = {
        "index_type": "SPARSE_INVERTED_INDEX", 
        "metric_type": "IP"
    }
    coll.create_index("sparse_vector", sparse_index_params)
    print(f"sparse_vector 인덱스 생성 ")
    
    coll.load()
    print(f"[Milvus] 인덱스 생성 및 로드 완료")
    return coll

def find_markdown_files(root_dir):
    """MkDocs 루트에서 en/ko 아래 모든 .md 파일 수집"""
    md_files = []
    for lang in LANGUAGE_DIRS:
        lang_dir = root_dir / lang
        if not lang_dir.exists():
            print(f"[Warning] {lang_dir} 가 없습니다.")
            continue
        for p in lang_dir.rglob("*.md"):
            md_files.append({
                "path": p,
                "rel":  str(p.relative_to(root_dir)),
                "lang": lang
            })
    print(f"[Info] 총 {len(md_files)}개의 MD파일 발견")
    return md_files

def chunk_text_by_char(text: str, size: int, overlap: int):
    """문자 단위로 text를 size씩 잘라 overlap만큼 겹치게 반환"""
    chunks = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + size, length)
        chunks.append(text[start:end])
        start += size - overlap
    return chunks

def process_chunks_in_batches(chunks: List[str], model, vectorizer, batch_size=MAX_BATCH_SIZE):
    """청크를 배치 단위로 처리하여 밀집 및 희소 벡터 생성"""
    all_dense_vectors = []
    all_sparse_vectors = []
    
    # TF-IDF 희소 벡터 생성을 위해 전체 코퍼스로 학습
    vectorizer.fit(chunks)
    
    # 배치 단위로 처리
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        print(f"[Batch] {i//batch_size + 1}번째 배치 처리 중 ({len(batch)}개 청크)")
        
        # 1. 밀집 벡터 생성 (Vertex AI)
        try:
            embeddings = model.get_embeddings(batch)
            dense_vectors = [embedding.values for embedding in embeddings]
            all_dense_vectors.extend(dense_vectors)
        except Exception as e:
            print(f"[Error] 밀집 벡터 생성 중 오류: {e}")
            # 오류 발생 시 0으로 채운 벡터 추가
            zero_vectors = [[0.0] * EMBEDDING_DIM for _ in range(len(batch))]
            all_dense_vectors.extend(zero_vectors)
        
        # 2. 희소 벡터 생성 (TF-IDF)
        sparse_matrix = vectorizer.transform(batch)
        
        # 각 행을 Milvus 희소 벡터 형식으로 변환
        for j in range(sparse_matrix.shape[0]):
            row = sparse_matrix[j]
            indices = row.indices.tolist()
            values = row.data.tolist()
            all_sparse_vectors.append({"indices": indices, "values": values})
        
        # API 요청 제한을 고려한 지연 시간 추가
        if i + batch_size < len(chunks):
            time.sleep(0.5)  # 0.5초 대기
    return all_dense_vectors, all_sparse_vectors

def insert_file_with_hybrid_chunks(file_info, collection, model, vectorizer, root_dir):
    """파일을 읽고 문자 단위 청킹 후 하이브리드 임베딩하여 Milvus에 삽입"""
    print("-----------------  insert_file_with_hybrid_chunks  ---------------------------")
    path = file_info["path"]
    rel  = file_info["rel"]
    lang = file_info["lang"]

    try:
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            print(f"[Skip] 빈 파일: {rel}")
            return

        # 문자 단위 청킹
        chunks = chunk_text_by_char(text, CHUNK_SIZE, CHUNK_OVERLAP)
        if not chunks:
            print(f"[Skip] 청킹 후 내용 없음: {rel}")
            return
            
        # 밀집 및 희소 벡터 생성 (배치 처리)
        dense_vectors, sparse_vectors = process_chunks_in_batches(chunks, model, vectorizer)

        # 각 필드 데이터 준비
        file_paths, langs, titles, contents, dirs = [], [], [], [], []
        for idx, chunk in enumerate(chunks):
            file_paths.append(rel)
            langs.append(lang)
            titles.append(f"{path.stem}_chunk{idx}")
            contents.append(chunk)
            dirs.append(str(path.parent.relative_to(root_dir)))

        # Milvus에 삽입 (배치 단위로)
        max_batch = 1000  # Milvus 삽입 배치 크기 (64MB 제한 고려)
        for i in range(0, len(chunks), max_batch):
            end_idx = min(i + max_batch, len(chunks))
            
            batch_dense = dense_vectors[i:end_idx]
            batch_sparse = sparse_vectors[i:end_idx]
            batch_paths = file_paths[i:end_idx]
            batch_langs = langs[i:end_idx]
            batch_titles = titles[i:end_idx]
            batch_contents = contents[i:end_idx]
            batch_dirs = dirs[i:end_idx]
            
            # Milvus에 삽입
            entities = [
                batch_dense,     # dense_vector 필드
                batch_sparse,    # sparse_vector 필드
                batch_paths,     # file_path 필드
                batch_langs,     # language 필드
                batch_titles,    # title 필드
                batch_contents,  # content 필드
                batch_dirs,      # directory 필드
            ]
            print(f"entities 삽입 시작 : {entities}")
            
            try:
                res = collection.insert(entities)
                print(f"[Inserted] {rel} 배치 {i//max_batch + 1}/{(len(chunks)+max_batch-1)//max_batch} → {len(batch_dense)}개 청크")
            except Exception as e:
                print(f"[Error] {rel} 삽입 중 오류: {e}")

    except Exception as e:
        print(f"[Error] {rel} 처리 중 예외: {e}")

def main():
    model = setup_vertex_ai()
    vectorizer = setup_tfidf_vectorizer()
    collection = setup_milvus_collection()

    if not DOCS_ROOT.exists():
        print(f"[Error] MkDocs 루트가 잘못되었습니다: {DOCS_ROOT}")
        return

    md_files = find_markdown_files(DOCS_ROOT)
    if not md_files:
        print("[Info] 삽입할 파일이 없습니다.")
        return

    for file_info in md_files:
        insert_file_with_hybrid_chunks(file_info, collection, model, vectorizer, DOCS_ROOT)

    print("[Done] 모든 파일의 하이브리드 임베딩 청크 삽입 완료")

if __name__ == "__main__":
    main()