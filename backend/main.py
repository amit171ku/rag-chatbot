import logging
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from chunking import chunk_text
from config import settings
from documents import ALLOWED_EXTENSIONS, EmptyDocumentError, extract_text
from rag import VectorStore, embed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chatbot")

SYSTEM_PROMPT = "You are a helpful, concise assistant."
GROUNDED_PROMPT = """You answer questions about the user's uploaded document: "{filename}".

Rules:
- Answer ONLY from the context below. Do not use outside knowledge.
- If the context does not contain the answer, reply exactly: "I couldn't find that in the document."
- Keep answers concise and specific to the document.

Context:
{context}
"""
TOP_K = 5

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

client = genai.Client(api_key=settings.gemini_api_key)
store = VectorStore()
app = FastAPI(title="Gemini Chatbot")


class Message(BaseModel):
    role: Literal["user", "model"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[Message] = Field(default_factory=list, max_length=50)

class Source(BaseModel):
    score: float
    text: str
    
class ChatResponse(BaseModel):
    reply: str
    grounded: bool = False
    sources: list[Source] = Field(default_factory=list)


@app.get("/api/health")
async def health():
    return {"status": "ok", "model": settings.gemini_model, "document": store.filename}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    system_prompt = SYSTEM_PROMPT
    grounded = False
    sources: list[Source] = []

    if store.ready:
        try:
            qvec = (await embed(client, [req.message], "RETRIEVAL_QUERY"))[0]
        except Exception:
            logger.exception("Query embedding failed")
            raise HTTPException(502, "Embedding error. Check server logs.")
        hits = store.search(qvec, TOP_K)
        context = "\n\n---\n\n".join(chunk for _, chunk in hits)
        system_prompt = GROUNDED_PROMPT.format(filename=store.filename, context=context)
        grounded = True
        sources = [Source(score=round(s, 3), text=c) for s, c in hits]

    contents = [
        types.Content(role=m.role, parts=[types.Part(text=m.content)])
        for m in req.history
    ]
    contents.append(types.Content(role="user", parts=[types.Part(text=req.message)]))

    try:
        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.2 if grounded else 0.7,
            ),
        )
    except Exception:
        logger.exception("Gemini request failed")
        raise HTTPException(502, "Upstream model error. Check server logs.")

    if not response.text:
        raise HTTPException(502, "Model returned an empty response.")

    return ChatResponse(reply=response.text, grounded=grounded, sources=sources)


@app.get("/api/search")
async def search(q: str, k: int = TOP_K):
    """Debug endpoint: test retrieval on its own, without Gemini generation."""
    if not store.ready:
        raise HTTPException(409, "No document uploaded yet.")
    qvec = (await embed(client, [q], "RETRIEVAL_QUERY"))[0]
    return [
        {"score": round(score, 3), "chunk": chunk}
        for score, chunk in store.search(qvec, min(k, 10))
    ]


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, f"Unsupported file type. Allowed: {sorted(ALLOWED_EXTENSIONS)}")

    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large (max 10 MB).")

    try:
        text = await run_in_threadpool(extract_text, ext, data)
    except EmptyDocumentError as e:
        raise HTTPException(422, str(e))
    except Exception:
        logger.exception("Failed to extract text from %s", filename)
        raise HTTPException(422, "Could not read this file. It may be corrupted or protected.")

    chunks = chunk_text(text)

    try:
        vectors = await embed(client, chunks, "RETRIEVAL_DOCUMENT")
    except Exception:
        logger.exception("Embedding failed for %s", filename)
        raise HTTPException(502, "Embedding failed. Check server logs (key, quota, model name).")

    store.set(filename, chunks, vectors)

    return {
        "filename": filename,
        "characters": len(text),
        "chunk_count": len(chunks),
        "embedded": True,
    }


# Must be mounted LAST so it doesn't shadow /api routes
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")