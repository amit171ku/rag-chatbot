import numpy as np
from google.genai import types

EMBED_MODEL = "gemini-embedding-001"
BATCH_SIZE = 100  # API limit per embed request


async def embed(client, texts: list[str], task_type: str) -> np.ndarray:
    """task_type: RETRIEVAL_DOCUMENT for chunks, RETRIEVAL_QUERY for questions."""
    vectors: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        res = await client.aio.models.embed_content(
            model=EMBED_MODEL,
            contents=texts[i : i + BATCH_SIZE],
            config=types.EmbedContentConfig(task_type=task_type),
        )
        vectors.extend(e.values for e in res.embeddings)

    arr = np.array(vectors, dtype=np.float32)
    arr /= np.linalg.norm(arr, axis=1, keepdims=True)  # normalize: dot product = cosine
    return arr


class VectorStore:
    """Single-document, in-memory store. A new upload replaces the old one."""

    def __init__(self):
        self.filename: str | None = None
        self.chunks: list[str] = []
        self.vectors: np.ndarray | None = None

    @property
    def ready(self) -> bool:
        return self.vectors is not None and len(self.chunks) > 0

    def set(self, filename: str, chunks: list[str], vectors: np.ndarray) -> None:
        self.filename, self.chunks, self.vectors = filename, chunks, vectors

    def search(self, query_vec: np.ndarray, k: int = 5) -> list[tuple[float, str]]:
        scores = self.vectors @ query_vec
        top = np.argsort(scores)[::-1][:k]
        return [(float(scores[i]), self.chunks[i]) for i in top]