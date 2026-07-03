# AI Conversation Studio

An AI Conversation Studio for enterprise teams to manage knowledge sources, test prompts against assistants, evaluate response quality (relevance, groundedness, hallucination risk), collect feedback, govern risky responses, and track quality analytics over time.

Built for the [Hackathon Name] — Challenge 4: AI Conversation Studio.

## Team

- **Team name:** _[fill in]_
- **Members:** Sneh Patel, Parth Shah
- **College:** CHARUSAT / DEPSTAR

## Technology stack

- **Frontend:** Streamlit (Python)
- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL
- **Charts:** Plotly
- **LLM layer:** Mocked (deterministic, explainable, swappable — see below)

## Why this stack

Given a 24-hour window, we chose an all-Python stack (Streamlit + FastAPI) to maximize build speed while keeping backend and frontend cleanly separated behind a REST API — so the backend could be swapped to power a React frontend later without any rework.

## Build & run instructions

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Postgres

Easiest via Docker:

```bash
docker compose up -d
```

This starts Postgres on `localhost:5432` with database `ai_conversation_studio`,
user `studio_user`, password `studio_pass` (see `docker-compose.yml`).

No Docker? Point `DATABASE_URL` at any Postgres instance you already have —
just create an empty database first (`createdb ai_conversation_studio`).

Then, in `backend/`, copy the env template and adjust if needed:

```bash
cd backend
cp .env.example .env
```

`database.py` reads `DATABASE_URL` from the environment (via `.env`) and
falls back to `postgresql://postgres:postgres@localhost:5432/ai_conversation_studio`
if unset.

### 3. Start the backend

```bash
cd backend
python seed_data.py     # populates demo knowledge sources + assistants
uvicorn main:app --reload --port 8000
```

Backend runs at `http://localhost:8000`. Interactive API docs at `http://localhost:8000/docs`.
`init_db()` runs automatically on startup and creates all tables if they don't exist yet.

### 4. Start the frontend (in a new terminal)

```bash
cd frontend
streamlit run app.py
```

Frontend opens at `http://localhost:8501`.

## Project structure

```
ai-conversation-studio/
├── docker-compose.yml    # Local Postgres for development
├── backend/
│   ├── main.py            # FastAPI app + all API routes
│   ├── database.py        # PostgreSQL connection + schema (psycopg2)
│   ├── .env.example        # DATABASE_URL template
│   ├── models.py          # Pydantic request/response models
│   ├── knowledge.py       # Simulated retrieval (keyword-overlap based)
│   ├── mock_llm.py        # Mock LLM response generation
│   ├── evaluation.py      # Rule-based evaluation engine
│   └── seed_data.py       # Demo data loader
├── frontend/
│   ├── app.py             # Home / overview
│   ├── api_client.py      # Shared HTTP client
│   └── pages/
│       ├── 1_Playground.py         # Test prompts, see evaluated responses
│       ├── 2_Knowledge_Base.py     # Manage knowledge sources
│       ├── 3_Evaluation_History.py # Browse all past conversations
│       ├── 4_Governance.py         # Review flagged responses
│       └── 5_Analytics.py          # Quality trends dashboard
└── requirements.txt
```

## Real LLM + real retrieval

This is a working RAG (retrieval-augmented generation) system, not just a mock:

- **Retrieval** uses TF-IDF cosine similarity (`backend/knowledge.py`) over real or manually-entered knowledge sources — a genuine, explainable retrieval technique that works offline (important for unreliable venue wifi).
- **Generation** calls Google Gemini (`gemini-2.5-flash`) live via `backend/llm_service.py` when an API key is configured in the **Settings** page. Get a free key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) — no credit card required.
- **Graceful degradation**: if no key is set, or the real call fails for any reason (bad key, rate limit, no internet), the system automatically falls back to a deterministic mock generator so a live demo never hard-crashes. Every conversation is tagged with `generation_mode`: `real`, `mock`, or `mock_fallback`, and the fallback reason is preserved for debugging — this is itself a piece of the governance/explainability story.
- **Real documents**: upload PDF or `.txt` files in the Knowledge Base page — they're parsed, chunked, and immediately retrievable, alongside manual text entries.
- **Evaluation** is still rule-based (TF-IDF cosine similarity between each response sentence and the retrieved sources), not another LLM call — this keeps every score deterministic, free, and fully explainable regardless of whether the response came from the real model or the mock.

## Key assumptions

1. **Chunking is simple word-count based** (~150 words/chunk), not semantic chunking — a documented trade-off for the build window.
2. **Settings/API key storage is a local JSON file**, not a secrets manager — fine for a single-user hackathon demo, called out as a security trade-off.
3. **Single-tenant, no auth** — out of scope for the hackathon window; noted as future work.
4. **TF-IDF retrieval, not dense embeddings** — chosen for reliability (no model download, no internet dependency) over the marginal quality gain of embeddings at hackathon scale. The retrieval interface is designed so `knowledge.py` can be swapped for a vector DB without touching any consumer.

## Future enhancements

- Dense embedding-based retrieval (sentence-transformers + pgvector/Pinecone) for semantic (not just lexical) matching
- LLM-as-judge evaluation layer alongside the rule-based one
- Multi-assistant side-by-side comparison in the Playground
- Role-based access control for governance reviewers
- Prompt versioning and A/B testing
- ~~Postgres instead of SQLite for concurrent multi-user access~~ — done; see `backend/database.py`
- Proper secrets manager instead of a local JSON settings file
- Support for additional LLM providers (OpenAI, Anthropic) behind the same interface
- Connection pooling (e.g. `psycopg2.pool` or PgBouncer) for production-scale concurrent load
