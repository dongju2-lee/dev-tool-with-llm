#!/usr/bin/env python3

import asyncio
from app.graph.instance import process_chat_message

async def quick_test():
    result = await process_chat_message('Node Exporter Full 대시보드를 렌더링해주세요')
    print(f"✅ 응답 성공 (길이: {len(result.get('content', ''))}자)")
    print(f"📷 이미지 데이터: {'있음' if result.get('image_data') else '없음'}")
    if result.get('image_data'):
        print(f"🖼️  이미지 형태: {result['image_data'][:50]}...")

asyncio.run(quick_test()) 