# CLAUDE.md

**the-abstract** — an open-source weekly arXiv ML Digest pipeline. See `objective.md` for the full product spec.

## Most important rule: use the skills, and keep them current

This project leans on skills instead of repeating instructions here. **Before doing a task, check whether a skill covers it and use it.** When the project's conventions, architecture, or tooling change, **update the relevant skill in the same change** — a stale skill is worse than none. New recurring workflow → consider adding a skill (`/skill-creator`).

| Task | Skill |
|---|---|
| Review changes before shipping | `/review` |
| Commit, push, open a PR | `/ship` |
| Write/refactor/review Python (backend) | `python-code-quality` |
| Write/refactor/review pytest tests | `python-unit-tests` |
| Build/debug event-driven pipeline steps | `llamaindex-workflows` |
| RAG / indexing / retrieval (Q&A) | `llamaindex-framework` |
| Parse PDFs, extract structured data | `llamacloud` |
| FastAPI endpoints & Pydantic models | `fastapi` |
| Postgres / pgvector schema & queries | `supabase-postgres-best-practices` |
| React (frontend) performance & patterns | `vercel-react-best-practices` |

If you change how the pipeline is structured, how we commit, or what the toolchain is, edit `/review` and `/ship` to match.

## Architecture (the one rule that shapes everything)

Monorepo. The backend is organized around **LlamaIndex Workflows**: everything that *does work* is a step; everything a step *reaches for* is a client.

```
backend/src/arxiv_digest/
├── workflows/   # digest.py (qa.py later) — the explicit pipeline: every @step METHOD here, in order
├── steps/<stage>/   # step.py = pure async logic fn; events.py = the stage's event class
├── clients/     # llm.py, db.py, arxiv.py, parse.py — ALL external I/O lives here
├── api/         # FastAPI — thin HTTP layer over the workflows
└── config.py    # env-driven config
frontend/        # Vite + React SPA — talks to the API only
```

- **The workflow file is the orchestration hub.** `DigestWorkflow` in `workflows/digest.py` holds every stage as a `@step` **method**, in pipeline order. Each method calls its stage's logic function, handles errors/branching, and returns the next event. Order + branching live here, readable top-to-bottom.
- **Steps are pure logic.** `steps/<stage>/step.py` is a plain `async` function (e.g. `classify_papers(papers) -> list[Paper]`) with no `@step`/workflow coupling; `events.py` holds the stage's event class. The workflow method wraps the logic's return into an event.
- **Clients own all external I/O.** A raw HTTP/SDK/SQL call inside a step's logic or a workflow method is a layer violation — it belongs in `clients/`.
- **Workflow primitives** (`ctx.send_event`, `@step(num_workers=N)`, `ctx.collect_events`, `Context[StateModel]`) go in the workflow methods, never hand-rolled `asyncio.gather`.
- **The API and the weekly pipeline are two entry points into the same package**, sharing `clients/` and the DB.

## Conventions

- **Python**: ruff (lint+format) + mypy, run via `uv`. Full type hints, no bare `Any`. Events, API bodies, and config are Pydantic models. DB row types are generated, not hand-written.
- **Commits**: conventional one-liners, no scope parens, **no `Co-Authored-By` trailer**, never `--no-verify`, never amend. (Handled by `/ship`.)
- **OSS hygiene**: this repo is public. No secrets in code (only `config.py` reads env); document every new env var in `.env.example`; no real personal/mailing data — sample data only. Config-drive anything a forker would change (categories, schedule, model names).

## Verify before shipping

```bash
uv run ruff check backend && uv run mypy backend   # backend
npm --prefix frontend run typecheck                # frontend
```
