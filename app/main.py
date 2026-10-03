"""FastAPI application for the advanced assistant."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.agent import chat_agent
from app.config import (
    CORS_ORIGINS,
    client,
    DOCUMENTS_PATH,
    OPENWEATHER_API_KEY,
    STATIC_PATH,
    TAVILY_API_KEY,
)
from app.memory import clear_history, get_conversations, get_history, init_db
from app.rag import collection, ingest_documents


app = FastAPI(
    title="Advanced AI Chatbot",
    description="A memory-enabled assistant with tools, web search, and RAG.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_PATH)), name="static")


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=12000)


@app.on_event("startup")
def startup():
    init_db()
    # Re-indexing is safe because the RAG layer uses upsert.  Avoid doing a
    # network embedding request on every boot when no Gemini key is present.
    if client is not None and DOCUMENTS_PATH.exists():
        try:
            ingest_documents(str(DOCUMENTS_PATH))
        except Exception as error:
            # The assistant should remain available even if an optional index
            # cannot be refreshed during startup.
            print(f"RAG startup indexing skipped: {error}")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(str(STATIC_PATH / "index.html"))


@app.get("/health")
def health():
    return {
        "status": "ok",
        "services": {
            "gemini": client is not None,
            "weather": bool(OPENWEATHER_API_KEY),
            "web_search": bool(TAVILY_API_KEY),
            "knowledge_base": collection is not None,
        },
    }


@app.post("/chat")
def chat(request: ChatRequest):
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Message cannot be empty.")

    try:
        reply = chat_agent(request.session_id.strip(), message)
    except Exception as error:
        print(f"Chat request failed: {type(error).__name__}: {error}")
        raise HTTPException(
            status_code=503,
            detail="The assistant is temporarily unavailable. Please try again.",
        ) from error

    return {"reply": reply}


@app.get("/history/{session_id}")
def history(session_id: str):
    return {
        "history": [
            {"role": role, "message": message}
            for role, message in get_history(session_id)
        ]
    }


@app.get("/conversations")
def conversations():
    return {
        "conversations": [
            {"session_id": session_id, "title": title, "created_at": created_at}
            for session_id, title, created_at in get_conversations()
        ]
    }


@app.delete("/history/{session_id}")
def delete_history(session_id: str):
    clear_history(session_id)
    return {"message": "Chat history cleared."}
