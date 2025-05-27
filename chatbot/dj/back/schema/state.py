from typing_extensions import TypedDict, Annotated
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class DevToolState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    agent_mode: str