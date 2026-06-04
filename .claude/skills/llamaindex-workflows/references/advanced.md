# LlamaIndex Workflows — Advanced Patterns

Read this when the base SKILL.md isn't enough: human-in-the-loop, retries,
resource injection, sub-workflows, visualization, cross-run state, and the
prebuilt agent abstractions.

## Human-in-the-loop

Emit `InputRequiredEvent` to pause for input; resume by sending a
`HumanResponseEvent`. The recommended approach is the two-event pattern (NOT
`ctx.wait_for_event`, which replays preceding step code):

```python
from workflows import Workflow, step
from workflows.events import (
    StartEvent, StopEvent, InputRequiredEvent, HumanResponseEvent,
)

class HITLWorkflow(Workflow):
    @step
    async def ask(self, ev: StartEvent) -> InputRequiredEvent:
        return InputRequiredEvent(prefix="Enter a number: ")

    @step
    async def receive(self, ev: HumanResponseEvent) -> StopEvent:
        return StopEvent(result=ev.response)

handler = HITLWorkflow().run()
async for event in handler.stream_events():
    if isinstance(event, InputRequiredEvent):
        response = input(event.prefix)
        handler.ctx.send_event(HumanResponseEvent(response=response))
result = await handler
```

**Pause/resume across processes** — serialize the context, cancel, restore later:

```python
ctx_dict = handler.ctx.to_dict()
await handler.cancel_run()
# ... later, possibly in another process ...
from workflows import Context
restored = Context.from_dict(workflow, ctx_dict)
result = await workflow.run(ctx=restored)
```

## Retry policies

Attach a policy to a flaky step so transient errors retry with backoff:

```python
from workflows.retry_policy import (
    retry_policy, retry_if_exception_type, wait_exponential, stop_after_attempt,
)

policy = retry_policy(
    retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    wait=wait_exponential(multiplier=1, exp_base=2, max=30),
    stop=stop_after_attempt(5),
)

@step(retry_policy=policy)
async def flaky_step(self, ev: SomeEvent) -> StopEvent:
    ...
```

## Resource injection

Share dependencies across steps via `Annotated` + `Resource(factory)`. The factory
runs once per run and the value is shared across steps that ask for it:

```python
from typing import Annotated
from workflows.resource import Resource

def get_memory(*args, **kwargs):
    return Memory(...)

@step
async def my_step(
    self,
    ev: StartEvent,
    memory: Annotated[Memory, Resource(get_memory)],
) -> StopEvent:
    ...
```

## Nested / sub-workflows

A workflow author can leave a slot for a sub-workflow and supply it at runtime:

```python
w = MainWorkflow()
w.add_workflows(reflection=ReflectionWorkflow())
result = await w.run(...)
```

The sub-workflow is injected as a `Context` resource and run with its own `.run()`.
You can supply a default sub-workflow so the parent runs standalone, then override
it. Note: `draw_all_possible_flows` renders only the **main** workflow — a nested
flow is a separate workflow, not a step.

LlamaIndex also ships prebuilt workflows you can subclass and override individual
steps on, to customize behavior without rewriting the whole thing. Steps can also be
attached to a workflow outside the class body via the standalone package's
step-adding API — useful for composing workflows programmatically.

## Visualization & debugging

```python
# pip install llama-index-utils-workflow
from llama_index.utils.workflow import (
    draw_all_possible_flows, draw_most_recent_execution,
)

draw_all_possible_flows(MyWorkflow, filename="all_paths.html")  # static, all edges

handler = w.run(topic="Pirates")
await handler
draw_most_recent_execution(handler, filename="most_recent.html")  # actual path
```

Pass `verbose=True` to the constructor for per-step event logging. For production
tracing, the standalone package integrates with `llama-index-instrumentation`
(OpenTelemetry, Arize Phoenix, Langfuse):

```python
from llama_index_instrumentation import get_dispatcher
from llama_index_instrumentation.base import BaseEvent

dispatcher = get_dispatcher()

class ExampleEvent(BaseEvent):
    data: str

@dispatcher.span
def example_fn(data: str) -> None:
    dispatcher.event(ExampleEvent(data=data))
```

## Cross-run state

Build a `Context` once and pass it into successive `.run()` calls to carry state
across runs (e.g., a chat loop):

```python
from workflows import Context

workflow = MyWorkflow()
ctx = Context(workflow)
await workflow.run(ctx=ctx, msg="first")
await workflow.run(ctx=ctx, msg="second")   # state from the first run preserved
```

## Prebuilt agents: FunctionAgent & AgentWorkflow

Workflows underpin LlamaIndex's agent abstractions. For most agentic apps you don't
write raw steps — you use these.

```python
from llama_index.llms.openai import OpenAI
from llama_index.core.agent.workflow import FunctionAgent, AgentStream, ToolCall

async def search_web(query: str) -> str:
    """Useful for searching the web to answer questions."""  # docstring = tool desc
    ...

agent = FunctionAgent(
    tools=[search_web],
    llm=OpenAI(model="gpt-4o-mini"),
    system_prompt="You are a helpful assistant that can search the web.",
)

# Simple run:
response = await agent.run(user_msg="What is the weather in San Francisco?")

# Streaming:
handler = agent.run(user_msg="What is the weather in Saskatoon?")
async for event in handler.stream_events():
    if isinstance(event, AgentStream):
        print(event.delta, end="", flush=True)
    elif isinstance(event, ToolCall):
        print(event.tool_name, event.tool_kwargs)
```

**Multi-agent** — `AgentWorkflow` coordinates multiple `FunctionAgent`s with
handoffs. Set a `root_agent`; each agent declares `can_handoff_to=["OtherAgent"]`
(defaults to all). The workflow loops until an agent responds with no tool calls, a
`return_direct=True` tool fires, or it times out. Every tool needs a docstring and
type annotations, or schema inference fails.

```python
from llama_index.core.agent.workflow import AgentWorkflow

workflow = AgentWorkflow(
    agents=[research_agent, write_agent],
    root_agent=research_agent.name,
)
response = await workflow.run(user_msg="Research and write about X.")
```

## A note on the RAG-as-workflow pattern

A workflow can have multiple `StartEvent` steps that each guard on which kwargs are
present and `return None` to no-op when not applicable — e.g. an `ingest` step
triggered by `.run(dirname=...)` and a `retrieve` step triggered by
`.run(query=..., index=...)`. This lets one workflow class handle distinct entry
modes.
