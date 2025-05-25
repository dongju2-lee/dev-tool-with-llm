from pymilvus import connections, utility

# Milvus 연결 정보
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"

def drop_all_collections(host: str, port: str):
    # 1) Milvus 서버에 연결
    connections.connect(host=host, port=port)
    # 2) 현재 존재하는 모든 컬렉션 이름 조회
    col_names = utility.list_collections()
    if not col_names:
        print("삭제할 컬렉션이 없습니다.")
        return

    print(f"총 {len(col_names)}개의 컬렉션을 삭제합니다:")
    for name in col_names:
        print(f"  - {name}")
    confirm = input("정말 모두 삭제하시겠습니까? (y/N): ").strip().lower()
    if confirm != 'y':
        print("삭제 취소됨.")
        return

    # 3) 컬렉션 삭제
    for name in col_names:
        try:
            utility.drop_collection(name)
            print(f"[OK] '{name}' 삭제 완료")
        except Exception as e:
            print(f"[Error] '{name}' 삭제 실패: {e}")

    print("모든 컬렉션 삭제 작업이 완료되었습니다.")

if __name__ == "__main__":
    drop_all_collections(MILVUS_HOST, MILVUS_PORT)