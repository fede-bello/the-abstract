---
name: llamaindex-workflows
description: >-
  Build event-driven, step-based orchestration with LlamaIndex Workflows in
  Python — the `Workflow` class, `@step` decorator, `Event`/`StartEvent`/`StopEvent`,
  the `Context` object, branching, loops, parallel fan-out/fan-in, streaming,
  human-in-the-loop, retries, and visualization. Use this skill WHENEVER the user
  is writing or debugging LlamaIndex Workflows code, mentions `@step`, `StartEvent`,
  `StopEvent`, `ctx.send_event`, `collect_events`, `AgentWorkflow`/`FunctionAgent`
  orchestration, or wants to structure an agentic/RAG pipeline as an event-driven
  workflow — even if they just say "build a workflow" in a LlamaIndex context.
  Covers both the standalone `workflows` package and the legacy
  `llama_index.core.workflow` import path.
---

# LlamaIndex Workflows

Workflows are LlamaIndex's **event-driven orchestration** primitive. Instead of a
DAG, you split logic into **steps** (async methods) that consume and emit
**events**. Routing is inferred from type hints — control flow lives in the event
types, which makes loops, branching, and concurrency feel natural. This is the
foundation under the higher-level `FunctionAgent` / `AgentWorkflow` agents.

## Package & imports (decide this first)

There are two valid import paths. They are equivalent — `llama_index.core.workflow`
re-exports from the standalone package.

```python
# Preferred for NEW code — the standalone, actively-developed package:
# pip install llama-index-workflows
from workflows import Workflow, step, Context
from workflows.events import Event, StartEvent, StopEvent

# Legacy / what most existing examples & tutorials use (still works):
# from llama_index.core.workflow import (
#     Workflow, step, Context, Event, StartEvent, StopEvent,
# )
```

**Guidance:** write new code with `from workflows import ...`. When editing an
existing file, match whichever path it already uses — don't mix them. Avoid
`from llama_index.workflows import ...` (not canonical).

## Core mental model

- **`Workflow`** — subclass it. Constructor: `timeout` (seconds — **default is short,
  ~10s; set `timeout=60`+ for any LLM/RAG work or it raises `WorkflowTimedOutEvent`**),
  `verbose=True` for per-step logging.
- **`@step`** — decorates an `async def` method. The framework reads the **type
  hints**: the parameter annotated as an `Event` subtype decides what triggers the
  step; the **return annotation** decides what it emits. Wrong/missing annotations
  silently break routing, or raise `WorkflowValidationError` ("at least one parameter
  annotated as type Event").
- **`StartEvent`** — entry event. Kwargs passed to `.run(topic="x")` land on it as
  `ev.topic` (or `ev.get("topic")`).
- **`StopEvent`** — returning it ends the run; `StopEvent(result=...)` is what
  `.run()` resolves to.
- **Custom `Event`** — subclass `Event` (it's a Pydantic model) to carry typed
  payloads between steps.
- **`Context`** — add `ctx: Context` to a step's signature to get shared state,
  event emission, fan-in collection, and streaming.

## Minimal runnable workflow

```python
import asyncio
from workflows import Workflow, step
from workflows.events import Event, StartEvent, StopEvent
from llama_index.llms.openai import OpenAI

class JokeEvent(Event):
    joke: str

class JokeFlow(Workflow):
    llm = OpenAI(model="gpt-4.1")

    @step
    async def generate_joke(self, ev: StartEvent) -> JokeEvent:
        response = await self.llm.acomplete(f"Write a joke about {ev.topic}.")
        return JokeEvent(joke=str(response))

    @step
    async def critique_joke(self, ev: JokeEvent) -> StopEvent:
        response = await self.llm.acomplete(f"Critique this joke: {ev.joke}")
        return StopEvent(result=str(response))

async def main():
    result = await JokeFlow(timeout=60).run(topic="pirates")
    print(str(result))

asyncio.run(main())
```

Steps are `async def`; `.run()` is awaited. That's the whole loop.

## Branching and loops

**Branch** — return a `Union` of event types; the instance you return picks the path:

```python
@step
async def route(self, ev: StartEvent) -> BranchAEvent | BranchBEvent:
    return BranchAEvent(...) if condition else BranchBEvent(...)
```

**Loop** — return an event consumed by an earlier (or the same) step until an exit
condition emits `StopEvent`:

```python
class LoopEvent(Event):
    count: int

@step
async def loop_step(self, ev: LoopEvent) -> LoopEvent | StopEvent:
    if ev.count <= 0:
        return StopEvent(result="done")
    return LoopEvent(count=ev.count - 1)
```

## Parallelism: fan-out and fan-in

**Fan-out** — emit multiple events with `ctx.send_event()` and process them
concurrently with `@step(num_workers=N)`. A step that only emits via `send_event`
and returns nothing must be annotated `-> SomeEvent | None` and `return None`:

```python
@step
async def spread(self, ctx: Context, ev: StartEvent) -> SubEvent | None:
    for q in ev.queries:
        ctx.send_event(SubEvent(query=q))
    return None  # emitted via send_event, nothing to return

@step(num_workers=4)
async def handle(self, ev: SubEvent) -> DoneEvent:
    return DoneEvent(result=await do_work(ev.query))
```

**Fan-in** — `ctx.collect_events(ev, [DoneEvent] * N)` buffers events and returns
`None` until all N have arrived, then returns them as a list. You **must** return
`None` while it's incomplete or you break the join. The order of the type list
determines output order (deterministic regardless of arrival order):

```python
@step
async def gather(self, ctx: Context, ev: DoneEvent) -> StopEvent | None:
    results = ctx.collect_events(ev, [DoneEvent] * 3)
    if results is None:
        return None
    return StopEvent(result=[r.result for r in results])
```

## State with `Context` (async!)

`ctx.store.get/set` are **async — always `await`** (a top source of bugs):

```python
@step
async def step_a(self, ctx: Context, ev: StartEvent) -> StopEvent:
    count = await ctx.store.get("count", default=0)
    await ctx.store.set("count", count + 1)
    return StopEvent()
```

For read-modify-write under concurrency (`num_workers > 1`), use the atomic editor
instead of separate get/set:

```python
async with ctx.store.edit_state() as state:
    state["count"] = state.get("count", 0) + 1
```

Typed state via a Pydantic model — parametrize `Context[StateModel]`:

```python
from pydantic import BaseModel, Field

class State(BaseModel):
    count: int = Field(default=0)

@step
async def s(self, ctx: Context[State], ev: StartEvent) -> StopEvent:
    async with ctx.store.edit_state() as state:
        state.count += 1
    return StopEvent(result="ok")
```

> Legacy code uses `ctx.set(key, val)` / `ctx.get(key)` — these map to the store.
> Prefer `ctx.store.*` in new code.

## Streaming progress events

Write progress from any step; consume it from the handler. The key gotcha:
**`handler = w.run(...)` is NOT awaited when streaming** — iterate first, then
`await handler` for the final result.

```python
class ProgressEvent(Event):
    msg: str

# inside a step:
ctx.write_event_to_stream(ProgressEvent(msg="working..."))

# driver:
handler = MyWorkflow(timeout=60).run(query="...")   # not awaited yet
async for ev in handler.stream_events():
    if isinstance(ev, ProgressEvent):
        print(ev.msg)
result = await handler                               # now await for the result
```

Terminal events also appear on the stream: `WorkflowTimedOutEvent`,
`WorkflowCancelledEvent`, `WorkflowFailedEvent` (from `workflows.events`).

## When to reach for the reference file

The patterns above cover most workflows. For these topics, read
`references/advanced.md`:

- **Human-in-the-loop** (`InputRequiredEvent` / `HumanResponseEvent`, pause/resume
  across processes).
- **Retry policies** (`@step(retry_policy=...)`).
- **Resource injection** (`Annotated[T, Resource(factory)]`).
- **Nested / sub-workflows** (`add_workflows`) and adding steps externally.
- **Visualization** (`draw_all_possible_flows`, `draw_most_recent_execution`).
- **Cross-run state** (passing a shared `Context` into successive `.run()` calls).
- **`FunctionAgent` / `AgentWorkflow`** — the prebuilt agent abstractions built on
  workflows, including multi-agent handoffs.

## Pitfalls checklist

- `ctx.store.get/set` are **async** — `await` them.
- Default `timeout` is ~10s — set `timeout=60`+ for LLM/RAG steps.
- Every step needs ≥1 parameter annotated as an `Event` subtype; routing is driven
  entirely by type hints.
- When streaming, **don't await `.run()`** — iterate `stream_events()`, then await
  the handler.
- `collect_events` returns `None` until complete — `return None` to keep the step
  parked.
- `send_event`-only steps: annotate `-> Event | None` and `return None`.
- Use `ctx.store.edit_state()` for concurrent read-modify-write.
- Agent tools need docstrings + type hints, or schema inference fails.
- `draw_all_possible_flows` won't render nested sub-workflows (only the main flow).

## Key docs

- Workflows guide: https://developers.llamaindex.ai/python/framework/module_guides/workflow/
- Basic flow / branches / loops / concurrency / state / streaming:
  https://developers.llamaindex.ai/python/framework/understanding/workflows/
- Cookbook (all features): https://developers.llamaindex.ai/python/examples/workflow/workflows_cookbook/
- API reference: https://developers.llamaindex.ai/python/workflows-api-reference/
- Standalone repo: https://github.com/run-llama/workflows-py
