from pymilvus import MilvusClient

# Milvus 클라이언트 생성
client = MilvusClient(
    uri="http://localhost:19530",
    token="root:Milvus"
)

# 모든 컬렉션 목록 확인
collections = client.list_collections()
print("컬렉션 목록:", collections)

# 특정 컬렉션의 상세 정보 확인
collection_name = "COLLECTION_NAME"  # 확인하려는 컬렉션 이름
collection_info = client.describe_collection(
    collection_name=collection_name
)
print(f"\n{collection_name} 컬렉션 상세 정보:")
print(collection_info)