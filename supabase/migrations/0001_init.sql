-- Storage schema for the-abstract (objective.md §6): papers + their embedded chunks.
-- Embedding dimension (384) is tied to the configured model (BAAI/bge-small-en-v1.5);
-- changing the model means re-embedding and altering paper_chunks.embedding.

create extension if not exists vector;

create table papers (
    arxiv_id text primary key,
    entry_id text not null,
    title text not null,
    abstract text not null,
    authors jsonb not null,                      -- [{name, affiliation}]
    primary_category text not null,
    categories text[] not null,
    comment text,
    journal_ref text,
    doi text,
    published timestamptz not null,
    updated timestamptz not null,
    pdf_url text not null,
    full_text text,
    topics text[] not null default '{}',
    classification_label text not null default 'useful',
    classification_rationale text,
    summary_short text,
    summary_long text,
    summary_conclusions text,
    created_at timestamptz not null default now()
);
create index papers_published_idx on papers (published);
create index papers_categories_idx on papers using gin (categories);

create table paper_chunks (
    id bigint generated always as identity primary key,
    arxiv_id text not null references papers (arxiv_id) on delete cascade,
    chunk_index int not null,
    content text not null,
    embedding vector(384) not null,
    unique (arxiv_id, chunk_index)
);
create index paper_chunks_arxiv_id_idx on paper_chunks (arxiv_id);
create index paper_chunks_embedding_idx on paper_chunks using hnsw (embedding vector_cosine_ops);

-- RLS: the backend writes via the table-owner role (bypasses RLS); the future Q&A SPA reads
-- via the anon/publishable key, so expose read-only access. Papers are public arXiv content.
alter table papers enable row level security;
alter table paper_chunks enable row level security;
create policy "public read papers" on papers for select to anon, authenticated using (true);
create policy "public read chunks" on paper_chunks for select to anon, authenticated using (true);
