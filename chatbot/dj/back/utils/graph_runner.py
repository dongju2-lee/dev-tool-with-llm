import asyncio
import logging

from langgraph.checkpoint.memory import MemorySaver
from langfuse.callback import CallbackHandler
from langchain_core.messages import HumanMessage

from graphs.supervisor import build_supervisor_graph

logger = logging.getLogger("runner")
logging.basicConfig(level=logging.INFO)
memory = MemorySaver()


class GraphRunner:
    def __init__(self) -> None:

        self._graph = build_supervisor_graph().compile(checkpointer=memory)
        self._lock = asyncio.Lock()
        self.langfuse_handler = CallbackHandler(
            public_key="",
            secret_key="",
            host="",
        )

    async def ask(
        self, *, session_id: str, user_input: str, agent_mode: str
    ) -> str:
        logger.info(
            f"GraphRunner received user input: {user_input} "
            f"for session: {session_id}"
            f"system mode : {agent_mode}"
        )
        state = {
            "messages": [],
            "agent_mode": agent_mode,
        }

        # callbacks = []

        async with self._lock:
            try:
                state["messages"].append(HumanMessage(content=user_input))
                final_state = await self._graph.ainvoke(
                    input=state,
                    config={
                        "callbacks": [self.langfuse_handler],
                        "configurable": {"thread_id": session_id},
                    },
                )

            except Exception as e:
                logger.error(f"Graph execution error: {e}")
                raise

        response = final_state["messages"][-1].content
        logger.info(f"response: { response}")

        return response