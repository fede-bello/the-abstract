---
name: llamaindex-framework
description: >-
  Build RAG and LLM applications with the LlamaIndex Python framework (v0.10+
  modular structure). Covers loading data (`SimpleDirectoryReader`), indexing
  (`VectorStoreIndex`, `Document`/`Node`, `SentenceSplitter`), querying
  (`as_query_engine`, `as_retriever`, `as_chat_engine`), the global `Settings`
  object (which replaced `ServiceContext`), persistence (`StorageContext`,
  `load_index_from_storage`), LLM/embedding config, vector stores (Chroma, etc.),
  and agents/tools (`FunctionAgent`, `QueryEngineTool`). Use this skill WHENEVER
  the user is building or debugging anything with LlamaIndex / `llama_index` /
  `llama-index-core` — RAG over documents, chat over a knowledge base, vector
  search, query engines, or wiring up an index — even if they just say "build a
  RAG app with LlamaIndex." For event-driven orchestration use the
  llamaindex-workflows skill; for hosted parsing/extraction use the llamacloud skill.
---

# LlamaIndex Framework (Python)

LlamaIndex is a data framework for LLM apps — most commonly **RAG**. This skill
targets the **current modular API** (v0.10+, currently v0.14.x, Python ≥3.10).

> **The single most important thing to get right:** since v0.10, imports for
> abstractions come from `llama_index.core`, and every integration (LLMs,
> embeddings, vector stores, readers) is a **separately installed package**. Use
> `Settings`, not the deprecated `ServiceContext`. Old tutorials with
> `from llama_index import GPTVectorStoreIndex` / `ServiceContext` / `LLMPredictor`
> are obsolete — do not generate that code.

## The RAG pipeline (mental model)

1. **Load** — sources → `Document` objects (`SimpleDirectoryReader`, LlamaHub readers).
2. **Index** — split into `Node`s (chunks), embed, build a `VectorStoreIndex`.
3. **Store** — persist so you don't re-index every run (local `./storage` or a vector DB).
4. **Query** — retrieve relevant nodes + synthesize an answer (`as_query_engine`,
   `as_retriever`, `as_chat_engine`).

Global config flows through the **`Settings`** singleton. Agents wrap query engines
as `QueryEngineTool`.

## Install & package structure

The namespace rule is the key mental model:
- Imports **with `core`** → from `llama-index-core` (abstractions, zero third-party deps).
- Imports **without `core`** → from a separately-installed integration package.

```bash
# Starter: core + OpenAI LLM + OpenAI embeddings + file reader. Needs OPENAI_API_KEY.
pip install llama-index

# Custom (core only + pick integrations):
pip install llama-index-core \
  llama-index-llms-openai \
  llama-index-embeddings-huggingface \
  llama-index-vector-stores-chroma \
  llama-index-readers-file
```

Integration naming: `llama-index-llms-<provider>`, `llama-index-embeddings-<provider>`,
`llama-index-vector-stores-<db>`, `llama-index-readers-<source>`. Browse readers/tools
at https://llamahub.ai.

## Minimal RAG (the 4-line version)

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

documents = SimpleDirectoryReader("data").load_data()
index = VectorStoreIndex.from_documents(documents)
response = index.as_query_engine().query("Summarize the documents.")
print(response)
```

## Loading data

```python
from llama_index.core import SimpleDirectoryReader

# Every supported file in a folder (pdf, md, txt, docx, ...)
documents = SimpleDirectoryReader("data").load_data()
# Useful kwargs: input_files=[...], required_exts=[".pdf"], recursive=True
```

## Indexing: Documents, Nodes, splitters

```python
from llama_index.core import Document, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter

# Manual documents with metadata:
documents = [Document(text="some text", metadata={"source": "doc1", "year": 2024})]

# Explicit node parsing (more control than from_documents):
splitter = SentenceSplitter(chunk_size=512, chunk_overlap=20)
nodes = splitter.get_nodes_from_documents(documents)

index = VectorStoreIndex(nodes)                    # pass pre-parsed Nodes positionally
# vs.
index = VectorStoreIndex.from_documents(documents) # classmethod for raw Documents
```

**Common error:** `VectorStoreIndex(nodes)` (constructor, for `Node`s) vs.
`VectorStoreIndex.from_documents(documents)` (classmethod, for `Document`s). Don't
mix them up.

## Querying

```python
# Query engine (retrieve + synthesize):
qe = index.as_query_engine(similarity_top_k=5)
response = qe.query("What did the author do growing up?")
print(response)
print(response.source_nodes)        # retrieved nodes + scores

# Streaming:
index.as_query_engine(streaming=True).query("...").print_response_stream()

# Pure retriever (no LLM synthesis):
nodes = index.as_retriever(similarity_top_k=3).retrieve("query")

# Chat engine (stateful, multi-turn):
chat = index.as_chat_engine(chat_mode="condense_plus_context")
print(chat.chat("Tell me about X"))
print(chat.chat("And how does it relate to Y?"))   # remembers context
```

**Response modes** (`response_mode=` on `as_query_engine`): `compact` (default),
`refine`, `tree_summarize` (good for summarizing many nodes), `simple_summarize`,
`no_text` (nodes only).

**Chat modes** (`chat_mode=`): `condense_plus_context` (recommended default),
`condense_question`, `context`, `react`/`best`, `simple`.

## `Settings` (replaces `ServiceContext`)

A global singleton with lazily-instantiated attributes — set once, used as defaults
downstream. Local params passed to a module override the global.

```python
from llama_index.core import Settings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.node_parser import SentenceSplitter

Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0.1)
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
Settings.node_parser = SentenceSplitter(chunk_size=1024, chunk_overlap=20)
Settings.chunk_size = 512   # shortcut for the default splitter

# Local override beats global:
qe = index.as_query_engine(llm=OpenAI(model="gpt-4o"))
```

## Persistence

```python
from llama_index.core import StorageContext, load_index_from_storage

# Save (local ./storage JSON stores):
index.storage_context.persist(persist_dir="./storage")

# Load later — MUST set the same embed model used at index time (via Settings or
# kwargs), or retrieval silently degrades:
storage_context = StorageContext.from_defaults(persist_dir="./storage")
index = load_index_from_storage(storage_context)
```

A robust "index once, reuse after" pattern:

```python
import os
from llama_index.core import (
    VectorStoreIndex, SimpleDirectoryReader, StorageContext, load_index_from_storage,
)

PERSIST_DIR = "./storage"
if not os.path.exists(PERSIST_DIR):
    documents = SimpleDirectoryReader("data").load_data()
    index = VectorStoreIndex.from_documents(documents)
    index.storage_context.persist(persist_dir=PERSIST_DIR)
else:
    index = load_index_from_storage(StorageContext.from_defaults(persist_dir=PERSIST_DIR))
```

## LLM & embedding configuration

```python
# OpenAI (default):
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
Settings.llm = OpenAI(model="gpt-4o-mini")
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

# Local / no-OpenAI (Ollama + HuggingFace embeddings):
# pip install llama-index-llms-ollama llama-index-embeddings-huggingface
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
Settings.llm = Ollama(model="llama3.1", request_timeout=120.0)
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
```

**Gotcha:** OpenAI is the implicit default for *both* LLM and embeddings. Without
`OPENAI_API_KEY`, even "local" setups fail unless you explicitly override both
`Settings.llm` and `Settings.embed_model`.

Using an LLM standalone (no index):

```python
from llama_index.core.llms import ChatMessage
from llama_index.llms.openai import OpenAI

llm = OpenAI(model="gpt-4o-mini")
print(llm.complete("Paul Graham is "))
resp = llm.chat([
    ChatMessage(role="system", content="You are a pirate."),
    ChatMessage(role="user", content="What is your name?"),
])
for chunk in llm.stream_complete("Paul Graham is "):
    print(chunk.delta, end="")
```

## Vector store: Chroma

```bash
pip install llama-index-vector-stores-chroma chromadb
```
```python
import chromadb
from llama_index.core import VectorStoreIndex, StorageContext, SimpleDirectoryReader
from llama_index.vector_stores.chroma import ChromaVectorStore

db = chromadb.PersistentClient(path="./chroma_db")
collection = db.get_or_create_collection("quickstart")
vector_store = ChromaVectorStore(chroma_collection=collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# First run — build & store:
documents = SimpleDirectoryReader("data").load_data()
index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)

# Later runs — reconnect WITHOUT re-embedding:
index = VectorStoreIndex.from_vector_store(vector_store)
```

**Key distinction:** `from_documents(..., storage_context=...)` to build/add;
`from_vector_store(vector_store)` to reconnect to an already-populated store. Calling
`from_documents` again re-embeds and can duplicate data.

## Agents & tools (high level)

Current agents live in `llama_index.core.agent.workflow` and are **async**
(`await agent.run(...)`). Plain functions with docstrings + type hints become tools;
wrap a query engine as a `QueryEngineTool` to give an agent RAG.

```python
import asyncio
from llama_index.llms.openai import OpenAI
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import QueryEngineTool

def multiply(a: float, b: float) -> float:
    """Useful for multiplying two numbers."""   # docstring + hints = the tool schema
    return a * b

rag_tool = QueryEngineTool.from_defaults(
    query_engine=index.as_query_engine(),
    name="paul_graham_essay",
    description="Answers questions about Paul Graham's essay. Use a detailed question.",
)

agent = FunctionAgent(
    tools=[multiply, rag_tool],
    llm=OpenAI(model="gpt-4o-mini"),
    system_prompt="You answer questions, search documents, and do math.",
)

async def main():
    print(await agent.run("What did the author do in college? Also what's 7*8?"))

asyncio.run(main())
```

`FunctionAgent` needs a tool-calling LLM; `ReActAgent(tools=..., llm=...)` works with
any LLM. For multi-step agent orchestration and `AgentWorkflow`, use the
**llamaindex-workflows** skill.

## Pitfalls checklist

- v0.10 restructure: `from llama_index.core import ...` for abstractions; install +
  import integrations separately. No more `from llama_index import GPTVectorStoreIndex`.
- `ServiceContext` is removed — use `Settings` (global) or pass params locally.
- `VectorStoreIndex(nodes)` vs `.from_documents(documents)` — pick by input type.
- On reload, set the same embed model used at index time or retrieval degrades.
- Vector DB: `from_vector_store` to reconnect, `from_documents` to build (re-embeds).
- Agents are async (`await agent.run(...)`); old `OpenAIAgent` / `.from_tools()` are legacy.
- OpenAI is the default LLM + embedding; override both for local setups.

## Key docs

- Installation: https://developers.llamaindex.ai/python/framework/getting_started/installation/
- Starter example: https://developers.llamaindex.ai/python/framework/getting_started/starter_example/
- Settings: https://developers.llamaindex.ai/python/framework/module_guides/supporting_modules/settings/
- Documents & Nodes: https://developers.llamaindex.ai/python/framework/module_guides/loading/documents_and_nodes/
- Query engines: https://developers.llamaindex.ai/python/framework/module_guides/deploying/query_engine/
- Chat engines: https://developers.llamaindex.ai/python/framework/module_guides/deploying/chat_engines/
- Persisting & loading: https://developers.llamaindex.ai/python/framework/module_guides/storing/save_load/
- Agents: https://developers.llamaindex.ai/python/framework/understanding/agent/
- LlamaHub: https://llamahub.ai/
