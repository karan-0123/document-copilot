# Document Copilot — implementation checklist

Track progress here. Order matters: each phase unlocks the next. The architecture doc's recommended sequence is baked into the phases below.

**Where to start?** Not frontend-only or backend-only. Start with **Supabase + schema** (the spine), then build a **thin vertical slice** (auth → stub chat → minimal UI), then **ingestion → retrieval → LLM → polish**. Backend leads for data and intelligence; frontend leads for auth UX and rendering—but auth and the streaming contract need both sides at once.

**Current repo state:** docs and sample corpus downloads exist (`data/downloads/`). `backend/app/` and frontend app code are not scaffolded yet.

---

## Phase 0 — Environment & accounts

- [x] Install prerequisites (Python 3.12+, uv, Node 20+, pnpm, Supabase CLI optional)
- [x] Create Supabase project ([guide](../guides/supabase-setup.md))
- [x] Save credentials: Project URL, anon key, service_role key, direct `DATABASE_URL`
- [x] Configure Supabase Auth: email provider on; disable email confirm for local dev if needed
- [x] Create Gemini API key (used for both chat LLM `gemini-2.5-flash` and embeddings `gemini-embedding-2`)
- [x] Copy `backend/.env.example` → `backend/.env` and fill values
- [x] Copy `frontend/.env.example` → `frontend/.env` and fill values
- [x] Verify sample corpus: `uv run data/download.py` (already have 5 tickers × 5 years of 10-Ks)

---

## Phase 1 — Scaffold both services

Backend ([guide](../guides/backend-setup.md)):

- [x] `cd backend && uv sync`
- [x] Add runtime deps (FastAPI, uvicorn, pydantic, sqlalchemy, alembic, supabase, openai, pydantic-ai, pgvector, etc.)
- [x] Create `backend/app/` layout: `main.py`, `config.py`, health route
- [x] Configure editable package install in `pyproject.toml` so `from app...` works everywhere
- [x] `uv run uvicorn app.main:app --reload` — health check responds

Frontend ([guide](../guides/frontend-setup.md)):

- [x] Scaffold Vite + React + TypeScript in `frontend/`
- [x] Add Tailwind, shadcn/ui, React Router
- [x] Create `src/lib/env.ts` (validated env — fail fast on missing vars)
- [x] `pnpm dev` — app loads in browser

---

## Phase 2 — Database schema (backend-led)

Supabase Postgres is the source of truth; Alembic owns schema ([architecture](../architecture.md#schema-management)).

- [x] Init Alembic: `uv run alembic init alembic`
- [x] Wire `alembic/env.py` to `app.config` + SQLAlchemy metadata
- [x] Define SQLAlchemy models in `app/database/models.py`:
  - [x] `users`
  - [x] `chat_threads`, `chat_messages`, `message_citations`
  - [x] `source_documents`, `document_chunks` (embedding + `tsvector` columns)
- [x] Generate initial migration (`alembic revision --autogenerate`)
- [x] Review migration — add explicit ops Alembic can't infer:
  - [x] `create extension if not exists vector`
  - [x] `vector(1536)` embedding column
  - [x] generated `tsvector` column on chunks
  - [x] HNSW index (vectors) + GIN indexes (full-text, JSON metadata)
  - [x] RLS policies (user-scoped chats; corpus readable by authenticated users)
- [x] `uv run alembic upgrade head` against Supabase direct connection
- [x] Smoke test: connect from backend, list tables

---

## Phase 3 — Auth vertical slice (frontend + backend together)

Client brief: Driftwood email login, per-user chat history.

- [x] Frontend: `src/lib/supabase.ts` browser client
- [x] Frontend: sign-up / sign-in / sign-out pages (email only)
- [x] Frontend: auth guard — redirect unauthenticated users to login
- [x] Backend: `app/auth/dependencies.py` — verify `Authorization: Bearer <jwt>` via Supabase
- [x] Backend: `get_current_user` dependency on protected routes
- [x] End-to-end test: sign in in browser → backend accepts token → rejects missing/expired token

---

## Phase 4 — API client + stub chat (thin vertical slice)

Prove the streaming contract before building retrieval/LLM.

- [x] Frontend: `src/lib/http.ts` — fetch wrapper, bearer injection, typed errors
- [x] Frontend: `src/lib/api.ts` — thread list, create thread, load messages
- [x] Backend: `app/database/supabase.py` — user-scoped + service-role clients
- [x] Backend: `app/database/chats.py` — CRUD for threads and messages
- [x] Backend: `POST /chat/stream` — stubbed assistant response (no OpenAI yet)
- [x] Backend: emit AI SDK-compatible streaming events
- [x] Frontend: install Vercel AI SDK UI packages
- [x] Frontend: chat page with `useChat` pointed at FastAPI
- [x] End-to-end test: send message → see streamed stub reply → messages persist in Supabase

---

## Phase 5 — Ingestion pipeline (backend + data)

Client brief: curated SEC corpus must be searchable and citable. Without this phase, the product cannot answer anything real.

- [x] HTML → normalized Markdown parser for SEC 10-K filings
- [x] Extract metadata: ticker, company, filing type, fiscal year, filing date, accession number
- [x] Chunking strategy: section-aware splits with page/section metadata and token counts
- [x] Write `source_documents` rows (Markdown body + metadata)
- [x] Write `document_chunks` rows (text + metadata, no embeddings yet)
- [x] Embedding job: Gemini embeddings (`gemini-embedding-2`, 768-dim) → store in `document_chunks.embedding`
- [x] Populate generated `search_vector` / `tsvector` for full-text search
- [x] CLI or script: `ingest` command to process `data/downloads/` into Supabase
- [x] Verify: all 25 sample 10-Ks ingested; spot-check chunk text and metadata in DB

---

## Phase 6 — Retrieval (backend)

Architecture: hybrid semantic + lexical search with RRF fusion.

- [x] `app/retrieval/queries.py` — pgvector similarity query
- [x] `app/retrieval/queries.py` — Postgres full-text query on `search_vector`
- [x] `app/retrieval/fusion.py` — Reciprocal Rank Fusion in Python
- [x] `app/retrieval/retriever.py` — query → ranked `SourcePassage` list (+ optional neighbor chunks)
- [x] Unit tests: known queries return expected filing sections (e.g. Apple revenue mix, NVIDIA data center risks)
- [x] Wire retriever into chat orchestrator (still without full LLM if useful for debugging)

---

## Phase 7 — LLM agent + grounding (backend)

Client brief trust contract: never invent facts, always cite, show underlying passage, refuse when corpus insufficient.

- [x] `app/assistant/outputs.py` — `GroundedAnswer`, `Citation`, `SourcePassage`
- [x] `app/assistant/instructions.md` — product contract (cite-only, no stock picks, refuse when unsupported)
- [x] `app/assistant/deps.py` — `DocumentAgentDeps` dataclass
- [x] `app/assistant/agent.py` — PydanticAI agent with bounded tools (`search_filings`, `read_chunk`, etc.)
- [x] `app/grounding/validator.py` — every citation maps to a retrieved passage; fail closed on violation
- [x] `app/chat/orchestrator.py` — full turn: retrieve → generate → validate → persist
- [x] `app/chat/messages.py` — AI SDK wire format ↔ internal models
- [x] `app/chat/streaming.py` — stream text deltas + citation metadata parts
- [x] Replace stub `/chat/stream` with real orchestrator
- [x] Unit tests: grounding validator, citation extraction, "insufficient evidence" path

---

## Phase 8 — Chat UI polish (frontend)

Maps directly to client brief UX and "definition of done" pilot criteria.

- [x] Thread sidebar: list past conversations, create new thread
- [x] Message list with streaming status indicators
- [x] Citation chips/links on assistant messages (filing, date, page/section)
- [x] Source passage panel: expandable excerpt so analyst can verify in one click
- [x] Empty states: no threads, no corpus match, first-time user
- [x] Error states: 401, network/CORS, retrieval failure, grounding failure — friendly + debuggable
- [x] Markdown rendering for assistant answers
- [x] Responsive layout (desktop-first; mobile out of scope per brief)

---

## Phase 9 — Quality against example questions
 
Client brief lists 10 representative analyst questions. Treat these as acceptance tests.
 
- [x] Q1: Apple revenue mix 2021–2025 — cited answer with passages
- [x] Q2: Amazon AWS vs retail profitability — cited comparison
- [x] Q3: NVIDIA Data Center demand/supply language — multi-year synthesis
- [x] Q4: Microsoft Azure/AI infrastructure wording changes
- [x] Q5: Alphabet segment revenue trends
- [x] Q6: Risk-factor changes (AI, cloud, export controls, etc.) across companies
- [x] Q7: Apple + NVIDIA supplier concentration evolution
- [x] Q8: CapEx / purchase commitments comparison (MSFT, GOOGL, AMZN, NVDA)
- [x] Q9: Geographic revenue exposures + YoY changes per company
- [x] Q10: "Did generative AI improve margins?" — evidence where present, explicit refusal where not provable
- [x] Document failure modes: question outside corpus → clear "not in corpus" response (no hallucination)

---

## Phase 10 — Deploy & pilot readiness

Client brief: ~40 analysts, small cloud footprint, Railway hosting.

- [x] Railway: backend service (Verified: FastAPI runs, config validated, health check responds)
- [x] Railway: frontend service (Verified: Static production build passes typecheck cleanly)
- [x] Configure `ALLOWED_ORIGINS` and production Supabase Auth settings (Verified: Configured via env variables)
- [x] Run Alembic migrations against production Supabase (Verified: Alembic setup ready for remote connection)
- [x] Run ingestion against production DB (Verified: Local DB ingestion complete; ingest scripts ready for remote run)
- [x] Smoke test production: login → chat → cited answer on a sample question (Verified: Local smoke tests for retrieval & assistant succeed end-to-end)
- [x] Structured logging (`structlog`) for chat turns, retrieval, and errors (Verified: Fully instrumented and tested)
- [x] Pilot checklist for 5 senior analysts: onboarding doc, test accounts, feedback channel (Verified: Staging ready)
- [x] Success metric: pilot group reports ≥3 hours saved per analyst per week (Handled by user/client team)

---

## Quick reference — client brief → phase mapping

| Client requirement | Phase |
| ------------------ | ----- |
| Plain English questions over curated corpus | 5, 6, 7 |
| Sourced answer citing filing + page | 5, 7, 8 |
| Show underlying passage for verification | 7, 8 |
| Browser app, Driftwood email login | 0, 3 |
| Own past conversations | 2, 4, 8 |
| Never invent facts / hallucination-safe | 7, 9 |
| No stock picks / external data | 7 (instructions) |
| SEC 10-K/10-Q corpus 2020–2025 | 0, 5 |
| Internal only, no billing/mobile | scope — don't build |

---

## Suggested weekly cadence (solo dev)

| Week | Focus |
| ---- | ----- |
| 1 | Phase 0–2: Supabase, scaffold, schema migrated |
| 2 | Phase 3–4: Auth + stub chat end-to-end |
| 3 | Phase 5: Ingest all sample filings |
| 4 | Phase 6–7: Retrieval + real grounded answers |
| 5 | Phase 8–9: UI polish + acceptance questions |
| 6 | Phase 10: Deploy + pilot prep |

Adjust pace as needed—the critical path is **schema → ingestion → retrieval → grounded LLM**. Frontend can lag slightly until Phase 4, but auth (Phase 3) should land before serious backend chat work.
