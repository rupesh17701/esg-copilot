# ESG Copilot — Technology & Theory Reference

A study/interview-prep reference explaining **what** was used and **why**,
and the domain concepts behind them. Read this before an interview to
refresh talking points. For deployment/ops details, see `PROJECT_NOTES.md`;
for the user-facing project description, see `README.md`.

---

## 1. Domain theory: what is a BRSR report?

**BRSR (Business Responsibility and Sustainability Report)** is a disclosure
format mandated by **SEBI** (Securities and Exchange Board of India) for the
top 1,000 listed companies by market capitalization. It replaced the older,
less structured "Business Responsibility Report." Every BRSR filing has
three sections:

- **Section A — General Disclosures**: company identity, products, employee
  counts, CSR details.
- **Section B — Management and Process Disclosures**: whether/how the
  company has policies covering each of the nine NGRBC principles.
- **Section C — Principle-wise Performance**: the actual quantitative and
  qualitative disclosures, split into **Essential Indicators** (mandatory)
  and **Leadership Indicators** (voluntary, more advanced) for each
  principle.

### The 9 NGRBC Principles

NGRBC = **National Guidelines on Responsible Business Conduct**, issued by
India's Ministry of Corporate Affairs. BRSR Section C is structured around
nine of these principles:

| # | Principle | Roughly covers |
|---|---|---|
| 1 | Ethical, Transparent and Accountable Business Conduct | Anti-corruption, governance, whistleblower mechanisms |
| 2 | Safety and Sustainability of Goods and Services | Product lifecycle, sustainable sourcing |
| 3 | Employee and Worker Wellbeing | Health, safety, benefits, training |
| 4 | Stakeholder Interests | Grievance redressal, stakeholder engagement |
| 5 | Human Rights | Human rights policy, forced/child labor, harassment |
| 6 | Environment Protection and Restoration | **This is where carbon/energy/water/waste data lives** |
| 7 | Public and Regulatory Policy Engagement | Trade association membership, policy advocacy |
| 8 | Inclusive Growth and Equitable Development | CSR spend, community impact |
| 9 | Consumer Value and Responsibility | Product information, consumer complaints, data privacy |

This app's `NGRBC_PRINCIPLES` dict and `PrincipleDisclosure` model mirror
this structure directly.

### ESG and why it's scored the way it is

**ESG** = Environmental, Social, Governance — a framework investors and
regulators use to assess non-financial risk. A company can be financially
healthy but carry high ESG risk (e.g., heavy emitter with no transition
plan, weak board oversight, poor labor practices), which can translate into
regulatory, reputational, or capital-cost risk later.

This app scores each dimension 0–100 using a **transparent, rule-based**
method (see `esg_scoring.py`) rather than an opaque single number or an LLM
judgment call. Every point is traceable to a specific disclosed figure via
a `rationale` list. This is a deliberate choice: rule-based scoring is
**reproducible** (same input always gives same output), **auditable** (a
human can check the math), and **free to compute** (no API cost) — properties
that matter a lot for something claiming to assess *risk*.

### Carbon accounting: Scope 1, 2, 3

The GHG Protocol (the standard carbon accounting framework) splits emissions
into three "scopes":

- **Scope 1** — Direct emissions from sources the company owns/controls
  (e.g., fuel burned in company vehicles or boilers).
- **Scope 2** — Indirect emissions from purchased electricity, steam,
  heating/cooling.
- **Scope 3** — All other indirect emissions in the value chain (supplier
  emissions, employee commuting, product use, etc.). Almost always the
  largest scope and the hardest to measure — most companies, including the
  synthetic sample here, don't disclose it, which the app explicitly flags
  as an observation rather than silently treating as zero.

**Carbon intensity** (this app: tCO2e per INR crore of revenue) normalizes
absolute emissions by company size so a small and a large company in the
same sector can be compared fairly — a large company naturally emits more
in absolute terms without necessarily being less efficient.

---

## 2. Backend technology

### FastAPI

A modern, async-first Python web framework. Chosen over Flask/Django for:
automatic OpenAPI/Swagger docs generation from type hints (`/docs` route,
zero extra code), native async support, and tight integration with
**Pydantic** for request/response validation.

### Pydantic (v2)

Defines the app's data models (`schemas.py`) with runtime type validation.
Key concept used here: **`@computed_field`** — a property computed from
other fields that *is* included in JSON serialization (unlike a plain
`@property`, which is Python-only and silently disappears from the API
response — a real bug this project hit and fixed, see `PROJECT_NOTES.md`).

### SQLAlchemy + SQLite

SQLAlchemy is an ORM (Object-Relational Mapper) — Python classes map to
database tables, so most of the app never writes raw SQL. **SQLite** is a
file-based, serverless database — no separate DB server to run, which is
ideal for a single-instance demo but not for concurrent multi-user
production (a scaling limitation this project is upfront about; the fix
would be Postgres).

### pdfplumber

A Python library for extracting text (and tables) from PDF files. Used in
`pdf_parser.py` to turn an uploaded PDF into plain text before any analysis
happens. Real PDFs are mostly images/fonts/vector graphics under the hood —
`pdfplumber` only pulls out the actual text layer, which is why extracted
text is usually far smaller than the PDF file size.

### Regex-based structured extraction (the "offline" path)

`brsr_extractor.py` uses **regular expressions** to pull structured data
(company name, emissions figures, Yes/No policy answers) out of raw text.
This is a **heuristic** approach: fast, deterministic, needs no API key —
but brittle to phrasing variation compared to an LLM-based extraction. The
tradeoff is explicit and documented: every field defaults to `None` rather
than guessing, so a missed pattern degrades gracefully instead of producing
a wrong number.

### TF-IDF + cosine similarity (the RAG retrieval layer)

**RAG (Retrieval-Augmented Generation)** is the pattern of retrieving
relevant document snippets and feeding them to an LLM as context, so the
model answers *grounded in the actual document* instead of from memory
alone (which reduces hallucination).

This app's retrieval (`rag.py`) uses **TF-IDF** (Term Frequency–Inverse
Document Frequency) via scikit-learn, not embeddings:

- **TF** — how often a word appears in a chunk (more occurrences = more
  relevant to that chunk).
- **IDF** — how rare a word is across all chunks (common words like "the"
  get down-weighted; distinctive words like "Scope" or "emissions" get
  up-weighted).
- Each chunk becomes a vector of TF-IDF scores; the query becomes a vector
  the same way; **cosine similarity** measures the angle between vectors to
  rank chunks by relevance.

This was a deliberate choice over embeddings: it needs no API call and no
model download, so retrieval works identically whether or not an
`ANTHROPIC_API_KEY` is configured — a real architectural constraint (offline
mode must be fully functional), not just a cost-saving shortcut.

### The provider-agnostic LLM layer

`llm_client.py` defines an abstract `LLMClient` interface with two
implementations: `AnthropicLLMClient` (real Claude calls) and
`OfflineLLMClient` (deterministic templated/extractive fallback). This is
the **Strategy pattern** — the rest of the app (`agent.py`, the API routes)
depends only on the interface, never on which implementation is active. A
factory function (`get_llm_client()`) picks the implementation based on
whether an API key is configured. This is why adding a real key requires
zero code changes anywhere else.

### Anthropic Claude API

When a key is configured, the app calls **Claude Opus 5**
(`claude-opus-5`) via the official `anthropic` Python SDK for two things:
generating a narrative ESG risk summary, and answering free-text chat
questions grounded in the retrieved report excerpts. The system prompt
explicitly instructs the model to answer only from the given context and
say so plainly if the context doesn't contain the answer — reducing
hallucination risk on a tool meant to inform real financial/compliance
decisions.

---

## 3. Frontend technology

### React + TypeScript

Component-based UI library + a typed superset of JavaScript. TypeScript
catches a whole class of bugs (wrong field names, null/undefined mismatches
between what the API returns and what the UI expects) at compile time
instead of at runtime in a user's browser.

### Vite

The build tool and dev server. Chosen over older tooling (Create React App,
Webpack directly) for near-instant dev-server startup and hot-reload, using
native ES modules during development and Rollup for optimized production
bundles.

### Tailwind CSS

A utility-first CSS framework — styling is composed from small utility
classes (`rounded-lg`, `text-sm`) directly in markup rather than writing
separate CSS files. Configured here (`tailwind.config.js`) with a custom
color palette (see below) rather than Tailwind's defaults.

### Data visualization principles applied

The dashboard's colors aren't arbitrary — they follow a systematic method:
**categorical colors** (Environmental/Social/Governance dimension bars) are
assigned from a fixed, pre-validated color order chosen so adjacent colors
remain distinguishable under common forms of color blindness (deuteranopia/
protanopia); **status colors** (risk band: green/amber/red) are a separate,
reserved palette that's never reused for a regular data series, always
paired with an icon and text label so meaning never depends on color alone;
a **sequential** single-hue ramp is used for the one-series NGRBC principle
completeness bars. This matters for accessibility and for looking like a
deliberately designed product rather than default-styled output.

---

## 4. Infrastructure & DevOps

### Docker & multi-stage builds

Each service (`backend/Dockerfile`, `frontend/Dockerfile`) is a
self-contained, reproducible build. The frontend uses a **multi-stage
build**: one stage compiles the React app with Node (`npm run build`), then
only the compiled static output is copied into a much smaller final `nginx`
image — the Node toolchain itself never ships in the production image.

### nginx as a reverse proxy

nginx serves the built frontend's static files *and* forwards any request
under `/api/` to the backend container. This means the browser only ever
talks to one origin (the frontend's domain) — no CORS complexity, and the
backend never needs a public address at all (in the Railway deployment,
only the frontend has a public domain).

### DNS resolution inside containers — the hard-won lesson

`proxy_pass http://hostname:port` in nginx resolves that hostname **once**,
at nginx startup, and caches the IP for the container process's entire
lifetime. On a platform where a redeployed service gets a **new** private
IP each time (Railway does this), that stale cache silently breaks routing
the moment the backend is redeployed on its own — with no crash and no
obvious error, just connection timeouts. The fix: route `proxy_pass`
through an nginx variable plus an explicit `resolver` directive, forcing
re-resolution on every request. (Full story, plus a follow-on IPv6-bracket
gotcha it exposed, is in `PROJECT_NOTES.md`.) This is a genuinely useful
piece of infrastructure knowledge beyond this one project — the same
failure mode hits any nginx-in-front-of-a-dynamic-backend setup (Kubernetes
with rolling pod IPs, ECS, etc.).

### Railway (Platform-as-a-Service)

A PaaS that builds and runs containers from a Dockerfile without needing to
manage servers directly. Concepts used: **services** (backend and frontend
are separate services in one project), **private networking** (services
reach each other over an internal address like
`backend.railway.internal`, not the public internet), **volumes**
(persistent disk that survives redeploys — used here for the SQLite file
and uploaded reports), and **environment variables** scoped per service.

### Git & GitHub

Standard distributed version control. Notable here: authentication was done
via **OAuth device-code flow** (`gh auth login --web`) rather than a
password — the CLI displays a one-time code, you approve it in a browser
you're already logged into, and a scoped access token is issued. No
password ever touches a script or a chat session, which is the correct
pattern for any CLI/agent needing GitHub access.

---

## 5. Software engineering practices applied

- **Separation of concerns**: `services/` (business logic) is independent
  of `api/` (HTTP layer) is independent of `models/` (data shape) — each
  can be tested and reasoned about alone.
- **Dependency injection via FastAPI's `Depends`**: routes receive a
  database session (`get_db`) rather than constructing one themselves,
  which is what makes swapping in an in-memory test database
  (`tests/conftest.py`) possible without touching route code.
- **12-factor-style config**: all environment-specific values (API keys,
  database URL, CORS origins) come from environment variables /
  `.env` files, never hardcoded — the same code runs unchanged locally, in
  Docker Compose, and on Railway.
- **Test coverage for edge cases, not just happy paths**: e.g. "a document
  with missing data should return `None`, never a guessed value," "an
  unrelated document should be rejected, not silently scored."
- **Regression tests for bugs after fixing them** — e.g. the test asserting
  `disclosure_completeness` is present in the *serialized JSON*, not just
  accessible on the Python object, added specifically after that bug was
  found and fixed.

---

## 6. Key algorithms, explained

### ESG dimension scoring (`esg_scoring.py`)

Each dimension (Environmental/Social/Governance) is scored out of 100 as a
weighted sum of sub-scores: disclosure completeness for the relevant NGRBC
principles (40 points), plus several quantitative signals (renewable energy
%, safety incidents, board independence, etc.) each worth a fixed slice.
Missing data doesn't score zero — it scores a **neutral midpoint**, so an
undisclosed field is penalized less than a disclosed *bad* figure, which
is a deliberate fairness choice (silence isn't the same as a bad result,
but it isn't rewarded either).

### BRSR validity check (`assess_brsr_validity`)

Before running the full pipeline, the app checks whether the uploaded
document is plausibly a BRSR filing at all: either it contains a BRSR/NGRBC
title phrase, **or** at least 3 of the 9 "Principle N" sections are found
with substantial content (≥80 characters, to avoid matching a
table-of-contents one-liner). Either condition alone is sufficient — this
is a deliberately lenient **OR**, tuned to catch obviously unrelated
documents (a resume, an invoice) without false-rejecting a real filing that
happens to be formatted slightly differently.

### Carbon benchmark comparison (`carbon_intelligence.py`)

Computed carbon intensity is compared against a per-sector "typical range"
(a lookup table of indicative, not certified, midpoints) to classify a
company as below/within/above its sector's typical range — giving a
relative signal even though the absolute benchmark numbers are approximate.
