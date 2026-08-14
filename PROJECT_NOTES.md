# ESG Copilot — Project Reference

Personal reference notes: where everything lives, how to run/redeploy it, and
a log of the non-obvious issues hit while deploying. Not meant for public
consumption — the public-facing docs are in `README.md`.

## Links

| What | Where |
|---|---|
| **Live app** | https://frontend-production-47ba.up.railway.app |
| **GitHub repo** | https://github.com/rupesh17701/esg-copilot (public) |
| **Railway project** | "esg-copilot" under Rupesh Mishra's Projects workspace |
| **Railway dashboard** | https://railway.com/project/e2a1d89c-2b49-4f92-b184-52b023a624c8 |

## Accounts used

- **GitHub**: `rupesh17701` — logged in via device-code browser flow (no password ever shared with any tool).
- **Railway**: `Rupesh Mishra` (mrupesh060@gmail.com) — same device-code flow.

Both logins are stored locally as CLI credentials, not passwords:
- GitHub CLI: `gh auth status` to check, `gh auth login` to re-auth if it expires.
- Railway CLI: `railway whoami` to check, `railway login` to re-auth if it expires.

## Local development

```bash
# Backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Add `ANTHROPIC_API_KEY` to `backend/.env` to
enable real Claude responses instead of offline mode.

### Run the tests

```bash
cd backend && source venv/bin/activate && pytest -q
```

### Run the full stack in Docker (matches production topology)

```bash
docker compose up --build
```

## Redeploying to Railway

The CLI is installed at `~/.local/bin/gh` and via
`npm install -g --prefix ~/.local @railway/cli` (binary at
`~/.local/bin/railway`). Both need `export PATH="$HOME/.local/bin:$PATH"`.

```bash
cd ~/AI-Projects/esg-copilot

# Backend changed:
railway service link backend
railway up ./backend --path-as-root --service backend

# Frontend changed:
railway service link frontend
railway up ./frontend --path-as-root --service frontend
```

**Important:** if you only redeploy the backend, the frontend's nginx now
re-resolves the backend's address per-request (see the DNS caching bug
below) — so this is safe on its own. Before the fix below, a backend-only
redeploy would silently break the whole app.

## Environment variables (set on Railway)

| Service | Variable | Value | Why |
|---|---|---|---|
| backend | `ANTHROPIC_MODEL` | `claude-opus-5` | Model to use if a key is added |
| backend | `ANTHROPIC_API_KEY` | *(unset)* | Add to enable real Claude responses |
| backend | `STORAGE_DIR` | `/app/db` | Railway allows one volume per service; this makes the SQLite DB and uploaded files share it |
| frontend | `BACKEND_HOST` | `backend.railway.internal` | Private network address of the backend service |
| frontend | `BACKEND_PORT` | `8000` | Port the backend listens on |
| frontend | `BASIC_AUTH_USER` / `BASIC_AUTH_PASSWORD` | *(unset)* | Left open intentionally — see README § Deployment |

## Bugs hit and fixed during deployment (useful history / interview talking points)

1. **nginx computed properties missing from API JSON.** `disclosure_completeness` was a plain Python `@property` on a Pydantic model — worked fine server-side, but silently dropped from the serialized JSON response, so the frontend saw `undefined` and crashed. Fixed with `@computed_field`. Caught by an actual browser test, not just backend unit tests — added a regression test asserting the field is present in the API response, not just accessible in Python.
2. **Offline chat answer truncated before the useful part.** The offline (no-API-key) chat mode built a context string of `<metrics summary> + <retrieved excerpts>` and truncated it at a fixed length — which cut off the actual answer behind the metrics preamble. Fixed by leading with the excerpts.
3. **nginx 1MB upload limit silently rejecting real PDFs.** nginx defaults `client_max_body_size` to 1MB. Real BRSR PDFs are often several MB, so nginx was killing the connection before the file ever reached the backend — the browser only showed a bare "Failed to fetch" with no real error. Raised to 50M.
4. **O(n²) string concatenation in principle extraction.** `extract_principles()` built up per-principle text by repeated `+=` in a loop, which is quadratic and could hang on documents with unusually many "Principle N" header matches. Fixed with list-append + single join.
5. **Railway CLI only allows one volume per service.** Originally tried mounting separate volumes for the SQLite DB and uploaded files; the CLI rejected the second one. Consolidated both under one `STORAGE_DIR` env var.
6. **The big one — nginx caching a stale backend IP.** `proxy_pass http://backend.railway.internal:8000` resolves that hostname *once*, when nginx starts, and caches the IP for the container's entire lifetime. Railway assigns a **new private IP** to a service on every redeploy. So: redeploy the backend alone (without also restarting the frontend), and nginx keeps sending traffic to the old, now-dead IP — the app goes down with no crash, no error in either service's logs, just connection timeouts. This is what caused the confusing "sometimes it works, sometimes it just hangs" behavior. Fixed by routing `proxy_pass` through an nginx variable plus an explicit `resolver` directive (reading the container's real nameserver from `/etc/resolv.conf` at startup), which forces nginx to re-resolve on every request instead of caching indefinitely.
   - Side effect of that fix: nginx stops doing its automatic "replace the location prefix" URI rewrite once `proxy_pass` targets a variable — so the literal `/api/` I'd written in the proxy_pass target was doubling up into `/api/api/...` and 404ing. Removed it; the original request URI passes through unchanged with a variable-based proxy_pass.
7. **Uploads not actually being BRSR reports.** The pipeline would happily "analyze" any PDF/text file — a resume, an invoice, anything — and produce a low-quality but plausible-looking score. Added a pre-check (`assess_brsr_validity`) that rejects anything without either the BRSR/NGRBC title phrase or at least 3 substantial "Principle N" sections, with a clear 422 explaining why, before any scoring runs.
8. **IPv6 resolver address broke the DNS-caching fix above.** After fixing #6, the very next frontend deploy 502'd completely — nginx was crash-looping. Root cause: Railway's internal DNS resolver is an IPv6 address (`fd12::10`), and nginx's `resolver` directive requires IPv6 addresses in square brackets (`[fd12::10]`) or it misparses the address's own colons as a port separator and refuses to start. Fixed by bracketing any resolver IP containing a colon before writing it into the nginx config. Verified this one with `docker run --entrypoint sh ... nginx -t` against a config generated from a mocked IPv6 nameserver — actually proving nginx accepts the syntax — rather than just redeploying and hoping, after getting burned by declaring the previous two fixes done based on partial checks.

## Design decisions worth remembering

- **No login on the public deployment** — deliberate, so the link is
  frictionless for recruiters (this app is part of a placement/portfolio
  push). `BASIC_AUTH_USER`/`PASSWORD` support exists in nginx if that
  changes later — see README § Deployment.
- **Offline-first LLM layer** — the app is fully functional with zero
  external API calls; Claude is additive, not required. Useful both for
  cost control and for demoing without needing to manage a key.
- **SQLite, not Postgres** — fine for a single-instance portfolio demo;
  would need to change for real multi-user concurrent use.
