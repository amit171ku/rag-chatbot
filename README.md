# RAG Chatbot

Upload a PDF, DOCX, or TXT file and ask questions about it. Answers are grounded in the document and shown with the source chunks used.

**Live demo:** https://gemini-rag-chatbot-vgz7.onrender.com/ (free tier: the first load can take about a minute)

## Features

- Upload PDF, DOCX, and TXT files (up to 10 MB)
- Grounded answers: the model answers only from retrieved text, otherwise it replies "I couldn't find that in the document."
- Sources dropdown with similarity scores (hidden when the answer is not found)
- Chat history for follow-up messages
- Markdown rendering of answers, sanitized with DOMPurify
- `/api/search` debug endpoint to inspect retrieval without calling the LLM

## How it works

```
Upload   -> extract text -> strip repeated lines -> chunk (700 chars, 120 overlap)
         -> embed (Gemini) -> normalize -> store in memory (NumPy)

Question -> embed -> dot product (cosine) -> top 5 chunks
         -> grounded prompt -> Groq LLM -> answer + sources
```

## Stack

| Part | Technology |
|---|---|
| Backend | FastAPI (Python) |
| Embeddings | Gemini `gemini-embedding-001` |
| Generation | Groq `openai/gpt-oss-20b` (OpenAI-compatible API) |
| Retrieval | Normalized vectors + NumPy dot-product search |
| Frontend | Vanilla HTML, CSS, JavaScript (marked + DOMPurify) |
| Hosting | Render |

## Project structure

```
rag-chatbot/
├── backend/
│   ├── main.py          # FastAPI routes: /api/chat, /api/upload, /api/search, /api/health
│   ├── config.py        # Loads and validates environment variables
│   ├── documents.py     # Text extraction (PDF, DOCX, TXT)
│   ├── chunking.py      # Boilerplate stripping + overlapping chunks
│   ├── rag.py           # Embeddings + in-memory vector store
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
└── README.md
```

## Run locally

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env            # Windows: copy .env.example .env
uvicorn main:app --reload
```

Open http://localhost:8000, click **Upload**, then ask a question. 

### Environment variables (`backend/.env`)

```env
GEMINI_API_KEY=your_gemini_key      # embeddings
LLM_API_KEY=your_groq_key           # generation
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-20b
```

Get keys at https://aistudio.google.com/apikey (Gemini) and https://console.groq.com (Groq). Model availability varies by account, so pick a model your Groq key can call.

## Deploy on Render

| Setting | Value |
|---|---|
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Environment | the four variables above, plus `PYTHON_VERSION=3.12.3` |

## API

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/health` | Status, model name, loaded document |
| POST | `/api/upload` | Upload a file; extract, chunk, embed, store |
| POST | `/api/chat` | `{message, history}` returns `{reply, grounded, sources}` |
| GET | `/api/search?q=...` | Top chunks and scores, no LLM call |

## Design choices

- **Grounded prompt:** low temperature (0.2) and a fixed "not found" reply reduce hallucination.
- **Visible sources:** users can verify every answer against the retrieved chunks.
- **Boilerplate stripping:** repeated lines such as slide footers are removed before chunking, because they add noise to embeddings.
- **No vector database:** one document at a time, so brute-force NumPy search is simple and fast enough.
- **Safe rendering:** user text uses `textContent`; model Markdown is sanitized before insertion.

## Known limits

- One document at a time, shared by all visitors
- Vectors live in memory, so a restart or sleep loses the document
- Dense retrieval only (no keyword search or reranking)
- Follow-up questions are embedded as typed (no query rewriting)
- Scanned PDFs are not supported (no OCR)
- Free-tier API quotas apply

## Roadmap

- [ ] Evaluation script (hit@k) to compare chunk sizes and settings
- [ ] Query rewriting for follow-up questions
- [ ] Per-session stores and persistence (Chroma)
- [ ] Offline mode with local models
