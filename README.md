# ESG Copilot

AI agent for BRSR analysis, ESG risk, and carbon intelligence.

**Live demo:** https://frontend-production-47ba.up.railway.app
**Source:** https://github.com/rupesh17701/esg-copilot

The demo is deployed open (no login) so it's frictionless to click through —
see [Deployment](#deployment) for the tradeoffs and how to lock it down.

ESG Copilot ingests a company's BRSR (Business Responsibility and
Sustainability Report — SEBI's mandated disclosure format for India's top
listed companies), extracts structured data across all nine NGRBC principles,
computes a transparent ESG risk score, analyzes carbon emissions against
sector benchmarks, and lets you ask an AI agent questions about the report.

**It works fully offline out of the box.** Extraction, scoring, and carbon
analysis are deterministic and need no API key. Add an `ANTHROPIC_API_KEY`
to unlock AI-generated narrative summaries and direct conversational answers
in the chat panel — everything else is unchanged.

## What it does

- **BRSR parsing** — uploads a PDF or text BRSR filing and extracts company
  metadata, per-principle disclosure completeness (Section C, all 9 NGRBC
  principles), and quantitative environmental/social/governance indicators.
- **ESG risk scoring** — a transparent, rule-based 0–100 score per dimension
  (Environmental / Social / Governance) with a plain-language rationale for
  every point awarded, plus an overall risk band (Low/Moderate/Elevated/High).
- **Carbon intelligence** — Scope 1/2/3 emissions summary, carbon intensity
  per unit revenue, and a comparison against indicative sector benchmarks.
- **AI copilot chat** — ask questions about the uploaded report; answers are
  grounded via retrieval (TF-IDF) over the report text plus the computed
  metrics. Claude-generated when a key is configured, extractive/templated
  otherwise — never fabricated.

## Architecture

```
backend/   FastAPI + SQLAlchemy (SQLite) + pdfplumber + scikit-learn
  app/services/
    pdf_parser.py          raw text extraction + chunking
    brsr_extractor.py      regex-based structured extraction (offline path)
    esg_scoring.py         rule-based ESG dimension scoring
    carbon_intelligence.py emissions summary + sector benchmarking
    rag.py                 TF-IDF retrieval over report chunks
    llm_client.py          pluggable LLM: AnthropicLLMClient | OfflineLLMClient
    agent.py                retrieval + metrics + LLM -> chat / summary
  app/api/                 upload, report detail, chat endpoints

frontend/  React + TypeScript + Vite + Tailwind
  src/components/          score gauge, dimension bars, carbon panel,
                            principle completeness list, chat, upload

samples/   Synthetic BRSR report for testing (SEBI-format, 9 principles)
```

The LLM layer is provider-agnostic by design: `app/services/llm_client.py`
defines an `LLMClient` interface with two implementations. Nothing else in
the codebase — routes, scoring, RAG — knows or cares which one is active.

## Quick start

### Option A — Docker Compose (recommended)

```bash
cp .env.example .env        # optionally add your ANTHROPIC_API_KEY
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000 (docs at `/docs`)

### Option B — run locally

**Backend:**

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # optionally add your ANTHROPIC_API_KEY
uvicorn app.main:app --reload --port 8000
```

**Frontend** (separate terminal):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api` to
`localhost:8000`.

### Try it

Upload `samples/greenfield_textiles_brsr_fy24.txt` — a synthetic BRSR filing
for a fictional textiles company — to see the full pipeline: score gauge,
dimension breakdown, carbon intelligence, principle-by-principle disclosure
completeness, and chat.

## Enabling Claude

Without `ANTHROPIC_API_KEY` set, the app runs in **offline mode**: the
dashboard, scoring, and carbon analysis are identical (they're deterministic
either way), but the "Generate summary" button and chat produce templated /
extractive output instead of a generated one, and the UI shows an "Offline
mode" badge.

Set `ANTHROPIC_API_KEY` (in `.env` for Docker, or `backend/.env` for a local
run) and restart the backend — the badge switches to "Claude connected" and
the summary/chat endpoints start calling `claude-opus-5` (configurable via
`ANTHROPIC_MODEL`).

## Testing

```bash
cd backend
source venv/bin/activate
pytest -q
```

26 tests cover extraction (including "missing data stays `None`, never
guessed"), scoring bounds and edge cases, carbon benchmarking, the offline
LLM fallback, RAG retrieval, and the full API flow (upload → score → chat →
delete) against an in-memory database.

## Deployment

The live demo runs on [Railway](https://railway.app) as two services from
this repo's Dockerfiles:

- **`backend`** — FastAPI, private networking only (no public URL). One
  persistent volume mounted at `/app/db`; `STORAGE_DIR=/app/db` tells the app
  to keep both the SQLite file and uploaded reports under that single mount
  (see `app/config.py` — hosts that allow more than one volume per service
  can instead set two docker-compose-style mounts and leave `STORAGE_DIR`
  unset).
- **`frontend`** — nginx serving the built React app and reverse-proxying
  `/api/*` to the backend over Railway's private network
  (`BACKEND_HOST=backend.railway.internal`). This is the only service with a
  public domain.

**Auth:** nginx supports HTTP Basic Auth for the whole app (frontend +
proxied API) via `BASIC_AUTH_USER` / `BASIC_AUTH_PASSWORD` env vars — see
`frontend/docker-entrypoint.sh`. Unset (as on the live demo above) means the
app is fully open, which is the intentional tradeoff for a portfolio/demo
deployment where the goal is a zero-friction link. Set both vars on the
`frontend` service to require a login before making a long-lived deployment
public.

To redeploy after a change, from the repo root with the Railway CLI linked
to this project:

```bash
railway up ./backend --path-as-root --service backend
railway up ./frontend --path-as-root --service frontend
```

## Design notes / limitations

- **Extraction is heuristic, not perfect.** `brsr_extractor.py` uses regex
  patterns tuned against the SEBI BRSR format's common phrasing. Real-world
  filings vary in wording; a field that isn't found is left `None` rather
  than guessed. This is the offline extraction path — the sample report is
  written to demonstrate it cleanly, and it degrades gracefully (partial
  data still produces a valid, honestly-partial score).
- **Sector carbon benchmarks are indicative**, not certified — assembled as
  rough order-of-magnitude midpoints for the MVP. Flagged as such in the UI
  and in `carbon_intelligence.py`'s docstring.
- **ESG scoring is rule-based and fully transparent** — every point is
  traceable to a specific disclosed figure via the `rationale` list returned
  alongside each dimension score. This is a deliberate choice over an
  LLM-scored approach: reproducible, auditable, and free to compute.
- **RAG uses TF-IDF, not embeddings** — keeps retrieval working identically
  with or without an API key, no network call, no extra cost.
