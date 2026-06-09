# the-abstract

> Weekly, AI-curated digests of the machine-learning papers worth your attention — plus a searchable Q&A app over everything it has ever read.

**the-abstract** is an open-source pipeline that ingests new ML papers from arXiv each week, filters out the noise with an LLM, fully parses and summarizes the useful ones, stores them with embeddings, and emails subscribers a personalized HTML digest. Every paper it has ever processed stays queryable through a RAG-powered web app.

> **Status:** early development. The product spec is in [`objective.md`](./objective.md); the architecture is settled and scaffolding is in progress.

## How it works

```
arXiv (cs.LG, cs.CL, cs.CV, …)
        ↓
classify  ──→ useful vs. noise        (cheap: title + abstract + authors)
        ↓ (useful only)
parse  ──→  text, figures, tables      (LlamaParse)
        ↓
categorize ──→ multi-label tags        (LLMs, Diffusion, RL, Agents, …)
        ↓
summarize ──→ short + long + takeaways
        ↓
store ──→ Postgres + pgvector (embeddings)
        ↓
   ┌──────────────────────┬─────────────────────────┐
weekly HTML email       Q&A web app (RAG)
(personalized)          search · filter · ask
```

Two stages of cost control: a cheap metadata classifier gates the expensive parse/summarize work, so only papers worth reading get the full treatment.

## Architecture

A monorepo built around **LlamaIndex Workflows** — everything that does work is a *step*, everything a step reaches for is a *client*.

```
backend/                     # Python: LlamaIndex Workflows + FastAPI
  src/arxiv_digest/
    workflows/   # ingest.py (weekly batch) · qa.py (on-demand RAG)
    steps/       # one self-contained folder per pipeline stage
    clients/     # arXiv, LLM, DB, LlamaParse — all external I/O
    api/         # FastAPI — thin layer the frontend talks to
    config.py
frontend/                    # Vite + React SPA
```

The weekly pipeline and the API are two entry points into the same package, sharing the database. See [`CLAUDE.md`](./CLAUDE.md) for the architecture rules.

## Tech stack

| Layer | Choice |
|---|---|
| Orchestration | [LlamaIndex Workflows](https://developers.llamaindex.ai/python/llamaagents/workflows/) |
| Parsing | LlamaParse (LlamaCloud) |
| LLM / embeddings | Configurable provider |
| Database | Supabase / Postgres + pgvector |
| API | FastAPI |
| Frontend | Vite + React (TypeScript) |
| Python tooling | uv · ruff · mypy |

## Getting started

> Setup is still being scaffolded. The intended flow:

```bash
git clone git@github.com:fede-bello/the-abstract.git
cd the-abstract

# backend — the weekly pipeline
cp .env.example .env        # add your API keys (arXiv, LLM, LlamaCloud, DB)
uv sync
uv run arxiv-digest ingest  # run the weekly pipeline once to populate the DB

# frontend — reads Supabase directly via the anon key (no API server needed to browse)
cd frontend
cp .env.example .env        # set VITE_SUPABASE_URL + VITE_SUPABASE_ANON_KEY
npm install && npm run dev
```

The frontend reads papers, weekly issues, and facets straight from Supabase — the `papers` table's row-level security allows read-only public access to this public arXiv-derived data. There is no API server: the backend is just the weekly pipeline, so the whole app hosts on Vercel (static SPA) + Supabase (DB), free.

The frontend shows empty states until `arxiv-digest ingest` has populated the database; after a run, papers appear across This week / Browse / Archive / paper detail.

Configuration — arXiv categories, the topic-tag list, schedule day, model names — lives in `config.py` / environment variables so you can adapt it without touching code.

### Weekly automation & email signup

`.github/workflows/weekly-digest.yml` runs `arxiv-digest ingest` every Monday (and on demand from the Actions tab). That one command ingests the week's papers *and* emails the digest — its last step. Add these repository secrets for it to run: `ANTHROPIC_API_KEY`, `LLAMA_CLOUD_API_KEY`, `SUPABASE_DB_URL`, `SUPABASE_URL`, `SMTP_USERNAME`, `SMTP_PASSWORD`. It uses the pay-per-token Anthropic API (`LLM_BACKEND=litellm`); to run on a Claude subscription instead, swap to a `CLAUDE_CODE_OAUTH_TOKEN` (`claude setup-token`) and `LLM_BACKEND=claude_code`.

Visitors join the mailing list from the footer signup form. Signup is **double opt-in**: it calls the `subscribe` Supabase Edge Function, which records a pending row and emails a confirmation link; the subscriber is only added once they click it. Every digest carries a one-click unsubscribe link. Three Edge Functions handle this — deploy them and set their secrets:

```bash
supabase functions deploy subscribe
supabase functions deploy confirm --no-verify-jwt       # opened from an email link (no auth)
supabase functions deploy unsubscribe --no-verify-jwt
supabase secrets set SMTP_USERNAME=... SMTP_PASSWORD=...  # reuses the digest's Gmail creds
```

Apply migrations `0001`–`0006` to your Supabase project. Emails stay private — the anon key can neither read the `subscribers` table nor write to it (signup goes through the service-role Edge Function).

## Contributing

Contributions welcome once the initial scaffold lands. Conventional-commit messages, `ruff`/`mypy` clean, and a green type-check on any frontend change.

## License

TBD — a `LICENSE` file will be added before the first release (likely MIT or Apache-2.0).
