# Streamlit 앱에서 비동기 처리 방식

## 1. nest_asyncio 사용
- `nest_asyncio.apply()`로 중첩된 이벤트 루프 허용
- Streamlit의 기존 이벤트 루프 내에서 다른 비동기 작업 실행 가능

```python
import nest_asyncio
nest_asyncio.apply()
```

## 2. 글로벌 이벤트 루프 생성 및 재사용
- 세션 상태에 이벤트 루프를 저장하여 앱 전체에서 재사용
- 매번 새 루프를 생성하지 않아 효율적

```python
if "event_loop" not in st.session_state:
    loop = asyncio.new_event_loop()
    st.session_state.event_loop = loop
    asyncio.set_event_loop(loop)
```

## 3. Windows 환경 특별 처리
- Windows에서는 ProactorEventLoop 정책 설정 필요

```python
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

## 4. 비동기 함수 직접 실행
- ThreadPoolExecutor 대신 저장된 이벤트 루프에서 직접 비동기 함수 실행

```python
result = st.session_state.event_loop.run_until_complete(async_function())
```

## 5. 타임아웃 처리
- 응답 시간이 너무 길어지는 것을 방지

```python
await asyncio.wait_for(async_task, timeout=timeout_seconds)
```

## 6. 비동기 스트리밍 처리
- `astream_graph` 함수로 결과를 실시간 스트리밍
- 콜백 함수를 사용해 UI 실시간 업데이트

```python
response = await astream_graph(
    agent,
    {"messages": [HumanMessage(content=query)]},
    callback=streaming_callback,
    config=RunnableConfig(
        recursion_limit=recursion_limit,
        thread_id=thread_id
    )
)
```

## 7. MCP 클라이언트 비동기 관리
- 비동기 컨텍스트 매니저 패턴 활용

```python
client = MultiServerMCPClient(mcp_config)
await client.__aenter__()
# 사용 후
await client.__aexit__(None, None, None)
```

## 결론
이 방식은 ThreadPoolExecutor보다 효율적이며, 스트림릿의 세션 상태를 활용해 이벤트 루프를 일관되게 관리합니다. 콜백 기능으로 실시간 UI 업데이트도 구현했습니다.