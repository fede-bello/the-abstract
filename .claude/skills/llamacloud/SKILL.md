---
name: llamacloud
description: >-
  Use LlamaCloud — the hosted document-AI platform from LlamaIndex — in Python:
  LlamaParse (parse complex PDFs/DOCX/PPTX/images to clean Markdown/JSON),
  LlamaExtract (schema-driven structured extraction from invoices, resumes,
  contracts), and LlamaCloud managed Index/retrieval pipelines. Covers the new
  `llama-cloud` v2 SDK (`LlamaCloud` client) AND the classic `llama-cloud-services`
  API (`LlamaParse`, `LlamaExtract`, `LlamaCloudIndex`). Use this skill WHENEVER the
  user wants to parse/OCR documents for RAG, extract structured data from documents
  with a schema, build a managed/hosted retrieval index, or mentions LlamaParse,
  LlamaExtract, LlamaCloudIndex, `LLAMA_CLOUD_API_KEY`, or `result_type="markdown"` —
  even if they just say "parse this PDF for my RAG pipeline" or "pull fields out of
  these invoices." For local indexing/RAG use the llamaindex-framework skill.
---

# LlamaCloud (Python)

LlamaCloud is LlamaIndex's **managed, agentic document-processing platform**. Three
products:

- **LlamaParse** — GenAI-native parser/OCR. Complex PDFs, DOCX, PPTX, XLSX, images
  (130+ formats) → clean Markdown/text/JSON optimized for LLMs/RAG. Strong on tables,
  multi-column layouts, charts, scanned docs.
- **LlamaExtract** — schema-driven structured extraction (give it a Pydantic/JSON
  schema, get typed JSON back) — invoices, resumes, contracts.
- **LlamaCloud Index** — fully managed ingestion + vector index + hybrid retrieval +
  reranking, exposed as a LlamaIndex `LlamaCloudIndex`.

## ⚠️ Two SDK generations — choose deliberately

| | New SDK (v2) — **prefer for new code** | Classic SDK — **fallback / most existing code** |
|---|---|---|
| Package | `llama-cloud` (v2.x) | `llama-cloud-services` (v0.6.x) |
| Client | `from llama_cloud import LlamaCloud` | `from llama_cloud_services import LlamaParse, LlamaExtract, LlamaCloudIndex` |
| API | LlamaParse/Extract **v2** | v1 |
| Style | Lower-level: explicit upload → job → poll/expand | Ergonomic helpers (`result_type`, `file_extractor`, `create_agent`) |
| Status | Actively developed | **Legacy/EOL — maintained only through May 1, 2026**; still works but unmaintained |

**Default to v2 (`llama-cloud`) for new projects.** Reach for the classic
`llama-cloud-services` API when (a) editing an existing codebase that already uses
it, or (b) you need the smooth LlamaIndex framework integration (`file_extractor`
dict, `LlamaCloudIndex.from_documents`, `create_agent`) — those ergonomics are
unmatched in v2. The two APIs are **not drop-in compatible** (v2 uses tiers; v1 uses
flags like `premium_mode`). Don't mix them in one flow.

## Authentication

One key for everything: **`LLAMA_CLOUD_API_KEY`** (format `llx-...`). Get it at
https://cloud.llamaindex.ai/api-key. All SDKs read the env var automatically; you can
also pass `api_key=`.

```bash
export LLAMA_CLOUD_API_KEY="llx-..."
```

Resources live under a project (default `"default"`); index/extract calls accept
`project_name=` / `project_id=`.

---

## LlamaParse

### v2 (new SDK — recommended)

```bash
pip install "llama-cloud>=2.1"
```
```python
from llama_cloud import LlamaCloud

client = LlamaCloud()  # reads LLAMA_CLOUD_API_KEY

file = client.files.create(file="./document.pdf", purpose="parse")
result = client.parsing.parse(
    file_id=file.id,
    tier="agentic",        # "fast" | "cost_effective" | "agentic" | "agentic_plus"
    version="latest",
    expand=["markdown"],   # request only what you need: text/markdown/items/images...
)
print(result.markdown.pages[0].markdown)
```

**Tiers** (replace v1's `premium_mode`/multimodal flags): `fast` (plain text,
cheapest) → `cost_effective` → `agentic` (recommended default for visually rich
content) → `agentic_plus` (max accuracy, dense financial/scientific layouts). Use
`AsyncLlamaCloud` for async. v2 groups options into `input_options`/`output_options`/
`processing_options` (e.g. OCR languages → `processing_options={"ocr_parameters":
{"languages": ["fr"]}}`). Field names like `expand`/`output_options` are evolving —
double-check against the live API reference if something doesn't resolve.

### Classic (`llama-cloud-services` — most existing code, best framework integration)

```bash
pip install llama-cloud-services   # provides `from llama_cloud_services import LlamaParse`
```
```python
from llama_cloud_services import LlamaParse

parser = LlamaParse(
    result_type="markdown",   # "markdown" | "text"
    num_workers=4,
    verbose=True,
)
documents = parser.load_data("./my_file.pdf")        # -> list[Document]
# Async (needs nest_asyncio.apply() in notebooks/running loops):
# documents = await parser.aload_data("./my_file.pdf")
```

Key classic options:
```python
parser = LlamaParse(
    result_type="markdown",
    language="en",                                   # OCR language hint
    parsing_instruction="Financial report; preserve all tables as markdown.",
    premium_mode=True,                               # best accuracy (costlier)
    # or multimodal:
    use_vendor_multimodal_model=True,
    vendor_multimodal_model_name="anthropic-sonnet-3.5",
)
```

**Canonical RAG ingestion pattern** — plug the parser into `SimpleDirectoryReader` as
a `file_extractor` (classic only):
```python
from llama_index.core import SimpleDirectoryReader

parser = LlamaParse(result_type="markdown")
documents = SimpleDirectoryReader(
    "./data", file_extractor={".pdf": parser}
).load_data()
```

JSON result mode (per-page layout, bounding boxes, images):
```python
json_objs = parser.get_json_result("./my_file.pdf")   # list of dicts, one per file
pages = json_objs[0]["pages"]
images = parser.get_images(json_objs, download_path="./images")
```

---

## LlamaExtract

### v2 (new SDK)

```python
from pydantic import BaseModel, Field
from llama_cloud import LlamaCloud

class Resume(BaseModel):
    name: str = Field(description="Full name")
    email: str | None = Field(default=None, description="Email address")
    skills: list[str] = Field(description="Technical skills")

client = LlamaCloud()
file_obj = client.files.create(file="resume.pdf", purpose="extract")
job = client.extract.create(
    file_input=file_obj.id,                      # or a prior parse_job.id — no re-upload
    configuration={
        "data_schema": Resume.model_json_schema(),
        "extraction_target": "per_doc",          # or "per_page"
        "tier": "agentic",
    },
)

import time
while job.status not in ("COMPLETED", "FAILED", "CANCELLED"):
    time.sleep(2)
    job = client.extract.get(job.id)
print(job.extract_result)
```

`client.extract.generate_schema(...)` auto-creates a schema from a prompt or sample.

### Classic (`create_agent` pattern)

```python
from pydantic import BaseModel, Field
from llama_cloud_services import LlamaExtract
from llama_cloud_services.types import ExtractConfig

class Resume(BaseModel):
    name: str = Field(description="Full name of the candidate")
    email: str | None = Field(default=None, description="Email address")
    skills: list[str] = Field(description="Technical skills")

extractor = LlamaExtract()  # reads LLAMA_CLOUD_API_KEY
agent = extractor.create_agent(
    name="resume-parser",
    data_schema=Resume,                              # Pydantic model OR a JSON Schema dict
    config=ExtractConfig(extraction_mode="BALANCED", extraction_target="PER_DOC"),
)
result = agent.extract("resume.pdf")
print(result.data)                                   # dict matching the schema
# Reusable: extractor.get_agent(name="resume-parser") to reconnect.
# Async/batch: agent.queue_extraction("resume.pdf") -> poll the ExtractJob.
```

**Schema design tip (both SDKs):** make fields that may be absent `Optional`/`| None`
— required fields force the model to hallucinate when data is missing. Use
`Field(description=...)` to embed formatting rules. Deeply nested/huge schemas degrade
accuracy.

---

## LlamaCloud Index / managed retrieval

The classic `LlamaCloudIndex` (re-exported from `llama_cloud_services`) is the
smoothest path for RAG apps; the v2 equivalent is `client.indexes.*`.

```python
import os
os.environ["LLAMA_CLOUD_API_KEY"] = "llx-..."
from llama_cloud_services import LlamaCloudIndex, LlamaCloudRetriever
from llama_index.core import SimpleDirectoryReader

# Create from documents (server-side ingest/embed/store):
documents = SimpleDirectoryReader("./data").load_data()
index = LlamaCloudIndex.from_documents(documents, "my_first_index", project_name="default")

# Or connect to an existing (already-ingested) index:
index = LlamaCloudIndex("my_first_index", project_name="default")

# Hybrid retrieval + reranking:
retriever = index.as_retriever(
    dense_similarity_top_k=5,
    sparse_similarity_top_k=5,
    alpha=0.5,                 # 1.0 = pure dense, 0.0 = pure sparse
    enable_reranking=True,
    rerank_top_n=3,
)
nodes = retriever.retrieve("What was Q3 revenue?")

query_engine = index.as_query_engine(llm=llm)   # plug any LlamaIndex LLM
chat_engine = index.as_chat_engine(llm=llm)
```

## Common patterns

**Parse → index RAG pipeline:**
```python
from llama_cloud_services import LlamaParse
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex

parser = LlamaParse(result_type="markdown")
docs = SimpleDirectoryReader("./data", file_extractor={".pdf": parser}).load_data()
index = VectorStoreIndex.from_documents(docs)         # local index
# or push to managed retrieval: LlamaCloudIndex.from_documents(docs, "idx")
```

**Structured extraction from invoices/resumes:** define a Pydantic schema with
optional fields → `create_agent` (classic) or `extract.create` (v2) → run over docs.

**Complex PDFs with tables:** `result_type="markdown"` + a `parsing_instruction` to
preserve tables; escalate to `premium_mode=True` (classic) / `tier="agentic_plus"`
(v2) for dense layouts; JSON result mode when you need bounding boxes/images.

## Pitfalls checklist

- **Async in notebooks/servers:** classic SDK needs `nest_asyncio.apply()` before
  awaiting in an already-running loop (Jupyter, FastAPI), or you get "event loop
  already running."
- **Everything is a remote async job.** For big batches use async clients + a
  `Semaphore` (and `num_workers` on the classic parser), not serial loops. v2 makes
  the upload→job→poll lifecycle explicit.
- **Credits/pricing.** Usage is metered; `premium_mode`/multimodal (classic) and
  `agentic_plus` (v2) cost materially more per page than `fast`/`cost_effective`.
  Warn before recommending premium modes on large corpora.
- **Rate limits / file size.** Handle 429s with backoff; chunk very large files. Jobs
  can take minutes for big/complex docs.
- **Extract schema:** prefer optional fields; it's JSON Schema under the hood
  (Pydantic is sugar).
- **Version mismatch:** `llama-cloud-services` = v1 API; `llama-cloud` = v2 only. Not
  drop-in compatible — don't mix in one flow.

## Key docs

- Migration blog (v2 SDK + Parse API v2 — essential): https://www.llamaindex.ai/blog/announcing-new-llamacloud-sdks-and-parse-api-v2
- LlamaParse getting started: https://developers.llamaindex.ai/python/cloud/llamaparse/getting_started
- Parsing modes: https://docs.cloud.llamaindex.ai/llamaparse/parsing/parsing_modes
- LlamaExtract getting started + SDK: https://developers.llamaindex.ai/python/cloud/llamaextract/getting_started/
- LlamaExtract schema design: https://docs.cloud.llamaindex.ai/llamaextract/features/schema_design
- LlamaCloudIndex + Retriever: https://developers.llamaindex.ai/python/framework/module_guides/indexing/llama_cloud_index/
- GitHub: https://github.com/run-llama/llama-cloud-py (new) · https://github.com/run-llama/llama_cloud_services (classic)
