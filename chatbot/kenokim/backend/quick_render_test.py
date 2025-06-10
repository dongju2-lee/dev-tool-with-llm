import asyncio
from app.graph.instance import process_chat_message

async def quick_render_test():
    """대시보드 렌더링 빠른 테스트"""
    print("🖼️ 대시보드 렌더링 테스트")
    
    message = "Node Exporter Full 대시보드를 렌더링해주세요"
    print(f"요청: {message}")
    
    try:
        result = await process_chat_message(message, "render-test")
        
        response_content = result.get('content', '')
        print(f"응답 길이: {len(response_content)} 문자")
        
        if len(response_content) > 10000:
            print("✅ 대용량 응답 - 이미지가 포함된 것으로 보임")
            print("응답 시작 부분:", response_content[:200], "...")
        else:
            print("📝 텍스트 응답:", response_content)
            
    except Exception as e:
        print(f"❌ 오류: {e}")

if __name__ == "__main__":
    asyncio.run(quick_render_test()) 