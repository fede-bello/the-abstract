---
name: python-code-quality
description: Python code-quality rules for the-abstract backend — function shape, helper placement, mutation hazards, exception handling, abstraction timing, async/event-loop hazards, and a critical-review checklist. Load before writing, refactoring, or reviewing non-trivial Python in backend/src/arxiv_digest/.
---

# Python Code Quality

Be critical about code shape — yours and existing code you're meaningfully touching. Push back on these patterns instead of mirroring them.

This skill complements (does not duplicate) the architecture rules in the project `CLAUDE.md` and the `/review` skill — the layered `workflows` / `steps/<stage>` / `clients` design, where external I/O lives, event/DTO placement, and config-ization are all defined there. This skill is about the *shape of the code inside* those layers.

## Function shape

- **Nesting**: 3+ levels of nesting (`with` / `for` / `if`) is a smell — find an extraction. `for x: for y: if z:` in particular: extract the inner block, or invert iteration order if that flattens it.
- **Length**: ~50 lines is a soft cap. Beyond that, the function is doing more than one thing.
- **Guard clauses**: prefer early-return cascades over nested branches. But a long cascade of guards that all build similar return shapes points at *Helper placement* below — extract the preamble or move the builder onto the type.
- **Comprehensions**: list/dict comprehensions over manual `for x: result.append(...)` when the body is a clean transform. (See `classify_papers`'s filter-comprehension for the idiom.)
- **Boolean flag parameters**: a function with `do_thing(data, fast=False, paranoid=True)` is two (or four) functions in a trench coat. Split them. Exception: when the flag is a genuine user-facing toggle that passes through, not a code-path switch.

## Helper placement

- **Empty / builder helpers**: a module-level `_empty_foo(...)` whose only job is to call `Foo(...)` with defaults belongs on the type itself as a `Foo.empty(...)` classmethod. Same for any single-purpose builder with no surrounding logic.
- **Shared preamble across siblings**: if two step logic functions or two client functions in the same module share a multi-line preamble (resolve X → fetch Y → validate Z), extract it to a helper or context object. Same-module duplication is as bad as the cross-feature duplication the `/review` skill already covers — this is its sibling rule.
- **Single-use private helpers**: fine when they flatten the caller (the `_format_authors` / `_format_metadata` split in the classifier is a good example); not fine when they're indirection for its own sake. Inline if the inlined version reads cleaner.
- **Many parameters → context object**: 5+ parameters that travel together across call sites are a context object in disguise. Bundle into a Pydantic model or dataclass. (The arXiv client's `fetch_recent_papers(categories, max_results, days_back, pdf_dir, max_attempts)` is near this line — watch it as more options accrue.)
- **Don't abstract too early**: rule of three — extract a helper on the *third* duplicate, not the second. A helper invented for one caller is dead weight; inline it until a second caller appears. The "shared preamble" rule above kicks in *after* the duplication exists, not on speculative future use.

## Trust the types — don't re-check the known

When a value's type or control flow already guarantees it's not None / not empty / within range, **don't add a defensive check anyway**. Redundant guards mislead the reader into thinking the case is reachable. mypy runs in `strict` mode here — lean on it.

- `x: int` (no `| None`) → never write `if x is None`. If you think it might be None, fix the type instead.
- After `if x is None: return`, `x` is narrowed to non-None for the rest of the function — don't re-check.
- After `assert x is not None`, no further checks needed.
- Function returns `Foo` (not `Foo | None`) → callers don't None-check the result.
- Pydantic required field (declared without `| None` and no default) is guaranteed non-None — treat it as such. `Paper.title` is always present; don't guard it.
- Compound conditions: `if x is not None and x >= T` when `x` is already None-guarded by control flow → just `if x >= T`.
- "Is empty" checks: don't `if my_list and len(my_list) > 0:` — pick one.

## Mutation hazards

- **Don't mutate function arguments.** If the caller passes a list/dict you need to change, copy first. Step logic functions take `list[Paper]` and should return a new list, not mutate the input in place.
- **Never `def f(items=[])` or `def f(opts={})`.** The default is shared across all calls — a classic correctness bug. Use `items=None` and reassign inside. (`Settings` already does this correctly with `default_factory=lambda: list(DEFAULT_ARXIV_CATEGORIES)`.)
- **Don't modify a collection while iterating it.** Build a new one or collect changes and apply after.

## Exception handling

Complements the layering rules in `CLAUDE.md`: **clients raise, the workflow method decides.** A client function (`clients/llm.py`, `clients/arxiv.py`, …) raises a specific exception on failure; the `@step` workflow method that called it owns the retry / skip / branch decision. Don't bury error policy inside a client or a step logic function.

- **Never `except Exception:` or bare `except:`.** Catch the specific exception you handle. The one deliberate exception in this codebase is the `auto` backend fallback in `clients/llm.py`, which catches broadly *and re-raises via fallback* with a `# noqa: BLE001` and a reason — that's the bar for a broad catch: a documented, recovering reason.
- **Exceptions aren't control flow.** Don't `try / except KeyError` to test membership — use `key in d`. Don't `try / except ValueError` around `int()` when `str.isdigit()` works.
- **Logging an exception isn't handling it.** If you can't recover, let it propagate so the workflow's timeout/retry policy (or the caller) sees it. Log with `exc_info=True` only where you actually add context, like the SDK-fallback warning.
- **Raise the right type at the boundary.** Define and raise a domain error (e.g. `LLMError`) instead of leaking a third-party SDK exception type up through the layers.

## Constants and configuration — no magic literals

- `if minutes >= MIN_MINUTES_THRESHOLD:` not `if minutes >= 600:`. Named constants tell the reader *why* the value matters.
- **Anything a forker might tune** — model names, thresholds, concurrency, timeouts, categories, schedule — is a field on `Settings` in `config.py`, read from the environment, and documented in `.env.example`. Never hardcode it in a step or client. (See `classification_model`, `llm_max_concurrency`, etc.)
- **Genuine fixed constants** (not env-tunable) live as module-level `UPPER_SNAKE_CASE` near their use, like `_RETRYABLE_STATUSES` in `clients/arxiv.py` or `_MAX_OUTPUT_TOKENS` in `clients/llm.py`. A leading underscore marks them module-private.

## Data access and external I/O

The ORM-specific rules from upstream don't apply (this project uses Supabase/pgvector via LlamaIndex vector stores, not a hand-written SQLAlchemy layer), but the principles do:

- **All external I/O lives in `clients/`.** A raw `httpx` request, an inline SDK call, or a raw SQL string inside a step logic function or a workflow method is a layer violation — route it through a client function. (Enforced by `/review`; repeated here because it's the most common drift.)
- **Parameterized queries only.** When `clients/db.py` lands, never build SQL by string concatenation — bind parameters.
- **Batch, don't loop-query.** If you find yourself issuing one query per item in a loop, fetch the set in one query and join in memory. (The N+1 trap, ORM or not.)

## Async — don't block the event loop

The whole backend is `async` (LlamaIndex Workflows). Blocking the loop serializes everything.

- **Wrap blocking sync libraries in `asyncio.to_thread`.** `clients/arxiv.py` does exactly this — the synchronous `arxiv` library runs in a worker thread so the loop stays free. Do the same for any sync SDK, file, or network call you must use from an `async def`.
- **Never call a blocking function directly from an `async def`** (no sync `requests`, no sync DB driver, no `time.sleep` on the request path).
- **Use the workflow's concurrency primitives, not hand-rolled `asyncio.gather`,** for fan-out across a step — `ctx.send_event` + `@step(num_workers=N)` + `ctx.collect_events`. (Architecture rule from `CLAUDE.md`; the classification stage is the worked example. `asyncio.gather` is fine in *test* code.)

## Pythonic style

- **`match` / dict dispatch** over long `if / elif` chains on string literals.
- **`dataclass` / Pydantic model for fixed-shape records** — never `dict[str, Any]` to represent a known schema. Events and results are Pydantic models here.
- **`enumerate` / `zip`** over `range(len(...))` and parallel index loops. Use `zip(..., strict=True)` when the lengths must match (as `classify_papers` does).
- **Walrus `:=`** only when it removes a duplicate expression — not for cleverness.
- **`Any` and `# type: ignore`** are escape hatches. Challenge every one — what's the real type? Bare `Any` is banned by `CLAUDE.md`; ruff runs `select = ["ALL"]`.

## Critical-review checklist

Actively flag, in any code you write or review:

- Comments that restate the code — delete them; rename the variable instead. (Comments earn their place by explaining *why*, like the 429/503-retry note in `clients/arxiv.py`.)
- Generic names: `data`, `info`, `result`, `obj` — almost always a more specific name is available.
- Helpers that exist only because the caller "felt long" but aren't a meaningful unit of work.
- Repeated kwargs across multiple builder calls — bind once and splat.
- Speculative parameters with no in-tree caller — dead weight, delete.
- `dict` / `list` type hints without parameters when the contents are uniform.
- Functions that return `int | str | dict | None` (or any incoherent union) — split or wrap in a tagged Pydantic model.
- A hardcoded model name, threshold, or category that should be a `Settings` field.
