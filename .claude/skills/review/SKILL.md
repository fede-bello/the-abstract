---
name: review
description: Review current changes for clean code, DRY violations, dead code, unnecessary comments, and architecture compliance in the arXiv ML Digest project. Use after implementing a feature and before shipping.
disable-model-invocation: true
model: opus
allowed-tools: Read Glob Grep Bash Agent
---

# Code Review

You are reviewing the current workspace changes in **the-abstract** — an open-source arXiv ML Digest pipeline. The codebase is a monorepo: a Python backend built on **LlamaIndex Workflows** (a weekly pipeline, no API server), and a **Vite + React (TypeScript)** frontend that reads **Supabase/Postgres (pgvector)** directly.

This is a thorough review focused on DRY, reusability, dead code, unnecessary comments, and the project's layered architecture — not a linting pass (ruff/mypy handle style).

**Before reviewing, load the project conventions:**
- Read `CLAUDE.md` and/or `AGENTS.md` if present (architecture, naming, conventions).
- Read `objective.md` for the product spec and pipeline stages.
- Skim the relevant `backend/src/arxiv_digest/` modules for the area being changed (the matching `steps/<stage>/`, `clients/`, or `workflows/`), and for frontend changes the relevant `frontend/src/` files (including the `src/data/` Supabase access layer).

If the project layout differs from what's described here (the codebase is young and evolving), trust the actual structure and adapt — the architecture *principles* below are what matter, not exact paths.

## The Architecture (what "correct placement" means here)

The backend is organized around LlamaIndex Workflows. The workflow file is the explicit orchestration; each stage's *work* is a pure logic function; everything those functions *reach for* is a client.

```
backend/src/arxiv_digest/
├── workflows/        # digest.py — the pipeline: every @step METHOD, in order
├── steps/            # one folder per pipeline stage
│   └── <stage>/      #   step.py (pure async logic fn) + events.py (the stage's event class)
├── clients/          # llm.py, db.py, arxiv.py, parse.py — external I/O, called BY logic fns
└── config.py         # Settings: config.toml (non-secret) + env/.env (secrets)
frontend/             # Vite + React SPA — reads Supabase directly (anon key); no backend server
```

There is no API server: the backend is the weekly pipeline (writes to Supabase) and the SPA reads Supabase directly — the app hosts on Vercel (static) + Supabase (DB) for free.

**The load-bearing rules:**
- **The workflow file is the orchestration hub.** `workflows/digest.py` declares `DigestWorkflow` with every stage as a `@step` **method**, in pipeline order. A method resolves inputs, calls its stage's logic function, handles errors/branching, and returns the next `Event`. This is the right place for control flow (order, branches, fan-out) — but NOT for external I/O (no raw arXiv/LLM/SQL calls in a method; those go through a logic fn → client).
- **Steps are pure logic.** `steps/<stage>/step.py` is a plain `async` function (e.g. `classify_papers(papers) -> list[Paper]`) with no `@step` decorator and no workflow imports; `events.py` holds the stage's `Event` class. A logic function that imports `workflows` or builds `Event`s is misplaced — the workflow method owns the event wrapping.
- **Clients own all external I/O.** Every arXiv call, LLM/embedding call, LlamaParse call, and DB query lives in `clients/`. A logic function (or workflow method) containing a raw `httpx` request, an inline SDK call, or a raw SQL string is a layer violation — it should call a client function.
- **The frontend reads Supabase directly.** Papers/weeks/facets come from the `papers` table and the read-only views (`supabase/migrations/`) via the anon key + RLS, through the single data-access seam (`src/data/client.ts` → `SupabaseApiClient`) — not scattered `fetch`/`createClient` calls. No service-role key or secrets in the browser; only the public anon key. Derived aggregates belong in SQL views, not re-derived ad hoc.

## Step 1: Understand the Feature Scope

Check for changes:

```bash
git status --short && git diff --stat && git diff --cached --stat
```

Then read the full diffs (unstaged + staged):

```bash
git diff && git diff --cached
```

Understand what the change does before reviewing. Identify which files are new vs modified, and which side of the monorepo (backend / frontend) they touch.

**Scope rule**: The review covers ONLY the files in the diff (new + modified). You may search the rest of the codebase to detect duplication or missing reuse, but every fix you propose or apply must target a file in the changeset. Never modify files outside the diff. If you spot cross-codebase duplication, note it as an **Observation** — do not extract it yourself.

## Step 2: Read Every Changed File in Full

For each file in the diff, **read the entire file** — not just the changed lines. Full context is needed to spot duplicated logic in the same module, a helper or client function that already exists, dead code left after a refactor, and comments that restate the obvious.

## Step 3: Search for Duplication and Reuse Opportunities

This is the most important step. For every new step, event, client function, workflow, endpoint, hook, or component introduced:

1. **Search for something that already does this.** Common reuse points in this project:
   - **Clients** — before writing any external call, check `clients/` for an existing function. Don't re-instantiate the LLM or DB client inside a step; reuse the shared client/factory (and prefer LlamaIndex `Resource` injection where the project uses it).
   - **Events** — check the relevant `steps/<stage>/events.py` before defining a new event. An event with the same payload under a new name is duplication.
   - **Prompts / schemas** — shared prompt templates, Pydantic output schemas, and embedding helpers should be reused, not re-pasted per step.
   - **Config** — categories, arXiv category list, schedule day, model names, and thresholds are `Settings` fields in `config.py`, with non-secret defaults in `config.toml`. Never hardcode them in a step.
   - **Frontend** — check `frontend/src/` for an existing data-client method (`src/data/`), hook, type, SQL view, or UI primitive before adding a new one.

2. **Check placement against the architecture above.** External I/O in a workflow method or a logic function (should be a client). A logic function that imports `workflows` or builds `Event`s (the workflow method should own that). Heavy business logic inlined in a workflow method instead of its `steps/<stage>/step.py` logic function. A raw SQL string outside `clients/db.py`.

3. **Check for near-duplicates within the changed files** — two logic functions, events, or client functions that do almost the same thing with minor variations should be unified. Cross-file duplication with untouched code → report as an Observation, don't refactor it.

## Step 4: Identify Dead Code and Unnecessary Comments

### Dead code
- Unused imports, variables, or function parameters
- Commented-out code blocks (use git history, not comments)
- Functions / steps / events defined but never referenced or registered
- Unreachable code after early returns
- Leftover debugging (`print(...)`, stray `logging.debug`, `console.log`)

### Unnecessary comments
- Comments that restate the code or the function name
- TODO/FIXME for things that should just be done now
- Commented-out alternative implementations
- Section-separator comments that add nothing

### Keep these (NOT unnecessary)
- Comments explaining **why** a non-obvious decision was made
- Notes on a known limitation or workaround (e.g. why a step retries, why an arXiv field is parsed defensively)
- `# type: ignore[code]` with a reason

## Step 5: Check Clean Code Principles

### DRY (Don't Repeat Yourself)
- Any logic block appearing 2+ times with only parameter differences should be one function.
- Any external call that duplicates an existing `clients/` function.
- Any logic function / component that is a copy-paste of another with minor changes.

### Architecture Compliance
- **Workflow (`digest.py`)**: every stage is a `@step` method, in order. A method resolves inputs, calls its stage's logic function, and returns the next `Event` — control flow only. Use workflow primitives here — `ctx.send_event()` for fan-out, `@step(num_workers=N)` for concurrency, `ctx.collect_events()` for fan-in, `Context[StateModel]` + `ctx.store.edit_state()` for shared state. Flag hand-rolled `asyncio.gather`, busy-wait loops, and external I/O inlined in a method.
- **Step logic (`steps/<stage>/step.py`)**: a pure `async` function, fully type-hinted, returning data (e.g. `list[Paper]`) — NOT an `Event`. No `@step`, no `workflows` import. `events.py` holds the stage's `Event` class.
- **Clients**: external I/O only. No workflow/step imports leaking in. Raise on error so the workflow method can apply a retry policy.
- **Frontend**: functional components, reach data through the hooks → `getClient()` seam (Supabase), never a concrete client or raw `fetch`, props destructured in the signature.

### Type Safety
- **Python**: full type hints. No bare `Any` — use a precise type, a `TypeVar`, or `object`/`unknown`-style narrowing. Events and config are **Pydantic models**. DB row types come from generated Supabase types, never hand-written.
- **TypeScript**: no `any` (use `unknown` if truly unknown); Supabase rows are mapped through a typed row interface.

### Configuration & OSS hygiene
- This is an open-source project — it must run for anyone who clones it. No hardcoded categories, schedules, model names, or magic thresholds; they belong in `config.py` (defaults in `config.toml`).
- When a new `Settings` field is introduced, add its default to `config.toml`; add to `.env.example` only if it's a secret.
- No personal data in the repo (real mailing lists, private API keys, sample emails with real addresses) — sample/synthetic data only.

### Security
- No secrets or API keys in code — only `config.py` reads them from the environment.
- Validate external input with Pydantic at the boundaries (config, CLI args, parsed/LLM output) before it reaches the DB.
- Parameterized queries only — never build SQL by string concatenation.
- New Supabase tables/views need RLS policies (or explicit grants) — the frontend reads them with the public anon key, so anything exposed is world-readable. Never ship the service-role key to the browser.

### Layer Violations (call these out explicitly)
- A logic function or workflow method making a raw HTTP/SDK/DB call instead of going through `clients/`.
- A step logic function importing `workflows` or constructing `Event`s (the workflow method owns event wrapping).
- A workflow method carrying heavy business logic that belongs in its stage's logic function.
- SQL built by string concatenation, or a raw SQL string outside `clients/db.py`.
- A client importing a workflow or a step.
- The frontend bypassing the `src/data/client.ts` seam (raw `createClient`/`fetch` in components), exposing a non-anon key, or re-deriving in JS what a SQL view should serve.

## Step 6: Report

Present findings grouped by severity:

```
## Review: [feature summary]

### Must Fix
[Layer violations, duplication, dead code, leaked secrets, missing config-ization]

1. **[Category]** — `file:line`
   **Problem**: [what's wrong]
   **Fix**: [specific action — move call into clients/X, extract step, delete Z, read from config]

### Should Fix
[Reusability improvements, naming, comment cleanup, type tightening]

### Observations
[Non-blocking suggestions / cross-codebase duplication outside the current diff]
```

For each "Must Fix" and "Should Fix" item, give the concrete fix — don't just describe the problem. Show the change or point to the existing function/client that should be reused.

**After presenting the report, ask the user if they want you to apply the fixes.** If yes, apply them **only to files in the feature diff** in a single pass, then verify against the toolchain for the side(s) you touched:

```bash
# backend changes
uv run ruff check backend && uv run mypy backend

# frontend changes
npm --prefix frontend run typecheck   # or: cd frontend && npx tsc --noEmit
```

If a verification command doesn't exist yet (the project is still being scaffolded), say so rather than inventing output — and note which check should be wired up.

$ARGUMENTS
