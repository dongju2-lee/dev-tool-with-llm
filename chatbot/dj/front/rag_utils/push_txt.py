import os
import pathlib
import numpy as np
import time
import argparse
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
COLLECTION_NAME  = "TXT_COLLECTION"  # txt 파일용 컬렉션 이름

VERTEX_PROJECT_ID = "certain-wharf-453410-p8"
VERTEX_LOCATION   = "us-central1"
VERTEX_MODEL_ID   = "text-multilingual-embedding-002"  # 다국어 모델 사용
EMBEDDING_DIM     = 768  # 모델 출력 차원

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

    # 스파스 벡터 필드 제거
    fields = [
        FieldSchema(name="id",           dtype=DataType.INT64,            is_primary=True, auto_id=True),
        FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR,     dim=EMBEDDING_DIM),
        FieldSchema(name="file_path",    dtype=DataType.VARCHAR,          max_length=500),
        FieldSchema(name="language",     dtype=DataType.VARCHAR,          max_length=20),
        FieldSchema(name="title",        dtype=DataType.VARCHAR,          max_length=200),
        FieldSchema(name="content",      dtype=DataType.VARCHAR,          max_length=10000),
        FieldSchema(name="directory",    dtype=DataType.VARCHAR,          max_length=500),
    ]
    schema = CollectionSchema(fields, description="TXT 문서 검색 저장소")
    coll = Collection(name=COLLECTION_NAME, schema=schema, consistency_level="Strong")
    print(f"[Milvus] 컬렉션 생성: {COLLECTION_NAME}")

    # 밀집 벡터 인덱스 생성
    dense_index_params = {
        "index_type":  "HNSW",
        "metric_type": "COSINE",
        "params":      {"M": 8, "efConstruction": 64}
    }
    coll.create_index("dense_vector", dense_index_params)
    print(f"dense_vector 인덱스 생성 ")
    
    coll.load()
    print(f"[Milvus] 인덱스 생성 및 로드 완료")
    return coll

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
    """청크를 배치 단위로 처리하여 밀집 벡터 생성"""
    all_dense_vectors = []
    
    # 배치 단위로 처리
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        print(f"[Batch] {i//batch_size + 1}번째 배치 처리 중 ({len(batch)}개 청크)")
        
        # 밀집 벡터 생성 (Vertex AI)
        try:
            embeddings = model.get_embeddings(batch)
            dense_vectors = [embedding.values for embedding in embeddings]
            all_dense_vectors.extend(dense_vectors)
        except Exception as e:
            print(f"[Error] 밀집 벡터 생성 중 오류: {e}")
            # 오류 발생 시 0으로 채운 벡터 추가
            zero_vectors = [[0.0] * EMBEDDING_DIM for _ in range(len(batch))]
            all_dense_vectors.extend(zero_vectors)
        
        # API 요청 제한을 고려한 지연 시간 추가
        if i + batch_size < len(chunks):
            time.sleep(0.5)  # 0.5초 대기
    return all_dense_vectors

def process_single_txt_file(file_path, collection, model, vectorizer):
    """지정된 텍스트 파일 하나만 처리하고 Milvus에 저장"""
    file_path = pathlib.Path(file_path)
    
    if not file_path.exists():
        print(f"[Error] 파일이 존재하지 않습니다: {file_path}")
        return False
    
    if not file_path.is_file() or file_path.suffix.lower() != '.txt':
        print(f"[Error] 유효한 TXT 파일이 아닙니다: {file_path}")
        return False
    
    print(f"[Info] 파일 처리 시작: {file_path}")
    
    # 언어 추측 (파일 이름이나 경로에서)
    file_name = file_path.stem
    lang = "unknown"
    for lang_code in ["ko", "en"]:
        if lang_code in file_name.lower() or lang_code in str(file_path).lower():
            lang = lang_code
            break
    
    try:
        # 텍스트 파일 읽기
        text = file_path.read_text(encoding="utf-8").strip()
        if not text:
            print(f"[Skip] 빈 파일입니다: {file_path}")
            return False
        
        # 문자 단위 청킹
        chunks = chunk_text_by_char(text, CHUNK_SIZE, CHUNK_OVERLAP)
        if not chunks:
            print(f"[Skip] 청킹 후 내용이 없습니다: {file_path}")
            return False
        
        print(f"[Info] 총 {len(chunks)}개 청크로 분할되었습니다")
        
        # 밀집 벡터만 생성 (희소 벡터 제거)
        dense_vectors = process_chunks_in_batches(chunks, model, vectorizer)
        
        # 각 필드 데이터 준비
        file_paths, langs, titles, contents, dirs = [], [], [], [], []
        for idx, chunk in enumerate(chunks):
            file_paths.append(str(file_path))
            langs.append(lang)
            
            # 타이틀 설정: 파일명 + 청크 번호 + 청크 시작부분
            title_preview = chunk[:20].replace("\n", " ")
            titles.append(f"{file_path.stem}_chunk{idx}: {title_preview}...")
            
            contents.append(chunk)
            dirs.append(str(file_path.parent))
        
        # Milvus에 삽입 (배치 단위로)
        max_batch = 1000  # Milvus 삽입 배치 크기
        for i in range(0, len(chunks), max_batch):
            end_idx = min(i + max_batch, len(chunks))
            
            batch_dense = dense_vectors[i:end_idx]
            batch_paths = file_paths[i:end_idx]
            batch_langs = langs[i:end_idx]
            batch_titles = titles[i:end_idx]
            batch_contents = contents[i:end_idx]
            batch_dirs = dirs[i:end_idx]
            
            # Milvus에 삽입 (희소 벡터 필드 제거)
            entities = [
                batch_dense,     # dense_vector 필드
                batch_paths,     # file_path 필드
                batch_langs,     # language 필드
                batch_titles,    # title 필드
                batch_contents,  # content 필드
                batch_dirs,      # directory 필드
            ]
            
            try:
                res = collection.insert(entities)
                print(f"[Inserted] 배치 {i//max_batch + 1}/{(len(chunks)+max_batch-1)//max_batch} → {len(batch_dense)}개 청크 삽입 완료")
            except Exception as e:
                print(f"[Error] 삽입 중 오류 발생: {e}")
                return False
        
        print(f"[Success] 파일 '{file_path.name}'의 모든 청크가 Milvus에 삽입되었습니다")
        return True
    
    except Exception as e:
        print(f"[Error] 파일 처리 중 예외 발생: {e}")
        return False

def parse_arguments():
    """명령줄 인수 파싱"""
    parser = argparse.ArgumentParser(description='텍스트 파일을 Milvus 벡터 데이터베이스에 임베딩')
    parser.add_argument('--file', type=str, required=True, help='처리할 텍스트 파일 경로')
    parser.add_argument('--collection', type=str, default=COLLECTION_NAME, help='Milvus 컬렉션 이름')
    parser.add_argument('--chunk-size', type=int, default=CHUNK_SIZE, help='청크 크기 (문자 수)')
    parser.add_argument('--chunk-overlap', type=int, default=CHUNK_OVERLAP, help='청크 겹침 크기 (문자 수)')
    
    return parser.parse_args()

def main():
    # 명령줄 인수 파싱
    args = parse_arguments()
    
    # 전역 변수에 설정값 적용
    global COLLECTION_NAME, CHUNK_SIZE, CHUNK_OVERLAP
    COLLECTION_NAME = args.collection
    CHUNK_SIZE = args.chunk_size
    CHUNK_OVERLAP = args.chunk_overlap
    
    print(f"[Config] 파일: {args.file}, 컬렉션: {COLLECTION_NAME}, 청크 크기: {CHUNK_SIZE}, 청크 겹침: {CHUNK_OVERLAP}")
    
    # 모델 및 컬렉션 초기화
    model = setup_vertex_ai()
    vectorizer = setup_tfidf_vectorizer()
    collection = setup_milvus_collection()
    
    # 단일 파일 처리
    success = process_single_txt_file(args.file, collection, model, vectorizer)
    
    if success:
        print(f"[Done] '{args.file}' 파일이 성공적으로 Milvus에 저장되었습니다.")
    else:
        print(f"[Failed] '{args.file}' 파일 처리 중 오류가 발생했습니다.")

if __name__ == "__main__":
    main()