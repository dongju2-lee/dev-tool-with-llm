import vertexai
from vertexai.language_models import TextEmbeddingModel
from pymilvus import connections, Collection, utility
import sys

# Milvus 연결 정보
# MILVUS_HOST     = "localhost"
# MILVUS_PORT     = "19530"
# COLLECTION_NAME = "COLLECTION_NAME"

# # Vertex AI 설정
# VERTEX_PROJECT_ID = "USER-PROJECT-ID"
# VERTEX_LOCATION   = "us-central1"
# VERTEX_MODEL_ID   = "text-embedding-005"
MILVUS_HOST      = "localhost"
MILVUS_PORT      = "19530"
COLLECTION_NAME  = "my_collection"  # txt 파일용 컬렉션 이름

VERTEX_PROJECT_ID = "certain-wharf-453410-p8"
VERTEX_LOCATION   = "us-central1"
VERTEX_MODEL_ID   = "text-multilingual-embedding-002"  # 다국어 모델 사용

def setup_vertex_ai():
    """Vertex AI 임베딩 모델 초기화"""
    print(f"[Info] Vertex AI 초기화: 프로젝트={VERTEX_PROJECT_ID}, 지역={VERTEX_LOCATION}")
    vertexai.init(project=VERTEX_PROJECT_ID, location=VERTEX_LOCATION)
    model = TextEmbeddingModel.from_pretrained(VERTEX_MODEL_ID)
    print(f"[Success] 모델 로드 완료: {VERTEX_MODEL_ID}")
    return model

def main():
    try:
        # 1) Milvus 연결
        print(f"[Info] Milvus 연결 시도: {MILVUS_HOST}:{MILVUS_PORT}")
        connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)
        
        # 컬렉션 존재 여부 확인
        if not utility.has_collection(COLLECTION_NAME):
            print(f"[Error] 컬렉션 '{COLLECTION_NAME}'이(가) 존재하지 않습니다.")
            print("[Info] 사용 가능한 컬렉션 목록:")
            collections = utility.list_collections()
            if collections:
                for i, coll in enumerate(collections, 1):
                    print(f"  {i}. {coll}")
            else:
                print("  (컬렉션 없음)")
            return
        
        print(f"[Info] 컬렉션 '{COLLECTION_NAME}' 로드 중...")
        collection = Collection(name=COLLECTION_NAME)
        collection.load()
        print(f"[Success] 컬렉션 로드 완료")
        
        # 2) Vertex AI 모델 로드
        model = setup_vertex_ai()
        
        # 3) 검색할 자연어 질문
        if len(sys.argv) > 1:
            query = " ".join(sys.argv[1:])
        else:
            query = input("검색할 질문을 입력하세요: ")
            
        print(f"[Search] 검색 쿼리: '{query}'")
        
        # 4) 질문을 임베딩
        print("[Info] 쿼리 임베딩 생성 중...")
        embedding = model.get_embeddings([query])[0].values
        print("[Success] 쿼리 임베딩 생성 완료")
        
        # 5) Milvus에 검색 요청
        search_params = {
            "metric_type": "COSINE",
            "params": {"ef": 64}
        }
        
        print("[Info] Milvus 검색 실행 중...")
        # 언어 필터는 주석 처리 (필요시 해제)
        # expr = 'language == "ko"'
        results = collection.search(
            data=[embedding],            # 쿼리 벡터 리스트
            anns_field="dense_vector",   # 컬렉션의 벡터 필드명 수정
            param=search_params,
            limit=5,
            # expr=expr,                 # 필터가 필요 없으면 주석 처리
            output_fields=["file_path", "title", "content", "language"]
        )
        
        # 6) 결과 출력
        print(f"\n===== 검색 결과: '{query}' =====\n")
        
        if not results or len(results) == 0 or len(results[0]) == 0:
            print("검색 결과가 없습니다.")
            return
            
        for i, hits in enumerate(results[0], start=1):
            print(f"▶ 결과 #{i} (유사도: {hits.score:.4f})")
            print(f"- 언어: {hits.entity.get('language', '알 수 없음')}")
            print(f"- 경로: {hits.entity.get('file_path', '경로 없음')}")
            print(f"- 제목: {hits.entity.get('title', '제목 없음')}")
            
            # 내용은 너무 길면 잘라서 보여줌
            content = hits.entity.get('content', '')
            if content:
                snippet = content[:500].replace("\n", " ")
                print(f"- 내용: {snippet}..." if len(content) > 500 else f"- 내용: {content}")
            print("-" * 80)
    
    except Exception as e:
        print(f"[Error] 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()