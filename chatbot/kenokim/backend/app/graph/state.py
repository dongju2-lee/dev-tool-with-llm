from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class GraphState(TypedDict):
    """LangGraph 표준 State schema"""
    messages: Annotated[list[BaseMessage], add_messages]


# 이전 호환성을 위한 별칭
AgentState = GraphState 