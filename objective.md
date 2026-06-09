# arXiv ML Digest
**Open Source Project — Feature Specification**
*v0.1 Draft · May 2026*

---

## Overview

arXiv ML Digest is a weekly automated pipeline that ingests machine learning papers from arXiv, filters and classifies them using AI, generates structured summaries, stores everything in a searchable database, and distributes personalized HTML email digests to subscribers.

---

## 1. Paper Ingestion

### 1.1 Sources

The system reads papers from arXiv on a weekly schedule, covering all categories relevant to machine learning and applied mathematics:

- cs.LG — Machine Learning
- cs.CL — Computation and Language
- cs.CV — Computer Vision and Pattern Recognition
- cs.AI — Artificial Intelligence
- cs.NE — Neural and Evolutionary Computing
- stat.ML — Statistics / Machine Learning
- math.OC — Optimization and Control
- math.ST — Statistics Theory

The category list is configurable.

### 1.2 Scope

The ingestion collects all new submissions from the target week — including new papers and cross-listed entries. Revisions of previously ingested papers are not re-processed.

---

## 2. AI Classification: Useful vs. Noise

### 2.1 Purpose

Given the volume of weekly arXiv submissions (hundreds to thousands across target categories), a classification step is applied before any expensive processing. Only papers flagged as "useful" proceed to full parsing and summarization.

### 2.2 Classification Input

The classifier receives only lightweight metadata per paper:

- Title
- Abstract
- Author names and affiliations (when available)

### 2.3 Classification Criteria

The AI evaluates papers using the following signals, weighted holistically:

- Recognized authors or labs (e.g. DeepMind, Meta AI, Google Brain, top academic groups)
- Strong or surprising empirical claims in the abstract
- Novel architectural or theoretical contributions
- Clear real-world applicability or downstream impact
- Reproducible and well-scoped experiments
- Unusual or provocative framing worth attention

Papers that appear to be incremental extensions, narrow domain applications with no broader relevance, or workshop papers with no novel contribution are typically marked as noise. The bar is intentionally permissive — borderline papers lean toward "useful".

### 2.4 Output

Each paper is assigned one of two labels:

- `useful` — proceed to full parsing and summarization
- `noise` — discard, not stored beyond the classification record

---

## 3. Full Paper Parsing

### 3.1 Scope

Only papers classified as "useful" are fully parsed. The parser processes the PDF source of the paper.

### 3.2 Extracted Content

- Full text of the paper
- Images, figures, and diagrams (extracted and stored with captions)
- Tables
- References

Parsed content is stored in the database and associated with the paper record for future retrieval.

---

## 4. Categorization

### 4.1 Category List

Each useful paper is assigned one or more topic categories from a predefined list maintained by the project owner. Examples:

- LLMs
- Diffusion Models
- Graph Neural Networks
- Reinforcement Learning
- Computer Vision
- Multimodal
- Agents
- Reasoning
- Optimization
- Theory
- Efficient ML
- Safety & Alignment
- Benchmarks

### 4.2 Multi-label

A paper can belong to multiple categories simultaneously. For example, a paper on a graph-based diffusion model would be tagged as both *Diffusion Models* and *Graph Neural Networks*.

### 4.3 Assignment

Categories are assigned automatically by the AI based on the abstract and full text. The category list is defined and maintained manually by the project owner — it is not auto-generated.

---

## 5. Summarization

### 5.1 Short Summary

2–3 concise bullet points (one to two sentences each) covering the key contributions and findings. Intended for quick scanning in the digest email.

### 5.2 Long Summary

A detailed summary of approximately 2 paragraphs covering methodology, results, and implications. Intended for readers who want more context before deciding to read the full paper.

### 5.3 Conclusions

Both summary types include a brief conclusions section highlighting the paper's significance and potential impact within the field.

---

## 6. Storage & Retrieval

### 6.1 What Is Stored

For every useful paper, the system persists:

- Metadata (title, authors, arXiv ID, submission date, categories)
- Classification result and rationale
- Full parsed text, images, tables
- Short and long summaries
- Embeddings for semantic search

### 6.2 Retention

Papers are stored indefinitely. There is no automatic pruning or expiry policy.

### 6.3 Question & Answer Interface

> **Status: deferred — not implemented.** RAG Q&A needs server-side LLM calls, which would require hosting a backend. To keep the stack free and serverless (Vercel static SPA + Supabase), the app ships browse-only for now; the `paper_chunks` embeddings remain in the DB so this can be added later (e.g. as a serverless function).

Subscribers could ask natural language questions against the full paper database via the web application, using retrieval-augmented generation (RAG) to find relevant content and generate answers.

Query filtering options:

- By category (e.g. "only Diffusion Models papers")
- By paper title or arXiv ID
- By date range

Questions can span multiple papers or be directed at a single paper.

---

## 7. Weekly Email Digest

### 7.1 Schedule

One digest email is sent per week on a fixed day. The specific day of the week is configurable.

### 7.2 Format

The email is HTML-formatted. For each useful paper it includes:

- Title and authors
- Assigned categories (as tags)
- Short summary (3–4 bullets)
- Link to the arXiv page
- Link to the paper's page in the web app

### 7.3 Distribution

The digest is sent to a mailing list of subscribers. All subscribers receive the same base digest unless personalization preferences are configured (see Section 8).

### 7.4 Content

Only papers classified as "useful" appear in the digest. Noise papers are never included.

---

## 8. Personalization

### 8.1 Per-Subscriber Preferences

Each subscriber can optionally configure personal preferences to receive a customized version of the digest. Preferences may include:

- Preferred categories (e.g. "I only want LLMs and Reasoning")
- Excluded categories (e.g. "skip Computer Vision")
- Interest keywords or topics expressed in natural language

### 8.2 Personalized Digest

When preferences are configured, the subscriber's email digest is filtered and/or re-ranked to surface the most relevant papers for them. Papers outside their scope may be omitted or shown in a reduced "other notable papers" section.

### 8.3 Configuration

The mechanism for setting preferences (web UI, config file, command, etc.) is to be defined during implementation. This document specifies the feature at the product level only.

---

## 9. Web Application

A static single-page app (Vite + React) that reads Supabase directly via the public anon key — no API server. It hosts on Vercel for free.

### 9.1 Access

Public, read-only. No per-user authentication; the anon key is gated by row-level security to read-only access over public arXiv-derived data.

### 9.2 Capabilities

- Search and browse all stored papers
- Filter by category, date, or keyword
- View full summaries (short and long) for any paper
- Subscribe to the weekly email digest (footer form → Supabase, anon insert-only)
- _Deferred:_ natural-language Q&A over the database (see §6.3) and extracted figures/tables

---

## Feature Summary

| Feature | Description | Notes |
|---|---|---|
| Ingestion | Weekly arXiv pull | Configurable categories |
| Classification | AI — useful vs. noise | Abstract + authors |
| Parsing | Full PDF parse | Text, images, tables |
| Categorization | Multi-label tagging | Predefined list |
| Summarization | Short (3–4 bullets) + Long (2 paragraphs) | With conclusions |
| Storage | Indefinite, full content | Embeddings for RAG |
| Email digest | Weekly HTML email | Mailing list |
| Personalization | Per-subscriber filters | Categories + keywords |
| Web app | Browse/filter the digest | Static SPA reading Supabase; Vercel + Supabase, free |
| Q&A (RAG) | Natural-language questions | Deferred — needs a server |

---

*This document covers product-level features only. Implementation details, technology choices, and architecture are out of scope.*
