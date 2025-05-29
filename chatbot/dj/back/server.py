import uuid
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from utils.graph_runner import GraphRunner

import logging

logger = logging.getLogger("server")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Async Cooking Assistant")
runner = GraphRunner()


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    agent_mode: str


class ChatResponse(BaseModel):
    session_id: str
    response: str
    # agent_mode: str


@app.get("/health")
async def health_check():
    """서버 상태 확인"""
    return {
        "status": "healthy",
        "service": "chatbot",
        "graph_runner_ready": runner is not None
    }


@app.post(
    "/ask", response_model=ChatResponse, summary="Process chat messages"
)
async def ask(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message is empty")
    logger.info(f"ask request: {req}")
    session = req.session_id or str(uuid.uuid4())
    try:
        answer = await runner.ask(
            session_id=session,
            user_input=req.message,
            agent_mode=req.agent_mode,
        )
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    return ChatResponse(session_id=session, response=answer)


if __name__ == "__main__":  # pragma: no cover
    uvicorn.run("server:app", host="0.0.0.0", port=8800, reload=True)