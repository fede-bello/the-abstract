# the-abstract

> Weekly, AI-curated digests of the machine-learning papers worth your attention.

**the-abstract** is an open-source pipeline that ingests new ML papers from arXiv each week, filters out the noise with an LLM, fully parses and summarizes the useful ones, stores them with embeddings, and emails subscribers a personalized HTML digest. A lightweight web app lets anyone browse everything it has processed, by week and by topic.

> **Status:** the weekly pipeline runs in production via a GitHub Actions cron and emails subscribers; the web app browses the results. A RAG-powered Q&A layer over the corpus is on the roadmap — see [`objective.md`](./objective.md) for the full product spec.

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
weekly HTML email        web app
(personalized)           browse · archive · topics
```

Two stages of cost control: a cheap metadata classifier gates the expensive parse/summarize work, so only papers worth reading get the full treatment.

## Architecture

A monorepo built around **LlamaIndex Workflows** — everything that does work is a *step*, everything a step reaches for is a *client*. There is no API server.

```
backend/                     # Python: the weekly LlamaIndex Workflows pipeline
  src/arxiv_digest/
    workflows/   # digest.py — the explicit pipeline: every @step method, in order
    steps/       # one self-contained folder per pipeline stage
    clients/     # arXiv, LLM, DB, LlamaParse — all external I/O
    config.py
frontend/                    # Vite + React SPA — reads Supabase directly via the anon key
supabase/                    # migrations + double-opt-in Edge Functions (subscribe/confirm/unsubscribe)
```

The backend is purely the weekly pipeline: it writes to Supabase, and the SPA reads it directly via the anon key + row-level security (papers are public arXiv-derived data). The whole thing hosts on Vercel (static SPA) + Supabase (DB) for free. See [`CLAUDE.md`](./CLAUDE.md) for the architecture rules.

## Tech stack

| Layer | Choice |
|---|---|
| Orchestration | [LlamaIndex Workflows](https://developers.llamaindex.ai/python/llamaagents/workflows/) |
| Parsing | LlamaParse (LlamaCloud) |
| LLM / embeddings | Configurable provider (Claude subscription by default) |
| Database | Supabase / Postgres + pgvector |
| Newsletter | Supabase Edge Functions (Deno) |
| Frontend | Vite + React (TypeScript) |
| Python tooling | uv · ruff · mypy |

## Getting started

Prerequisites: [`uv`](https://docs.astral.sh/uv/), Node, and accounts for Supabase, LlamaCloud, and an SMTP sender — plus a Claude subscription (default) or an LLM API key.

```bash
git clone git@github.com:fede-bello/the-abstract.git
cd the-abstract

# backend — the weekly pipeline
cp .env.example .env        # add your secrets (LLM, LlamaCloud, Supabase DB, SMTP)
uv sync
uv run arxiv-digest ingest  # run the weekly pipeline once to populate the DB (and email the digest)

# frontend — reads Supabase directly via the anon key (no API server needed to browse)
cd frontend
cp .env.example .env        # set VITE_SUPABASE_URL + VITE_SUPABASE_ANON_KEY
npm install && npm run dev
```

The frontend reads papers, weekly issues, and facets straight from Supabase — the `papers` table's row-level security allows read-only public access to this public arXiv-derived data.

The frontend shows empty states until `arxiv-digest ingest` has populated the database; after a run, papers appear across This week / Browse / Archive / paper detail.

Configuration — arXiv categories, the topic-tag list, model names, the public site URL — lives in [`config.toml`](./config.toml) (non-secret) and environment variables (secrets), so you can adapt it without touching code. The schedule lives in the GitHub Actions workflow below.

### Weekly automation & email signup

`.github/workflows/weekly-digest.yml` runs `arxiv-digest ingest` every Monday (and on demand from the Actions tab). That one command ingests the week's papers *and* emails the digest — its last step. Add these repository secrets for it to run: `CLAUDE_CODE_OAUTH_TOKEN`, `LLAMA_CLOUD_API_KEY`, `SUPABASE_DB_URL`, `SUPABASE_URL`, `SMTP_USERNAME`, `SMTP_PASSWORD`.

By default the LLM runs on your **Claude subscription** — no API key. Generate the token once with `claude setup-token` and store it as `CLAUDE_CODE_OAUTH_TOKEN`; the workflow installs the `claude` CLI and sets `LLM_BACKEND=claude_code`. To use a pay-per-token API instead (Anthropic, OpenAI, …), set `LLM_BACKEND=litellm`, point the model strings in `config.toml` at that provider (e.g. `openai/gpt-4o-mini`), and supply `LLM_API_KEY` instead of the OAuth token — no code change.

Visitors join the mailing list from the footer signup form. Signup is **double opt-in**: it calls the `subscribe` Supabase Edge Function, which records a pending row and emails a confirmation link; the subscriber is only added once they click it. Every digest carries a one-click unsubscribe link. Three Edge Functions handle this — deploy them and set their secrets:

```bash
supabase functions deploy subscribe
supabase functions deploy confirm --no-verify-jwt       # opened from an email link (no auth)
supabase functions deploy unsubscribe --no-verify-jwt
supabase secrets set SMTP_USERNAME=... SMTP_PASSWORD=...  # reuses the digest's Gmail creds
```

Apply migrations `0001`–`0006` to your Supabase project. Emails stay private — the anon key can neither read the `subscribers` table nor write to it (signup goes through the service-role Edge Function).

## Contributing

Contributions welcome. Conventional-commit messages (no scope parens, no `Co-Authored-By` trailer), `ruff`/`mypy` clean on the backend, and a green type-check on any frontend change:

```bash
uv run ruff check backend && uv run mypy backend   # backend
npm --prefix frontend run typecheck                # frontend
```

## License

Released under the [MIT License](./LICENSE).
